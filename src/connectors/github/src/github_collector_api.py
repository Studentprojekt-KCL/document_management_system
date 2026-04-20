"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law.

GitHub connector API following the same route contract as the GitLab connector.
"""

import argparse
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from interfacer_github import GitHub

from shared_functions.boto_tools import upload_file
from shared_functions.initialisation_tools import read_env_variable, read_port


class API:
    """Management class for GitHub connector API."""

    app = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.github_instance = GitHub()
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/index_needed_bool", self.index_needed_bool, methods=["GET"])
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])
        self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handler."""
        errors: dict
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def index_needed_bool(
        self,
        subdata: str | None = None,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> dict[str, Any]:
        """Check whether any repo has new content to index."""
        token = x_github_token.removeprefix("Bearer ").strip() if x_github_token else None
        return self.github_instance.check_index_needed(subdata, token)

    async def get_files(
        self,
        file_pointers: dict[str, list],
        include_content: bool = False,
        include_last_edit_date: bool = True,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> Any:
        """Fetch specific files by pointer."""
        token = x_github_token.removeprefix("Bearer ").strip() if x_github_token else None
        return self.github_instance.get_files(
            file_pointers.get("file_pointers", []), include_content, include_last_edit_date, token
        )

    async def files_to_index(
        self,
        subdata: str | None = None,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> dict[str, Any]:
        """Bulk payload of all files to index; uploads to storage and returns file_url."""
        token = x_github_token.removeprefix("Bearer ").strip() if x_github_token else None
        content = self.github_instance.files_to_index(subdata, token)
        url = upload_file(content, "github_content.json")
        return {"subdata": content.get("subdata"), "file_url": url}

    async def stream_files_to_index(
        self,
        subdata: str | None = None,
        x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
    ) -> StreamingResponse:
        """Streaming endpoint for all files to index."""
        token = x_github_token.removeprefix("Bearer ").strip() if x_github_token else None
        return StreamingResponse(
            self.github_instance.stream_files_to_index(subdata, token),
            media_type="application/octet-stream",
        )

    async def connected_source_systems(self) -> list[str]:
        """Return the name of the configured GitHub source system."""
        return [self.github_instance.source_system]


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = read_port("CONGITHUB_BIND_PORT")
    host = read_env_variable("CONGITHUB_BIND_ADDR")

    uvicorn.run(api.app, host=host, log_level=api.log_level, port=port)
