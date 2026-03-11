"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
from contextlib import asynccontextmanager
from typing import Any, Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from gateway.config import settings
from gateway.routes import router


class API:
    """Management class for main API."""

    def __init__(self) -> None:
        """Constructor."""
        self.settings = settings
        self.app = FastAPI(title=self.settings.API_TITLE, version=self.settings.API_VERSION)
        self.log_level: str | None = None

        self.app.include_router(router)
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
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


def start() -> None:
    """Entry point for application."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host=settings.HOST, port=settings.PORT, log_level=api.log_level)
