"""Fetcher module for retrieving and processing document content from the connector service."""

import os
import base64
import httpx
from gateway.schemas import InputItem, MetadataTemplate, SummaryResult
from gateway.services.summarizer import summarize_documents

async def get_content(unique_id: str) -> InputItem:
    """
    Fetches file content from the connector and decodes it from Base64.

    Args:
        unique_id: The file_pointer / unique identifier for the file.

    Returns:
        An InputItem containing decoded content and metadata.
    """
    # Connector URL from environment
    connector_url = os.getenv("CONNECTOR_URL", "http://localhost:8080/file")

    params = {"file_pointer": unique_id, "include_content": "true"}
    headers = {"accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(connector_url, params=params, headers=headers)
        response.raise_for_status()
        data = await response.json()

    # Decode Base64 content safely
    base64_content = data.get("content", "")
    try:
        content_str = base64.b64decode(base64_content).decode("utf-8") if base64_content else " "

    except Exception:
        content_str = " "

    # Map metadata from response
    resp_metadata = data.get("metadata", {})
    metadata = MetadataTemplate(name=resp_metadata.get("name", "unknown"))

    return InputItem(content=content_str, metadata=metadata)

async def summarize_by_id(unique_id: str, ministral_url: str, ministral_model: str) -> SummaryResult | None:
    """
    Fetches content by ID and returns its summary via the summarizer.

    Args:
        unique_id: File identifier (file_pointer)
        ministral_url: URL of the Ministral LLM service
        ministral_model: Model identifier for summarization

    Returns:
        SummaryResult object or None if summarization fails
    """
    # Fetch and decode content
    item = await get_content(unique_id)

    # Wrap single document into a list and summarize
    return await summarize_documents([item], ministral_url, ministral_model)
