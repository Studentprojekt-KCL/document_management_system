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

from dmis_logger import dms_info, dms_warning, dms_error
from fastapi import Query

# Testing
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse


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
        allowed_origins = os.environ.get("API_ALLOWED_ORIGINS")

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
            dms_info(f"Allowing origins: {allowed_origins.split(',')}")
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=allowed_origins.split(","),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self.app.add_api_route("/search", self.search, methods=["GET"])
        self.app.add_api_route("/summary", self.summary, methods=["GET"])

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

    async def search(self, query=Query(..., min_length=1, max_length=200)) -> JSONResponse:
        """Forward search request to upstream search API."""
        search_api_url = os.getenv("DMIS_SEARCH_API_URL")
        query_api_url = os.getenv("DMIS_QUERY_API_URL")

        if not isinstance(search_api_url, str) or not search_api_url:
            dms_warning("DMIS_SEARCH_API_URL is not set.")
            return JSONResponse(status_code=500, content="")

        if not isinstance(query_api_url, str) or not query_api_url:
            dms_warning("DMIS_QUERY_API_URL is not set.")
            return JSONResponse(status_code=500, content="")

        query = query.strip()
        if not query:
            return JSONResponse(status_code=422, content="")

        # calling the search engine
        try:
            search_response = requests.get(
                f"{search_api_url.rstrip('/')}/search",
                params={"q": query},
                timeout=30,
            )
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            return JSONResponse(status_code=502, content="")

        if not search_response.ok:
            dms_warning(f"Upstream search API returned status code {search_response.status_code}.")
            return JSONResponse(status_code=502, content="")

        try:
            search_data = search_response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            return JSONResponse(status_code=502, content="")

        # return JSONResponse(status_code=200, content=data)

        # extract unique pointers from search metadata
        results = search_data.get("results", [])
        if not isinstance(results, list):
            dms_warning("Search API response missing valid 'results' list.")
            return JSONResponse(status_code=502, content="")
        
        unique_pointers = list[str] = []
        for entry in results:
            if not isinstance(entry, dict):
                continue
            
            metadata = entry.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            unique_pointer = metadata.get("unique_pointer")
            if isinstance(unique_pointer, str) and unique_pointer.strip():
                unique_pointers.append(unique_pointer.strip())

        if not unique_pointers:
            return JSONResponse(
                status_code=200,
                content={
                    "results"; [],
                    "query": query,
                    "detail": ""
                },
            )
        
        # send pointers to query service for classification and rerank
        query_payload: dict[str, Any] = {
            "query": query,
            "unique_pointers": unique_pointers,
        }

        try:
            query_response = requests.post(
                f"{query_api_url.rstrip('/')}/rerank",
                json=query_payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            dms_warning(f"Query service request failed: {exc}")
            return JSONResponse(status_code=502, content=""),
        
        if not query_response.ok:
            dms_warning(f"Query service returned status code {query_response.status_code}.")
            return JSONResponse(status_code=502, content="")

        try:
            query_data = query_response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Query service returned invalid JSON: {exc}")
            return JSONResponse(status_code=502, content="")
        
        # return the final result to frontend
        return JSONResponse(status_code=200, content=query_data)

    # Currently works with the example form query, we will change the payload to have unique pointer once that has been fixed.
    async def summary(self, file_pointer: str = Query(..., min_length=1, max_length=500)):
        """Forward summary request to upstream summary API and return plain text."""
        dmis_summary_url = os.getenv("DMIS_SUMMARY_API_URL")
        if not dmis_summary_url:
            dms_warning("DMIS_SUMMARY_API_URL is not set.")
            return JSONResponse(status_code=500, content="")

        # For testing: transform file_pointer into a payload
        payload = [
            {
                "content": "The servers went down at 2 AM due to a power outage. Backup generators kicked in successfully.",
                "metadata": {
                    "name": "Incident_Report_1.txt",
                    "author": "IT Admin",
                },
            },
            {
                "content": "Power was fully restored to the main grid by 4 AM. No data loss was reported.",
                "metadata": {
                    "name": "Incident_Report_2.txt",
                    "author": "IT Admin",
                },
            },
        ]

        try:
            response = requests.post(f"{dmis_summary_url.rstrip('/')}/summarize", json=payload, timeout=120)
            response.raise_for_status()
        except requests.RequestException as exc:
            dms_warning(f"Summary request to upstream API failed: {exc}")
            return JSONResponse(status_code=502, content="")

        # Return as plain text if upstream is text
        return PlainTextResponse(content=response.text, status_code=200)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api = API()
    api.start()
