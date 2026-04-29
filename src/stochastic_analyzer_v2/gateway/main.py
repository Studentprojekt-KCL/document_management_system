"""Application entry point."""

import logging

import uvicorn
from fastapi import FastAPI

from gateway.routes import create_router
from gateway.services.md_pdf import PdfConverter

from shared_functions.initialisation_tools import read_env_variable, read_port


def start() -> None:
    """entry point for stochastic_analyzer"""
    logging.basicConfig(level=logging.INFO)

    pdf_converter = PdfConverter()

    app = FastAPI(title="stochastic analyzer gateway")
    app.include_router(create_router(pdf_converter))

    uvicorn.run(app, host=read_env_variable("STOCHAN_BIND_ADDR"), port=read_port("STOCHAN_BIND_PORT"))
