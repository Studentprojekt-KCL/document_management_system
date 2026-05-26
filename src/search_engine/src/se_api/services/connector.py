"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from collections.abc import AsyncGenerator
import dbm
from json import JSONDecodeError
import json
import shelve
from typing import Any
from asyncio import Lock

from httpx import AsyncClient
import httpx

from se_api.constants import TIMEOUT

from shared_functions.dmis_logger import dms_error, dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Connector:
    """Connector service

    Manages all requests and file fetches from the connectors.

    Attributes:
        address: address to connector.
        subdata: connector file status.
    """

    GET_FILE_ENDPOINT: str = "/get_files"
    GET_FIELDS: str = "/defined_fields"
    STREAM_ENDPOINT: str = "/stream_files_to_index"
    DATA_FILE: str = "/data"

    subdata: dict[str, str | None]

    url_files_to_index: str
    url_get_files: str
    data_path: str

    client: AsyncClient

    def __init__(self) -> None:
        """Constructor"""
        address = read_env_variable("SEARCHENG_CONGATEWAY_URL", required=True).rstrip("/")  # type: ignore
        self.client = AsyncClient(base_url=address)
        self.data_path = f"{
                read_env_variable("SEARCHENG_WORKING_DIRECTORY", required=True).rstrip("/") # type: ignore
        }{self.DATA_FILE}"
        try:
            with shelve.open(self.data_path) as f:
                self.subdata = f.get("subdata", {})
        except OSError:
            dms_error(f"Failed to open file: {self.data_path}.")
        except dbm.error:
            dms_error(f"Failed opening file: {self.data_path}")
        self.subdata_lock = Lock()

    async def close(self) -> None:
        """Close clients"""
        await self.client.aclose()
        self.write_subdata()

    def write_subdata(self, subdata: dict | None = None) -> None:
        """Set the subdata.

        Args:
            subdata: subdata string returned from the connectos.
        """
        with shelve.open(self.data_path) as f:
            if subdata is not None:
                f["subdata"] = subdata
                self.subdata = subdata
            else:
                f["subdata"] = self.subdata

    async def connector_fetch(self, authorization: str | None) -> list:
        """Grab connectors from gateway.

        Returns: queue with stream urls.
        """
        streams: list = []
        try:
            response = await self.client.get(
                self.STREAM_ENDPOINT,
                headers=[("Authorization", authorization)] if authorization is not None else None,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            content = response.json()
            if not isinstance(content, list):
                dms_warning(f"Expected a list of dicts when calling: {self.STREAM_ENDPOINT}")
                return streams
            if content and not isinstance(content[0], dict):
                dms_warning(f"Expected a list of dicts when calling: {self.STREAM_ENDPOINT}")
                return streams
            streams.extend(content)
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.GET_FILE_ENDPOINT}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.GET_FILE_ENDPOINT}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.GET_FILE_ENDPOINT}.")
        return streams

    async def get_fields(self) -> list[str] | None:
        """Fetch fields from connector.

        Returns: list of fields
        """
        try:
            response = await self.client.get(
                self.GET_FIELDS,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.GET_FIELDS}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.GET_FIELDS}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.GET_FIELDS}.")
        return None

    async def stream(self, stream_object: dict) -> AsyncGenerator:
        """Open stream connection to connector.

        Args:
            stream_url: url to stream from.
        """
        stream_url: str | None = stream_object.get("stream_url")
        headers: dict | None = stream_object.get("required_headers")

        if stream_url is None or headers is None:
            dms_warning("Recieved an empty field from gateway.")
            return

        async with AsyncClient() as client:
            raw = ""
            prev_subdata: str | None = self.subdata.get(stream_url)
            subdata: str | None = None
            data: dict
            async with client.stream(
                "POST",
                stream_url,
                timeout=TIMEOUT,
                headers=list(headers.items()),
                json={"subdata": prev_subdata} if prev_subdata is not None else None,
            ) as stream:
                async for chunk in stream.aiter_text():
                    raw += chunk
                    try:
                        if not raw.endswith("}"):
                            continue
                        data = json.loads(raw)
                        raw = ""
                    except json.JSONDecodeError:
                        continue
                    if subdata is None and "subdata" in data:
                        subdata = data.get("subdata")
                        continue
                    yield data
                self.subdata[stream_url] = subdata

    async def fetch_files(self, pointers: list[str], authorization: str | None) -> list[dict] | None:
        """Grab all files from the connectors pointed at by the pointers.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        response: Any | None = await self._get_file_from_pointers(pointers, authorization)
        if not isinstance(response, list):
            return None
        return response

    async def _get_file_from_pointers(self, pointers: list[str], authorization: str | None) -> Any | None:
        """Get file from pointer"""
        try:
            response = await self.client.post(
                self.GET_FILE_ENDPOINT,
                headers=[("Authorization", authorization)] if authorization is not None else None,
                params=[("include_content", False), ("include_last_edit_date", True)],
                json={"file_pointers": pointers},
                timeout=TIMEOUT,
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
