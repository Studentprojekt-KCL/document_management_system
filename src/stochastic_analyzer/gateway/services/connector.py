"""File for managing the content and metadata retreival from the connector"""

from base64 import b64decode
from io import BytesIO

import asyncio
import aiohttp
from markitdown import MarkItDown, FileConversionException, UnsupportedFormatException


from gateway.schemas import InputItem, MetadataTemplate

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Connector:
    """Fetches file content from connector gateway."""

    TIMEOUT: int = 120
    _converter = MarkItDown()

    def __init__(self) -> None:
        self.url = read_env_variable("STOCHAN_CONGATEWAY_URL").rstrip("/")
        self.session: aiohttp.ClientSession

    async def init(self) -> None:
        """Open the HTTP session."""
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close HTTP session."""
        await self.session.close()

    async def get_file_contents(self, pointers: list[str]) -> list[InputItem]:
        """Get file content from connector"""
        try:
            async with self.session.post(
                f"{self.url}/get_files",
                params={"include_content": "true", "include_last_edit_date": "false"},
                json={"file_pointers": pointers},
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            dms_warning(f"Connector request failed: {err}")
            return []

        items = []
        for entry in data:
            pointer = entry.get("unique_pointer")
            if not pointer:
                dms_warning("connector entry missing pointer.")
                continue
            content = await asyncio.to_thread(self._extract_text, entry.get("content"))
            if content is None:
                continue
            items.append(
                InputItem(
                    content=content,
                    metadata=MetadataTemplate(unique_pointer=pointer)),
                )
            )
        return items

    @staticmethod
    def _extract_text(encoded: str | None) -> str | None:
        """Decode payload and extract text. Tries markitdown first, falls back to utf-8."""
        if encoded is None:
            return None
        try:
            raw = b64decode(encoded)
        except ValueError as err:
            dms_warning(f"Base64 decode failed: {err}")
            return None

        try:
            return Connector._converter.convert_stream(BytesIO(raw)).text_content
        except (FileConversionException, UnsupportedFormatException):
            pass

        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            dms_warning("Could not extract text from content")
            return None
