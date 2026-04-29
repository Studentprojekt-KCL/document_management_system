"""Application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI

from gateway.routes import create_router
from gateway.services.md_pdf import PdfConverter
from gateway.services.connector import Connector
from gateway.services.summarize import Summarizer

from shared_functions.initialisation_tools import read_env_variable, read_port


def start() -> None:
    """Entry point for stochastic_analyzer."""
    logging.basicConfig(level=logging.INFO)

    pdf_converter = PdfConverter()
    connector = Connector()
    summarizer = Summarizer()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await connector.init()
        await summarizer.init()
        try:
            yield
        finally:
            await connector.close()
            await summarizer.close()

    app = FastAPI(title="stochastic analyzer gateway", lifespan=lifespan)
    app.include_router(create_router(pdf_converter, connector, summarizer))

    uvicorn.run(app, host=read_env_variable("STOCHAN_BIND_ADDR"), port=read_port("STOCHAN_BIND_PORT"))
