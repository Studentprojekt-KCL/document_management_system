"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import base64
from threading import Thread
import queue

from asyncio import AbstractEventLoop, Lock, Queue, create_task, get_event_loop
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

    WORKERS: int = 16  # Format and send workers
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

    async def preform_search(self, request: str | None, count: int, offset: int) -> list:
        """Get get files from collectors preform the search, returns a list.

        Args:
            request: Query to perform.
            count: how many results.
            offset: how deep in to grab the results.
        Returns: matching files or None.
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

        if request is None:
            return []
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
        dms_info("Starting indexing of new files.")
        start = datetime.now()
        index_queue: queue.Queue = queue.Queue()
        transfer_queue: Queue = Queue()

        indexer_thread: Thread = Thread(target=self._add_file, args=(index_queue,))

        raw: str = ""
        data: dict
        subdata: str | None = None

        indexer_thread.start()
        loop = get_event_loop()

        transfer_tasks: list = [create_task(self._transfer_file(index_queue, transfer_queue, loop)) for _ in range(self.WORKERS)]

        async for chunk in self.connector.streaming_fetch():
            raw += chunk
            try:
                if not raw.endswith("}"):
                    continue
                data = json.loads(raw)
                raw = ""
            except json.JSONDecodeError:
                continue
            if subdata is None and data.get("subdata") is not None:
                subdata = data.get("subdata")
                continue
            await transfer_queue.put(data)
        self.connector.subdata = subdata
        dms_info(f"Finished fetching new files, time: {(datetime.now() - start).total_seconds()}s.")

        await transfer_queue.join()
        for _ in transfer_tasks:
            await transfer_queue.put(None)
        dms_info(f"Formatted and transferred files to indexer, time: {(datetime.now() - start).total_seconds()}s.")
        await loop.run_in_executor(None, index_queue.join)
        await loop.run_in_executor(None, index_queue.put, None)
        await loop.run_in_executor(None, indexer_thread.join)
        self.indexing.release()
        dms_info(f"Finished indexing of new files, time: {(datetime.now() - start).total_seconds()}s.")

    async def _transfer_file(self, index_queue: queue.Queue, transfer_queue: Queue, loop: AbstractEventLoop) -> None:
        """Format and transfer file to search engine indexing queue.

        index_queue: queue containing all the ready files to index.
        transfer_queue: queue of raw dicts with file data.
        loop: global event loop.
        """

        while True:
            file: dict | None = await transfer_queue.get()
            if file is None:
                break
            flat_file: dict | None = self._decode(file)
            if flat_file is None:
                continue
            await loop.run_in_executor(None, index_queue.put, flat_file)
            transfer_queue.task_done()

    def _decode(self, file: dict) -> dict | None:
        """Decode file content.

        Args:
            file: dict containing the content in base64.
        Returns: dict with decoded file content, or none on failure.
        """
        flat_file = self._flatten_dict(file)
        content: str | None = flat_file.get("content")

        if content is None:
            dms_warning("File is missing content.")
            return None
        content_bytes: bytes = base64.b64decode(content)
        content = content_bytes.decode("utf-8")
        flat_file["content"] = content

        return flat_file

    def _add_file(self, index_queue: queue.Queue) -> None:
        """Wait for formatted file and add it to the search engine.

        Args:
            task_queue: queue containing all the files to add.
        """

        with self.search_engine:
            while True:
                file: dict | None = index_queue.get()
                if file is None:
                    break
                self.search_engine.add_file(file)
                index_queue.task_done()

    def _flatten_dict(self, d: dict) -> dict:
        """Flatten the dict.

        Args:
            d: dict to flatten.
        Return: a flat dict.
        """

        flat: dict = {}

        for key, val in d.items():
            if isinstance(val, dict):
                flat.update(self._flatten_dict(val))
            else:
                flat.update({key: str(val)})

        return flat
