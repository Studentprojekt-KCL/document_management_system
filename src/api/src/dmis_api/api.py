"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from __future__ import annotations

import argparse
import os
from typing import Any, Sequence

import requests
import uvicorn
from fastapi import FastAPI, Request, Query
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

    def __init__(self) -> None:
        """Constructor."""
        bind_address = os.environ.get("API_BIND_ADDRESS")
        port = os.environ.get("API_PORT")
        allowed_origins = os.environ.get("API_ALLOW_ORIGIN")

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

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"

        self.bind_address = bind_address
        self.port = int(port)

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler,
        )

        if allowed_origins is not None:
            origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
            dms_info(f"Allowing origins: {origins}")
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self.app.add_api_route("/search", self.search, methods=["GET"])
        self.app.add_api_route("/summary", self.summary, methods=["POST"])

    def start(self) -> None:
        """Start API"""
        uvicorn.run(self.app, host=self.bind_address, port=self.port, log_level=self.log_level)

    @staticmethod
    def _error_response(status_code: int) -> JSONResponse:
        """Return empty error body to client."""
        return JSONResponse(status_code=status_code, content="")

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
        search_api_url = os.getenv("DMIS_SEARCH_API_URL")
        query_api_url = os.getenv("DMIS_QUERY_API_URL")

        if not search_api_url:
            dms_warning("DMIS_SEARCH_API_URL is not set.")
            return self._error_response(500)

        if not query_api_url:
            dms_warning("DMIS_QUERY_API_URL is not set.")
            return self._error_response(500)

        query = query.strip()
        if not query:
            dms_warning("Search request received empty query.")
            return self._error_response(422)

        try:
            search_response = requests.get(
                f"{search_api_url.rstrip('/')}/search",
                params={"q": query},
                timeout=30,
            )
            search_response.raise_for_status()
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            return self._error_response(502)

        try:
            search_data = search_response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            return self._error_response(502)

        if isinstance(search_data, list):
            results = search_data
        elif isinstance(search_data, dict):
            results = search_data.get("results", [])
        else:
            dms_warning("Search API returned unexpected JSON shape.")
            return self._error_response(502)

        if not isinstance(results, list):
            dms_warning("Search API response missing valid 'results' list.")
            return self._error_response(502)

        unique_pointers: list[str] = []
        seen_pointers: set[str] = set()

        for entry in results:
            if not isinstance(entry, dict):
                continue

            unique_pointer = entry.get("unique_pointer")
            if not isinstance(unique_pointer, str):
                continue

            pointer = unique_pointer.strip()
            if pointer and pointer not in seen_pointers:
                unique_pointers.append(pointer)
                seen_pointers.add(pointer)

        if not unique_pointers:
            return JSONResponse(
                status_code=200,
                content={
                    "results": [],
                    "query": query,
                    "detail": "",
                },
            )

        classification_payload: dict[str, Any] = {
            "pointers": unique_pointers,
        }

        try:
            classification_response = requests.post(
                f"{query_api_url.rstrip('/')}/classify",
                json=classification_payload,
                timeout=30,
            )
            classification_response.raise_for_status()
        except requests.RequestException as exc:
            response_text = ""
            if hasattr(exc, "response") and exc.response is not None:
                response_text = exc.response.text

            dms_warning(
                f"Classification request failed: {exc}. "
                f"Response body: {response_text}"
            )
            return self._error_response(502)

        try:
            classification_data = classification_response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Classification service returned invalid JSON: {exc}")
            return self._error_response(502)

        classification_map_by_pointer: dict[str, Any] = {}
        classification_map_by_name: dict[str, Any] = {}

        classification_items: list[dict[str, Any]] = []
        if isinstance(classification_data, list):
            classification_items = [item for item in classification_data if isinstance(item, dict)]
        elif isinstance(classification_data, dict):
            classification_items = [classification_data]
        else:
            dms_warning("Classification service returned unexpected JSON shape.")
            return self._error_response(502)

        for item in classification_items:
            pointer = item.get("pointer")
            if isinstance(pointer, str) and pointer.strip():
                classification_map_by_pointer[pointer.strip()] = item

            name = item.get("name")
            if isinstance(name, str) and name.strip():
                classification_map_by_name[name.strip()] = item

        for entry in results:
            if not isinstance(entry, dict):
                continue

            file_pointer = entry.get("unique_pointer")
            if not isinstance(file_pointer, str):
                continue

            file_pointer = file_pointer.strip()
            if not file_pointer:
                continue

            metadata = entry.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                entry["metadata"] = metadata

            classification_value = classification_map_by_pointer.get(file_pointer)

            if classification_value is None:
                entry_name = entry.get("name")
                if isinstance(entry_name, str):
                    entry_name = entry_name.strip()
                    if entry_name:
                        classification_value = classification_map_by_name.get(entry_name)

            metadata["classification"] = classification_value

        return JSONResponse(
            status_code=200,
            content={
                "results": results,
                "query": query,
            },
        )


    async def summary(self, body: dict[str, Any]) -> JSONResponse:
        """Forward summary request to upstream summary API and return response."""
        query_api_url = os.getenv("DMIS_QUERY_API_URL")
        if not query_api_url:
            dms_warning("DMIS_QUERY_API_URL is not set.")
            return self._error_response(500)

        file_pointer = body.get("file_pointer")
        if not isinstance(file_pointer, str):
            dms_warning("Summary request missing file_pointer.")
            return self._error_response(422)

        file_pointer = file_pointer.strip()
        if not file_pointer:
            dms_warning("Summary request received empty file_pointer.")
            return self._error_response(422)

        payload = {
            "pointers": [file_pointer],
        }

        try:
            response = requests.post(
                f"{query_api_url.rstrip('/')}/summarize",
                json=payload,
                timeout=100,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_text = ""
            if hasattr(exc, "response") and exc.response is not None:
                response_text = exc.response.text

            dms_warning(
                f"Summary request to upstream API failed: {exc}. "
                f"Response body: {response_text}"
            )
            return self._error_response(502)

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                return JSONResponse(status_code=200, content=response.json())
            except requests.JSONDecodeError as exc:
                dms_warning(f"Summary API returned invalid JSON: {exc}")
                return self._error_response(502)

        return PlainTextResponse(content=response.text, status_code=200)




def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api = API()
    api.start()