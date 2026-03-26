"""Services regarding the connector."""

from json.decoder import JSONDecodeError
from os import environ

from asyncio import create_task

from dmis_logger import dms_error, dms_warning
from httpx import AsyncClient, HTTPError

from gateway.schemas import InputItem, MetadataTemplate

class ConnectorService:
    FILE_ENDPOINT: str = "/file"

    url: str

    def __init__(self) -> None:
        address = environ.get("CONNECTOR_ADDRESS")

        if address is None:
            dms_error("CONNECTOR_ADDRESS is not defined.")
            return

        self.url = address.rstrip("/") + "/" + self.FILE_ENDPOINT

    async def _get_content(self, pointer: str, client: AsyncClient) -> InputItem | None:
        content: str | None = None
        try:
            response = (await client.get(self.url, params=[("file_pointer", pointer)], timeout=120)).json()
            content = response.get("content")
        except HTTPError as err:
            dms_warning(f"HTTP Exception for {err.request.url} - {err}")
        except JSONDecodeError as err:
            dms_warning(f"Failed parsing JSON response: {err.doc}")

        if content is None:
            dms_warning(f"Content is none, pointer: {pointer}")
            return None

        return InputItem(content=content, metadata=MetadataTemplate()) # What is metadata? IDK

    async def get_file_contents(self, pointers: list[str]) -> list[InputItem]:
        async with AsyncClient() as client:
            file_gatherers = [create_task(self._get_content(pointer[0], client)) for pointer in pointers]
            results: list[InputItem] = []
            for gatherer in file_gatherers:
                result: InputItem | None = await gatherer
                if result is not None:
                    results.append(result)

        return results

