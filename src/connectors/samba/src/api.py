"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

from contextlib import asynccontextmanager
import logging
import argparse
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated, Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
import uvicorn

from services.samba import Samba

from shared_functions.initialisation_tools import read_env_variable, read_port


class API:
    """Samba connector API.

    Variables:
        app: the fastapi object.
        samba_service: The local samba service.
        host: The API host.
        port: The API port.
        log_level: the log level.
    """

    app: FastAPI
    samba_service: Samba
    host: str
    port: int
    log_level: str

    def __init__(self) -> None:
        """constructor"""
        self.host: str = read_env_variable("CONSMB_BIND_ADDR")  # type: ignore
        self.port: int = read_port("CONSMB_BIND_PORT")

        logging.basicConfig()

        parser = argparse.ArgumentParser()
        _ = parser.add_argument("--dev", action="store_true")
        args = parser.parse_args()

        if args.dev:
            self.log_level = "debug"
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
            self.log_level = "info"

        self.samba_service = Samba()

        self.app = FastAPI(lifespan=self.lifespan)

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/get_files", self.files, methods=["POST"])
        self.app.add_api_route("/index_needed_bool", self.index_needed_bool, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["POST"])
        self.app.add_api_route("/defined_fields", self.get_defined_fields, methods=["GET"])
        self.app.add_api_route("/validate_token", self.validate_token, methods=["GET"])

    @asynccontextmanager
    async def lifespan(self, _: FastAPI) -> AsyncGenerator:
        """API lifespan handler."""
        self.samba_service.start_watch()
        yield
        self.samba_service.stop_watch()

    def start(self) -> None:
        """Start the API."""
        uvicorn.run(self.app, host=self.host, port=self.port, log_level=self.log_level)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""
        logging.basicConfig()

        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            content = "ERROR"
            logging.getLogger().setLevel(logging.INFO)
        return JSONResponse(status_code=422, content=content)

    async def index_needed_bool(self, subdata: str | None = None) -> Any:
        """Check if indexing is needed.

        Args:
            subdata: base64 encoded date.
        Returns: true if needed else false.
        """
        return await self.samba_service.check_index_needed(subdata)

    async def files(
        self,
        content: dict,
        authorization: Annotated[str | None, Header()] = None,
        include_content: bool = True,
        include_last_edit_date: bool = True,
    ) -> JSONResponse:
        """Grab a list of files as a user.

        Args:
            content: json body containing pointers and authentication details.
            include_content: if file content is wanted or not.
            include_last_edit_date: if last modification date is wanted or not.
        Returns: json response with the files.
        """
        if authorization is None:
            return JSONResponse(content=[])
        response = self.samba_service.grab_files(content, authorization, include_content, include_last_edit_date)
        return JSONResponse(content=response)

    async def stream_files_to_index(self, body: dict[str, str | None] | None = None) -> StreamingResponse:
        """Endpoint retrieving a pointer to a JSON file containing all content and metadata to index."""
        subdata: str | None = body.get("subdata") if body is not None else None
        return StreamingResponse(self.samba_service.stream_files_to_index(subdata), media_type="application/octet-stream")

    async def validate_token(self, authorization: Annotated[str | None, Header()] = None) -> JSONResponse:
        """Validate user auth.

        Args:
            authorization: user credentials.
        Returns: response with true/false
        """
        return JSONResponse(content=self.samba_service.check_auth(authorization), status_code=200)

    @staticmethod
    async def get_defined_fields() -> list[str]:
        """Get defined fields"""
        return ["unique_pointer", "name", "size", "source_system", "last_edit_date", "content"]


def run() -> None:
    """Connector entrypoint."""
    api: API = API()
    api.start()
