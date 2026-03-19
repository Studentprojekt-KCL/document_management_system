from os import environ
from typing import Any, Sequence
from dmis_logger import dms_error
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
import uvicorn
from services.samba import Samba

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

class API:
    app: FastAPI
    samba_service: Samba
    host: str
    port: int
    log_level: str

    def __init__(self) -> None:
        host: str = environ.get("SC_HOST", "0.0.0.0")
        port: str = environ.get("SC_PORT", "8000")

        if not port.isdigit():
            dms_error("SC_PORT is expected to be a number.")
        self.port = int(port)
        if self.port <= 0 or self.port > 65534:
            dms_error("SC_PORT has to be between 0 and 65535.")

        self.host = host
        # TODO: remove hard code
        self.log_level = "debug"

        self.samba_service = Samba()
        self.samba_service.mount()

        self.app = FastAPI()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_api_route("/files", self.files, methods=["GET"])
    

    def start(self) -> None:
        uvicorn.run(self.app, host=self.host, port=self.port, log_level=self.log_level)

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Overwrite FastAPI exception handeler."""

        errors: dict[str, str | Sequence[Any]]
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}
        content: str | dict[str, str]
        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"
        return JSONResponse(status_code=422, content=content)

    async def files(self, subdata: str | None = None) -> JSONResponse:
        pointers = self.samba_service.get_files(subdata)
        return JSONResponse(
            content={
                "subdata": None,
                "file_pointers": pointers
            }
        )

def run() -> None:
    api: API = API()
    api.start()
