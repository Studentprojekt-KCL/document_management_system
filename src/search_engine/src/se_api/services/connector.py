"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from json import JSONDecodeError
from typing import Any, AsyncGenerator
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

    INDEX_NEEDED_ENDPOINT: str = "/index_needed_bool"
    FILES_TO_INDEX_ENDPOINT: str = "/files_to_index"
    GET_FILE_ENDPOINT: str = "/get_files"
    STREAM_ENDPOINT: str = "/stream_files_to_index"

    subdata: str | None

    index_needed_bool: str
    url_files_to_index: str
    url_get_files: str

    client: AsyncClient

    def __init__(self) -> None:
        """Constructor"""
        address = read_env_variable("SE_API_CONNECTOR_ADDRESS")
        self.client = AsyncClient(base_url=address)
        self.subdata = None

    async def close(self) -> None:
        """Close clients"""
        await self.client.aclose()

    def reset(self) -> None:
        """Resets the subdata, getting all files."""
        self.subdata = None

    async def streaming_fetch(self) -> AsyncGenerator:
        async with self.client.stream(
            "GET",
            self.STREAM_ENDPOINT,
            timeout=120,
            params=[("subdata", self.subdata)] if self.subdata is not None else None
        ) as stream:
            async for chunk in stream.aiter_text():
                yield chunk

    async def reindex_needed(self) -> bool:
        """Check if new reindex is required."""
        try:
            response = await self.client.get(
                self.INDEX_NEEDED_ENDPOINT,
                timeout=Connector.TIMEOUT,
                params=[("subdata", self.subdata)] if self.subdata is not None else None,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return True
            return not data.get("index_needed") is False
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.FILES_TO_INDEX_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        return True

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

    async def get_files(self) -> list:
        """Grab all new files pointers from connectors.

        Returns:
            A list of files.
        """

        file_url = await self._files_to_index()
        if file_url is None:
            return []

        response: Any | None = await self._get_files_from_url(file_url)
        if response is None:
            return []
        if not isinstance(response, dict):
            dms_warning("Response is not formatted as a dict.")
            return []

        data = response.get("files")
        subdata = response.get("subdata")

        if data is None:
            dms_warning("No files in collector response.")
            return []
        if subdata is None:
            dms_warning("Connector returned empty subdata.")

        self.subdata = subdata
        return data

    async def _files_to_index(self) -> str | None:
        """Get the url for the file containing all new files."""

        response: Any | None = await self._get_file_to_index()
        if response is None or not isinstance(response, dict) or response.get("index_needed") is False:
            return None

        subdata = response.get("subdata")
        file_url = response.get("file_url")

        if subdata is None:
            dms_warning("No subdata delievered by collector.")
        if file_url is None:
            dms_warning("No returned collection URL.")

        self.subdata = subdata

        return file_url

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
            dms_warning(f"Request timed out, url: {self.FILES_TO_INDEX_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        return None

    async def _get_files_from_url(self, url: str) -> Any | None:
        """Get files from url"""
        try:
            response = await self.client.get(url, timeout=Connector.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.FILES_TO_INDEX_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        return None

    async def _get_file_to_index(self) -> Any | None:
        """Get file to index"""
        try:
            response = await self.client.get(
                self.FILES_TO_INDEX_ENDPOINT, 
                params=[("subdata", self.subdata)] if self.subdata is not None else None,
                timeout=self.TIMEOUT
            )
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.FILES_TO_INDEX_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.FILES_TO_INDEX_ENDPOINT}.")
        return None
