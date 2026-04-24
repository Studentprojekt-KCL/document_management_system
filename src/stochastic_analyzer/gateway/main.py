"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

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

from gateway.config import APIConfiguration
from gateway.routes import Services, create_router
from gateway.services.classifier import Classifier
from gateway.services.connector import Connector
from gateway.services.summarizer import Summarizer
from gateway.services.summarizer_pdf import PdfConverter
from gateway.services.indexer import Indexer, IndexerConfig


class API:
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        config: API configuration.
        http_client: Shared async HTTP client for all outbound service calls.
    """

    app: FastAPI
    config: APIConfiguration
    http_client: httpx.AsyncClient

    def __init__(self) -> None:
        logging.basicConfig()
        self.config = APIConfiguration()

        if self.config.log_level == "debug":
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
            connector=Connector(
                url=self.config.services.connector_url,
                client=self.http_client,
            ),
            summarizer=Summarizer(
                url=self.config.services.any_llm.url,
                model=self.config.services.any_llm.model,
                timeout=self.config.services.any_llm.timeout,
                client=self.http_client,
            ),
            classifier=Classifier(
                url=self.config.services.classifier_url,
                escalation_threshold=self.config.services.escalation_threshold,
                client=self.http_client,
            ),
            pdf_converter=PdfConverter(),
            indexer=Indexer(
                config=IndexerConfig(
                    embedding_url=self.config.services.vector.embedding_url,
                    qdrant_url=self.config.services.vector.qdrant_url,
                    batch_size=self.config.services.vector.batch_size,
                    max_chars=self.config.services.vector.max_chars,
                ),
                client=self.http_client,
            ),
        )

        self.app.include_router(create_router(services, self.config.device))
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
            host=self.config.bind,
            port=self.config.port,
            log_level=self.config.log_level,
        )

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
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


def start() -> None:
    """Entry point for application."""
    api: API = API()
    api.start()
