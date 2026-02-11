"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
from typing import Any, Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime

from .handlers import handel_get_logs, handel_add_log
from .models import Log

class API:

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
    @app.get("/logs")
    async def get_logs(start: datetime | None = None, end: datetime | None = None) -> list[Log] | None:
        """Get logs, either returns a list or None"""
        return handel_get_logs(start, end)


    @staticmethod
    @app.post("/logs")
    async def add_log(log: Log):
        """Add a log to the database, returns the Log."""
        return handel_add_log(log)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", log_level=api.log_level)
