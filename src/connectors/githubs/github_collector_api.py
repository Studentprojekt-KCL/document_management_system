"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

GitHub connector following same structure as GitLab connector.
Must return:
- files
- subdata
- file_pointers
Same format as GitLab.
"""

import argparse
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from boto_tools import upload_file
from dmis_logger import dms_error
from interfacer_github import GitHub


class API:
    """Management class for GitHub connector API (same routes/shape as GitLab connector)."""

    app = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.github_instance = GitHub()
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
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
        """List file pointers plus subdata (same as GitLab /files)."""
        return self.github_instance.pointers_to_all_files_to_index(subdata)

    async def file(self, file_pointer: str, include_content: bool = True) -> Any:
        """Single file by pointer (same metadata/content shape as GitLab /file)."""
        return self.github_instance.get_file(file_pointer, include_content)

    async def files_to_index(self, subdata: str | None = None) -> dict:
        """Bulk payload uploaded like GitLab; response includes subdata and file_url."""
        content = self.github_instance.files_to_index(subdata)
        url = upload_file(content, "github_content.json")
        return {"subdata": content.get("subdata"), "file_url": url}


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = os.environ.get("GITHUB_CONNECTOR_PORT")
    if port is None or not port.isdigit():
        dms_error(
            "Port for GitHub connector not set in local environment, please export GITHUB_CONNECTOR_PORT."
        )
        return

    host = os.environ.get("GITHUB_CONNECTOR_HOST")
    if not host:
        dms_error(
            "Host for GitHub connector not set in local environment, please export GITHUB_CONNECTOR_HOST."
        )
        return

    uvicorn.run(api.app, host=host, log_level=api.log_level, port=int(port))
