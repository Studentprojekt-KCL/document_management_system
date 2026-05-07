"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from asyncio import Queue, QueueShutDown, create_task, to_thread

from dataclasses import dataclass
import io
import base64
import httpx
from markitdown import FileConversionException, MarkItDown, UnsupportedFormatException

from se_api.constants import (
    CLASSIFICATION,
    CLASSIFICATION_QUEUE_SIZE,
    CONTENT,
    CONVERTABLE_TYPES,
    GENERIC_QUEUE_SIZE,
    GENERIC_WORKER_COUNT,
    MAX_PENDING_CONTENT_SIZE,
    POINTER_QUEUE_SIZE,
    UNIQUE_POINTER,
)

from se_api.services.classifier import Classifier
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

from shared_functions.dmis_logger import datetime, dms_info, dms_warning


@dataclass
class Queues:
    """Queue holder object"""

    fetch_queue: Queue
    decode_queue: Queue
    index_queue: Queue
    lookup_queue: Queue
    classify_queue: Queue
    reindex_queue: Queue


class IndexPipeline:
    """Index pipeline class"""

    queues: Queues

    def __init__(self, search_engine: SearchEngine, connector: Connector, classifier: Classifier) -> None:
        """Constructor"""
        self.search_engine = search_engine
        self.connector = connector
        self.classifier = classifier

    def stop(self) -> None:
        """Stop indexing"""
        self.queues.fetch_queue.shutdown(immediate=True)
        self.queues.decode_queue.shutdown(immediate=True)
        self.queues.index_queue.shutdown(immediate=True)
        self.queues.lookup_queue.shutdown(immediate=True)
        self.queues.classify_queue.shutdown(immediate=True)
        self.queues.reindex_queue.shutdown(immediate=True)

    async def run(self) -> None:
        """Run indexing pipeline.

        Args:
            search_engine: the search engine object.
            connector: connector object.
            classifier: classifier object.
        """
        dms_info("Indexing started.")
        start = datetime.now()

        fetch_queue: Queue = await self.connector.connector_fetch()
        decode_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        index_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        lookup_queue: Queue = Queue(POINTER_QUEUE_SIZE)
        classify_queue: Queue = Queue(CLASSIFICATION_QUEUE_SIZE)
        reindex_queue: Queue = Queue(GENERIC_QUEUE_SIZE)

        self.queues = Queues(fetch_queue, decode_queue, index_queue, lookup_queue, classify_queue, reindex_queue)

        fetch_tasks: list = [create_task(self._ingest_fetch(fetch_queue, decode_queue)) for _ in range(GENERIC_WORKER_COUNT)]
        decode_tasks: list = [create_task(self._ingest_decode(decode_queue, index_queue)) for _ in range(GENERIC_WORKER_COUNT)]
        create_task(self._ingest_index(index_queue, lookup_queue))

        create_task(self._classifier_load_index(lookup_queue, classify_queue))
        classify_tasks: list = [create_task(self._classifier_execute(classify_queue, reindex_queue)) for _ in range(GENERIC_WORKER_COUNT)]
        create_task(self._classifier_refresh_index(reindex_queue))

        # Wait for fetching job to finish.
        await fetch_queue.join()
        for _ in fetch_tasks:
            await fetch_queue.put(None)
        dms_info(f"Finished fetching from connector, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for decode job to finish.
        await decode_queue.join()
        for _ in decode_tasks:
            await decode_queue.put(None)
        dms_info(f"Finished decoding, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for index job to finish.
        await index_queue.join()
        await index_queue.put(None)
        await index_queue.join()
        dms_info(f"Finished indexing, time: {round((datetime.now() - start).total_seconds(), 3)}s.")
        dms_info("Ingestion stage completed.")

        # Wait for fetching job to finish.
        await fetch_queue.join()
        await fetch_queue.put(None)
        await fetch_queue.join()
        dms_info(f"Finished fetching from index, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for classification job to finish.
        await classify_queue.join()
        for _ in classify_tasks:
            await classify_queue.put(None)
        await classify_queue.join()
        dms_info(f"Finished classifying, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

        # Wait for reindex job to finish.
        await reindex_queue.join()
        await reindex_queue.put(None)
        await reindex_queue.join()
        dms_info(f"Finished indexing, time: {round((datetime.now() - start).total_seconds(), 3)}s.")
        dms_info("Ingestion stage completed.")

    async def _ingest_fetch(self, fetch_queue: Queue, decode_queue: Queue) -> None:
        """Fetch files from stream.

        Args:
            fetch_queue: queue with urls to connectors.
            decode_queue: queue for decoding files.
            connector: connector object.
        """
        while True:
            try:
                stream_url: str | None = await fetch_queue.get()
                if stream_url is None:
                    break
                try:
                    async for file in self.connector.stream(stream_url):
                        await decode_queue.put(file)
                except httpx.HTTPError:
                    dms_warning(f"Failed to connect to {stream_url}.")
                fetch_queue.task_done()
            except QueueShutDown:
                break

    async def _ingest_decode(self, decode_queue: Queue, index_queue: Queue) -> None:
        """Format and doecode files.

        Args:
            decode_queue: queue of raw dicts with file data.
            index_queue: queue containing all the ready files to index.
        """
        while True:
            try:
                file: dict | None = await decode_queue.get()
                if file is None:
                    break
                file, raw_content = await self._decode_base64(file)
                if file is None or raw_content is None:
                    continue
                file[CONTENT] = await self._convert_content(raw_content)
                file[CLASSIFICATION] = "Pending"
                await index_queue.put(file)
                decode_queue.task_done()
            except QueueShutDown:
                break

    async def _ingest_index(self, index_queue: Queue, classify_queue: Queue) -> None:
        """Index file batches of files.

        Args:
            index_queue: index queue.
            classify_queue: classification queue.
            search_engine: SearchEngine object.
        """
        content_total_size: int = 0
        batch: list[dict] = []
        while True:
            try:
                file: dict | None = await index_queue.get()
                if file is not None:
                    size = file.get("size", 0)
                    batch.append(file)
                    content_total_size += int(size)
                if content_total_size >= MAX_PENDING_CONTENT_SIZE or file is None:
                    await self._index_batch(self.search_engine, batch)
                    dms_info(f"Ingest: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
                    for item in batch:
                        unique_pointer: str = item.get(UNIQUE_POINTER, "")
                        await classify_queue.put(unique_pointer)
                    batch = []
                    content_total_size = 0
                index_queue.task_done()
                if file is None:
                    break
            except QueueShutDown:
                break

    async def _classifier_load_index(self, fetch_queue: Queue, classify_queue: Queue) -> None:
        """Fetch files from search engine.

        Args:
            fetch_queue: files to be fetched.
            classify_queue: files to be classified.
            search_engine: SearchEngine object.
        """
        done: list = []
        async for old_file in self.search_engine.fetch_pending():
            try:
                await classify_queue.put(old_file)
                done.append(old_file.get(UNIQUE_POINTER))
            except QueueShutDown:
                break

        while True:
            try:
                pointer: str | None = await fetch_queue.get()
                if pointer is None:
                    break
                if pointer in done:
                    continue
                file: dict = await self._grab_files_from_index(self.search_engine, pointer)
                await classify_queue.put(file)
                fetch_queue.task_done()
            except QueueShutDown:
                break

    async def _classifier_execute(self, classify_queue: Queue, index_queue: Queue) -> None:
        """Classify batch of files.

        Args:
            classify_queue: files to classify.
            index_queue: files to be indexed.
            classifier: Classifier object.
        """
        batch: list = []
        while True:
            try:
                file: dict | None = await classify_queue.get()
                if file is not None:
                    batch.append(file)
                if len(batch) >= self.classifier.BATCH_SIZE or file is None:
                    await self.classifier.classify(batch)
                    for file in batch:
                        await index_queue.put(file)
                    batch = []
                classify_queue.task_done()
                if file is None:
                    break
            except QueueShutDown:
                break

    async def _classifier_refresh_index(self, index_queue: Queue) -> None:
        """Reindex batch of files with classification.

        Args:
            index_queue: files to be indexed.
            search_engine: SearchEngine object.
        """
        content_total_size: int = 0
        batch: list[dict] = []
        while True:
            try:
                file: dict | None = await index_queue.get()
                if file is not None:
                    size = file.get("size", 0)
                    batch.append(file)
                    content_total_size += int(size)
                if content_total_size >= MAX_PENDING_CONTENT_SIZE or file is None:
                    await self._index_batch(self.search_engine, batch)
                    dms_info(f"Classification: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
                    batch = []
                    content_total_size = 0
                index_queue.task_done()
                if file is None:
                    break
            except QueueShutDown:
                break

    @staticmethod
    async def _grab_files_from_index(search_engine: SearchEngine, unique_pointer: str) -> dict:
        """Grab a file from the index.

        Args:
            search_engine: SearchEngine object
            pointer: file pointer.
        Returns: file dict.
        """

        def task() -> dict:
            try:
                return search_engine.grab_file(unique_pointer)
            except RuntimeError:
                dms_warning("Failed to grab file from index.")
                return {}

        return await to_thread(task)

    @staticmethod
    async def _index_batch(search_engine: SearchEngine, files: list[dict]) -> None:
        """Index a batch of files.

        Args:
            search_engine: SearchEngine object.
            files: files to index.
        """

        try:
            async with search_engine.open_writer():
                for file in files:
                    await to_thread(search_engine.add_file, file)
        except RuntimeError:
            dms_warning("Failed to write file to index.")

    @staticmethod
    async def _decode_base64(file: dict) -> tuple[dict | None, bytes | None]:
        """Decode file content.

        Args:
            file: dict containing the content in base64.
        Returns: dict with decoded file content, or none on failure.
        """

        def task() -> tuple[dict | None, bytes | None]:
            flat_file: dict = IndexPipeline._flatten_dict(file)
            content: str | None = flat_file.get(CONTENT)
            if content is None:
                dms_warning("File is missing content.")
                return (None, None)
            content_bytes = base64.b64decode(content)
            flat_file[CONTENT] = ""
            return flat_file, content_bytes

        return await to_thread(task)

    @staticmethod
    async def _convert_content(content: bytes) -> str:
        """Try to convert content into markdown.

        Args:
            content: file content as bytes.
            file_type: the files type.
        Returns: File content as markdown, str
        """

        def task() -> str:
            decoded_content: str | None = ""
            if IndexPipeline._is_convertable(content):
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

        return await to_thread(task)

    @staticmethod
    def _flatten_dict(d: dict) -> dict:
        """Flatten the dict.

        Args:
            d: dict to flatten.
        Return: a flat dict.
        """

        flat: dict = {}

        for key, val in d.items():
            if isinstance(val, dict):
                flat.update(IndexPipeline._flatten_dict(val))
            else:
                flat.update({key: str(val)})
        return flat

    @staticmethod
    def _is_convertable(content: bytes) -> bool:
        """Check if file is convertable.

        Args:
            content: file content in bytes.
        Returns: True if convertable, else False.
        """
        for convertable in CONVERTABLE_TYPES:
            if content[: int(len(convertable) / 2)].hex() == convertable:
                return True
        return False
