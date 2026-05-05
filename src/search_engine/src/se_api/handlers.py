"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import asyncio
import base64
from threading import Thread
import queue
import io

from asyncio import Lock, Queue, create_task, get_event_loop
from datetime import datetime
import httpx
from markitdown import FileConversionException, MarkItDown, UnsupportedFormatException

from se_api.constants import CLASSIFICATION, CONTENT, CONVERTABLE_TYPES, UNIQUE_POINTER
from se_api.services.classifier import Classifier
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

from shared_functions.dmis_logger import dms_info, dms_warning


class Handler:
    """Handler for internal processing.

    Attributes:
        connector: Connector service.
        search_engine: Search engine service.
    """

    connector: Connector
    classifier: Classifier
    search_engine: SearchEngine

    FETCH_WORKERS: int = 8
    DECODE_WORKERS: int = 8
    CLASSIFY_WORKERS: int = 8
    BATCH_SIZE: int = 1000
    indexing: Lock

    def __init__(self) -> None:
        """Constructor"""
        self.connector = Connector()
        self.search_engine = SearchEngine()
        self.classifier = Classifier()
        self.indexing = Lock()

    async def init(self) -> None:
        """Init handler"""

        fields: list[str] | None = await self.connector.get_fields()
        self.search_engine.init(fields)

    async def close(self) -> None:
        """Clean up"""
        await self.connector.close()

    async def reset(self) -> None:
        """Reset the connector."""
        fields: list[str] | None = await self.connector.get_fields()
        self.search_engine.reset(fields)
        self.connector.write_subdata({})
        dms_info("Search engine was reset.")

    def get_classifications(self) -> list[str]:
        """Get list of classifications.

        Returns: list of classifications.
        """
        classifications = self.classifier.LABELS
        classifications.append("Pending")
        return classifications

    def find_matching(self, pointer: str, count: int | None = None) -> dict:
        """Grab pointers for matching files.

        Args:
            pointer: file to compare with.
            count: number of results.
        Returns: the matching pointers and their scores.
        """
        return self.search_engine.find_matching(pointer, count)

    def grab_searchable_fields(self) -> set:
        """Grab searchable fields.

        Returns a set with the fields.
        """
        fields = self.search_engine.categories
        fields.remove("is_document")
        fields.add("documents_only")
        return fields

    async def set_classification(self, change: dict[str, str]) -> dict[str, str]:
        """Set the classification of a file.

        Args:
            change: dict containing the unique pointer and new classification.
        Returns: dict containing the unique pointer, classification, and if edited.
        """

        pointer: str | None = change.get(UNIQUE_POINTER)
        classification: str | None = change.get(CLASSIFICATION)
        if pointer is None or classification is None:
            return {}
        if classification not in self.classifier.LABELS:
            return {}
        if self.search_engine.set_classification(pointer, classification) is None:
            return {}
        files = await self.connector.fetch_files([pointer])
        if files:
            file: dict = files[0]
            file.update({CLASSIFICATION: classification})
            return file
        return {}

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

    async def preform_search(self, content: dict, count: int, offset: int) -> list:
        """Get get files from collectors preform the search, returns a list.

        Args:
            content: query per field.
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

        if not self.indexing.locked():
            loop = get_event_loop()
            loop.create_task(self._handle_new())

        matches, classifications = self.search_engine.query_files(content, offset + count)
        matches = matches[offset : count + offset]
        files: list[dict] = await self.connector.fetch_files(matches)
        self.clean_misses(matches, files)
        for file in files:
            classification = classifications.get(file.get(UNIQUE_POINTER, ""))
            file.update({CLASSIFICATION: classification})
        return files

    async def _handle_new(self) -> None:
        """Grab connector stream output and pipe it into search engine."""
        await self.indexing.acquire()
        dms_info("Starting indexing of new files.")
        start = datetime.now()
        fetch_queue: Queue = await self.connector.connector_fetch()
        decode_queue: Queue = Queue()
        classify_queue: Queue = Queue()
        index_queue: queue.Queue = queue.Queue()
        indexer_thread: Thread = Thread(target=self._index_file, args=(index_queue, classify_queue))

        indexer_thread.start()

        fetch_tasks: list = [create_task(self._fetch_files(fetch_queue, decode_queue)) for _ in range(self.FETCH_WORKERS)]
        decode_tasks: list = [
            create_task(self._decode_content(decode_queue, index_queue)) for _ in range(self.DECODE_WORKERS)
        ]
        classify_tasks: list = [
            create_task(self._classify_content(classify_queue, index_queue)) for _ in range(self.CLASSIFY_WORKERS)
        ]

        # Wait for fetching job to finish.
        await fetch_queue.join()
        for _ in fetch_tasks:
            await fetch_queue.put(None)
        dms_info(f"Finished fetching, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for decode job to finish.
        await decode_queue.join()
        for _ in decode_tasks:
            await decode_queue.put(None)
        dms_info(f"Finished formating, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for classify job to finish.
        await classify_queue.join()
        for _ in classify_tasks:
            await classify_queue.put(None)
        dms_info(f"Finished classifying, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for index job to finish.
        index_queue.join()
        index_queue.put(None)
        indexer_thread.join()

        self.connector.write_subdata()
        self.indexing.release()
        dms_info(f"Finished indexing, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

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

    async def _decode_content(self, decode_queue: Queue, index_queue: queue.Queue) -> None:
        """Format and transfer file to search engine indexing queue.

        index_queue: queue containing all the ready files to index.
        transfer_queue: queue of raw dicts with file data.
        """
        loop = get_event_loop()
        while True:
            file: dict | None = await decode_queue.get()
            if file is None:
                break
            file, raw_content = await loop.run_in_executor(None, self._decode_base64, file)
            if file is None or raw_content is None:
                continue
            file[CONTENT] = await loop.run_in_executor(None, self._convert_content, raw_content)
            file[CLASSIFICATION] = "Pending"
            await loop.run_in_executor(None, index_queue.put, file)
            decode_queue.task_done()


    def _index_file(self, index_queue: queue.Queue, classify_queue: Queue) -> None:
        """Wait for formatted file and index it.

        Args:
            task_queue: queue containing all the files to add.
        """
        batch: list[dict] = []
        unique_files: list[dict]
        total: int = 0

        pending: list[str] = []
        finnished: list[str] = []

        start_wait = datetime.now()

        while True:
            data: dict | None = index_queue.get()

            if data is not None:
                unique_pointer: str = data.get(UNIQUE_POINTER, "")
                if unique_pointer in pending:
                    pending.remove(unique_pointer)
                    finnished.append(unique_pointer)
                    batch.append(data)
                if unique_pointer not in finnished:
                    batch.append(data)

            if len(batch) >= self.BATCH_SIZE or data is None:
                end_wait = datetime.now()
                start = datetime.now()
                unique_files = self._clear_duplicates(batch)
                with self.search_engine.open_writer():
                    for file in unique_files:
                        self.search_engine.add_file(file)
                for file in unique_files:
                    unique_pointer = file.get(UNIQUE_POINTER, "")
                    pending.append(unique_pointer)
                    asyncio.run(classify_queue.put(unique_pointer))
                index_time = (datetime.now() - start).total_seconds()
                wait_time = (end_wait - start_wait).total_seconds()
                total += len(unique_files)
                dms_info(
                    f"Batch of {len(unique_files)} (total: {total}) commited"
                    + f", wait time: {round(wait_time, 3)}s"
                    + f", index time: {round(index_time, 3)}s"
                )
                batch = []
                start_wait = datetime.now()
            index_queue.task_done()
            if data is None:
                break

    async def _classify_content(self, classify_queue: Queue, index_queue: queue.Queue) -> None:
        """Classify the file content.

        Args:
            classify_queue: Files to classify.
            index_queue: Files ready to be indexed.
        """
        batch: list[dict] = []
        loop = get_event_loop()
        while True:
            pointer: str | None = await classify_queue.get()
            if pointer is None:
                break
            batch.append(self.search_engine.grab_file(pointer))
            if len(batch) >= Classifier.BATCH_SIZE:
                await self.classifier.classify(batch)
                for file in batch:
                    await loop.run_in_executor(None, index_queue.put, file)
                batch = []
            classify_queue.task_done()
        if batch:
            await self.classifier.classify(batch)
            await loop.run_in_executor(None, index_queue.put, batch)
            batch = []

    def _decode_base64(self, file: dict) -> tuple[dict | None, bytes | None]:
        """Decode file content.

        Args:
            file: dict containing the content in base64.
        Returns: dict with decoded file content, or none on failure.
        """
        flat_file = self._flatten_dict(file)
        content: str | None = flat_file.get("content")

        if content is None:
            dms_warning("File is missing content.")
            return (None, None)
        content_bytes: bytes = base64.b64decode(content)
        return flat_file, content_bytes

    @staticmethod
    def _convert_content(content: bytes) -> str:
        """Try to convert content into markdown.

        Args:
            content: file content as bytes.
            file_type: the files type.
        Returns: File content as markdown, str
        """

        if Handler._is_convertable(content):
            try:
                md = MarkItDown()
                stream = io.BytesIO(content)
                decoded_content = md.convert_stream(stream).text_content
                return decoded_content
            except (FileConversionException, UnsupportedFormatException):
                decoded_content = None
        try:
            decoded_content = content.decode("utf-8")
        except UnicodeDecodeError:
            decoded_content = ""
        return decoded_content

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

    @staticmethod
    def _clear_duplicates(files: list[dict]) -> list[dict]:
        """Remove any duplicates from the list.

        Args:
            files: original file list.
        Returns: list with the latest files.
        """
        latest_files: list[dict] = []
        latest_pointers: list[str] = []
        for file in files[::-1]:
            pointer: str | None = file.get(UNIQUE_POINTER)
            if pointer is None or pointer in latest_pointers:
                continue
            latest_pointers.append(pointer)
            latest_files.append(file)
        return latest_files

    @staticmethod
    def _is_convertable(content: bytes) -> bool:
        for convertable in CONVERTABLE_TYPES:
            if content[: int(len(convertable) / 2)].hex() == convertable:
                return True
        return False
