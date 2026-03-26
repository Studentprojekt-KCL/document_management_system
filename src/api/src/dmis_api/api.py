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

from dmis_logger import dms_warning, dms_error
from fastapi import Query

# Testing
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse



class API:
    """Management class for main API."""


    app: FastAPI = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080"],  # frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        )
    
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
    @app.get("/search", status_code=200)
    async def search(query = Query(..., min_length=1, max_length=200)) -> JSONResponse:
        """Forward search request to upstream search API."""
        search_api_url = os.getenv("DMIS_SEARCH_API_URL")
        if not isinstance(search_api_url, str) or not search_api_url:
            dms_warning("DMIS_SEARCH_API_URL is not set.")
            return JSONResponse(status_code=500, content="")

        try:
            response = requests.get(
                f"{search_api_url.rstrip('/')}/search",
                params={"q": query},
                timeout=120,
            )
        except requests.RequestException as exc:
            dms_warning(f"Search request to upstream API failed: {exc}")
            return JSONResponse(status_code=502, content="")

        if not response.ok:
            dms_warning(f"Upstream search API returned status code {response.status_code}.")
            return JSONResponse(status_code=502, content="")

        try:
            data = response.json()
        except requests.JSONDecodeError as exc:
            dms_warning(f"Upstream search API returned invalid JSON: {exc}")
            return JSONResponse(status_code=502, content="")

        return JSONResponse(status_code=200, content=data)
    
    # Currently works with the example form query, we will change the payload to have unique pointer once that has been fixed.
    @staticmethod
    @app.get("/summary")
    async def summary(file_pointer: str = Query(..., min_length=1, max_length=500)) :
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

            }
        ]

        try:
            response = requests.post(
                f"{dmis_summary_url.rstrip('/')}/summarize",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            dms_warning(f"Summary request to upstream API failed: {exc}")
            return JSONResponse(status_code=502, content="")

        # Return as plain text if upstream is text
        return PlainTextResponse(content=response.text, status_code=200)
        

def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = os.getenv("API_PORT")
    if port is None or not port.isdigit():
        dms_error("Port for DMIS API not set as digit in local environment, please export API_PORT.")
        return

    uvicorn.run(
        api.app,
        host="0.0.0.0",
        port=int(port),
        log_level=api.log_level,
    )
