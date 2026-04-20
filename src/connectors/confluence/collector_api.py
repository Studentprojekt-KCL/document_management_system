"""Confluence connector API with GitLab-like endpoints.

Authentication matches the GitHub connector idea: credentials are supplied per HTTP
request via headers (not stored in the connector process as the only source).
"""

import argparse
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from interfacer_confluence import ConfluenceInterfacer


class API:
    """Management class for Confluence connector API."""

    log_level: str | None = None

    def __init__(self) -> None:
        self.app = FastAPI()
        self.confluence_instance = ConfluenceInterfacer()
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Return a JSON error payload for FastAPI request validation failures."""
        errors: dict[str, Any]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, Any] = "ERROR"
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        return JSONResponse(status_code=422, content=content)

    async def files(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> Any:
        """Return file pointers for incremental indexing (honours ``subdata`` checkpoint)."""
        if x_confluence_email is None or x_confluence_token is None:
            return {"subdata": subdata, "file_pointers": []}
        token = x_confluence_token.removeprefix("Bearer ").strip()
        return self.confluence_instance.pointers_to_all_files_to_index(subdata, x_confluence_email.strip(), token)

    async def file(
        self,
        file_pointer: str,
        include_content: bool = True,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> Any:
        """Return one page as metadata plus optional base64-encoded plain text."""
        if x_confluence_email is None or x_confluence_token is None:
            return {}
        token = x_confluence_token.removeprefix("Bearer ").strip()
        return self.confluence_instance.get_page(
            file_pointer, include_content, x_confluence_email.strip(), token
        )

    async def files_to_index(
        self,
        subdata: str | None = None,
        x_confluence_email: str | None = Header(default=None, alias="X-Confluence-Email"),
        x_confluence_token: str | None = Header(default=None, alias="X-Confluence-Token"),
    ) -> dict[str, Any]:
        """Return full page payloads for every pointer due for indexing."""
        if x_confluence_email is None or x_confluence_token is None:
            return {"subdata": subdata, "files": [], "deleted": []}
        token = x_confluence_token.removeprefix("Bearer ").strip()
        return self.confluence_instance.files_to_index(subdata, x_confluence_email.strip(), token)


def run() -> None:
    """Start Confluence connector API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    if args.dev:
        api.log_level = "debug"

    port = os.environ.get("CONFLUENCE_CONNECTOR_PORT")
    if port is None or not port.isdigit():
        return
    uvicorn.run(api.app, host="0.0.0.0", log_level=api.log_level, port=int(port))


if __name__ == "__main__":
    run()

app = API().app
