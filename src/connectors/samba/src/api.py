from typing import Any, Sequence
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
import uvicorn
from samba import Samba

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

class API:
    app: FastAPI
    samba_service: Samba
    host: str
    port: int
    log_level: str

    def __init__(self) -> None:
        # TODO: remove hard code
        self.host = "0.0.0.0"
        self.port = 8000
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

    async def files(self) -> None:
        pass

def run() -> None:
    api: API = API()
    api.start()
