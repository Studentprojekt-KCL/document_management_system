"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse
import requests

# from pathlib import Path
# from dmis_api.structures import IndexRequest
# imported but not used for the time being

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse  # PlainTextResponse
from fastapi.encoders import jsonable_encoder

# from fastapi.middleware.cors import CORSMiddleware

# from fastapi import Query


class API:
    """Management class for main API."""

    def __init__(self) -> None:
        self.app = FastAPI()
        self.log_level: str | None = None

        # Register exception handler
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        # Register routes
        self._register_routes()

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        if self.log_level == "debug":
            content: str | dict = jsonable_encoder(errors)
        else:
            content = "ERROR"

        return JSONResponse(status_code=422, content=content)

    def _register_routes(self) -> None:
        """Register API endpoints."""

        @self.app.get("/search")
        async def search(query: str) -> Any:
            """
            This endpoint fetches data from the endpoint 10.3.0.2:8001/search

            To grab the data from this endpoint you need to perform the curl:
            curl "http://127.0.0.1:8000/search?query=alibaba"
            """

            # - add metadata
            # - the actual production api_url
            # - create environmental variables

            api_url = "http://10.3.0.2:8001/search"

            try:
                r = requests.get(api_url, json={"user_id": "test", "query": query}, timeout=5)
                r.raise_for_status()

            except requests.RequestException as e:
                raise HTTPException(status_code=502, detail=str(e)) from e

            return r.json()


api_instance = API()
app = api_instance.app


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", port=8000, log_level=api.log_level)
