"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

import argparse
import os
from typing import Any, Sequence

import requests
import uvicorn
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from dmis_logger import dms_info, dms_warning, dms_error


class API:
    """Management class for main API."""

    app: FastAPI = FastAPI()

    log_level: str | None = None
    bind_address: str
    port: int
    search_api_url: str
    query_api_url: str

    def __init__(
        self,
        bind_address: str,
        port: int,
        search_api_url: str,
        query_api_url: str,
        log_level: str | None = None,
    ) -> None:
        """Constructor."""
        self.app = FastAPI()

        self.log_level = log_level
        self.bind_address = bind_address
        self.port = int(port)
        self.search_api_url = search_api_url.rstrip("/")
        self.query_api_url = query_api_url.rstrip("/")

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

        self.app.add_api_route("/search", self.search, methods=["GET"])
        self.app.add_api_route("/summary", self.summary, methods=["POST"])

    def start(self) -> None:
        """Start API"""
        uvicorn.run(
            self.app,
            host=self.bind_address,
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

        content: str | dict[str, Any]
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def search(self, query: str = Query(..., min_length=1, max_length=200)) -> JSONResponse:
        """Forward search request to upstream search API, enrich results with classification, and return results."""
        query = query.strip()
        if not query:
            dms_warning("Search request received empty query.")
            raise HTTPException(status_code=422)

        try:
            response = requests.get(
                f"{self.search_api_url}/search",
                params={"q": query},
                timeout=120,
            )
            response.raise_for_status()
            search_data = response.json()
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            raise HTTPException(status_code=502) from exc
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc

        if not isinstance(search_data, list):
            dms_warning("Search API returned unexpected JSON shape.")
            raise HTTPException(status_code=502)

        return JSONResponse(
            status_code=200,
            content={
                "results": search_data,
                "query": query,
            },
        )

    async def summary(self, body: dict[str, Any]) -> JSONResponse:
        """Forward summary request to upstream summary API and return response."""

        file_pointer = body.get("file_pointer")
        if not isinstance(file_pointer, str):
            dms_warning("Summary request missing file_pointer.")
            raise HTTPException(status_code=422)

        file_pointer = file_pointer.strip()
        if not file_pointer:
            dms_warning("Summary request received empty file_pointer.")
            raise HTTPException(status_code=422)

        payload = {
            "pointers": [file_pointer],
        }

        try:
            response = requests.post(
                f"{self.query_api_url}/summarize",
                json=payload,
                timeout=100,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_text = ""
            if hasattr(exc, "response") and exc.response is not None:
                response_text = exc.response.text

            dms_warning(f"Summary request to upstream API failed: {exc}. " f"Response body: {response_text}")
            raise HTTPException(status_code=502) from exc

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                return JSONResponse(status_code=200, content=response.json())
            except requests.JSONDecodeError as exc:
                dms_warning(f"Summary API returned invalid JSON: {exc}")
                raise HTTPException(status_code=502) from exc

        return PlainTextResponse(content=response.text, status_code=200)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parge_args()

    bind_address = os.environ.get("API_BIND_ADDRESS")
    port = os.environ.get("API_PORT")
    search_api_url = os.getenv("DMIS_SEARCH_API_URL")
    query_api_url = os.getenv("DMIS_QUERY_API_URL")

    if bind_address is None:
        dms_error("API_BIND_ADDRESS is not defined.")
        return
    if port is None:
        dms_error("API_PORT is not defined.")
        return
    if not port.isdigit():
        dms_error("API_PORT expected integer.")
        return
    if int(port) <= 0 or int(port) >= 65535:
        dms_error("API_PORT should be between 0 and 65535.")
        return
    if not search_api_url:
        dms_error("DMIS_SEARCH_API_URL is not set.")
    if not query_api_url:
        dms_error("DMIS_QUERY_API_URL is not set.")

    log_level = "debug" if args.dev else None

    api = API(
        bind_address=bind_address,
        port=port,
        search_api_url=search_api_url,
        query_api_url=query_api_url,
        log_level=log_level,
    )

    api.start()
