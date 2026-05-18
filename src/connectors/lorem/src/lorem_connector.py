"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from asyncio import to_thread
from typing import Any
from collections.abc import AsyncGenerator
from datetime import datetime
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder
from lorem_text import lorem

from shared_functions.initialisation_tools import read_int_env_variable, read_port, read_env_variable


class API:
    """Management class for Gitlab connector API."""

    app: FastAPI

    log_level: str | None = None
    session_states: dict = {}

    def __init__(self) -> None:
        """Constructor."""
        self.app = FastAPI()
        self.cap = read_int_env_variable("CONLOREM_STREAM_CAP") * 1024 * 1024
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])
        self.app.add_api_route("/defined_fields", self.defined_fields, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        errors: dict
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    def run(self) -> None:
        """Run the api"""
        uvicorn.run(
            self.app,
            host=read_env_variable("CONLOREM_BIND_ADDR"),  # type: ignore
            port=read_port("CONLOREM_BIND_PORT"),
        )

    @staticmethod
    async def get_files(file_pointers: dict[str, list]) -> Any:
        """Grab files"""
        results: list[dict] = []
        for pointer in file_pointers.get("file_pointers", []):
            text = lorem.words(500).encode("utf-8")
            results.append(
                {
                    "source_system": "lorem",
                    "last_edit_date": datetime.now().isoformat(),
                    "content": text,
                    "name": lorem.words(5).replace(" ", "-"),
                    "unique_pointer": pointer,
                    "size": len(text),
                    "type": "source_file",
                }
            )
        return results

    async def stream_files_to_index(self) -> StreamingResponse:
        """Stream lorem data"""

            

        async def _stream() -> AsyncGenerator:
            total_size = 0
            yield json.dumps({"subdata": "subdata"}).encode("utf-8")
            while total_size < self.cap:
                text = lorem.words(500)
                size = len(text.encode("utf-8"))
                total_size += size
                pointer = lorem.words(5).replace(" ", "-")
                chunk = {
                    "source_system": "lorem",
                    "last_edit_date": datetime.now().isoformat(),
                    "content": text,
                    "name": pointer,
                    "unique_pointer": pointer,
                    "size": size,
                    "type": "source_file",
                }
                yield json.dumps(chunk).encode("utf-8")

        return StreamingResponse(_stream(), media_type="application/octet-stream")

    @staticmethod
    async def defined_fields() -> list:
        """Retrieve fields delivered for file conent."""
        return ["source_system", "last_edit_date", "modified", "content", "name", "unique_pointer", "size", "type", "file_type"]


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    api = API()
    api.run()
