"""Define API and routes."""

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

from dmis_logger import dms_warning
from gateway.schemas import (
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
from gateway.services.summarizer_pdf import PdfConverter
from gateway.services.indexer import Indexer


@dataclass
class Services:
    """Pre-configured service dependencies."""

    connector: Connector
    summarizer: Summarizer
    classifier: Classifier
    pdf_converter: PdfConverter
    indexer: Indexer


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


def create_router(services: Services, device: str) -> APIRouter:
    """Create router with pre-constructed service dependencies.

    Args:
        services: Pre-configured service instances.
        device: Device identifier for health checks.

    Returns:
        Configured APIRouter with all endpoints.
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthCheck)
    async def health_check() -> dict:
        """Health checks."""
        return {"status": "active", "model_loaded": True, "device": device}

    @router.post("/rerank", response_model=RankResponse)
    async def rerank_documents(payload: PointerRequest) -> dict:
        """Endpoint for semantic document similarity search using vector retrieval."""
        if len(payload.pointers) != 1:
            raise HTTPException(status_code=400, detail="Provide exactly one reference pointer.")

        query_pointer = payload.pointers[0]
        reference_items = await services.connector.get_file_contents([query_pointer])
        if not reference_items:
            dms_warning("Failed to retrieve reference document from connector.")
            raise HTTPException(status_code=502, detail="Failed to retrieve reference document.")

        query = reference_items[0].content

        results = await services.indexer.search_similar(query)
        results = [(p, s) for p, s in results if p != query_pointer]
        if not results:
            return {"ranked_results": []}

        scored = [ScoredPointer(score=float(score), pointer=pointer) for pointer, score in results]
        return {"ranked_results": scored}

    @router.post("/index")
    async def trigger_index() -> dict:
        """Trigger document indexing into Qdrant."""
        return await services.indexer.index(services.connector.url)

    @router.post("/classify", response_model=list[ClassificationResult])
    async def classify_endpoint(payload: PointerRequest) -> list[dict]:
        """Endpoint to classify documents via batched NLI inference."""
        items = await _retrieve_documents(services.connector, payload.pointers)
        results = await services.classifier.classify(items)
        return [r.model_dump(by_alias=True) for r in results]

    @router.post("/summarize", response_model=SummaryResult)
    async def summarize_batch(payload: PointerRequest) -> dict:
        """Endpoint to summarize documents by fetching content via file pointers."""
        items = await _retrieve_documents(services.connector, payload.pointers)
        result = await _generate_summary(services.summarizer, items)
        return result.model_dump()

    @router.get("/classifications")
    def classifications() -> Response:
        """Endpoint for retrieving existing classifications."""
        return JSONResponse(content=LABELS, status_code=200)

    @router.post("/md-to-pdf")
    async def md_pdf_converter(payload: PointerRequest) -> Response:
        """Endpoint to summarize documents and return result as PDF."""
        items = await _retrieve_documents(services.connector, payload.pointers)
        result = await _generate_summary(services.summarizer, items)
        pdf: bytes = services.pdf_converter.convert(result.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
