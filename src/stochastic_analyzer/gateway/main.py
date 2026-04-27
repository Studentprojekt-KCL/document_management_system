"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import argparse
import logging
from contextlib import asynccontextmanager
from typing import Any
from collections.abc import AsyncIterator, Sequence

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from gateway.routes import Services, create_router
from gateway.services.classifier import Classifier
from gateway.services.connector import Connector
from gateway.services.summarizer import Summarizer
from gateway.services.summarizer_pdf import PdfConverter
from gateway.services.indexer import Indexer

from shared_functions.initialisation_tools import read_env_variable, read_port


def _parse_log_level() -> str:
    """Parse the --dev CLI flag into a log level."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    return "debug" if args.dev else "info"


class API:
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        http_client: Shared async HTTP client for all outbound service calls.
        log_level: Log level string ('debug' or 'info').
        bind: Bind address for the HTTP server.
        port: Bind port for the HTTP server.
    """

    app: FastAPI
    http_client: httpx.AsyncClient
    log_level: str
    bind: str
    port: int

    def __init__(self) -> None:
        logging.basicConfig()
        self.log_level = _parse_log_level()
        self.bind = read_env_variable("STOCHAN_BIND_ADDR")
        self.port = read_port("STOCHAN_BIND_PORT")
        device = read_env_variable("STOCHAN_DEVICE")

        if self.log_level == "debug":
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
        )

        self.app = FastAPI(
            title="stochastic analyzer gateway",
            version="1.0.0",
            lifespan=self._lifespan,
        )

        services = Services(
            connector=Connector.from_env(self.http_client),
            summarizer=Summarizer.from_env(self.http_client),
            classifier=Classifier.from_env(self.http_client),
            pdf_converter=PdfConverter(),
            indexer=Indexer.from_env(self.http_client),
        )

        self.app.include_router(create_router(services, device))
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI) -> AsyncIterator[None]:
        """Ensure the shared HTTP client is closed on shutdown."""
        try:
            yield
        finally:
            await self.http_client.aclose()

    def start(self) -> None:
        """Start the API."""
        uvicorn.run(
            self.app,
            host=self.bind,
            port=self.port,
            log_level=self.log_level,
        )

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, str] = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"
        return JSONResponse(status_code=422, content=content)


def start() -> None:
    """Entry point for application."""
    api: API = API()
    api.start()
