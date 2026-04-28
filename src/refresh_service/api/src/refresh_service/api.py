"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

# Refresh service is not installed in pylint env.
from refresh_service.session_encryption_tools import SessionEncryption  # pylint: disable=E0611
from refresh_service.auth_token import authorize_and_get_token  # pylint: disable=E0611
from refresh_service.database import RedisDataBase  # pylint: disable=E0611
from refresh_service.token_refresh import insert_session  # pylint: disable=E0611

from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.dmis_logger import dms_warning


class RefreshService:
    """Refresh service API."""

    app = FastAPI()
    session_encryption: SessionEncryption

    def __init__(self, log_level: str | None = None):
        """Constructor."""
        self.log_level = log_level
        self.ad_issuer = read_env_variable("REFSERVICE_AD_URL")
        self.openid_connect_url = read_env_variable("REFSERVICE_AD_JWKS_URL")

        self.redis_database = RedisDataBase()
        self.session_enc = SessionEncryption(read_env_variable("REFSERVICE_SESSION_ENC_PASSW"))

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        self.app.add_api_route("/add_session", self.add_session, methods=["POST"])
        self.app.add_api_route("/get_session", self.get_session, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, Any] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def add_session(
        self, service_name: str, body: dict[Any, Any], authorization: str | None = Header(default=None)
    ) -> JSONResponse:
        """Store users session token for given service, body should be given as
        {"refresh_url": "<refresh_url>", "session_variables": <session_token>}."""
        refresh_url = body.get("refresh_url")
        session_variables = body.get("session_variables")
        if (str, dict) != (type(refresh_url), type(session_variables)):
            raise HTTPException(status_code=422)

        status, token_values = authorize_and_get_token(authorization, self.ad_issuer, self.openid_connect_url)
        if status is False:
            raise HTTPException(status_code=401)

        user = token_values.get("sub")
        if not isinstance(user, str):
            dms_warning(f"Recieded token with missing 'sub': {token_values}")
            raise HTTPException(status_code=400)
        if not isinstance(refresh_url, str):
            dms_warning(f"Recieved unexpected format for refresh_url key in request body: {body}")
            raise HTTPException(status_code=400)
        if not isinstance(session_variables, dict):
            dms_warning(f"Recieved unexpected format for session_variables key in request body: {body}")
            raise HTTPException(status_code=400)

        if insert_session(user, service_name, refresh_url, session_variables) is False:
            raise HTTPException(status_code=400)

        return JSONResponse(status_code=200, content={"status": "success"})

    async def get_session(self, service_name: str, authorization: str | None = Header(default=None)) -> dict | None:
        """Endpoint for retrieving single sesison token for specified service."""
        status, token_values = authorize_and_get_token(authorization, self.ad_issuer, self.openid_connect_url)
        if status is False:
            raise HTTPException(status_code=401)

        user = token_values.get("sub")
        if not isinstance(user, str):
            dms_warning(f"Recieded token with missing 'sub': {token_values}")
            raise HTTPException(status_code=400)

        content = self.redis_database.get_session_token(user, service_name)[0]
        return self.session_enc.decrypt_session_variables(content).get("access_token")


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    log_level = "debug" if args.dev else None
    refresch_service = RefreshService(log_level)

    uvicorn.run(
        refresch_service.app,
        host=read_env_variable("REFSERVICE_BIND_ADDR"),
        port=read_port("REFSERVICE_BIND_PORT"),
        log_level=log_level,
    )
