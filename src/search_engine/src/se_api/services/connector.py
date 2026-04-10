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

    index_needed_bool: str
    url_files_to_index: str
    url_get_files: str

    def __init__(self) -> None:
        address = environ.get("SE_API_CONNECTOR_ADDRESS", None)
        if address is None:
            dms_error("SE_API_CONNECTOR_ADDRESS is not set.")
            return
        self.address = address.rstrip("/")
        self.subdata = None
        self.index_needed_bool = f"{self.address}/index_needed_bool"
        self.url_files_to_index = f"{self.address}/files_to_index"
        self.url_get_files = f"{self.address}/get_files"

    def reset(self) -> None:
        """Resets the subdata, getting all files."""
        self.subdata = None

    def reindex_needed(self) -> bool:
        """Check if new reindex is required."""
        try:
            response = get(
                self.index_needed_bool,
                timeout=Connector.TIMEOUT,
                params=[("subdata", self.subdata)] if self.subdata is not None else None,
            ).json()
            if not isinstance(response, dict):
                return True

            return not response.get("index_needed") is False
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.index_needed_bool}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.index_needed_bool}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.index_needed_bool}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.index_needed_bool}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.index_needed_bool}.")
        return True

    def fetch_files(self, pointers: list[str]) -> list[dict]:
        """Grab all files from the connectors pointed at by the pointers.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        client: Session = Session()
        response: Any | None = self._get_file_from_pointer(pointers, client)

        if not isinstance(response, list):
            return []

        client.close()

        return response

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
        subdata = response.get("subdata")

        if data is None:
            dms_warning("No files in collector response.")
            return []
        if subdata is None:
            dms_warning("Connector returned empty subdata.")

        self.subdata = subdata
        return data

    def _files_to_index(self) -> str | None:
        """Get the url for the file containing all new files."""

        response: Any | None = self._get_file_to_index()
        if response is None or not isinstance(response, dict) or response.get("index_needed") is False:
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

    def _get_file_from_pointer(self, pointers: list[str], client: Session) -> Any | None:
        """Get file from pointer"""
        try:
            return client.post(
                self.url_get_files,
                params=[("include_content", False), ("include_last_edit_date", True)],
                json={"file_pointers": pointers},
                timeout=Connector.TIMEOUT,
            ).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_get_files}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_get_files}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.url_get_files}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_get_files}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.url_get_files}.")
        return None

    def _get_files_from_url(self, url: str) -> Any | None:
        """Get files from url"""
        try:
            return get(url, timeout=Connector.TIMEOUT).json()
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {url}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {url}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {url}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {url}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {url}.")
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
            dms_warning(f"Something went wrong, url: {self.url_files_to_index}.")
        return None
