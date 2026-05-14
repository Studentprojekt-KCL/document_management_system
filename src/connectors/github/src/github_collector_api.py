"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

GitHub connector API following the same route contract as the GitLab connector.
"""

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
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from interfacer_github import GitHub

from shared_functions.dmis_logger import dms_info
from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.signing_tools import sign_encode_state, validate_decode_state


class API:
    """Management class for GitHub connector API."""

    app = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.github_instance = GitHub()
        self.client_id = read_env_variable("CONGITHUB_CLIENT_ID")
        self.client_secret = read_env_variable("CONGITHUB_CLIENT_SECRET")
        self.state_secret = read_env_variable("CONGITHUB_STATE_SIGNING_SECRET")
        self.github_base_url = read_env_variable("CONGITHUB_GITHUB_BASE_URL").rstrip("/")

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/defined_fields", self.defined_fields_route, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])
        self.app.add_api_route("/auth_user", self.auth_user, methods=["GET"])
        self.app.add_api_route("/callback", self.callback, methods=["GET"])
        self.app.add_api_route("/refresh_token", self.refresh_token, methods=["GET"])
        self.app.add_api_route("/validate_token", self.validate_token, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def get_files(
        self,
        file_pointers: dict[str, list],
        include_content: bool = False,
        include_last_edit_date: bool = True,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> Any:
        """Fetch specific files by pointer."""
        token = x_github_token.removeprefix("Bearer ").strip() if x_github_token else None
        return self.github_instance.get_files(
            file_pointers.get("file_pointers", []), include_content, include_last_edit_date, token
        )

    async def defined_fields_route(self) -> list[str]:
        """Field keys compatible with gateway ``retrieve_defined_fields`` union (matches GitLab contract)."""
        return list(self.github_instance.defined_fields.keys())

    @staticmethod
    def _strip_github_token(header: str | None) -> str | None:
        return header.removeprefix("Bearer ").strip() if header else None

    async def stream_files_to_index(
        self,
        body: dict[str, str | None] | None = None,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> StreamingResponse:
        """Stream NDJSON: subdata line then one JSON object per file — POST + body shape as GitLab (``{"subdata": ...}``)."""
        subdata: str | None = body.get("subdata") if isinstance(body, dict) else None
        token = self._strip_github_token(x_github_token)
        return StreamingResponse(
            self.github_instance.stream_files_to_index(subdata, token),
            media_type="application/octet-stream",
        )

    def auth_user(self, request: Request) -> RedirectResponse:
        """Redirect the user to GitHub OAuth authorization."""
        payload = {"nonce": secrets.token_urlsafe(16), "iat": int(time.time())}
        signed_state = sign_encode_state(payload, self.state_secret)
        params = {
            "client_id": self.client_id,
            "redirect_uri": str(request.url_for("callback")),
            "state": signed_state,
        }
        return RedirectResponse(f"{self.github_base_url}/login/oauth/authorize?{urlencode(params)}")

    async def callback(self, request: Request, code: str | None = None) -> JSONResponse:
        """Exchange GitHub authorization code for access and refresh tokens."""
        setup_action = request.query_params.get("setup_action")

        if setup_action == "request":
            return JSONResponse(content={"message": "Installation requested, pending admin approval."}, status_code=200)

        if setup_action != "install":
            signed_state = request.query_params.get("state")
            if signed_state is None:
                dms_info("No state returned from GitHub when trying to authenticate a user.")
                return JSONResponse(content="ERROR", status_code=403)
            validation_status, _ = validate_decode_state(signed_state, self.state_secret)
            if not validation_status:
                return JSONResponse(content="ERROR", status_code=403)

        token_url = f"{self.github_base_url}/login/oauth/access_token"
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": str(request.url_for("callback")),
                },
                headers={"Accept": "application/json"},
                timeout=120,
            )
        token_json = token_resp.json()
        if not token_json.get("access_token"):
            return JSONResponse(content="ERROR", status_code=400)
        return JSONResponse(content=token_json, status_code=200)

    async def refresh_token(self, refresh_token: Annotated[str | None, Header()] = None) -> JSONResponse:
        """Refresh a GitHub access token using a refresh token."""
        token_url = f"{self.github_base_url}/login/oauth/access_token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Accept": "application/json"},
                timeout=120,
            )
        return JSONResponse(content=response.json(), status_code=200)

    async def validate_token(self, x_github_token: str | None = Header(default=None, alias="X-GitHub-Token")) -> JSONResponse:
        """Validate token access.

        Args:
            x_github_token: token
        returns: true / false
        """
        return JSONResponse(content={"valid": await self.github_instance.verify_token(x_github_token)}, status_code=200)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = read_port("CONGITHUB_BIND_PORT")
    host = read_env_variable("CONGITHUB_BIND_ADDR")

    uvicorn.run(api.app, host=host, log_level=api.log_level, port=port)
