"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import base64
from threading import Thread
import queue

from asyncio import Lock, Queue, create_task, get_event_loop
from datetime import datetime
from fastapi import HTTPException
import httpx
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

    WORKERS: int = 8  # Format and send workers
    BATCH_SIZE: int = 10_000
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
        self.search_engine.init()

    async def close(self) -> None:
        """Clean up"""
        await self.query.close()
        await self.connector.close()

    def reset(self) -> None:
        """Reset the connector."""
        self.search_engine.reset()
        self.connector.write_subdata({})
        self.query.reset()
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
        if not self.indexing.locked():
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
        fetch_queue: Queue = await self.connector.connector_fetch()
        index_queue: queue.Queue = queue.Queue()
        transfer_queue: Queue = Queue()
        indexer_thread: Thread = Thread(target=self._add_file, args=(index_queue,))

        indexer_thread.start()

        fetch_tasks: list = [create_task(self._fetch_files(fetch_queue, transfer_queue)) for _ in range(self.WORKERS)]
        transfer_tasks: list = [create_task(self._transfer_file(index_queue, transfer_queue)) for _ in range(self.WORKERS)]

        await fetch_queue.join()
        for _ in fetch_tasks:
            await fetch_queue.put(None)
        dms_info(f"Finished fetching new files, time: {(datetime.now() - start).total_seconds()}s.")
        await transfer_queue.join()
        for _ in transfer_tasks:
            await transfer_queue.put(None)
        dms_info(f"Formatted and transferred files to indexer, time: {(datetime.now() - start).total_seconds()}s.")
        index_queue.join()
        index_queue.put(None)
        indexer_thread.join()
        self.connector.write_subdata()
        self.indexing.release()
        dms_info(f"Finished indexing of new files, time: {(datetime.now() - start).total_seconds()}s.")

    async def _fetch_files(self, fetch_queue: Queue, transfer_queue: Queue) -> None:
        """Fetch files from stream.

        Args:
            fetch_queue: queue with urls to connectors.
            transfer_queue: queue for transferring files to the searchengine.
        """
        while True:
            stream_url: str | None = await fetch_queue.get()
            if stream_url is None:
                break
            try:
                async for file in self.connector.stream(stream_url):
                    await transfer_queue.put(file)
            except httpx.HTTPError:
                dms_warning(f"Failed to connect to {stream_url}.")
            fetch_queue.task_done()

    async def _transfer_file(self, index_queue: queue.Queue, transfer_queue: Queue) -> None:
        """Format and transfer file to search engine indexing queue.

        index_queue: queue containing all the ready files to index.
        transfer_queue: queue of raw dicts with file data.
        loop: global event loop.
        """

        loop = get_event_loop()

        while True:
            file: dict | None = await transfer_queue.get()
            if file is None:
                break
            flat_file: dict | None = self._decode(file)
            if flat_file is None:
                continue
            await loop.run_in_executor(None, index_queue.put, flat_file)
            transfer_queue.task_done()

    def _add_file(self, index_queue: queue.Queue) -> None:
        """Wait for formatted file and add it to the search engine.

        Args:
            task_queue: queue containing all the files to add.
        """

        batch: list[dict] = []

        while True:
            file: dict | None = index_queue.get()
            if file is None:
                break
            batch.append(file)
            if len(batch) >= self.BATCH_SIZE:
                self.search_engine.open_writer()
                for file in batch:
                    self.search_engine.add_file(file)
                dms_info(f"Batch of {len(batch)} commited")
                self.search_engine.close_writer()
                batch.clear()
            index_queue.task_done()
        if batch:
            self.search_engine.init()
            for file in batch:
                self.search_engine.add_file(file)
            dms_info(f"Batch of {len(batch)} commited")
            self.search_engine.close_writer()
            batch.clear()

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
