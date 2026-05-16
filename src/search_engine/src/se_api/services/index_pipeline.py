"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from asyncio import Lock, Queue, QueueFull, QueueShutDown, Task, create_task, gather, to_thread

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
    MODIFIED,
    POINTER_QUEUE_SIZE,
    UNIQUE_POINTER,
)

from se_api.services.classifier import Classifier
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

from shared_functions.dmis_logger import dms_info, dms_warning


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
    _tasks: list[Task]

    working_on: list
    working_on_lock: Lock

    def __init__(self, search_engine: SearchEngine, connector: Connector, classifier: Classifier) -> None:
        """Constructor"""
        self.search_engine = search_engine
        self.connector = connector
        self.classifier = classifier
        self._tasks = []
        self.working_on = []
        self.working_on_lock = Lock()

    async def start(self) -> None:
        """Start the indexing pipeline."""
        fetch_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        decode_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        index_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        lookup_queue: Queue = Queue(POINTER_QUEUE_SIZE)
        classify_queue: Queue = Queue(CLASSIFICATION_QUEUE_SIZE)
        reindex_queue: Queue = Queue(GENERIC_QUEUE_SIZE)
        self.queues = Queues(fetch_queue, decode_queue, index_queue, lookup_queue, classify_queue, reindex_queue)
        fetch_tasks: list[Task] = [create_task(self._ingest_fetch()) for _ in range(GENERIC_WORKER_COUNT)]
        decode_tasks: list[Task] = [create_task(self._ingest_decode()) for _ in range(GENERIC_WORKER_COUNT)]
        ingest_index_task: Task = create_task(self._ingest_index())

        classifier_load_task: Task = create_task(self._classifier_load_index())
        classify_tasks: list[Task] = [create_task(self._classifier_execute()) for _ in range(GENERIC_WORKER_COUNT)]
        classifier_refresh_task: Task = create_task(self._classifier_refresh_index())

        self._tasks = [
            *fetch_tasks,
            *decode_tasks,
            *classify_tasks,
            classifier_load_task,
            ingest_index_task,
            classifier_refresh_task,
        ]

        await self._load_pending()

    async def stop(self) -> None:
        """Stop indexing and wait for workers to exit."""
        for queue in (
            self.queues.fetch_queue,
            self.queues.decode_queue,
            self.queues.index_queue,
            self.queues.lookup_queue,
            self.queues.classify_queue,
            self.queues.reindex_queue,
        ):
            queue.shutdown(immediate=True)
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await gather(*self._tasks, return_exceptions=True)
        self.working_on = []

    async def add(self, authorization: str | None) -> None:
        """Add request to indexing pipeline.

        Args:
            authorization: user authorization token.
        """
        streams: list = await self.connector.connector_fetch(authorization)
        for stream in streams:
            await self.queues.fetch_queue.put(stream)


    async def _ingest_fetch(self) -> None:
        """Fetch files from stream.

        Args:
            fetch_queue: queue with urls to connectors.
            decode_queue: queue for decoding files.
            connector: connector object.
        """
        while True:
            try:
                stream_object: dict = await self.queues.fetch_queue.get()
                stream_url = stream_object.get("stream_url")
                async with self.working_on_lock:
                    if stream_url in self.working_on:
                        continue
                    self.working_on.append(stream_object.get("stream_url"))
                try:
                    async for file in self.connector.stream(stream_object):
                        await self.queues.decode_queue.put(file)
                except httpx.HTTPError:
                    dms_warning(f"Failed to connect to {stream_url}.")
                async with self.working_on_lock:
                    self.working_on.remove(stream_url)
                dms_info(f"Finished streaming from {stream_url}")
                self.queues.fetch_queue.task_done()
            except QueueShutDown:
                break

    async def _ingest_decode(self) -> None:
        """Format and doecode files.

        Args:
            decode_queue: queue of raw dicts with file data.
            index_queue: queue containing all the ready files to index.
        """
        while True:
            try:
                file: dict = await self.queues.decode_queue.get()
                file, raw_content = await self._decode_base64(file)
                if file is not None and raw_content is not None:
                    file[CONTENT] = await self._convert_content(raw_content)
                    file[CLASSIFICATION] = "Pending"
                    file[MODIFIED] = False
                    await self.queues.index_queue.put(file)
                self.queues.decode_queue.task_done()
            except QueueShutDown:
                break

    async def _ingest_index(self) -> None:
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
                file: dict = await self.queues.index_queue.get()
                size = file.get("size", 0)
                batch.append(file)
                content_total_size += int(size)
                if content_total_size >= MAX_PENDING_CONTENT_SIZE or self._open_index():
                    await self._index_batch(self.search_engine, batch)
                    dms_info(f"Ingest: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
                    for item in batch:
                        unique_pointer: str = item.get(UNIQUE_POINTER, "")
                        await self.queues.lookup_queue.put(unique_pointer)
                    batch = []
                    content_total_size = 0
                self.queues.index_queue.task_done()
            except QueueShutDown:
                break

    async def _load_pending(self) -> None:
        """Fetch pending classifications and add them to the queue."""
        dms_info("Looking for pending classifications in the index.")
        try:
            async for pointer in self.search_engine.grab_pending():
                await self.queues.lookup_queue.put(pointer)
            dms_info(f"Done, {self.queues.lookup_queue.qsize()} pointers in queue.")
        except QueueFull:
            dms_warning("Failed to add pointer to queue, queue is full.")
        except QueueShutDown:
            dms_warning("Failed to add pointer to queue, queue is closed.")

    async def _classifier_load_index(self) -> None:
        """Fetch files from search engine.

        Args:
            fetch_queue: files to be fetched.
            classify_queue: files to be classified.
            search_engine: SearchEngine object.
        """

        while True:
            try:
                pointer: str = await self.queues.lookup_queue.get()
                file: dict = await self._grab_files_from_index(self.search_engine, pointer)
                await self.queues.classify_queue.put(file)
                self.queues.lookup_queue.task_done()
            except QueueShutDown:
                break

    async def _classifier_execute(self) -> None:
        """Classify batch of files.

        Args:
            classify_queue: files to classify.
            index_queue: files to be indexed.
            classifier: Classifier object.
        """
        batch: list = []
        while True:
            try:
                file: dict = await self.queues.classify_queue.get()
                batch.append(file)
                if len(batch) >= self.classifier.BATCH_SIZE or (
                    self.queues.lookup_queue.qsize() <= 0 and self.queues.classify_queue.qsize() <= 0
                ):
                    await self.classifier.classify(batch)
                    for file in batch:
                        await self.queues.reindex_queue.put(file)
                    batch = []
                self.queues.classify_queue.task_done()
            except QueueShutDown:
                break

    async def _classifier_refresh_index(self) -> None:
        """Reindex batch of files with classification.

        Args:
            index_queue: files to be indexed.
            search_engine: SearchEngine object.
        """
        content_total_size: int = 0
        batch: list[dict] = []
        while True:
            try:
                file: dict = await self.queues.reindex_queue.get()
                size = file.get("size", 0)
                batch.append(file)
                content_total_size += int(size)
                if content_total_size >= MAX_PENDING_CONTENT_SIZE or self._open_reindex():
                    await self._index_batch(self.search_engine, batch)
                    dms_info(f"Classification: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
                    batch = []
                    content_total_size = 0
                self.queues.reindex_queue.task_done()
            except QueueShutDown:
                break

    def _open_index(self) -> bool:
        return len(self.working_on) <= 0 and self.queues.decode_queue.qsize() <= 0 and self.queues.index_queue.qsize() <= 0

    def _open_reindex(self) -> bool:
        return (
            self.queues.lookup_queue.qsize() <= 0
            and self.queues.classify_queue.qsize() <= 0
            and self.queues.reindex_queue.qsize() <= 0
        )

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
                    await search_engine.add_file(file)
        except RuntimeError:
            dms_warning("Failed to write file to index.")

    @staticmethod
    async def _decode_base64(file: dict) -> tuple[dict, bytes | None]:
        """Decode file content.

        Args:
            file: dict containing the content in base64.
        Returns: dict with decoded file content, or none on failure.
        """

        def task() -> tuple[dict, bytes | None]:
            flat_file: dict = IndexPipeline._flatten_dict(file)
            content: str | None = flat_file.get(CONTENT)
            if content is None:
                dms_warning(f"File is missing content: {flat_file.get(UNIQUE_POINTER)}")
                return (flat_file, None)
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
