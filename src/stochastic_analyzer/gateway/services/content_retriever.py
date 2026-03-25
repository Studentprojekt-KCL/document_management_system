"""Content retrieval service for fetching documents by unique ID."""

import base64

import binascii
import httpx

from dmis_logger import dms_warning
from gateway.schemas import InputItem, MetadataTemplate

async def get_content(unique_id: str, connector_url: str) -> InputItem | None:
    """Resolve a unique file pointer into the `InputItem` expected by downstream services."""
    if not unique_id.strip():
        dms_warning("Cannot retrieve content for an empty unique ID.")
        return None
    if not connector_url.strip():
        dms_warning("Cannot retrieve content without a connector URL.")
        return None

    params = {
        "file_pointer": unique_id,
        "include_content": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{connector_url.rstrip('/')}/file", params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as err:
        dms_warning(f"HTTP error when retrieving content for {unique_id}: {err}")
        return None
    except httpx.TimeoutException as err:
        dms_warning(f"Timeout when retrieving content for {unique_id}: {err}")
        return None
    except Exception as err:  # pylint: disable=broad-except
        dms_warning(f"Error retrieving content for {unique_id}: {err}")
        return None

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
    except Exception as err:  # pylint: disable=broad-except
        dms_warning(f"Could not build InputItem for {unique_id}: {err}")
        return None


def _decode_content(content: str) -> str:
    """Decode connector content, which is typically base64 encoded."""
    if not content:
        return ""

    try:
        return base64.b64decode(content, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return content
