"""Handeling routes in the API."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from gateway.services.md_pdf import PdfConverter
from gateway.schemas import MarkdownRequest

from shared_functions.dmis_logger import dms_warning


def create_router(pdf_converter: PdfConverter) -> APIRouter:
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

    return router
