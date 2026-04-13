"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
from typing import Any
from collections.abc import Sequence
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from log_api.database import Database
from log_api.models import Log
from initialisation_tools import read_port, read_env_variable


class API:
    """API object, holds all endpoints and configuration."""

    app: FastAPI
    database: Database

    log_level: str | None = None
    bind: str
    port: int

    def __init__(self) -> None:
        """Constructor."""
        self.port = read_port("LOGGER_PORT")
        self.bind = read_env_variable("LOGGER_BIND_ADDRESS")

        parser = argparse.ArgumentParser()
        parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"

        self.app = FastAPI()

        self.app.add_api_route("/logs", self.get_logs, methods=["GET"])
        self.app.add_api_route("/logs", self.add_log, methods=["POST"])
        self.app.add_api_route("/health", self.check_health, methods=["GET"])

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        self.database = Database()

    def start(self) -> None:
        """Start the api."""
        uvicorn.run(self.app, host=self.bind, log_level=self.log_level)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, str] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def get_logs(self, start: datetime | None = None, end: datetime | None = None) -> list[Log] | None:
        """Get logs, either returns a list or None"""
        if start is None:
            start = datetime.now() + timedelta(hours=-1)
        if end is None:
            end = datetime.now()

        return self.database.database_get_logs(start, end)

    async def add_log(self, log: Log) -> Log:
        """Add a log to the database, returns the Log."""
        return self.database.database_add_log(log)

    async def check_health(self) -> JSONResponse:
        """Respond to health check"""
        return JSONResponse(status_code=200, content={"msg": "healthy"})


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api = API()
    api.start()
