"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from multiprocessing import Process
from multiprocessing.connection import Connection
import argparse
import logging
from typing import Any
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from initialisation_tools import read_env_variable, read_port

from search_engine.classifier.classifier import Classifier

# from search_engine.api.handlers import Handler

class API(Process):
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        config: API configuration.
        handler: data handler and processor.
    """

    port: int
    host: str
    log_level: str
    MAX_PORT: int = 65536

    search_engine: Connection
    classifier: Classifier

    def __init__(self, search_engine: Connection, log_level: str) -> None:
        super().__init__()

        self.port: int = read_port("SE_API_PORT")
        self.host: str = read_env_variable("SE_API_HOST")
        self.log_level = log_level
        self.search_engine = search_engine
        # self.handler = Handler()

    def run(self) -> None:
        """Start the API."""
        logging.basicConfig()
        if self.log_level == "debug":
            logging.getLogger().setLevel(logging.DEBUG)
        else: 
            logging.getLogger().setLevel(logging.INFO)

        self.classifier = Classifier()
        app = FastAPI()

        app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        app.add_api_route("/search", self.query, methods=["GET"])
        app.add_api_route("/check_health", self.check_health, methods=["GET"])
        app.add_api_route("/reset", self.reset, methods=["POST"], status_code=204)

        uvicorn.run(app, host=self.host, log_level=self.log_level, port=self.port)

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

        self.search_engine.send((query, count, offset))
        files: list[dict[str, str]] = self.search_engine.recv()
        classifications = self.classifier.classify(files)
        for file in files:
            pointer = file.get("unique_pointer")
            if pointer is None:
                continue
            file.update({"security_class": classifications.get(pointer, "")})
        return files
        # return self.handler.preform_search(query, count, offset)

    async def check_health(self) -> JSONResponse:
        """Respond to health check"""
        return JSONResponse(status_code=200, content={"msg": "healthy"})

    async def reset(self) -> None:
        """Reset connector."""
        # self.handler.reset()

