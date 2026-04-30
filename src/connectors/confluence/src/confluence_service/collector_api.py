"""FastAPI service for the Confluence connector.

Routes follow the student DMS GitLab connector shape: ``/index_needed_bool``,
``/get_files`` (POST), ``/files_to_index`` (prefers MinIO ``file_url``, else inline
``files``), ``/stream_files_to_index``, ``/connected_source_systems``. Legacy GET
``/files``, ``/file``, and ``/files_to_index`` behaviour remain available.

Authenticate with ``X-Confluence-Email`` and ``X-Confluence-Token`` (or env vars read by
``ConfluenceInterfacer``). Requires ``CONFLUENCE_CONNECTOR_PORT`` and ``CONFLUENCE_ADDRESS``;
optional MinIO env vars for uploads.
"""

import argparse
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from shared_functions.boto_tools import upload_file
from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_port

from .interfacer_confluence import ConfluenceInterfacer, GetFilesInput

# When compose interpolates unset ${CONFLUENCE_CONNECTOR_PORT} to "", it overrides Dockerfile ENV;
# treat blank like unset so preview stacks still boot (override per env in real deployments).
_CONF_PORT_FALLBACK = 8010


class GetFilesBody(BaseModel):
    """JSON body for ``POST /get_files``."""

    file_pointers: list[str] = Field(default_factory=list)
    include_content: bool = False
    include_last_edit_date: bool = True


class API:
    """Management class for Confluence connector API."""

    log_level: str | None = None

    def __init__(self) -> None:
        self.confluence_instance = ConfluenceInterfacer()
        self.app = FastAPI(lifespan=self.lifespan)
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        # Legacy (same as older GitLab connector in this repo)
        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        # DMS-aligned routes
        self.app.add_api_route("/index_needed_bool", self.index_needed_bool, methods=["GET"])
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncGenerator:
        """Handle startup and shutdown lifecycle for the API."""
        yield
        await self.confluence_instance.session.aclose()

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Return a JSON error payload for FastAPI request validation failures."""
        errors: dict[str, Any]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, Any] = "ERROR"
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        return JSONResponse(status_code=422, content=content)

    @staticmethod
    def _token(x_confluence_token: str | None) -> str | None:
        if x_confluence_token is None:
            return None
        return x_confluence_token.removeprefix("Bearer ").strip()

    async def files(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> Any:
        """Return file pointers for incremental indexing (honours ``subdata`` checkpoint)."""
        if x_confluence_email is None or x_confluence_token is None:
            return {"subdata": subdata, "file_pointers": []}
        token = self._token(x_confluence_token)
        return await self.confluence_instance.pointers_to_all_files_to_index(subdata, x_confluence_email.strip(), token)

    async def file(
        self,
        file_pointer: str,
        include_content: bool = True,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> Any:
        """Return one page as metadata plus optional base64-encoded plain text."""
        if x_confluence_email is None or x_confluence_token is None:
            return {}
        token = self._token(x_confluence_token)
        return await self.confluence_instance.get_page(file_pointer, include_content, x_confluence_email.strip(), token)

    async def index_needed_bool(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> dict[str, Any]:
        """Whether a new index run has work (DMS ``/index_needed_bool``)."""
        if x_confluence_email is None or x_confluence_token is None:
            return {"index_needed": False}
        token = self._token(x_confluence_token)
        return await self.confluence_instance.check_index_needed(subdata, x_confluence_email.strip(), token)

    async def get_files(
        self,
        body: GetFilesBody,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> list[dict[str, Any]]:
        """Batch fetch pages by pointers (DMS ``POST /get_files``)."""
        if x_confluence_email is None or x_confluence_token is None:
            return []
        token = self._token(x_confluence_token)
        return await self.confluence_instance.get_files(
            GetFilesInput(
                file_pointers=body.file_pointers,
                include_content=body.include_content,
                include_last_edit_date=body.include_last_edit_date,
                email=x_confluence_email.strip(),
                api_token=token,
            )
        )

    async def stream_files_to_index(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> StreamingResponse:
        """Stream JSON chunks of pages to index (DMS ``/stream_files_to_index``)."""
        token = self._token(x_confluence_token) if x_confluence_email and x_confluence_token else None
        email = x_confluence_email.strip() if x_confluence_email else None

        async def stream() -> Any:
            async for chunk in self.confluence_instance.stream_files_to_index(subdata, email, token):
                yield chunk

        return StreamingResponse(stream(), media_type="application/octet-stream")

    async def files_to_index(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> dict[str, Any]:
        """Full payload; prefers upload URL like DMS GitLab ``/files_to_index``."""
        if x_confluence_email is None or x_confluence_token is None:
            return {
                "subdata": subdata,
                "files": [],
                "deleted": [],
                "index_needed": False,
            }
        tok = self._token(x_confluence_token)
        content = await self.confluence_instance.files_to_index(subdata, x_confluence_email.strip(), tok)
        try:
            url = upload_file(content, "confluence_content.json")
            return {
                "subdata": content.get("subdata"),
                "index_needed": content.get("index_needed"),
                "file_url": url,
            }
        except (OSError, ValueError) as err:
            dms_warning(f"Could not upload confluence payload to object storage: {err}")
            return {
                "subdata": content.get("subdata"),
                "index_needed": content.get("index_needed"),
                "files": content.get("files", []),
                "deleted": content.get("deleted", []),
            }


def run() -> None:
    """Start Confluence connector API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"
    port = read_port("CONFLUENCE_CONNECTOR_PORT")
    uvicorn.run(api.app, host="0.0.0.0", log_level=api.log_level, port=port)
