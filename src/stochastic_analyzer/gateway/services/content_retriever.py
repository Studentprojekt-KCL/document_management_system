"""Content retrieval and document orchestration service for unique document IDs.

This module handles both individual and bulk document retrieval operations:
- Single document fetching by unique ID
- Parallel batch document retrieval
- Integration with classifier and summarizer services
"""

import asyncio
import base64
import binascii
import os

import httpx

from dmis_logger import dms_warning
from pydantic import ValidationError

from gateway.config import APIConfiguration
from gateway.schemas import ClassificationResult, InputItem, MetadataTemplate, SummaryResult
from gateway.services.classifier import classify_documents
from gateway.services.summarizer import summarize_documents

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================


def _get_connector_url() -> str:
    """Get connector URL from environment variable.

    Returns:
        Connector URL from environment.

    Raises:
        ValueError: If connector URL is not set in environment.
    """
    connector_url = os.getenv("CONNECTOR_URL", "").strip()
    if not connector_url:
        raise ValueError("CONNECTOR_URL environment variable is not set or empty")
    return connector_url


# ============================================================================
# SINGLE DOCUMENT RETRIEVAL
# ============================================================================


async def get_content(unique_id: str) -> InputItem | None:
    """Resolve a unique file pointer into the `InputItem` expected by downstream services.

    This is the low-level retrieval function for a single document.

    Args:
        unique_id: Unique identifier for the document.

    Returns:
        InputItem if retrieval succeeds, None otherwise.
    """

    if not unique_id.strip():
        dms_warning("Cannot retrieve content for an empty unique ID.")
        return None

    try:
        connector_url = _get_connector_url()
    except ValueError as err:
        dms_warning(f"Failed to get connector URL: {err}")
        return None

    params: dict[str, str | bool] = {
        "file_pointer": unique_id,
        "include_content": True,
    }

    data = await _fetch_content_payload(unique_id, connector_url, params)
    if data is None:
        return None

    return _build_input_item(unique_id, data)


async def _fetch_content_payload(unique_id: str, connector_url: str, params: dict[str, str | bool]) -> dict | None:
    """Fetch raw payload from the connector.

    Args:
        unique_id: Unique identifier for the document.
        connector_url: URL of the connector service.
        params: Query parameters for the request.

    Returns:
        Response payload dictionary if successful, None otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{connector_url.rstrip('/')}/file",
                params=params,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as err:
        dms_warning(f"HTTP error when retrieving content for {unique_id}: {err}")
    except httpx.TimeoutException as err:
        dms_warning(f"Timeout when retrieving content for {unique_id}: {err}")
    except httpx.RequestError as err:
        dms_warning(f"Request error when retrieving content for {unique_id}: {err}")
    except ValueError as err:
        dms_warning(f"Invalid JSON when retrieving content for {unique_id}: {err}")
    return None


def _build_input_item(unique_id: str, data: dict) -> InputItem | None:
    """Convert connector payload into the summarizer/classifier input shape.

    Args:
        unique_id: Unique identifier for the document.
        data: Raw payload from connector.

    Returns:
        InputItem if successful, None otherwise.
    """
    raw_content = data.get("content", "")
    content = _decode_content(raw_content)
    if not content.strip():
        dms_warning(f"Connector returned empty content for {unique_id}.")
        return None

    metadata_info = data.get("metadata", {})
    metadata = MetadataTemplate(
        name=metadata_info.get("name") or unique_id.split("/")[-1],
        author=metadata_info.get("author") or "",
    )

    try:
        return InputItem(content=content, metadata=metadata)
    except ValidationError as err:
        dms_warning(f"Could not build InputItem for {unique_id}: {err}")
        return None


def _decode_content(content: str) -> str:
    """Decode connector content, which is typically base64 encoded.

    Args:
        content: Content string to decode.

    Returns:
        Decoded content string or original content if decoding fails.
    """
    if not content:
        return ""

    try:
        return base64.b64decode(content, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return content


# ============================================================================
# BULK OPERATIONS WITH PARALLEL ORCHESTRATION
# ============================================================================


async def summarize_by_unique_id(
    unique_ids: list[str],
    config: APIConfiguration,
) -> SummaryResult | None:
    """Fetch documents by unique ID and forward them to the summarizer.

    Retrieves multiple documents in parallel and synthesizes them into
    a single summary.

    Args:
        unique_ids: List of unique document identifiers.
        config: API configuration containing service URLs and models.

    Returns:
        SummaryResult if summarization succeeds, None otherwise.
    """
    items = await _get_items_by_unique_ids(unique_ids)
    if not items:
        return None
    return await summarize_documents(items, config.services.ministral_url, config.services.ministral_model)


async def classify_by_unique_id(
    unique_ids: list[str],
    config: APIConfiguration,
) -> list[ClassificationResult]:
    """Fetch documents by unique ID and forward them to the classifier.

    Retrieves multiple documents in parallel and classifies each one.

    Args:
        unique_ids: List of unique document identifiers.
        config: API configuration containing service URLs.

    Returns:
        List of ClassificationResult objects.
    """
    items = await _get_items_by_unique_ids(unique_ids)
    if not items:
        return []
    return await classify_documents(items, config.services.classifier_url)


async def _get_items_by_unique_ids(unique_ids: list[str]) -> list[InputItem]:
    """Resolve each unique ID into an `InputItem` for downstream processing.

    Uses asyncio.gather to fetch all documents in parallel instead of
    sequentially waiting in a for loop, providing significant performance
    improvements for bulk operations.

    Performance Example:
    - Sequential: 100 documents × 100ms latency = 10 seconds
    - Parallel: 100 documents in parallel = 100ms total

    Args:
        unique_ids: List of unique document identifiers.

    Returns:
        List of successfully retrieved InputItem objects.
    """
    tasks = [_fetch_and_build_item(unique_id) for unique_id in unique_ids]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    items: list[InputItem] = []
    for result in results:
        if result is not None:
            items.append(result)

    return items


async def _fetch_and_build_item(unique_id: str) -> InputItem | None:
    """Fetch content for a single unique ID and build an InputItem.

    Helper function used by asyncio.gather for parallel execution.

    Args:
        unique_id: Unique document identifier.

    Returns:
        InputItem if retrieval succeeds, None otherwise.
    """
    content_item = await get_content(unique_id)
    if content_item is None:
        dms_warning(f"Could not retrieve content for ID: {unique_id}")
    return content_item
