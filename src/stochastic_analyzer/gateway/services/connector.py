"""File content retrieval from the connector microservice."""

import binascii
from base64 import b64decode

import httpx

from shared_functions.dmis_logger import dms_warning
from gateway.schemas import InputItem, MetadataTemplate


class Connector:
    """Client for fetching file contents from the connector microservice.

    Attributes:
        url: Base URL for the connector file endpoint.
        timeout: Request timeout in seconds.
    """

    def __init__(self, url: str, timeout: int = 120) -> None:
        self.url = url
        self.timeout = timeout

    async def _get_content(self, pointers: list[str], client: httpx.AsyncClient) -> list[InputItem]:
        """Fetch and decode files from the connector."""
        try:
            response = await client.post(
                f"{self.url.rstrip('/')}/get_files",
                params=[("include_content", True), ("include_last_edit_date", False)],
                json={"file_pointers": pointers},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (
            httpx.HTTPStatusError,
            httpx.TimeoutException,
            ValueError,
            httpx.ConnectError,
        ) as err:
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
            items.append(
                InputItem(
                    content=content,
                    metadata=MetadataTemplate(unique_pointer=unique_pointer),
                )
            )

        return items

    async def get_file_contents(self, pointers: list[str]) -> list[InputItem]:
        """Fetch contents for all file pointers from the connector.

        Args:
            pointers: List of unique file pointers.

        Returns:
            List of successfully retrieved InputItems.
        """
        async with httpx.AsyncClient() as client:
            return await self._get_content(pointers, client)

    async def get_file_metadata(self, pointers: list[str]) -> list[dict]:
        """Fetch file metadata from the connector without content payloads.

        The connector applies authorization filtering: files the requesting
        user is not permitted to view are omitted from the response, so the
        returned list may be shorter than the input pointers list.

        Args:
            pointers: List of unique file pointers.

        Returns:
            List of metadata dicts as provided by the connector, or an
            empty list if the request fails.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.url.rstrip('/')}/get_files",
                    params=[("include_content", False), ("include_last_edit_date", True)],
                    json={"file_pointers": pointers},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (
                httpx.HTTPStatusError,
                httpx.TimeoutException,
                ValueError,
                httpx.ConnectError,
            ) as err:
                dms_warning(f"Connector metadata request failed: {err}")
                return []
