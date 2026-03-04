"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from logging import error
from os import environ
from datetime import datetime
from requests import get, exceptions, Session

from se_api.exceptions import SeAPIException
from se_api.models import File, Metadata

# from logger import dms_error  # pylint: disable=no-name-in-module


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
            raise SeAPIException("SE_API_CONNECTOR_ADDRESS is not defined.")

        self.address = address
        self.subdata = None

    def get_file_pointers(self) -> list[str]:
        """Fetch file pointers from connectors.

        Returns:
            List of file pointers.

        Raises:
            SeAPIException: For potential formatting errors.
        """
        if self.address is None:
            raise SeAPIException("SE_API_CONNECTOR_ADDRESS is not defined.")

        params: dict[str, str] = {}

        if self.subdata is not None:
            params.update({"subdata": self.subdata})

        response = get(f"{self.address}/files", params=params, timeout=120).json()

        if not isinstance(response, dict):
            return []

        file_pointers: list[str] = []
        pointers = response["file_pointers"]

        if not isinstance(pointers, list):
            raise SeAPIException("Expected results to be list[str].")

        if not isinstance(response["subdata"], str):
            raise SeAPIException("Expected subdata to be str.")

        for pointer in pointers:
            if isinstance(pointer, str):
                file_pointers.append(pointer)

        self.subdata = response["subdata"]

        return file_pointers

    def get_file(self, pointer: str, session: Session | None = None) -> File | None:
        """Graps a file from the connectors.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """

        file: File | None = None

        s: Session
        if session is None:
            s = Session()
        else:
            s = session

        try:
            response = get(f"{self.address}/file", params={"file_pointer": pointer}, timeout=120).json()
            if not isinstance(response["metadata"], dict):
                raise SeAPIException("")

            unique_pointer = response["metadata"]["unique_pointer"]
            name = response["metadata"]["name"]
            size = response["metadata"]["size"]
            edited = response["metadata"]["last_edit_date"]
            contnet_type = response["metadata"]["type"]
            content = response["content"]

            if not isinstance(unique_pointer, str):
                raise SeAPIException("")
            if not isinstance(name, str):
                raise SeAPIException("")
            if not isinstance(size, int):
                raise SeAPIException("")
            if not isinstance(edited, str):
                raise SeAPIException("")
            if not isinstance(contnet_type, str):
                raise SeAPIException("")
            if not isinstance(content, str):
                raise SeAPIException("")

            file = File(
                content=content,
                metadata=Metadata(
                    unique_pointer=unique_pointer,
                    name=name,
                    size=size,
                    edited=datetime.fromisoformat(edited),
                    type=contnet_type,
                ),
            )

        except exceptions.InvalidJSONError as e:
            error(e.strerror if e.strerror is not None else "")

        if session is None:
            s.close()

        return file

    def get_files(self) -> list[File]:
        """Grab all new files from connectors.

        Returns:
            A list of files.
        """
        pointers: list[str] = self.get_file_pointers()
        files: list[File] = []

        with Session() as session:
            for pointer in pointers:
                file: File | None = self.get_file(pointer, session)
                if file is not None:
                    files.append(file)

        return files
