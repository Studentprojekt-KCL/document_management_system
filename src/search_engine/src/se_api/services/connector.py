"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from json import JSONDecodeError
from typing import Any
from collections.abc import AsyncGenerator
from httpx import AsyncClient
import httpx

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Connector:
    """Connector service

    Manages all requests and file fetches from the connectors.

    Attributes:
        address: address to connector.
        subdata: connector file status.
    """

    TIMEOUT: int = 120

    GET_FILE_ENDPOINT: str = "/get_files"
    STREAM_ENDPOINT: str = "/stream_files_to_index"

    subdata: str | None

    index_needed_bool: str
    url_files_to_index: str
    url_get_files: str

    client: AsyncClient

    def __init__(self) -> None:
        """Constructor"""
        address = read_env_variable("SEARCHENG_CONGATEWAY_URL").rstrip("/")
        self.client = AsyncClient(base_url=address)
        self.subdata = None

    async def close(self) -> None:
        """Close clients"""
        await self.client.aclose()

    def reset(self) -> None:
        """Resets the subdata, getting all files."""
        self.subdata = None

    async def streaming_fetch(self) -> AsyncGenerator:
        """Grab file stream from connector.

        Returns: response chunks as an async generator.
        """
        try:
            async with self.client.stream(
                "GET",
                self.STREAM_ENDPOINT,
                timeout=self.TIMEOUT,
                params=[("subdata", self.subdata)] if self.subdata is not None else None,
            ) as stream:
                async for chunk in stream.aiter_text():
                    yield chunk
        except httpx.HTTPError:
            dms_warning("Failed to connect to connector.")

    async def fetch_files(self, pointers: list[str]) -> list[dict]:
        """Grab all files from the connectors pointed at by the pointers.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        response: Any | None = await self._get_file_from_pointers(pointers)
        if not isinstance(response, list):
            return []
        return response

    async def _get_file_from_pointers(self, pointers: list[str]) -> Any | None:
        """Get file from pointer"""
        try:
            response = await self.client.post(
                self.GET_FILE_ENDPOINT,
                params=[("include_content", False), ("include_last_edit_date", True)],
                json={"file_pointers": pointers},
                timeout=Connector.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.GET_FILE_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.GET_FILE_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.GET_FILE_ENDPOINT}.")
        return None
