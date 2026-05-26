"""Handeling routes in the API."""

import asyncio
from fastapi import APIRouter, Header
from fastapi.responses import Response, JSONResponse
from aiohttp import ClientError

from gateway.services.md_pdf import PdfConverter
from gateway.schemas import MarkdownRequest, PointerRequest
from gateway.services.summarize import Summarizer
from gateway.services.connector import Connector

from shared_functions.dmis_logger import dms_warning


def create_router(
    pdf_converter: PdfConverter,
    connector: Connector,
    summarizer: Summarizer,
) -> APIRouter:
    """Create a router that handles the logic for services."""
    router = APIRouter()

    @router.post("/md-to-pdf")
    async def md_to_pdf(payload: MarkdownRequest) -> Response:
        """Route that takes a markdown string and returns a PDF."""
        pdf = await asyncio.to_thread(pdf_converter.convert, payload.markdown)
        if pdf is None:
            return JSONResponse(
                status_code=502,
                content={"error": "PDF conversion failed"},
            )
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    @router.post("/summarize")
    async def summarize(payload: PointerRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
        """Summarize one or more documents."""
        if not payload.pointers:
            dms_warning("summarize requires at least 1 pointer.")
            return {"summary": ""}
        try:
            items = await connector.get_file_contents(payload.pointers, authorization)
        except (ClientError, TimeoutError, ValueError):
            dms_warning("connector unreachable")
            return {"summary": ""}

        if not items:
            return {
                "summary": (
                    "I wasn't able to extract any readable content from the documents "
                    "you provided—this usually happens with file types I don't support, "
                    "image-only documents, or empty files."
                )
            }

        result = await summarizer.summarize(items)
        if result is None:
            dms_warning("summarization failed")
            return {"summary": ""}

        return result

    @router.post("/merge")
    async def merge(payload: PointerRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
        """Endpoint for returning merged documents."""
        if len(payload.pointers) <= 1:
            dms_warning("merge requires minimum 2 pointers.")
            return {"summary": ""}
        try:
            items = await connector.get_file_contents(payload.pointers, authorization)
        except (ClientError, TimeoutError, ValueError):
            dms_warning("connector unreachable")
            return {"summary": ""}

        if not items:
            return {
                "summary": (
                    "I wasn't able to extract any readable content from the documents "
                    "you provided—this usually happens with file types I don't support, "
                    "image-only documents, or empty files."
                )
            }

        result = await summarizer.merge(items)
        if result is None:
            dms_warning("merge failed")
            return {"summary": ""}
        return result

    return router
