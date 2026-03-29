"""File content retrieval from the connector microservice."""

import asyncio
import binascii
from base64 import b64decode

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, MetadataTemplate


async def _get_content(url: str, pointer: str, client: httpx.AsyncClient) -> InputItem | None:
    """Fetch and decode a single file from the connector.

    Args:
        url: Connector file endpoint URL.
        pointer: Unique file pointer.
        client: Shared async HTTP client.

    Returns:
        InputItem on success, None on failure.
    """
    try:
        response = await client.get(url, params={"file_pointer": pointer}, timeout=120)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, ValueError) as err:
        dms_warning(f"Connector request failed for pointer '{pointer}': {err}")
        return None

    encoded_content = data.get("content")
    if encoded_content is None:
        dms_warning(f"No content returned for pointer '{pointer}'")
        return None

    try:
        content = b64decode(encoded_content).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        dms_warning(f"Base64 decode failed for pointer '{pointer}'")
        return None

    return InputItem(content=content, metadata=MetadataTemplate())


async def get_file_contents(connector_url: str, pointers: list[str]) -> list[InputItem]:
    """Fetch contents for all file pointers from the connector.

    Args:
        connector_url: Base URL for the connector file endpoint.
        pointers: List of unique file pointers.

    Returns:
        List of successfully retrieved InputItems.
    """
    async with httpx.AsyncClient() as client:
        tasks = [_get_content(connector_url, pointer, client) for pointer in pointers]
        results = await asyncio.gather(*tasks)

    return [item for item in results if item is not None]
