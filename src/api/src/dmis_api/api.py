"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse
import requests

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.encoders import jsonable_encoder

from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

from dmis_api.structures import IndexRequest


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

        @self.app.get("/index", status_code=200)
        async def index(item: IndexRequest) -> Any:
            """DMIS API index endpoint definition."""
            return item

        # --- Testing functions ---

        @self.app.get("/txt-content", response_class=PlainTextResponse)
        async def txt_content() -> str:
            """
            Main API -> Front-end text test.

            Looks for the test file in the same folder as this api.py file.
            """
            file_path = Path(__file__).resolve().parent / "MainAPI_to_FrontEnd_TEST.txt"

            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Missing file: {file_path}. Create it to use /txt-content."
                )

            return file_path.read_text(encoding="utf-8")

        @self.app.get("/search")
        async def search(query: str) -> Any:

            api_url = "http://10.3.0.2:8001/search"

            try:
                r = requests.get(
                    api_url,
                    json={
                        "user_id": "test",
                        "query": query
                    },
                    timeout=5
                )
                r.raise_for_status()

            except requests.RequestException as e:
                raise HTTPException(status_code=502, detail=str(e))

            return r.json()


        # TEST

        FILES_DIR = Path(__file__).resolve().parent / "data"
        @self.app.get("/files/search")
        async def search_files(q: str = Query(..., min_length=1)) -> dict:
                """
                Search for files by name (case-insensitive) in FILES_DIR.
                Example: /files/search?q=MainAPI
                """
                if not FILES_DIR.exists():
                    raise HTTPException(status_code=500, detail=f"FILES_DIR missing: {FILES_DIR}")

                q_lower = q.lower()
                matches = sorted(
                    [p.name for p in FILES_DIR.iterdir() if p.is_file() and q_lower in p.name.lower()]
                )

                return {"query": q, "matches": matches}


        @self.app.get("/files/{filename}", response_class=PlainTextResponse)
        async def get_file(filename: str) -> str:
            """
            Get file contents from FILES_DIR by filename.
            Example: /files/MainAPI_to_FrontEnd_TEST.txt
            """
            # Prevent path traversal like ../../etc/passwd
            safe_name = Path(filename).name
            file_path = FILES_DIR / safe_name

            if not file_path.exists() or not file_path.is_file():
                raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

            return file_path.read_text(encoding="utf-8")


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