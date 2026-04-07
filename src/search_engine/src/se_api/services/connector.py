"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
from typing import Any
from dmis_logger import dms_error, dms_warning
from requests import Session, get
from requests import exceptions


class Connector:
    """Connector service

    Manages all requests and file fetches from the connectors.

    Attributes:
        address: address to connector.
        subdata: connector file status.
    """

    TIMEOUT: int = 120

    address: str
    subdata: str | None

    url_files: str
    url_files_to_index: str
    url_file: str

    def __init__(self) -> None:
        address = environ.get("SE_API_CONNECTOR_ADDRESS", None)
        if address is None:
            dms_error("SE_API_CONNECTOR_ADDRESS is not set.")
            return
        self.address = address.rstrip("/")
        self.subdata = None
        self.url_files = f"{self.address}/files"
        self.url_files_to_index = f"{self.address}/files_to_index"
        self.url_file = f"{self.address}/file"

    def reset(self) -> None:
        """Resets the subdata, getting all files."""
        self.subdata = None

    def get_file_pointers(self) -> list[str]:
        """Fetch file pointers from connectors.

        Returns:
            List of file pointers.

        Raises:
            SeAPIException: For potential formatting errors.
        """
        response: Any | None = self._get_file_pointers()

        if response is None:
            return []

        if not isinstance(response, dict):
            return []

        pointers = response.get("file_pointers")
        return pointers if pointers is not None else []

    def fetch_files(self, pointers: list[str]) -> list[dict]:
        """Grab all files from the connectors pointed at by the pointers.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        response: Any | None = self._get_file_from_pointer(pointer)
        client: Session = Session()
        responses: list[dict] = []
        for pointer in pointers:
            response: Any | None = self._get_file_from_pointer(pointer, client)
            if not isinstance(response, dict):
                continue
            metadata: dict | None = response.get("metadata")
            if metadata is None:
                continue
            responses.append(metadata)

        client.close()

        return responses

    def get_files(self) -> list:
        """Grab all new files pointers from connectors.

        Returns:
            A list of files.
        """

        file_url = self._files_to_index()
        if file_url is None:
            return []

        response: Any | None = self._get_files_from_url(file_url)
        if response is None:
            return []
        if not isinstance(response, dict):
            dms_warning("Response is not formatted as a dict.")
            return []

        data = response.get("files")

        if data is None:
            dms_warning("No files in collector response.")
            return []

        return data

    def _files_to_index(self) -> str | None:
        """Get the url for the file containing all new files."""

        response: Any | None = self._get_file_to_index()
        if response is None:
            return None
        if not isinstance(response, dict):
            dms_warning(f"Response is not formated as a dict, url: {self.url_files_to_index}.")
            return None

        subdata = response.get("subdata")
        file_url = response.get("file_url")

        if subdata is None:
            dms_warning("No subdata delievered by collector.")
        if file_url is None:
            dms_warning("No returned collection URL.")

        self.subdata = subdata

        return file_url

    def _get_file_pointers(self) -> Any | None:
        """Get file pointers"""
        try:
            return get(
                self.url_files, params=[("subdata", self.subdata)] if self.subdata is not None else None, timeout=Connector.TIMEOUT
            ).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files_to_index}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files_to_index}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.url_files_to_index}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files_to_index}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")
        return None

    def _get_file_from_pointer(self, pointer: str, client: Session) -> Any | None:
        """Get file from pointer"""
        try:
            return client.get(
                self.url_file,
                params=[("file_pointer", pointer), ("include_content", False)],
                timeout=Connector.TIMEOUT,
            ).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files_to_index}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files_to_index}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.url_files_to_index}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files_to_index}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")
        return None

    def _get_files_from_url(self, url: str) -> Any | None:
        """Get files from url"""
        try:
            return get(url, timeout=Connector.TIMEOUT).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files_to_index}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files_to_index}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.url_files_to_index}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files_to_index}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")
        return None

    def _get_file_to_index(self) -> Any | None:
        """Get file to index"""
        try:
            return get(
                self.url_files_to_index,
                params=[("subdata", self.subdata)] if self.subdata is not None else None,
                timeout=Connector.TIMEOUT,
            ).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files_to_index}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files_to_index}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.url_files_to_index}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files_to_index}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")
        return None
