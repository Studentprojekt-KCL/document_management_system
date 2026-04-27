"""Define API and routes."""

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

from gateway.services.classifier import Classifier, LABELS
from gateway.services.connector import Connector, ConnectorUnreachable, ContentUnavailable
from gateway.services.summarizer import Summarizer
from gateway.services.summarizer_pdf import PdfConverter
from gateway.services.indexer import Indexer

from gateway.schemas import (
    RankResponse,
    FileMetadata,
    HealthCheck,
    ClassificationResult,
    PointerRequest,
    SummaryResult,
    InputItem,
)

from shared_functions.dmis_logger import dms_warning


@dataclass
class Services:
    """Pre-configured service dependencies."""

    connector: Connector
    summarizer: Summarizer
    classifier: Classifier
    pdf_converter: PdfConverter
    indexer: Indexer


# Shared user-facing messages so the summarize and rerank endpoints stay consistent.
_UPSTREAM_UNAVAILABLE_MSG = "Document service is unavailable. Please try again later."
_CONTENT_UNAVAILABLE_MSG = (
    "No readable text could be extracted from the selected file. "
    "This can happen with unsupported file types, encrypted files, or empty documents."
)


async def _retrieve_documents(connector: Connector, pointers: list[str]) -> list[InputItem]:
    """Fetch documents from the connector or raise a specific HTTPException.

    Maps connector failure modes onto distinct HTTP responses so the frontend
    can surface a meaningful message to the user:
      - ConnectorUnreachable -> 502 Bad Gateway
      - ContentUnavailable   -> 422 Unprocessable Entity
      - no files returned    -> 404 Not Found
    """
    try:
        items = await connector.get_file_contents(pointers)
    except ConnectorUnreachable as err:
        raise HTTPException(status_code=502, detail=_UPSTREAM_UNAVAILABLE_MSG) from err
    except ContentUnavailable as err:
        raise HTTPException(status_code=422, detail=_CONTENT_UNAVAILABLE_MSG) from err

    if not items:
        dms_warning("Connector returned no documents for the requested pointers.")
        raise HTTPException(status_code=404, detail="Requested document could not be found.")
    return items


async def _generate_summary(summarizer: Summarizer, items: list[InputItem]) -> SummaryResult:
    """Summarize documents or raise 500."""
    result = await summarizer.summarize(items)
    if result is None:
        dms_warning("Summarization returned no result.")
        raise HTTPException(status_code=500, detail="Summarization failed.")
    return result


def create_router(services: Services) -> APIRouter:
    """Create router with pre-constructed service dependencies.

    Args:
        services: Pre-configured service instances.

    Returns:
        Configured APIRouter with all endpoints.
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthCheck)
    async def health_check() -> dict:
        """Health checks."""
        return {"status": "active", "model_loaded": True}

    @router.post("/rerank", response_model=RankResponse)
    async def rerank_documents(payload: PointerRequest) -> dict:
        """Endpoint for semantic document similarity search using vector retrieval.

        Returns file metadata enriched with similarity scores, ordered by
        descending similarity.
        """
        if len(payload.pointers) != 1:
            raise HTTPException(status_code=400, detail="Provide exactly one reference pointer.")

        query_pointer = payload.pointers[0]
        try:
            reference_items = await services.connector.get_file_contents([query_pointer])
        except ConnectorUnreachable as err:
            raise HTTPException(status_code=502, detail=_UPSTREAM_UNAVAILABLE_MSG) from err
        except ContentUnavailable as err:
            raise HTTPException(status_code=422, detail=_CONTENT_UNAVAILABLE_MSG) from err

        if not reference_items:
            raise HTTPException(status_code=404, detail="Reference document could not be found.")

        query = reference_items[0].content

        results = await services.indexer.search_similar(query, limit=6)
        results = [(p, s) for p, s in results if p != query_pointer][:5]
        if not results:
            return {"ranked_results": []}

        # Join scores with connector-provided metadata by unique_pointer.
        pointer_to_score = dict(results)
        metadata_list = await services.connector.get_file_metadata(list(pointer_to_score.keys()))

        enriched = [
            FileMetadata(**{**meta, "score": pointer_to_score[meta["unique_pointer"]]})
            for meta in metadata_list
            if meta.get("unique_pointer") in pointer_to_score
        ]
        enriched.sort(key=lambda x: x.score, reverse=True)

        return {"ranked_results": enriched}

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
