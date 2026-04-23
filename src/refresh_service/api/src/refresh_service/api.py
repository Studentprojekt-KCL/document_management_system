"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse

from typing import Any
import json
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from collections.abc import Sequence

from fastapi.exceptions import RequestValidationError
from refresh_service.session_encryption_tools import SessionEncryption
from refresh_service.auth_token import authorize_and_get_token
from shared_functions.initialisation_tools import read_env_variable, read_port

class RefreshService:
    """ ."""

    app = FastAPI()
    session_encryption: SessionEncryption

    db_storage: dict = {} #TODO remove this.

    def __init__(self, log_level: str | None = None):
        self.log_level = log_level
        self.session_enc = SessionEncryption(read_env_variable("REFSERVICE_SESSION_ENC_PASSW"))

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

    async def add_session(self, service_name: str, session_vars: dict[Any, Any], authorization: str | None = Header(default=None)):
        #TODO The SUB value is a unique value for each user, which prob also should be used in the encryption password.
        if not isinstance(session_vars, dict):
            raise HTTPException(status_code=422)
        print(authorization)
        status, token_values = authorize_and_get_token(authorization)
        if status is False:
            raise HTTPException(status_code=401)

        content = {service_name: session_vars}
        enc_session_vars = self.session_enc.encrypt_session_vars(content)

        self.db_storage[token_values.get("sub")] = enc_session_vars

        return JSONResponse(status_code=200, content={"status": "success"})

    async def get_session(self, service_name: str, authorization: str | None = Header(default=None)): #TODO, remove enc string.
        status, token_values = authorize_and_get_token(authorization)
        if status is False:
            raise HTTPException(status_code=401)
        content = self.db_storage.get(token_values.get("sub"))

        return json.loads(self.session_enc.decrypt_session_vars(content)).get(service_name).get("access_token") #TODO implement refresh


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
