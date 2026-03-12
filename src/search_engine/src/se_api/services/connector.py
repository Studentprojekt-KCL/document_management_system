"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
from typing import Any
from dmis_logger import dms_error, dms_warning
from requests import get
from requests.exceptions import HTTPError, JSONDecodeError, RequestException, Timeout, ConnectionError


class Connector:
    """Connector service

    Manages all requests and file fetches from the connectors.

    Attributes:
        address: address to connector.
        subdata: connector file status.
    """

    address: str | None
    subdata: str | None

    url_files: str
    url_files_to_index: str
    url_file: str

    def __init__(self) -> None:
        address = environ.get("SE_API_CONNECTOR_ADDRESS", None)
        if address is None:
            dms_error("SE_API_CONNECTOR_ADDRESS is not set.")
        self.address = address
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
        response: Any | None = None
        try:
            response = get(
                self.url_files, params=[("subdata", self.subdata)] if self.subdata is not None else None, timeout=120
            ).json()
        except ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files}.")
        except HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files}.")
        except Timeout:
            dms_warning(f"Request timed out, url: {self.url_files}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files}.")
        except RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")

        if response is None:
            return []

        if not isinstance(response, dict):
            return []

        pointers = response.get("file_pointers")
        return pointers if pointers is not None else []

    def get_file(self, pointer: str) -> dict | None:
        """Graps a file from the connectors.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        response: Any | None = None
        try:
            response = get(
                self.url_file,
                params=[("file_pointer", pointer), ("include_content", False)] if self.subdata is not None else None,
                timeout=120,
            ).json()
        except ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_file}.")
        except HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_file}.")
        except Timeout:
            dms_warning(f"Request timed out, url: {self.url_file}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_file}.")
        except RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")

        if response is None:
            return None

        if not isinstance(response, dict):
            dms_warning("File is not formated as a dict.")
            return None

        return response

    def get_files(self) -> list:
        """Grab all new files pointers from connectors.

        Returns:
            A list of files.
        """

        file_url = self._files_to_index()
        if file_url is None:
            return []

        response: Any | None = None

        try:
            response = get(file_url, timeout=120).json()
        except ConnectionError:
            dms_warning(f"Failed to connect, url: {file_url}.")
        except HTTPError:
            dms_warning(f"Invalid HTTP response, url: {file_url}.")
        except Timeout:
            dms_warning(f"Request timed out, url: {file_url}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {file_url}.")
        except RequestException:
            dms_warning(f"Something went wrong, url: {self.url_files}.")

        if response is None:
            return []

        data = response.get("files")
        subdata = response.get("subdata")

        if data is None:
            dms_warning("No files in collector response.")
            return []
        if subdata is None:
            dms_warning("No subdata delievered by collector.")
        self.subdata = subdata

        return data

    def _files_to_index(self) -> str | None:
        """Get the url for the file containing all new files."""

        response: Any | None = None
        try:
            response = get(
                self.url_files_to_index, params=[("subdata", self.subdata)] if self.subdata is not None else None, timeout=120
            ).json()
        except ConnectionError:
            dms_warning(f"Failed to connect, url: {self.url_files_to_index}.")
        except HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.url_files_to_index}.")
        except Timeout:
            dms_warning(f"Request timed out, url: {self.url_files_to_index}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.url_files_to_index}.")
        except RequestException as e:
            dms_warning(f"Something went wrong, url: {self.url_files}.")

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
