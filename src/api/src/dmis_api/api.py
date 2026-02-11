"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import sys

from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from dmis_api.structures import IndexRequest

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Overwrite FastAPI exception handeler."""
    content: str | dict
    if sys.argv[1] == "dev":
        content = jsonable_encoder({"detail": exc.errors(), "body": exc.body})
    else:
        content = "ERROR"
    return JSONResponse(status_code=422, content=content)


@app.get("/index", status_code=200)
async def index(item: IndexRequest) -> Any:
    """DMIS API index endpoint definition."""
    return item
