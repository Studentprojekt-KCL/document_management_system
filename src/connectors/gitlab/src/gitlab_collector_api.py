"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from typing import Any, Annotated
import argparse

import uvicorn
from fastapi import FastAPI, Request, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from interfacer import GitLab

from shared_functions.boto_tools import upload_file
from shared_functions.initialisation_tools import read_port, read_env_variable

class API:
    """Management class for Gitlab connector API."""

    app = FastAPI()

    log_level: str | None = None

    def __init__(self) -> None:
        """Constructor."""
        self.gitlab_instance = GitLab()
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/index_needed_bool", self.index_needed_bool, methods=["GET"])
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])
        self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        errors: dict
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        content: str | dict = jsonable_encoder(errors) if self.log_level == "debug" else "ERROR"

        return JSONResponse(status_code=422, content=content)

    async def index_needed_bool(self, subdata: str | None = None, x_gitlab_token: Annotated[str | None, Header()] = None) -> Any:
        """Endpoint returning status if new index is needed."""
        return self.gitlab_instance.check_index_needed(subdata, x_gitlab_token)

    async def get_files(
        self, file_pointers: dict[str, list], include_content: bool = False, include_last_edit_date: bool = True, x_gitlab_token: Annotated[str | None, Header()] = None
    ) -> Any:
        """Endpoint for retrieving specific file.
        Example request:
            curl -X 'POST' \
            '<HOST>/get_files?include_content=false&include_last_edit_date=true' \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
            "file_pointers": ["<FILE_PTR>"]
            }'
        """
        return self.gitlab_instance.get_files(file_pointers.get("file_pointers", []), x_gitlab_token, include_content, include_last_edit_date)

    async def files_to_index(self, subdata: str | None = None, x_gitlab_token: Annotated[str | None, Header()] = None) -> dict:
        """Endpoint retrieving a pointer to a JSON file containing all content and metadata to index.
        OBS; this method will be depricated."""
        content = self.gitlab_instance.files_to_index(subdata, x_gitlab_token)
        url = upload_file(content, "gitlab_content.json")
        return {"subdata": content.get("subdata"), "index_needed": content.get("index_needed"), "file_url": url}

    async def connected_source_systems(self) -> list:
        """NOT; THIS IS A TEMPORARY ENDPOINT WHICH WILL BE MIGRATED TO SHARED CONNECTOR."""
        return ["GitLab"]

    async def stream_files_to_index(self, subdata: str | None = None, x_gitlab_token: Annotated[str | None, Header()] = None) -> StreamingResponse:
        """Endpoint retrieving a pointer to a JSON file containing all content and metadata to index."""
        return StreamingResponse(self.gitlab_instance.stream_files_to_index(subdata, x_gitlab_token), media_type="application/octet-stream")


def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    uvicorn.run(
        api.app,
        host=read_env_variable("CONGITLAB_BIND_ADDR"),
        log_level=api.log_level,
        port=read_port("CONGITLAB_BIND_PORT"),
    )
