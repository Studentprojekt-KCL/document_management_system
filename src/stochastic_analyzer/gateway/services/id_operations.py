"""Service functions for operations based on unique document IDs."""

from gateway.schemas import ClassificationResult, InputItem, SummaryResult
from dmis_logger import dms_warning
from gateway.services.content_retriever import get_content
from gateway.services.classifier import classify_documents
from gateway.services.summarizer import summarize_documents


async def summarize_by_unique_id(
    unique_ids: list[str],
    ministral_url: str,
    ministral_model: str,
    connector_url: str,
) -> SummaryResult | None:
    """Fetch documents by unique ID and forward them to the summarizer."""
    items = await _get_items_by_unique_id(unique_ids, connector_url)
    if not items:
        return None
    return await summarize_documents(items, ministral_url, ministral_model)


async def classify_by_unique_id(
    unique_ids: list[str],
    classifier_url: str,
    connector_url: str,
) -> list[ClassificationResult]:
    """Fetch documents by unique ID and forward them to the classifier."""
    items = await _get_items_by_unique_id(unique_ids, connector_url)
    if not items:
        return []
    return await classify_documents(items, classifier_url)


async def _get_items_by_unique_id(unique_ids: list[str], connector_url: str) -> list[InputItem]:
    """Resolve each unique ID into an `InputItem` for downstream processing."""
    items: list[InputItem] = []
    for unique_id in unique_ids:
        content_item = await get_content(unique_id, connector_url)
        if content_item is None:
            dms_warning(f"Could not retrieve content for ID: {unique_id}")
            continue
        items.append(content_item)
    return items
