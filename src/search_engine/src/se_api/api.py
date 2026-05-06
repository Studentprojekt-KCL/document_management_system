"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import argparse
from contextlib import asynccontextmanager
import logging
from collections.abc import AsyncGenerator
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

from se_api.handlers import Handler
from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.file_type_logic import get_file_resource, get_documents_only_rescource


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
    file_resource_var: list
    documents_only_var: list

    def __init__(self) -> None:
        """Constructor"""
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

        self.port: int = read_port("SEARCHENG_BIND_PORT")
        self.host: str = read_env_variable("SEARCHENG_BIND_ADDR", required=True)  # type: ignore[attr-defined]

        self.app = FastAPI(lifespan=self.lifespan)

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/search", self.query, methods=["POST"])
        self.app.add_api_route("/check_health", self.check_health, methods=["GET"])
        self.app.add_api_route("/reset", self.reset, methods=["POST"], status_code=204)
        self.app.add_api_route("/classification", self.set_classification, methods=["POST"])
        self.app.add_api_route("/classifications", self.get_classifications, methods=["GET"])
        self.app.add_api_route("/file_types", self.file_types, methods=["GET"])
        self.app.add_api_route("/file_types_documents_only", self.file_types_documents_only, methods=["GET"])
        self.app.add_api_route("/find_matching", self.find_matching, methods=["GET"])
        self.app.add_api_route("/searchable_fields", self.searchable_fields, methods=["GET"])

    def start(self) -> None:
        """Start the API."""

        uvicorn.run(self.app, host=self.host, log_level=self.log_level, port=self.port)

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncGenerator:
        """FastAPI lifespan"""
        self.handler = Handler()
        await self.handler.init()
        yield
        await self.handler.close()

    @property
    def file_resource(self) -> list:
        """Read get_file_resource."""
        if not hasattr(self, "FILE_RESOURCE"):
            self.file_resource_var = get_file_resource()
        return self.file_resource_var

    @property
    def documents_only_rescource(self) -> list:
        """Read documents_only_rescource."""
        if not hasattr(self, "DOCUMENTS_ONLY_RESOURCE"):
            self.documents_only_var = get_documents_only_rescource()
        return self.documents_only_var

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""

        errors: dict[str, str | Sequence]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        content = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def find_matching(self, pointer: str) -> list[dict]:
        """Look for matching files.

        Args:
            pointer: file to compare with.
            count: number of wanted results.
        Returns: unique pointers and their score.
        """

        return await self.handler.find_matching(pointer)

    async def query(self, conent: dict[str, str], count: int = 10, offset: int = 0) -> list:
        """Preform query on documments, either returns a list or None

        Args:
            request: Query object.

        Returns:
            List of found files or None.
        """
        return await self.handler.preform_search(conent, count, offset)

    async def set_classification(self, change: dict[str, str]) -> dict:
        """Manualy set the classification of a pointer."""
        return await self.handler.set_classification(change)

    @staticmethod
    async def check_health() -> JSONResponse:
        """Respond to health check"""
        return JSONResponse(status_code=200, content={"msg": "healthy"})

    async def reset(self) -> None:
        """Reset connector."""
        await self.handler.reset()

    async def searchable_fields(self) -> set:
        """Retrive all searchable fields."""
        return self.handler.grab_searchable_fields()

    async def file_types(self) -> list:
        """Retrieve all supported file types."""
        return self.file_resource

    async def file_types_documents_only(self) -> list:
        """Retrieve file types labeled as documents only."""
        return self.documents_only_rescource

    async def get_classifications(self) -> list[str]:
        """Get classifications.

        Returns: list of classifications labels.
        """
        return self.handler.get_classifications()


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api: API = API()
    api.start()
