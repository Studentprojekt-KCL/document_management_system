from os import environ
from datetime import datetime
from logger import dms_error
from requests import Session, get, exceptions
import threading

from se_api.exceptions import SeAPIException
from se_api.models import File, Metadata

class Connector:
    address: str | None
    subdata: str | None

    def __init__(self):
        address = environ.get("SE_API_CONNECTOR_ADDRESS", None)
        if address is None:
            raise SeAPIException(f"SE_API_CONNECTOR_ADDRESS is not defined.")

        self.address = address
        self.subdata = None

    def get_file_pointers(self) -> list[str]:
        if self.address is None:
            raise SeAPIException(f"SE_API_CONNECTOR_ADDRESS is not defined.")

        params: dict[str, str] = {}

        if self.subdata is not None:
            params.update({"subdata": self.subdata})

        response = get(f"{self.address}/files", params=params).json()

        if not isinstance(response, dict):
            return []

        file_pointers: list[str] = []
        pointers = response["file_pointers"]

        if not isinstance(pointers, list):
            raise SeAPIException(f"Expected results to be list[str].")

        if not isinstance(response["subdata"], str):
            raise SeAPIException(f"Expected subdata to be str.")

        for pointer in pointers:
            if isinstance(pointer, str):
                file_pointers.append(pointer)

        self.subdata = response["subdata"]

        return file_pointers

    def get_file(self, pointer: str, session: Session | None = None) -> File | None:
        file: File | None = None

        s: Session
        if session is None:
            s = Session()
        else:
            s = session


        try:            
            response = s.get(f"{self.address}/file", params={"file_pointer": pointer}).json()
            if not isinstance(response["metadata"], dict):
                raise SeAPIException("")

            unique_pointer = response["metadata"]["unique_pointer"]
            name = response["metadata"]["name"]
            size = response["metadata"]["size"]
            edited = response["metadata"]["last_edit_date"]
            type = response["metadata"]["type"]
            content = response["content"]

            if not isinstance(unique_pointer, str): raise SeAPIException("")
            if not isinstance(name, str): raise SeAPIException("")
            if not isinstance(size, int): raise SeAPIException("")
            if not isinstance(edited, str): raise SeAPIException("")
            if not isinstance(type, str): raise SeAPIException("")
            if not isinstance(content, str): raise SeAPIException("")

            file = File(
                content=content,
                metadata=Metadata(
                    unique_pointer=unique_pointer,
                    name=name,
                    size=size,
                    edited=datetime.fromisoformat(edited),
                    type=type
                )
            )

        except exceptions.InvalidJSONError as e:
            dms_error(e.strerror if e.strerror is not None else "") 

        if session is None:
            s.close()

        return file

    def get_files(self) -> list[File]:
        pointers: list[str] = self.get_file_pointers()
        files: list[File] = []

        with Session() as session:
            for pointer in pointers:
                file: File | None = self.get_file(pointer, session)
                if file is not None:
                    files.append(file)

        return files

