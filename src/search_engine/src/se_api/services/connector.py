"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
from dmis_logger import dms_error, dms_warning
from requests import get
from requests.exceptions import JSONDecodeError


class Connector:
    """Connector service

    Manages all requests and file fetches from the connectors.

    Attributes:
        address: address to connector.
        subdata: connector file status.
    """

    address: str | None
    subdata: str | None

    def __init__(self) -> None:
        address = environ.get("SE_API_CONNECTOR_ADDRESS", None)
        if address is None:
            dms_error("Expected connector address.")

        self.address = address
        self.subdata = None

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
        params: dict[str, str] = {}
        if self.subdata is not None:
            params.update({"subdata": self.subdata})
        response = get(f"{self.address}/files", params=params, timeout=120).json()

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

        response = get(f"{self.address}/file", params={"file_pointer": pointer}, timeout=120).json()

        if not isinstance(response, dict):
            dms_error("File is not formated as a dict.")
            return None

        if response.get("metadata") is None:
            dms_error("File has no metadata.")
            return None

        if response.get("content") is None:
            dms_error("File has no content.")
            return None

        return response

    def get_files(self) -> list:
        """Grab all new files from connectors.

        Returns:
            A list of files.
        """

        file_url = self._files_to_index()
        if file_url is None:
            return []

        response = get(file_url, timeout=120).json()

        data = response.get("files")

        if data is None:
            dms_error("No files in collector response.")
            return []

        subdata = response.get("subdata")

        if subdata is None:
            dms_warning("No subdata delievered by collector.")

        self.subdata = subdata

        return data

    def _files_to_index(self) -> str | None:
        """Get the url for the ziped file containing all new files."""
        try:
            param = {"subdata": self.subdata} if self.subdata is not None else None
            response = get(f"{self.address}/files_to_index", params=param, timeout=120).json()
            subdata = response.get("subdata")
            file_url = response.get("file_url")

            if subdata is None:
                dms_warning("No subdata delievered by collector.")
            if file_url is None:
                dms_error("No returned collection URL.")

            self.subdata = subdata

            return file_url
        except JSONDecodeError as e:
            dms_error(e.msg)
            return None
