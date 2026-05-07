"""FastAPI service for the Confluence connector.

Authenticate with ``X-Confluence-Email`` and ``X-Confluence-Token`` (optional defaults via
env; see ``ConfluenceInterfacer``). ``GET /auth_user`` returns manual ``api_token`` metadata
(same route name as OAuth connectors; GitLab redirects, Confluence does not).

Server bind: ``CONCONFLUENCE_BIND_PORT`` / ``CONCONFLUENCE_BIND_ADDR`` (default ``0.0.0.0``).
Legacy port names ``CONFLUENCE_BIND_PORT`` / ``CONFLUENCE_CONNECTOR_PORT`` fill in when the DMIS-style
port env is unset.
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

from shared_functions.initialisation_tools import read_env_variable, read_port

from .interfacer_confluence import ConfluenceInterfacer, GetFilesInput

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

        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])
        self.app.add_api_route("/auth_user", self.auth_user, methods=["GET"])

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

    async def auth_user(self) -> JSONResponse:
        """Declare manual api-token auth (no OAuth redirect). Same ``/auth_user`` route as OAuth connectors (#478).

        Gateway may send extra headers for other connectors; this handler ignores them."""
        return JSONResponse(
            status_code=200,
            content={
                "type": "api_token",
                "method": "manual",
                "header_names": ["X-Confluence-Email", "X-Confluence-Token"],
                "labels": {
                    "X-Confluence-Email": "Confluence Email",
                    "X-Confluence-Token": "Confluence API Token",
                },
                "help_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
            },
        )

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

    def _port_digits(name: str) -> bool:
        val = os.environ.get(name)
        return isinstance(val, str) and bool(val.strip()) and val.strip().isdigit()

    if not _port_digits("CONCONFLUENCE_BIND_PORT"):
        for alt in ("CONFLUENCE_BIND_PORT", "CONFLUENCE_CONNECTOR_PORT"):
            val = os.environ.get(alt)
            if isinstance(val, str) and val.strip().isdigit():
                os.environ["CONCONFLUENCE_BIND_PORT"] = val.strip()
                break
        else:
            os.environ["CONCONFLUENCE_BIND_PORT"] = str(_CONF_PORT_FALLBACK)

    bind_primary = read_env_variable("CONCONFLUENCE_BIND_ADDR", required=False)
    legacy_bind = (os.environ.get("CONFLUENCE_BIND_ADDR") or "").strip()
    host_bind = (bind_primary.strip() if bind_primary else "") or legacy_bind or "0.0.0.0"

    uvicorn.run(
        api.app,
        host=host_bind,
        log_level=api.log_level,
        port=read_port("CONCONFLUENCE_BIND_PORT"),
    )
