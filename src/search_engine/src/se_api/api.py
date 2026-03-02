"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from typing import Any
from collections.abc import Sequence
from logging import error

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from se_api.exceptions import SeAPIException
from se_api.handlers import Handler
from se_api.models.file import File
from se_api.models.query import Query
from se_api.config import APIConfiguration

# from logger import dms_error  # pylint: disable=no-name-in-module


class API:
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        config: API configuration.
        handler: data handler and processor.
    """

    app: FastAPI = FastAPI()
    config: APIConfiguration
    handler: Handler

    def __init__(self) -> None:
        self.handler = Handler()
        self.config = APIConfiguration()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/search", self.query, methods=["GET"])
        self.app.add_api_route("/check_health", self.check_health, methods=["GET"])

    def start(self) -> None:
        """Start the API."""

        uvicorn.run(self.app, host=self.config.host, log_level=self.config.log_level)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""

        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        if self.config.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def query(self, request: Query) -> list[File] | None:
        """Preform query on documments, either returns a list or None

        Args:
            request: Query object.

        Returns:
            List of found files or None.
        """

        try:
            return self.handler.preform_search(request)
        except SeAPIException as e:
            error(e.msg)
            return None

    async def check_health(self) -> JSONResponse:
        """Respond to health check"""
        # check connection with collectors
        return JSONResponse(status_code=200, content={"msg": "healthy"})


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api: API = API()
    api.start()
