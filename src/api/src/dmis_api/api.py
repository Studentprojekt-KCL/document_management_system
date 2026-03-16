"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse
import logging
import os
from pathlib import Path

import requests

# from pathlib import Path
# from dmis_api.structures import IndexRequest
# imported but not used for the time being

import uvicorn
<<<<<<< HEAD
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
=======
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse  # PlainTextResponse
from fastapi.encoders import jsonable_encoder

# from fastapi.middleware.cors import CORSMiddleware

# from fastapi import Query
>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e


class API:
    """Management class for main API."""

<<<<<<< HEAD
    log_level: str = "info"

    def __init__(self) -> None:
        self.app = FastAPI()
=======
    def __init__(self) -> None:
        self.app = FastAPI()
        self.log_level: str | None = None

        # Register exception handler
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e

        # Register routes
        self._register_routes()

<<<<<<< HEAD
=======
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

>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e
    def _register_routes(self) -> None:
        """Register API endpoints."""

        @self.app.get("/search")
        async def search(query: str) -> Any:
<<<<<<< HEAD
            api_url = os.getenv("DMIS_SEARCH_API_URL")
            if not api_url:
                logger.error("DMIS_SEARCH_API_URL is not set")
                raise HTTPException(status_code=500, detail="Search API URL is not configured")

=======
            """
            This endpoint fetches data from the endpoint 10.3.0.2:8001/search

            To grab the data from this endpoint you need to perform the curl:
            curl "http://127.0.0.1:8000/search?query=alibaba"
            """

            # - add metadata
            # - the actual production api_url
            # - create environmental variables

            api_url = os.getenv("DMIS_SEARCH_API_URL", "http://10.3.0.2:8001/search")
>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e
            try:
                response = requests.get(
                    api_url,
                    params={"q": query},
                    timeout=5,
                )
                response.raise_for_status()

            except requests.RequestException as e:
<<<<<<< HEAD
                logger.exception("Search request to upstream API failed")
                raise HTTPException(status_code=502, detail="Upstream search API request failed") from e

            try:
                data = response.json()
            except ValueError as e:
                logger.exception("Upstream search API returned invalid JSON")
                raise HTTPException(status_code=502, detail="Upstream search API returned invalid JSON") from e

            return JSONResponse(content=data)

=======
                raise HTTPException(status_code=502, detail=str(e)) from e

            return r.json()


api_instance = API()
app = api_instance.app

>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e

def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
<<<<<<< HEAD

    # for finding .env file
    load_dotenv(Path(__file__).resolve().parent / ".env")
=======
>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e

    api = API()
    if args.dev:
        api.log_level = "debug"

<<<<<<< HEAD
    uvicorn.run(api.app, host="0.0.0.0", port=8000, log_level=api.log_level)
=======
    uvicorn.run(api.app, host="0.0.0.0", port=8000, log_level=api.log_level)
>>>>>>> 2d24660a7b3caafac85472f77fe30fccb2ba2a7e
