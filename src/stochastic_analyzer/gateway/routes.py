"""Define API and routes."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, JSONResponse
import asyncio

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
    SummarizeRequest,
)
from gateway.services.classifier import classify_documents
from gateway.services.ranker import rank_documents
from gateway.services.summarizer_pdf import md_to_pdf
from gateway.services.fetcher import fetch_file
from gateway.services.summarizer import summarize_documents


def create_router(config: APIConfiguration) -> APIRouter:
    """Create router with configuration bound via closure."""
    router = APIRouter()

    @router.get("/health", response_model=HealthCheck)
    async def health_check() -> dict:
        return {"status": "active", "model_loaded": True, "device": config.device}

    @router.post("/rerank", response_model=RankResponse)
    async def rerank_documents(payload: RankRequest) -> dict:
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
    async def classify_endpoint(payload: list[InputItem]) -> list[dict]:
        if not payload:
            return []

        results = await classify_documents(payload, config.services.classifier_url)
        return [r.model_dump(by_alias=True) for r in results]

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize_endpoint(payload: SummarizeRequest) -> dict:
        """
        Fetch one or more files by unique_id(s) from the connector, then summarize them via LLM.
        """
        try:
            if not payload.unique_ids:
                raise HTTPException(status_code=400, detail="unique_ids cannot be empty")

            # Fetch all files in parallel using the connector URL from config
            contents = await asyncio.gather(
                *(fetch_file(uid, config.services.connector_url) for uid in payload.unique_ids)
            )

            # Convert fetched content into InputItem objects
            items: list[InputItem] = [
                InputItem(
                    content=content,
                    metadata={"name": f"Document {i+1}"}
                )
                for i, content in enumerate(contents)
                if content is not None
            ]

            if not items:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch any documents from the connector."
                )

            # Send all fetched documents to the summarizer
            result = await summarize_documents(
                items,
                config.services.ministral_url,
                config.services.ministral_model,
            )

        except Exception as e:
            dms_warning(f"Summarization failure: {e}")
            raise HTTPException(status_code=500, detail="Summarization failed.") from e

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Summarization returned no result."
            )

        return result.model_dump()

    @router.post("/md-to-pdf")
    def md_pdf_converter(summary: SummaryResult) -> Response:
        pdf: bytes = md_to_pdf(summary.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
