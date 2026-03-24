"""SMB API - GitLab compatible"""

import os
import argparse
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from smb import SMBCollector
from boto_tools import upload_file
from logs import smb_error


class API:
    """Management class for SMB connector API."""

    app = FastAPI()
    log_level: str | None = None

    def __init__(self) -> None:
        self.smb_instance = SMBCollector()

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler
        )

        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])

    # ----------------------------
    # Error handling
    # ----------------------------
    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"

        return JSONResponse(status_code=422, content=content)

    # ----------------------------
    # /files → pointers only
    # ----------------------------
    async def files(self, subdata: str | None = None) -> Any:
        return self.smb_instance.pointers_to_all_files_to_index(subdata)

    # ----------------------------
    # /file → single file fetch
    # ----------------------------
    async def file(self, file_pointer: str, include_content: bool = True) -> Any:
        return self.smb_instance.get_file(file_pointer, include_content)

    # ----------------------------
    # /files_to_index → full/incremental
    # ----------------------------
    async def files_to_index(self, subdata: str | None = None) -> dict:
        content = self.smb_instance.files_to_index(subdata)

        url = upload_file(content, "smb_content.json")

        return {
            "subdata": content.get("subdata"),
            "file_url": url
        }


# ----------------------------
# Run server
# ----------------------------
def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()

    if args.dev:
        api.log_level = "debug"

    port = os.environ.get("SMB_CONNECTOR_PORT")

    if port is None or not port.isdigit():
        smb_error("Port not set. Please export SMB_CONNECTOR_PORT.")
        return

    uvicorn.run(
        api.app,
        host="0.0.0.0",
        port=int(port),
        log_level=api.log_level
    )