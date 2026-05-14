"""FastAPI service for the Confluence connector."""

import argparse
import secrets
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar
from urllib.parse import urlencode

import httpx
import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from shared_functions.initialisation_tools import read_port, read_env_variable
from shared_functions.signing_tools import sign_encode_state, validate_decode_state

from .interfacer_confluence import ConfluenceInterfacer, GetFilesInput


class GetFilesBody(BaseModel):
    """JSON body for ``POST /get_files``."""

    file_pointers: list[str] = Field(default_factory=list)
    include_content: bool = False
    include_last_edit_date: bool = True


@dataclass(frozen=True, slots=True)
class _OAuthConfig:
    client_id: str
    client_secret: str
    state_secret: str
    auth_url: str
    token_url: str
    scopes: str


class API:
    """Management class for Confluence connector API."""

    app: ClassVar[FastAPI]
    log_level: str | None = None

    def __init__(self) -> None:
        self.confluence_instance = ConfluenceInterfacer()
        self.oauth = _OAuthConfig(
            client_id=read_env_variable("CONCONFLUENCE_CLIENT_ID"),
            client_secret=read_env_variable("CONCONFLUENCE_CLIENT_SECRET"),
            state_secret=read_env_variable("CONCONFLUENCE_STATE_SIGNING_SECRET"),
            auth_url=read_env_variable("CONCONFLUENCE_AUTH_URL"),
            token_url=read_env_variable("CONCONFLUENCE_TOKEN_URL"),
            scopes=read_env_variable("CONCONFLUENCE_SCOPES"),
        )
        self.auth_callback_url = read_env_variable("CONCONFLUENCE_CONNECT_SERVICE_CALLBACK")
        session = self.confluence_instance.session

        @asynccontextmanager
        async def _lifespan(_: FastAPI) -> AsyncGenerator:
            yield
            await session.aclose()

        API.app = FastAPI(lifespan=_lifespan)
        API.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        API.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        API.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])
        API.app.add_api_route("/defined_fields", self.defined_fields_route, methods=["GET"])
        API.app.add_api_route("/auth_user", self.auth_user, methods=["GET"])
        API.app.add_api_route("/callback", self.callback, methods=["GET"])
        API.app.add_api_route("/refresh_token", self.refresh_token, methods=["GET"])

    def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
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

    def defined_fields_route(self) -> list[str]:
        """Field keys for gateway ``retrieve_defined_fields`` union."""
        return list(self.confluence_instance.defined_fields.keys())

    async def get_files(
        self,
        body: GetFilesBody,
        x_confluence_token: Annotated[str | None, Header()] = None,
    ) -> list[dict[str, Any]]:
        """Batch fetch pages by pointers (DMS ``POST /get_files``)."""
        if x_confluence_token is None:
            return []
        return await self.confluence_instance.get_files(
            GetFilesInput(
                file_pointers=body.file_pointers,
                include_content=body.include_content,
                include_last_edit_date=body.include_last_edit_date,
                api_token=x_confluence_token,
            )
        )

    def stream_files_to_index(
        self,
        body: dict[str, str] | None = None,
        x_confluence_token: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        """Stream NDJSON: first line is subdata checkpoint, then one page object per line.
        Body should be structured {'subdata': <SUBDATA>}."""

        subdata: str | None = body.get("subdata") if isinstance(body, dict) else None

        async def stream() -> Any:
            async for chunk in self.confluence_instance.stream_files_to_index(subdata, x_confluence_token):
                yield chunk

        return StreamingResponse(stream(), media_type="application/octet-stream")

    def auth_user(self) -> RedirectResponse:
        """Redirect user to Atlassian OAuth login."""
        payload = {"nonce": secrets.token_urlsafe(16), "iat": int(time.time())}
        signed_state = sign_encode_state(payload, self.oauth.state_secret)
        params = {
            "client_id": self.oauth.client_id,
            "redirect_uri": self.auth_callback_url,
            "response_type": "code",
            "scope": self.oauth.scopes.replace(",", " "),
            "audience": "api.atlassian.com",
            "state": signed_state,
        }

        return RedirectResponse(f"{self.oauth.auth_url}?{urlencode(params)}")

    async def callback(self, request: Request, code: str | None = None) -> JSONResponse:
        """Exchange Atlassian authorization code for access and refresh tokens."""
        signed_state = request.query_params.get("state")
        if not signed_state:
            return JSONResponse(content="ERROR", status_code=403)

        valid, _ = validate_decode_state(signed_state, self.oauth.state_secret)
        if not valid:
            return JSONResponse(content="ERROR", status_code=403)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.oauth.token_url,
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.oauth.client_id,
                    "client_secret": self.oauth.client_secret,
                    "code": code,
                    "redirect_uri": self.auth_callback_url,
                },
                timeout=120,
            )

        token_json = resp.json()
        if not token_json.get("access_token"):
            return JSONResponse(content="ERROR", status_code=400)
        return JSONResponse(content=token_json, status_code=200)

    async def refresh_token(
        self,
        refresh_token: Annotated[str | None, Header(alias="refresh-token")] = None,
    ) -> JSONResponse:
        """Refresh an Atlassian access token using a refresh token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.oauth.token_url,
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.oauth.client_id,
                    "client_secret": self.oauth.client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=120,
            )
        return JSONResponse(content=resp.json(), status_code=200)


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
