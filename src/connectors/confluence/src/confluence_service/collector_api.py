"""FastAPI service for the Confluence connector.

Authenticate with ``X-Confluence-Email`` and ``X-Confluence-Token`` (or env vars read by
``ConfluenceInterfacer``). Requires ``CONFLUENCE_CONNECTOR_PORT`` and ``CONFLUENCE_ADDRESS``;
optional MinIO env vars for uploads.
"""

import argparse
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from shared_functions.initialisation_tools import read_port, read_env_variable

from .interfacer_confluence import ConfluenceInterfacer, GetFilesInput


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

        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])

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
        body: dict[str, str] | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> StreamingResponse:
        """Endpoint retrieving a pointer to a JSON file containing all content and metadata to index.
        Body should be structured {'subdata': <SUBDATA>}."""

        subdata: str | None = body.get("subdata") if isinstance(body, dict) else None

        token = self._token(x_confluence_token) if x_confluence_email and x_confluence_token else None
        email = x_confluence_email.strip() if x_confluence_email else None

        async def stream() -> Any:
            async for chunk in self.confluence_instance.stream_files_to_index(subdata, email, token):
                yield chunk

        return StreamingResponse(stream(), media_type="application/octet-stream")


def run() -> None:
    """Start Confluence connector API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(
        api.app,
        host=read_env_variable("CONCONFLUENCE_BIND_ADDR"),
        log_level=api.log_level,
        port=read_port("CONCONFLUENCE_BIND_PORT"),
    )
