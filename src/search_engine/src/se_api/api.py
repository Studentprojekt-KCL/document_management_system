"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
import logging
from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from se_api.handlers import Handler
from initialisation_tools import read_env_variable, read_port


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

        self.port: int = read_port("SE_API_PORT")
        self.host: str = read_env_variable("SE_API_HOST")

        self.handler = Handler()

        self.app = FastAPI()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/search", self.query, methods=["GET"])
        self.app.add_api_route("/check_health", self.check_health, methods=["GET"])
        self.app.add_api_route("/reset", self.reset, methods=["POST"], status_code=204)

    def start(self) -> None:
        """Start the API."""

        uvicorn.run(self.app, host=self.host, log_level=self.log_level, port=self.port)

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
