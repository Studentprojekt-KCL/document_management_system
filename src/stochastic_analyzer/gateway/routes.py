"""Define API and routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from dmis_logger import dms_warning
from gateway.config import APIConfiguration
from gateway.schemas import (
    RerankRequest,
    RankResponse,
    ScoredPointer,
    HealthCheck,
    ClassificationResult,
    PointerRequest,
    SummaryResult,
)
from gateway.services.classifier import classify_documents
from gateway.services.connector import get_file_contents
from gateway.services.summarizer import summarize_documents
from gateway.services.ranker import rank_documents
from gateway.services.summarizer_pdf import md_to_pdf


def create_router(config: APIConfiguration) -> APIRouter:
    """Create router with configuration bound via closure.

    Args:
        config: API configuration.

    Returns:
        Configured APIRouter with all endpoints.
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthCheck)
    async def health_check() -> dict:
        """Health checks."""
        return {"status": "active", "model_loaded": True, "device": config.device}

    @router.post("/rerank", response_model=RankResponse)
    async def rerank_documents(payload: RerankRequest) -> dict:
        """Endpoint for pointer-based semantic reranking."""
        reference_items = await get_file_contents(config.services.connector_url, [payload.reference])
        if not reference_items:
            dms_warning("Failed to retrieve reference document from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve reference document.")

        compare_items = await get_file_contents(config.services.connector_url, payload.pointers)
        if not compare_items:
            dms_warning("Failed to retrieve comparison documents from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve comparison documents.")

        query = reference_items[0].content
        texts = [item.content for item in compare_items]
        scores = await rank_documents(query, texts, config.services.tei_url)

        scored = sorted(
            [ScoredPointer(score=float(s), pointer=p) for s, p in zip(scores, payload.pointers)],
            key=lambda x: x.score,
            reverse=True,
        )

        return {"ranked_results": scored}

    @router.post("/classify", response_model=list[ClassificationResult])
    async def classify_endpoint(payload: PointerRequest) -> list[dict]:
        """Endpoint to classify documents via batched NLI inference."""
        items = await get_file_contents(config.services.connector_url, payload.pointers)

        if not items:
            dms_warning("No documents could be retrieved from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve documents.")

        results = await classify_documents(items, config.services.classifier_url)
        return [r.model_dump(by_alias=True) for r in results]

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize_batch(payload: PointerRequest) -> dict:
        """Endpoint to summarize documents by fetching content via file pointers."""
        items = await get_file_contents(config.services.connector_url, payload.pointers)

        if not items:
            dms_warning("No documents could be retrieved from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve documents.")

        result = await summarize_documents(items, config.services.ministral_url, config.services.ministral_model)

        if result is None:
            dms_warning("Summarization returned no result.")
            raise HTTPException(status_code=500, detail="Summarization failed.")

        return result.model_dump()

    @router.post("/md-to-pdf")
    def md_pdf_converter(summary: SummaryResult) -> Response:
        """Endpoint to convert from markdown to pdf."""
        pdf: bytes = md_to_pdf(summary.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
