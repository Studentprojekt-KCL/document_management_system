"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse
import os
import requests
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

class API:
    """Management class for main API."""
    def _register_routes(self) -> None:
        """Register API endpoints."""
        @self.app.get("/search")
        async def search(query: str) -> Any:
           
            api_url = os.getenv("DMIS_SEARCH_API_URL")
            try:
                r = requests.get(
                    api_url,
                    params={"q": query},
                    timeout=5
                )
                r.raise_for_status()

            except requests.RequestException as e:
                raise HTTPException(status_code=502, detail=str(e)) from e
                # Repalce with our logger
    
            return r.json() # Jakob noted something ask him about it.
        
    def __init__(self) -> None:
            self.app = FastAPI()

            # Register routes
            self._register_routes()

def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    # for finding .env file
    load_dotenv(Path(__file__).resolve().parent / ".env")

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", port=8000, log_level=api.log_level)

