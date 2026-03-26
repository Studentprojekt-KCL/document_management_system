"""Define API and routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse
from dmis_logger import dms_warning

from gateway.config import APIConfiguration
from gateway.schemas import (
    RankRequest,
    RankResponse,
    ScoredDocument,
    HealthCheck,
    InputItem,
    ClassificationResult,
    SummaryResult,
    UniqueIdRequest,
)
from gateway.services.content_retriever import (
    summarize_by_unique_id,
    classify_by_unique_id,
)
from gateway.services.classifier import classify_documents
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
    async def rerank_documents(payload: RankRequest) -> dict:
        """Endpoint for the external TEI model."""
        if not payload.documents:
            return {"ranked_results": []}

        try:
            scores = await rank_documents(payload.query, payload.documents, config.services.tei_url)
        except Exception as e:
            dms_warning(f"Ranking engine failure: {e}")
            raise HTTPException(status_code=500, detail="Ranking engine failure.") from e

        scored_docs = sorted(
            [ScoredDocument(score=float(score), document=doc) for score, doc in zip(scores, payload.documents)],
            key=lambda x: x.score,
            reverse=True,
        )

        return {"ranked_results": scored_docs}

    @router.post("/classify", response_model=list[ClassificationResult])
    async def classify_endpoint(payload: list[InputItem] | UniqueIdRequest) -> list[dict]:
        """Endpoint to classify documents.

        Supports two modes:
        - Direct document classification: Pass list of InputItem objects with content
        - By unique ID: Pass UniqueIdRequest with list of unique IDs

        Args:
            payload: Either a list of InputItem objects or a UniqueIdRequest.

        Returns:
            List of ClassificationResult objects serialized with aliases.
        """
        if isinstance(payload, UniqueIdRequest):
            results = await classify_by_unique_id(payload.unique_ids, config)
        else:
            if not payload:
                return []
            results = await classify_documents(payload, config.services.classifier_url)

        if not results:
            dms_warning("Classification returned no results.")
            return []

        return [r.model_dump(by_alias=True) for r in results]

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize_endpoint(payload: list[InputItem] | UniqueIdRequest) -> dict:
        """Endpoint to summarize documents.

        Supports two modes:
        - Direct document summarization: Pass list of InputItem objects with content
        - By unique ID: Pass UniqueIdRequest with list of unique IDs

        Args:
            payload: Either a list of InputItem objects or a UniqueIdRequest.

        Returns:
            SummaryResult with the generated summary.
        """
        result = None

        if isinstance(payload, UniqueIdRequest):
            result = await summarize_by_unique_id(payload.unique_ids, config)
        else:
            if not payload:
                dms_warning("Empty document list provided for summarization.")
                return JSONResponse(status_code=400, content={"detail": "Document list cannot be empty."})
            result = await summarize_documents(payload, config.services.ministral_url, config.services.ministral_model)

        if result is None:
            dms_warning("Summarization returned no result.")
            return JSONResponse(status_code=500, content={"detail": "Summarization failed or no valid documents found."})

        return result.model_dump()

    @router.post("/md-to-pdf")
    def md_pdf_converter(summary: SummaryResult) -> Response:
        """Endpoint to convert from markdown to pdf.

        Args:
            summary: SummaryResult containing markdown text.

        Returns:
            PDF response with attachment header.
        """
        pdf: bytes = md_to_pdf(summary.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
