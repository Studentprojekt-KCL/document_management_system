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
    def md_to_pdf(payload: MarkdownRequest) -> Response:
        """Route that takes string as input and gives PDF."""
        pdf = pdf_converter.convert(payload.markdown)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize(payload: PointerRequest) -> SummaryResult:
        """Summarize one or more documents."""
        if not payload.pointers:
            dms_warning("summarize requires at least 1 pointer.")
            return SummaryResult(summary="")

        items = await connector.get_file_contents(payload.pointers)
        if not items:
            dms_warning("document retreival failure")
            return SummaryResult(summary="")
        result = await summarizer.summarize(items)
        if result is None:
            dms_warning("summarization failed")
            return SummaryResult(summary="")
        return result

    @router.post("/merge", response_model=SummaryResult)
    async def merge(payload: PointerRequest) -> SummaryResult:
        """Endpoint for returning merged documents."""
        if len(payload.pointers) <= 1:
            dms_warning("merge requires minimum 2 pointers.")
            return SummaryResult(summary="")
        items = await connector.get_file_contents(payload.pointers)
        if not items:
            dms_warning("document retreival failure")
            return SummaryResult(summary="")
        result = await summarizer.merge(items)
        if result is None:
            dms_warning("merge failed")
            return SummaryResult(summary="")
        return result

    return router
