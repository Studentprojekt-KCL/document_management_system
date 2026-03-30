"""Fetch file content from connector service."""

import base64
import httpx

from dmis_logger import dms_warning


async def fetch_file(file_pointer: str, connector_url: str) -> str | None:
    """Fetch raw file content from the connector service."""

    params = {
        "file_pointer": file_pointer,
        "include_content": "true",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(connector_url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            content_encoded = data.get("content", "")
            content_bytes = base64.b64decode(content_encoded)

            return content_bytes.decode("utf-8")

    except httpx.HTTPStatusError as err:
        dms_warning(f"Connector returned unexpected status from {connector_url}, {err}")

    except httpx.TimeoutException as err:
        dms_warning(f"Connector request timed out ({connector_url}), {err}")

    except Exception as err:
        dms_warning(f"Unexpected error while fetching file from {connector_url}, {err}")

    return None
