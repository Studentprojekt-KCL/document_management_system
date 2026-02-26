"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
from datetime import datetime
from requests import get, exceptions

from se_api.exceptions import SeAPIException
from se_api.models import File, Metadata

from logger import dms_error  # pylint: disable=no-name-in-module


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

        response = get(f"{self.address}/files", params=params).json()

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

    def get_file(self, pointer: str) -> File | None:
        """Graps a file from the connectors.

        Args:
            pointer: file pointer.

        Returns:
           The file or None.

        Raises:
            SeAPIException: Potential formatting errors.
        """
        try:
            response = get(f"{self.address}/file", params={"file_pointer": pointer}).json()
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

            file: File = File(
                content=content,
                metadata=Metadata(
                    unique_pointer=unique_pointer,
                    name=name,
                    size=size,
                    edited=datetime.fromisoformat(edited),
                    type=contnet_type,
                ),
            )

            return file
        except exceptions.InvalidJSONError as e:
            dms_error(e.strerror if e.strerror is not None else "")

        return None

    def get_files(self) -> list[File]:
        """Grab all new files from connectors.

        Returns:
            A list of files.
        """
        pointers: list[str] = self.get_file_pointers()
        files: list[File] = []
        count: int = 0

        for pointer in pointers:
            file: File | None = self.get_file(pointer)
            if file is not None:
                files.append(file)
            count += 1
            print(f"{count}/{len(pointers)}")

        return files
