"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
import logging
from os import environ
from typing import Any
from collections.abc import Sequence

from dmis_logger import dms_error
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from se_api.handlers import Handler

class API:
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        config: API configuration.
        handler: data handler and processor.
    """

    app: FastAPI
    handler: Handler

    port: int
    host: str
    log_level: str
    MAX_PORT: int = 65536

    def __init__(self) -> None:
        logging.basicConfig()

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
            self.log_level = "info"

        port: str | None = environ.get("SE_API_PORT")
        host: str | None = environ.get("SE_API_HOST")

        if port is None:
            dms_error("SE_API_PORT is not defined.")
            return
        if host is None:
            dms_error("SE_API_HOST is not defined.")
            return

        if not port.isdigit():
            dms_error("Port is expected to be an integer.")
        elif int(port) < 0 or int(port) >= self.MAX_PORT:
            dms_error(f"Port should be between 0 and {self.MAX_PORT}.")

        self.port = int(port)
        self.host = host

        self.handler = Handler()

        self.app = FastAPI()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/search", self.query, methods=["GET"])
        self.app.add_api_route("/check_health", self.check_health, methods=["GET"])
        self.app.add_api_route("/reset", self.reset, methods=["POST"], status_code=204)

    def start(self) -> None:
        """Start the API."""

        uvicorn.run(self.app, host=self.host, log_level=self.log_level)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""

        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        content = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def query(self, query: str, count: int = 10, offset: int = 0) -> list:
        """Preform query on documments, either returns a list or None

        Args:
            request: Query object.

        Returns:
            List of found files or None.
        """

        return self.handler.preform_search(query, count, offset)

    async def check_health(self) -> JSONResponse:
        """Respond to health check"""
        return JSONResponse(status_code=200, content={"msg": "healthy"})

    async def reset(self) -> None:
        """Reset connector."""
        self.handler.reset()


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api: API = API()
    api.start()
