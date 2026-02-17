"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from search_engine.handlers import preform_query
from search_engine.models import Query


class API:
    """API object, holds all endpoints and configuration."""

    app: FastAPI = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

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
    async def query(request: Query) -> list[str] | None:
        """Preform query on documments, either returns a list or None"""
        return preform_query(request)

    @staticmethod
    @app.get("/health")
    async def check_health() -> JSONResponse:
        """Respond to health check"""
        # check connection with collectors
        return JSONResponse(status_code=200, content={"msg": "healthy"})


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", log_level=api.log_level)
