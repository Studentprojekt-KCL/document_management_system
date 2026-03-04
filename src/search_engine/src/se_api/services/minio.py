from datetime import datetime
from os import environ
import re
from typing import Any

from minio import Minio
from minio.datatypes import Object
from urllib3 import BaseHTTPResponse

from se_api.exceptions import SeAPIException
from se_api.models.file import File
from se_api.models.metadata import Metadata

class MinIO:
    host: str
    user: str
    password: str
    bucket: str

    def __init__(self) -> None:
        host: str | None = environ.get("SE_MINIO_HOST")
        user: str | None = environ.get("SE_MINIO_USER")
        password: str | None = environ.get("SE_MINIO_PASSWORD")
        bucket: str | None = environ.get("SE_MINIO_BUCKET")

        if host is None:
            raise SeAPIException("Environment varibale SE_MINIO_HOST is not set.")
        if user is None:
            raise SeAPIException("Environment varibale SE_MINIO_USER is not set.")
        if password is None:
            raise SeAPIException("Environment varibale SE_MINIO_PASSWORD is not set.")
        if bucket is None:
            raise SeAPIException("Environment varibale SE_MINIO_BUCKET is not set.")

        self.host = host
        self.user = user
        self.password = password
        self.bucket = bucket

    def _connect(self) -> Minio:
        client = Minio(
            self.host,
            access_key=self.user,
            secret_key=self.password,
            secure=False
        )

        if not client.bucket_exists(self.bucket):
            raise SeAPIException(f"Bucket {self.bucket} doesn't exist.")

        return client

    def _get_object(self) -> list[Any]:
        client = self._connect()

        response: BaseHTTPResponse = client.get_object(self.bucket, "myfile.json")
        data = response.json()
        response.close()
        response.release_conn()

        if not isinstance(data, list):
            raise SeAPIException("")

        return data

    def get_files(self, pointers: list[str]) -> list[File]:
        data: list[Any] = self._get_object()
        files: list[File] = []
        print(data)
        for item in data:
            unique_pointer: str | None = None

            name = item["metadata"]["name"]
            size = item["metadata"]["size"]
            # edited = item["metadata"]["last_edit_date"]
            # contnet_type = item["metadata"]["type"]
            content = item["content"]

            # if unique_pointer not in pointers:
            #     continue


            if not isinstance(name, str):
                raise SeAPIException("Name is not of type str.")
            if not isinstance(size, int):
                raise SeAPIException("Size is not of type int.")
            # if not isinstance(edited, str):
            #     raise SeAPIException("")
            # if not isinstance(contnet_type, str):
            #     raise SeAPIException("")
            if not isinstance(content, str):
                raise SeAPIException("Content is not of type str.")

            for pointer in pointers:
                match = re.search(name, pointer)
                if isinstance(match, re.Match):
                    unique_pointer = match.string

            if not isinstance(unique_pointer, str):
                raise SeAPIException("Unique pointer is not of type str.")

            file = File(
                content=content,
                metadata=Metadata(
                    unique_pointer=unique_pointer,
                    name=name,
                    size=size,
                    # edited=datetime.fromisoformat(edited),
                    # type=contnet_type,
                ),
            )

            files.append(file)

        return files


