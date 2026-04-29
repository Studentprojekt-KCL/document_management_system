"""File for managing the content and metadata retreival from the connector"""

from base64 import b64decode

import aiohttp

from gateway.schemas import InputItem, MetadataTemplate

from shared_functions.dmis_logger import dms_warning
from shared_functions.initialisation_tools import read_env_variable


class Connector:
    """Fetches file content from connector gateway."""

    TIMEOUT: int = 120

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
        except (aiohttp.ClientError, TimeoutError) as err:
            dms_warning(f"Connector request failed: {err}")
            return []

        items = []
        for entry in data:
            content = self._decode(entry.get("content"))
            if content is None:
                continue
            items.append(
                InputItem(
                    content=content,
                    metadata=MetadataTemplate(unique_pointer=entry.get("unique_pointer", "")),
                )
            )
        return items

    @staticmethod
    def _decode(encoded: str | None) -> str | None:
        if encoded is None:
            dms_warning("Empty content cant be decoded")
            return None
        try:
            return b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            dms_warning("decoding failed")
            return None
