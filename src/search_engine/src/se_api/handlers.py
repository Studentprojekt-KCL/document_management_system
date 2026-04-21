"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from asyncio import Lock, Queue, create_task, get_event_loop
from datetime import datetime
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

    WORKERS: int = 8
    indexing: Lock

    def __init__(self) -> None:
        """Constructor"""
        self.connector = Connector()
        self.search_engine = SearchEngine()
        self.query = Query()
        self.indexing = Lock()

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

        dms_info(f"Preforming search: {request}")
        if await self.connector.reindex_needed() and not self.indexing.locked():  # This endpoint is approx 3x faster
            loop = get_event_loop()
            loop.create_task(self._handle_new())

        matches: list = self.search_engine.query_files(request, offset + count)[offset : count + offset]
        files: list[dict] = await self.connector.fetch_files(matches)
        self.clean_misses(matches, files)
        classifications: dict = await self.query.classify(files)
        for file in files:
            unique_pointer: str = file.get("unique_pointer", "")
            classification: str = classifications.get(unique_pointer, "")
            file.update({"security_class": classification})

        return files

    async def _handle_new(self) -> None:
        """Grab connector stream output and pipe it into search engine."""
        await self.indexing.acquire()
        start = datetime.now()
        task_queue: Queue = Queue()
        raw: str = ""
        data: dict
        subdata: str | None = None

        index_tasks: list = [create_task(self._add_file(task_queue)) for _ in range(self.WORKERS)]

        self.search_engine.init()
        async for chunk in self.connector.streaming_fetch():
            raw += chunk
            try:
                data = json.loads(raw)
                raw = ""
            except json.JSONDecodeError:
                continue
            if subdata is None and data.get("subdata") is not None:
                subdata = data.get("subdata")
                continue
            await task_queue.put(data)
        self.connector.subdata = subdata

        await task_queue.join()
        for _ in index_tasks:
            await task_queue.put(None)
        self.search_engine.close()
        self.indexing.release()
        dms_info(f"Total handle time: {datetime.now() - start}")

    async def _add_file(self, task_queue: Queue) -> None:
        """Wait for formatted file and add it to the search engine.

        Args:
            task_queue: queue containing all the files to add.
        """

        while True:
            file: dict | None = await task_queue.get()
            if file is None:
                break
            self.search_engine.add_file(file)
            task_queue.task_done()
