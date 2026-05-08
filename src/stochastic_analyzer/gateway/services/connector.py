"""File content retrieval from the connector microservice."""

import binascii
from base64 import b64decode
from io import BytesIO

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from gateway.schemas import InputItem, MetadataTemplate
from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Connector:
    """Client for fetching file contents from the connector microservice.

    Attributes:
        url: Base URL for the connector file endpoint.
        client: Shared async HTTP client.
        timeout: Request timeout in seconds.
    """

    def __init__(self, url: str, client: httpx.AsyncClient, timeout: int = 120) -> None:
        self.url = url
        self.client = client
        self.timeout = timeout

    @classmethod
    def from_env(cls, client: httpx.AsyncClient) -> "Connector":
        """Construct a Connector from environment variables.

        Reads:
            STOCHAN_CONGATEWAY_URL: Base URL for the connector service.
        """
        return cls(
            url=read_env_variable("STOCHAN_CONGATEWAY_URL"),
            client=client,
        )

    async def get_file_contents(self, pointers: list[str]) -> list[InputItem]:
        """Fetch contents for all file pointers from the connector.

        Args:
            pointers: List of unique file pointers.

        Returns:
            List of successfully retrieved InputItems.
        """
        try:
            response = await self.client.post(
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
            unique_pointer = individual_data.get("unique_pointer")
            if encoded_content is None:
                dms_warning(f"No content returned for pointer '{pointers}'")
                return []
            try:
                raw = b64decode(encoded_content)
                if raw.startswith(b"%PDF-"):
                    content = "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(raw)).pages).strip()
                else:
                    content = raw.decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, PdfReadError, ValueError) as err:
                dms_warning(f"Decode failed for pointer '{unique_pointer}': {err}")
                return []

            if not content:
                continue

            items.append(
                InputItem(
                    content=content,
                    metadata=MetadataTemplate(unique_pointer=unique_pointer),
                )
            )

        return items

    async def get_file_metadata(self, pointers: list[str]) -> list[dict]:
        """Fetch file metadata from the connector without content payloads.

        Args:
            pointers: List of unique file pointers.

        Returns:
            List of metadata dicts as provided by the connector, or an
            empty list if the request fails.
        """
        try:
            response = await self.client.post(
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
