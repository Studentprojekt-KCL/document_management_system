"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from fastapi import HTTPException
from se_api.services.connector import Connector
from se_api.services.query import Query
from se_api.services.search_engine import SearchEngine

from shared_functions.dmis_logger import dms_info, dms_warning


class Handler:
    """Handler for internal processing.

    Attributes:
        connector: Connector service.
        search_engine: Search engine service.
    """

    connector: Connector
    query: Query
    search_engine: SearchEngine

    def __init__(self) -> None:
        """Constructor"""
        self.connector = Connector()
        self.search_engine = SearchEngine()
        self.query = Query()

    async def init(self) -> None:
        """Init handler"""
        await self.query.init()

    async def close(self) -> None:
        """Clean up"""
        await self.query.close()
        await self.connector.close()

    def reset(self) -> None:
        """Reset the connector."""
        self.search_engine = SearchEngine()
        self.connector = Connector()
        self.query.reset()
        self.query = Query()
        dms_info("Search engine was reset.")

    def set_classification(self, change: dict[str, str]) -> dict[str, str]:
        """Set the classification of a file.

        Args:
            change: dict containing the unique pointer and new classification.
        Returns: dict containing the unique pointer, classification, and if edited.
        """

        pointer: str | None = change.get("unique_pointer")
        classification: str | None = change.get("classification")
        if pointer is None or classification is None:
            raise HTTPException(status_code=400)
        file: dict | None = self.query.set_classification(pointer, classification)
        if file is None:
            raise HTTPException(status_code=400)
        return file

    def clean_misses(self, matches: list[str], grabbed: list[dict]) -> None:
        """Remove missing files from cache and index.

        Args:
            matches: list of pointers
            grabbed: list of file dicts.
        """

        grabs = [grab.get("unique_pointer") for grab in grabbed]
        for match in matches:
            if match in grabs:
                continue
            self.search_engine.remove_file(match)
            self.query.cache.remove_classification(match)

    async def preform_search(self, request: str, count: int, offset: int) -> list:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.

        Returns:
            Returns matching files or None.
        """

        if count <= 0:
            dms_warning(f"Count result count is invalid. (count: {count}).")
            return []
        if offset < 0:
            dms_warning(f"Offset is invalid. (offset: {offset}).")
            return []

        if await self.connector.reindex_needed():  # This endpoint is approx 3x faster
            self.search_engine.init()
            raw: str = ""
            data: dict
            subdata: str | None = None
            async for chunk in self.connector.streaming_fetch():
                raw += chunk
                try:
                    data: dict = json.loads(raw)
                    raw = ""
                except json.JSONDecodeError:
                    continue

                if subdata is None and data.get("subdata") is not None:
                        subdata = data.get("subdata")
                self.search_engine.add_file(data)
            self.search_engine.commit()
            self.connector.subdata = subdata

        matches: list = self.search_engine.query_files(request, offset + count)[offset : count + offset]
        files: list[dict] = await self.connector.fetch_files(matches)
        self.clean_misses(matches, files)
        classifications: dict = await self.query.classify(files)
        for file in files:
            unique_pointer: str = file.get("unique_pointer", "")
            classification: str = classifications.get(unique_pointer, "")
            file.update({"security_class": classification})

        return files
