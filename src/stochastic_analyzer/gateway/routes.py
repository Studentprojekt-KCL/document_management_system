"""Define API and routes."""

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

from gateway.services.classifier import Classifier, LABELS
from gateway.services.connector import (
    Connector,
    ConnectorUnreachable,
    UnsupportedContent,
    EmptyContent,
)
from gateway.services.summarizer import Summarizer
from gateway.services.merger import Merger
from gateway.services.summarizer_pdf import PdfConverter
from gateway.services.indexer import Indexer
from gateway.services.token_counter import TokenCounter, MergeLimits

from gateway.schemas import (
    RankResponse,
    FileMetadata,
    HealthCheck,
    ClassificationResult,
    PointerRequest,
    MergeRequest,
    SummaryResult,
    InputItem,
)

from shared_functions.dmis_logger import dms_warning


@dataclass
class Services:
    """Pre-configured service dependencies."""

    connector: Connector
    summarizer: Summarizer
    merger: Merger
    classifier: Classifier
    pdf_converter: PdfConverter
    indexer: Indexer
    token_counter: TokenCounter


async def _fetch_one(connector: Connector, pointer: str) -> InputItem:
    """Fetch a single document, reusing the batch helper's error translation."""
    items = await _retrieve_documents(connector, [pointer])
    return items[0]


async def _retrieve_documents(connector: Connector, pointers: list[str]) -> list[InputItem]:
    """Fetch documents from connector, mapping connector failures to HTTP errors."""
    try:
        items = await connector.get_file_contents(pointers)
    except ConnectorUnreachable as err:
        raise HTTPException(
            status_code=502,
            detail="The document service is currently unavailable. Please try again in a moment.",
        ) from err
    except UnsupportedContent as err:
        raise HTTPException(
            status_code=415,
            detail=(
                f"'{err.filename}' could not be processed: {err.reason}. "
                f"We only support summarization of text-based documents "
                f"(PDF, Word, Excel, PowerPoint, plain text, HTML, and CSV)."
            ),
        ) from err
    except EmptyContent as err:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No text could be extracted from '{err.filename}'. "
                f"The file appears to be empty, contain only images or non-text content, "
                f"or be password-protected."
            ),
        ) from err

    if not items:
        dms_warning("Connector returned an empty list without raising.")
        raise HTTPException(status_code=502, detail="No documents were returned.")
    return items


async def _generate_summary(summarizer: Summarizer, items: list[InputItem]) -> SummaryResult:
    """Summarize documents or raise 500."""
    result = await summarizer.summarize(items)
    if result is None:
        dms_warning("Summarization returned no result.")
        raise HTTPException(status_code=500, detail="Summarization failed.")
    return result


async def _generate_merge(merger: Merger, items: list[InputItem]) -> SummaryResult:
    """Merge documents or raise 500."""
    result = await merger.merge(items)
    if result is None:
        dms_warning("Merge returned no result.")
        raise HTTPException(status_code=500, detail="Merge failed.")
    return result


def _enforce_token_limits(
    items: list[InputItem],
    counter: TokenCounter,
    max_doc_tokens: int,
    max_total_tokens: int,
) -> None:
    """Reject merge batches that exceed per-document or combined token limits."""
    counts = [counter.count(item.content) for item in items]

    for item, count in zip(items, counts, strict=True):
        if count > max_doc_tokens:
            name = item.metadata.name or item.metadata.unique_pointer or "unknown"
            raise HTTPException(
                status_code=400,
                detail=(f"Document '{name}' exceeds the per-document limit " f"({count:,} > {max_doc_tokens:,} tokens)."),
            )

    total = sum(counts)
    if total > max_total_tokens:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Combined document size exceeds the merge limit "
                f"({total:,} > {max_total_tokens:,} tokens). "
                f"Try merging fewer documents."
            ),
        )


def create_router(services: Services, merge_limits: MergeLimits) -> APIRouter:
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
        reference_item = await _fetch_one(services.connector, query_pointer)
        query = reference_item.content

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

    @router.post("/merge", response_model=SummaryResult)
    async def merge_documents(payload: MergeRequest) -> dict:
        """Endpoint to merge multiple similar documents into one coherent document."""
        items = await _retrieve_documents(services.connector, payload.pointers)
        _enforce_token_limits(
            items,
            services.token_counter,
            merge_limits.max_doc_tokens,
            merge_limits.max_total_tokens,
        )
        result = await _generate_merge(services.merger, items)
        return result.model_dump()

    @router.get("/classifications")
    def classifications() -> Response:
        """Endpoint for retrieving existing classifications."""
        return JSONResponse(content=LABELS, status_code=200)

    @router.post("/md-to-pdf")
    async def md_pdf_converter(payload: SummaryResult) -> Response:
        """Endpoint to convert markdown to PDF."""
        pdf: bytes = services.pdf_converter.convert(payload.summary)
        return Response(
            content=pdf,
            status_code=200,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename='summary.pdf'"},
        )

    return router
