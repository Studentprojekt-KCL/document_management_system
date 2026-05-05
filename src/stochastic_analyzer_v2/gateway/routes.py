"""Handeling routes in the API."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from gateway.services.md_pdf import PdfConverter
from gateway.schemas import MarkdownRequest, SummaryResult, PointerRequest
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
        """Route that takes string as input and gives PDF."""
        pdf = pdf_converter.convert(payload.markdown)
        if pdf is None:
            dms_warning("PDF conversion failed")
            raise HTTPException(status_code=500)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize(payload: PointerRequest) -> SummaryResult:
        """Summarize a single document."""
        if len(payload.pointers) != 1:
            dms_warning("Only 1 pointer plz")
            raise HTTPException(status_code=400)

        items = await connector.get_file_contents(payload.pointers)
        if not items:
            dms_warning("document retreival failure")
            raise HTTPException(status_code=502)
        result = await summarizer.summarize(items[0])
        if result is None:
            dms_warning("summarization failed")
            raise HTTPException(status_code=500)
        return result

    @router.post("/merge", response_model=SummaryResult)
    async def merge(payload: PointerRequest) -> SummaryResult:
        if len(payload.pointers) < 2:
            dms_warning("merge requires minimum 2 pointers.")
            raise HTTPException(status_code=400)
        items = await connector.get_file_contents(payload.pointers)
        if not items:
            dms_warning("document retreival failure")
            raise HTTPException(status_code=502)
        result = await summarizer.merge(items)
        if result is None:
            dms_warning("merge failed")
            raise HTTPException(status_code=500)
        return result

    return router
