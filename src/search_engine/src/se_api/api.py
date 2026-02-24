"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from se_api.handlers import preform_search
from se_api.models import File, Query
from se_api.config import APIConfiguration

class API:
    """API object, holds all endpoints and configuration."""

    app: FastAPI = FastAPI()
    config: APIConfiguration

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.config = APIConfiguration()

    def start(self):
        uvicorn.run(self.app, host=self.config.host, log_level=self.config.port)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"
        return JSONResponse(status_code=422, content=content)

    @staticmethod
    @app.get("/search")
    async def query(request: Query) -> list[File] | None:
        """Preform query on documments, either returns a list or None"""
        return preform_search(request)

    @staticmethod
    @app.get("/health")
    async def check_health() -> JSONResponse:
        """Respond to health check"""
        # check connection with collectors
        return JSONResponse(status_code=200, content={"msg": "healthy"})


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api: API = API()
    api.start()
