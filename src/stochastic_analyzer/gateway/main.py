"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import logging
from typing import Any
from collections.abc import Sequence

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
from gateway.services.ranker import Ranker
from gateway.services.summarizer_pdf import PdfConverter


class API:
    """API object, holds all endpoints and configuration.

    Attributes:
        app: FastAPI application.
        config: API configuration.
    """

    app: FastAPI
    config: APIConfiguration

    def __init__(self) -> None:
        logging.basicConfig()
        self.config = APIConfiguration()

        if self.config.log_level == "debug":
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

        self.app = FastAPI(title="stochastic analyzer gateway", version="1.0.0")

        services = Services(
            connector=Connector(url=self.config.services.connector_url),
            summarizer=Summarizer(
                url=self.config.services.ministral_url,
                model=self.config.services.ministral_model,
                timeout=self.config.services.ministral_timeout,
            ),
            classifier=Classifier(
                url=self.config.services.classifier_url,
                escalation_threshold=self.config.services.escalation_threshold,
            ),
            ranker=Ranker(url=self.config.services.tei_url),
            pdf_converter=PdfConverter(),
        )

        self.app.include_router(create_router(services, self.config.device))
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

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
