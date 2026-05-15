"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
import secrets
import time
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from interfacer_sharepoint import SharePoint

from shared_functions.dmis_logger import dms_info
from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.signing_tools import sign_encode_state, validate_decode_state

MS_LOGIN_BASE = "https://login.microsoftonline.com"


class API:
    """Management class for SharePoint connector API."""

    app = FastAPI()
    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.auth_callback_url = read_env_variable("CONSHAREPOINT_CONNECT_SERVICE_CALLBACK")
        self.tenant_id = read_env_variable("CONSHAREPOINT_TENANT_ID")
        self.client_id = read_env_variable("CONSHAREPOINT_CLIENT_ID")
        self.client_secret = read_env_variable("CONSHAREPOINT_CLIENT_SECRET")
        self.state_secret = read_env_variable("CONSHAREPOINT_STATE_SIGNING_SECRET")
        self.sharepoint_instance = SharePoint()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])
        self.app.add_api_route("/auth_user", self.auth_user, methods=["GET"])
        self.app.add_api_route("/callback", self.callback, methods=["GET"])
        self.app.add_api_route("/refresh_token", self.refresh_token, methods=["GET"])

    def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def get_files(
        self,
        file_pointers: dict[str, list],
        include_content: bool = False,
        include_last_edit_date: bool = True,
        x_sharepoint_token: Annotated[str | None, Header()] = None,
    ) -> Any:
        """Endpoint for retrieving specific files by pointer.
        Example request:
            curl -X 'POST' \
            '<HOST>/get_files?include_content=false&include_last_edit_date=true' \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
            "file_pointers": ["<FILE_PTR>"]
            }'
        """
        return await self.sharepoint_instance.get_files(
            file_pointers.get("file_pointers", []), x_sharepoint_token, include_content, include_last_edit_date
        )

    def stream_files_to_index(
        self, subdata: str | None = None, x_sharepoint_token: Annotated[str | None, Header()] = None
    ) -> StreamingResponse:
        """Endpoint streaming all qualifying documents for indexing."""
        return StreamingResponse(
            self.sharepoint_instance.stream_files_to_index(subdata, x_sharepoint_token),
            media_type="application/octet-stream",
        )

    def auth_user(self) -> JSONResponse:
        """Redirect user to Microsoft OAuth login."""
        payload = {"nonce": secrets.token_urlsafe(16), "iat": int(time.time())}
        signed_state = sign_encode_state(payload, self.state_secret)

        auth_url = f"{MS_LOGIN_BASE}/{self.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.auth_callback_url,
            "response_type": "code",
            "scope": "Sites.Read.All Files.Read.All offline_access",
            "state": signed_state,
        }

        return JSONResponse(content={"redirect": f"{auth_url}?{urlencode(params)}"})

    async def callback(self, request: Request, code: str | None = None) -> JSONResponse:
        """Exchange Microsoft authorization code for access and refresh tokens."""
        signed_state = request.query_params.get("state")
        if signed_state is None:
            dms_info("No state was returned from Microsoft when trying to authenticate a user.")
            return JSONResponse(content="ERROR", status_code=403)

        validation_status, _ = validate_decode_state(signed_state, self.state_secret)
        if not validation_status:
            return JSONResponse(content="ERROR", status_code=403)

        token_url = f"{MS_LOGIN_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(cookies={}) as client:
            token_resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.auth_callback_url,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=120,
            )

        token_json = token_resp.json()
        if not token_json.get("access_token"):
            return JSONResponse(content="ERROR", status_code=400)
        return JSONResponse(content=token_json, status_code=200)

    async def refresh_token(self, refresh_token: Annotated[str | None, Header()] = None) -> JSONResponse:
        """Refresh a Microsoft access token using a refresh token."""
        token_url = f"{MS_LOGIN_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(cookies={}) as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=120,
            )
        return JSONResponse(content=response.json(), status_code=200)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(
        api.app,
        host=read_env_variable("CONSHAREPOINT_BIND_ADDR"),
        log_level=api.log_level,
        port=read_port("CONSHAREPOINT_BIND_PORT"),
    )
