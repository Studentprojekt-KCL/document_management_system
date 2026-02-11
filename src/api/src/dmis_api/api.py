"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import sys
from typing import Any
import argparse

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from dmis_api.structures import IndexRequest

app = FastAPI()

log_level: str | None = None

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Overwrite FastAPI exception handeler."""
    content: str | dict
    if log_level == "debug":
        content = jsonable_encoder({"detail": exc.errors(), "body": exc.body})
    else:
        content = "ERROR"
    return JSONResponse(status_code=422, content=content)


@app.get("/index", status_code=200)
async def index(item: IndexRequest) -> Any:
    """DMIS API index endpoint definition."""
    return item

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    if args.dev:
        global log_level
        log_level = "debug"
    uvicorn.run(app, host="0.0.0.0", log_level=log_level)
