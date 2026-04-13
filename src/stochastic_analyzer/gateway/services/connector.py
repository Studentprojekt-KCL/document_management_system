"""File content retrieval from the connector microservice."""

import binascii
from base64 import b64decode

import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, MetadataTemplate


async def _get_content(url: str, pointers: list, client: httpx.AsyncClient) -> list[InputItem]:
    """Fetch and decode a single file from the connector.

    Args:
        url: Connector file endpoint URL.
        pointer: Unique file pointer.
        client: Shared async HTTP client.

    Returns:
        InputItem on success, None on failure.
    """
    try:
        response = await client.post(
            f"{url.rstrip("/")}/get_files",
            params=[("include_content", True), ("include_last_edit_date", False)],
            json={"file_pointers": pointers},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, ValueError, httpx.ConnectError) as err:
        dms_warning(f"Connector request failed for pointer '{pointers}': {err}")
        return []

    items = []
    for individual_data in data:
        encoded_content = individual_data.get("content")
        if encoded_content is None:
            dms_warning(f"No content returned for pointer '{pointers}'")
            return []
        try:
            content = b64decode(encoded_content).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            dms_warning(f"Base64 decode failed for pointer '{pointers}'")
            return []
        unique_pointer = individual_data.get("unique_pointer")
        items.append(InputItem(content=content, metadata=MetadataTemplate(unique_pointer=unique_pointer)))

    return items


async def get_file_contents(connector_url: str, pointers: list[str]) -> list[InputItem]:
    """Fetch contents for all file pointers from the connector.

    Args:
        connector_url: Base URL for the connector file endpoint.
        pointers: List of unique file pointers.

    Returns:
        List of successfully retrieved InputItems.
    """
    async with httpx.AsyncClient() as client:
        return await _get_content(connector_url, pointers, client)
