"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from se_api.handlers import Handler
from se_api.config import APIConfiguration


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
        self.config = APIConfiguration()
        self.handler = Handler()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/search", self.query, methods=["GET"])
        self.app.add_api_route("/check_health", self.check_health, methods=["GET"])
        self.app.add_api_route("/reset", self.reset, methods=["POST"], status_code=204)

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

    async def query(self, q: str, k: int = 10, p: int = 1) -> list:
        """Preform query on documments, either returns a list or None

        Args:
            request: Query object.

        Returns:
            List of found files or None.
        """

        return self.handler.preform_search(q, k, p)

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
