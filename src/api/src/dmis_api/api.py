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

    def __init__(self) -> None:
        """Constructor."""
        bind_address = os.environ.get("API_BIND_ADDRESS")
        port = os.environ.get("API_PORT")
        allowed_origins = os.environ.get("API_ALLOW_ORIGIN")
        search_api_url = os.getenv("DMIS_SEARCH_API_URL")
        query_api_url = os.getenv("DMIS_QUERY_API_URL")

        if bind_address is None:
            dms_error("API_BIND_ADDRESS is not defined.")
            raise RuntimeError("Startup failed.")
        if port is None:
            dms_error("API_PORT is not defined.")
            raise RuntimeError("Startup failed.")
        if not port.isdigit():
            dms_error("API_PORT expected integer.")
            raise RuntimeError("Startup failed.")
        if int(port) <= 0 or int(port) >= 65535:
            dms_error("API_PORT should be between 0 and 65535.")
            raise RuntimeError("Startup failed.")
        if not search_api_url:
            dms_error("DMIS_SEARCH_API_URL is not set.")
            raise RuntimeError("Startup failed.")
        if not query_api_url:
            dms_error("DMIS_QUERY_API_URL is not set.")
            raise RuntimeError("Startup failed.")

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"

        self.bind_address = bind_address
        self.port = int(port)
        self.search_api_url = search_api_url.rstrip("/")
        self.query_api_url = query_api_url.rstrip("/")

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
        self.app.add_api_route("/rerank", self.rerank, methods=["POST"])

    def start(self) -> None:
        """Start API"""
        uvicorn.run(self.app, host=self.bind_address, port=self.port, log_level=self.log_level)

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

    def fetch_search_results(self, query: str) -> list[Any]:
        """Fetch search results from upstream search API."""
        try:
            response = requests.get(
                f"{self.search_api_url}/search",
                params={"q": query},
                timeout=120,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            raise HTTPException(status_code=502) from exc

        try:
            search_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc

        if isinstance(search_data, list):
            results = search_data
        elif isinstance(search_data, dict):
            results = search_data.get("results", [])
        else:
            dms_warning("Search API returned unexpected JSON shape.")
            raise HTTPException(status_code=502)

        if not isinstance(results, list):
            dms_warning("Search API response missing valid 'results' list.")
            raise HTTPException(status_code=502)

        return results

    def fetch_classification_maps(self, pointers: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch classification data and build lookup maps."""
        try:
            response = requests.post(
                f"{self.query_api_url}/classify",
                json={"pointers": pointers},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_text = exc.response.text if exc.response is not None else ""
            dms_warning(f"Classification request failed: {exc}. " f"Response body: {response_text}")
            raise HTTPException(status_code=502) from exc

        try:
            classification_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Classification service returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc

        if isinstance(classification_data, list):
            classification_items = [item for item in classification_data if isinstance(item, dict)]
        elif isinstance(classification_data, dict):
            classification_items = [classification_data]
        else:
            dms_warning("Classification service returned unexpected JSON shape.")
            raise HTTPException(status_code=502)

        classification_map_by_pointer: dict[str, Any] = {}
        classification_map_by_name: dict[str, Any] = {}

        for item in classification_items:
            pointer = item.get("pointer")
            if isinstance(pointer, str) and pointer.strip():
                classification_map_by_pointer[pointer.strip()] = item

            name = item.get("name")
            if isinstance(name, str) and name.strip():
                classification_map_by_name[name.strip()] = item

        return classification_map_by_pointer, classification_map_by_name

    @staticmethod
    def apply_security_classes(
        results: list[Any],
        classification_map_by_pointer: dict[str, Any],
        classification_map_by_name: dict[str, Any],
    ) -> None:
        """Enrich search results with security classification."""
        for entry in results:
            if not isinstance(entry, dict):
                continue

            file_pointer = entry.get("unique_pointer")
            if not isinstance(file_pointer, str):
                continue

            file_pointer = file_pointer.strip()
            if not file_pointer:
                continue

            classification_value = classification_map_by_pointer.get(file_pointer)
            if classification_value is None:
                entry_name = entry.get("name")
                if isinstance(entry_name, str):
                    entry_name = entry_name.strip()
                    if entry_name:
                        classification_value = classification_map_by_name.get(entry_name)

            if isinstance(classification_value, dict):
                security_class = classification_value.get("Security-class")
                if isinstance(security_class, str) and security_class.strip():
                    entry["security_class"] = security_class.strip()
                else:
                    entry["security_class"] = None
            else:
                entry["security_class"] = None

    def fetch_rerank_results(
        self,
        reference_pointer: str,
        pointers: list[str],
    ) -> list[Any]:
        """Fetch reranked results from upstream rerank API."""
        payload = {
            "reference": reference_pointer,
            "pointers": pointers,
        }

        try:
            response = requests.post(
                f"{self.query_api_url}/rerank",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_text = exc.response.text if exc.response is not None else ""
            dms_warning(f"Rerank request to upstream API failed: {exc}. " f"Response body: {response_text}")
            raise HTTPException(status_code=502) from exc

        try:
            rerank_data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Rerank API returned invalid JSON: {exc}")
            raise HTTPException(status_code=502) from exc

        if not isinstance(rerank_data, dict):
            dms_warning("Rerank API returned unexpected JSON shape.")
            raise HTTPException(status_code=502)

        ranked_results = rerank_data.get("ranked_results")
        if not isinstance(ranked_results, list):
            dms_warning("Rerank API response missing valid 'ranked_results' list.")
            raise HTTPException(status_code=502)

        return ranked_results

    async def search(self, query: str = Query(..., min_length=1, max_length=200)) -> JSONResponse:
        """Forward search request to upstream search API, enrich results with classification, and return results."""
        query = query.strip()
        if not query:
            dms_warning("Search request received empty query.")
            raise HTTPException(status_code=422)

        results = self.fetch_search_results(query)

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

        classification_map_by_pointer, classification_map_by_name = self.fetch_classification_maps(unique_pointers)
        self.apply_security_classes(
            results,
            classification_map_by_pointer,
            classification_map_by_name,
        )

        return JSONResponse(
            status_code=200,
            content={
                "results": results,
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

    async def rerank(self, body: dict[str, Any]) -> JSONResponse:
        """Forward rerank request to upstream rerank API and return results."""
        reference_pointer = body.get("reference_pointer")
        if not isinstance(reference_pointer, str):
            dms_warning("Rerank request missing reference_pointer.")
            raise HTTPException(status_code=422)

        reference_pointer = reference_pointer.strip()
        if not reference_pointer:
            dms_warning("Rerank request received empty reference_pointer.")
            raise HTTPException(status_code=422)

        raw_pointers = body.get("pointers")
        if not isinstance(raw_pointers, list):
            dms_warning("Rerank request missing pointers list.")
            raise HTTPException(status_code=422)

        cleaned_pointers: list[str] = []
        seen_pointers: set[str] = set()

        for pointer in raw_pointers:
            if not isinstance(pointer, str):
                continue

            cleaned_pointer = pointer.strip()
            if not cleaned_pointer:
                continue

            if cleaned_pointer == reference_pointer:
                continue

            if cleaned_pointer in seen_pointers:
                continue

            cleaned_pointers.append(cleaned_pointer)
            seen_pointers.add(cleaned_pointer)

        if not cleaned_pointers:
            dms_warning("Rerank request has no valid candidate pointers after filtering.")
            raise HTTPException(status_code=422)

        ranked_results = self.fetch_rerank_results(reference_pointer, cleaned_pointers)

        return JSONResponse(
            status_code=200,
            content={
                "reference_pointer": reference_pointer,
                "ranked_results": ranked_results,
            },
        )


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api = API()
    api.start()
