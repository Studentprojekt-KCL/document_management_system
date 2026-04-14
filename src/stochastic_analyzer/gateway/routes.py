"""Define API and routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

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
    InputItem,
)
from gateway.services.classifier import Classifier, LABELS
from gateway.services.connector import Connector
from gateway.services.summarizer import Summarizer
from gateway.services.ranker import Ranker
from gateway.services.summarizer_pdf import PdfConverter


async def _retrieve_documents(connector: Connector, pointers: list[str]) -> list[InputItem]:
    """Fetch documents from connector or raise 502."""
    items = await connector.get_file_contents(pointers)
    if not items:
        dms_warning("No documents could be retrieved from connector.")
        raise HTTPException(status_code=502, detail="Failed to retrieve documents.")
    return items


async def _generate_summary(summarizer: Summarizer, items: list[InputItem]) -> SummaryResult:
    """Summarize documents or raise 500."""
    result = await summarizer.summarize(items)
    if result is None:
        dms_warning("Summarization returned no result.")
        raise HTTPException(status_code=500, detail="Summarization failed.")
    return result


def create_router(config: APIConfiguration) -> APIRouter:
    """Create router with configuration bound via closure.

    Args:
        config: API configuration.

    Returns:
        Configured APIRouter with all endpoints.
    """
    router = APIRouter()

    connector = Connector(url=config.services.connector_url)
    summarizer = Summarizer(
        url=config.services.ministral_url,
        model=config.services.ministral_model,
        timeout=config.services.ministral_timeout,
    )
    classifier = Classifier(
        url=config.services.classifier_url,
        escalation_threshold=config.services.escalation_threshold,
    )
    ranker = Ranker(url=config.services.tei_url)
    pdf_converter = PdfConverter()

    @router.get("/health", response_model=HealthCheck)
    async def health_check() -> dict:
        """Health checks."""
        return {"status": "active", "model_loaded": True, "device": config.device}

    @router.post("/rerank", response_model=RankResponse)
    async def rerank_documents(payload: RerankRequest) -> dict:
        """Endpoint for pointer-based semantic reranking."""
        reference_items = await connector.get_file_contents([payload.reference])
        if not reference_items:
            dms_warning("Failed to retrieve reference document from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve reference document.")

        compare_items = await connector.get_file_contents(payload.pointers)
        if not compare_items:
            dms_warning("Failed to retrieve comparison documents from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve comparison documents.")

        query = reference_items[0].content
        texts = [item.content for item in compare_items]
        scores = await ranker.rank(query, texts)

        scored = sorted(
            [ScoredPointer(score=float(s), pointer=p) for s, p in zip(scores, payload.pointers, strict=False)],
            key=lambda x: x.score,
            reverse=True,
        )
        return {"ranked_results": scored}

    @router.post("/classify", response_model=list[ClassificationResult])
    async def classify_endpoint(payload: PointerRequest) -> list[dict]:
        """Endpoint to classify documents via batched NLI inference."""
        items = await _retrieve_documents(connector, payload.pointers)
        results = await classifier.classify(items)
        return [r.model_dump(by_alias=True) for r in results]

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize_batch(payload: PointerRequest) -> dict:
        """Endpoint to summarize documents by fetching content via file pointers."""
        items = await _retrieve_documents(connector, payload.pointers)
        result = await _generate_summary(summarizer, items)
        return result.model_dump()

    @router.get("/classifications")
    def classifications() -> Response:
        """Endpoint for retrieving existing classifications."""
        return JSONResponse(content=LABELS, status_code=200)

    @router.post("/md-to-pdf")
    async def md_pdf_converter(payload: PointerRequest) -> Response:
        """Endpoint to summarize documents and return result as PDF."""
        items = await _retrieve_documents(connector, payload.pointers)
        result = await _generate_summary(summarizer, items)
        pdf: bytes = pdf_converter.convert(result.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
