"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

import argparse
import os
from typing import Any, Sequence

import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dmis_api.structures import IndexRequest
from dmis_logger import dms_info, dms_warning


class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()
    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict[str, Any]
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"

        return JSONResponse(status_code=422, content=content)

    @staticmethod
    @app.get("/index", status_code=200)
    async def index(item: IndexRequest) -> Any:
        """DMIS API index endpoint definition."""
        return item

    @staticmethod
    @app.get("/search", status_code=200)
    async def search(query: str) -> JSONResponse:
        """Forward search request to upstream search API."""
        search_api_url = os.getenv("DMIS_SEARCH_API_URL")
        if not isinstance(search_api_url, str) or not search_api_url:
            dms_warning("DMIS_SEARCH_API_URL is not set.")
            return JSONResponse(
                status_code=500,
                content="D"
            )

        try:
            response = requests.get(
                f"{search_api_url.rstrip('/')}/search",
                params={"q": query},
                timeout=120,
            )
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            return JSONResponse(
                status_code=502,
                content="A"
            )

        if not response.ok:
            dms_warning(f"Upstream search API returned status code {response.status_code}.")
            return JSONResponse(
                status_code=502,
                content="B"
            )

        try:
            data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            return JSONResponse(
                status_code=502,
                content="C"
            )

        return JSONResponse(status_code=200, content=data)

def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        api.app,
        host="0.0.0.0",
        port=port,
        log_level=api.log_level,
    )
