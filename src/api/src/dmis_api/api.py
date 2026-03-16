"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse
import logging
import os
from pathlib import Path

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class API:
    """Management class for main API."""

    log_level: str = "info"

    def __init__(self) -> None:
        self.app = FastAPI()

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register API endpoints."""

        @self.app.get("/search")
        async def search(query: str) -> Any:
            api_url = os.getenv("DMIS_SEARCH_API_URL")
            if not api_url:
                logger.error("DMIS_SEARCH_API_URL is not set")
                raise HTTPException(status_code=500, detail="Search API URL is not configured")

            try:
                response = requests.get(
                    api_url,
                    params={"q": query},
                    timeout=5,
                )
                response.raise_for_status()

            except requests.RequestException as e:
                logger.exception("Search request to upstream API failed")
                raise HTTPException(status_code=502, detail="Upstream search API request failed") from e

            try:
                data = response.json()
            except ValueError as e:
                logger.exception("Upstream search API returned invalid JSON")
                raise HTTPException(status_code=502, detail="Upstream search API returned invalid JSON") from e

            return JSONResponse(content=data)
        
        # Summarize


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.dev else logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    # loading env
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        load_dotenv(env_file)

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", port=8000, log_level=api.log_level)
