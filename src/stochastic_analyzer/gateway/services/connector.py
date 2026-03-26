"""Services regarding the connector."""

from json.decoder import JSONDecodeError

from asyncio import create_task

from dmis_logger import dms_warning
from httpx import AsyncClient, HTTPError

from gateway.schemas import InputItem, MetadataTemplate

async def _get_content(url: str, pointer: str, client: AsyncClient) -> InputItem | None:
    """Get the content of a file.

    Args:
        url: Connector url
        pointer: file pointer
        client: AsyncClient connection.
    Returns: InputItem on success else None
    """

    content: str | None = None
    try:
        response = (await client.get(url, params=[("file_pointer", pointer)], timeout=120)).json()
        content = response.get("content")
    except HTTPError as err:
        dms_warning(f"HTTP Exception for {err.request.url} - {err}")
    except JSONDecodeError as err:
        dms_warning(f"Failed parsing JSON response: {err.doc}")

    if content is None:
        dms_warning(f"Content is none, pointer: {pointer}")
        return None

    return InputItem(content=content, metadata=MetadataTemplate()) # What is metadata? IDK

async def get_file_contents(connector_url: str, pointers: list[str]) -> list[InputItem]:
    """Get the contents from all files pointed at.

    Args:
        connector_url: url to connector
        pointers: list of unique file pointers
    
    Returns: list of InputItems
    """

    async with AsyncClient() as client:
        file_gatherers = [create_task(_get_content(connector_url, pointer, client)) for pointer in pointers]
        results: list[InputItem] = []
        for gatherer in file_gatherers:
            result: InputItem | None = await gatherer
            if result is not None:
                results.append(result)

    return results

