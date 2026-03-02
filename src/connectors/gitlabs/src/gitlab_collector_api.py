"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any
import argparse

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from interfacer import GitLabs


class API:
    """Management class for Gitlabs connector API."""

    app = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.gitlabs_instance = GitLabs()
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        errors: dict
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def files(self, subdata: str | None = None) -> Any:
        """Endpoint returning a list of files available."""
        return self.gitlabs_instance.pointers_to_all_files_to_index(subdata)

    async def file(self, file_pointer: str, include_content: bool = True) -> Any:
        """Endpoint for retrieving specific file."""
        return self.gitlabs_instance.get_file(file_pointer, include_content)

    async def files_to_index(self, subdata: str, include_content: bool = True) -> Any:
        self.gitlabs_instance.files_to_index()

def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(api.app, host="0.0.0.0", log_level=api.log_level)
