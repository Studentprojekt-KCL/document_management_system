from asyncio import Queue, create_task, get_event_loop, get_running_loop
import logging

import asyncio
import io
import base64
import math
from threading import Thread
import httpx
from markitdown import FileConversionException, MarkItDown, UnsupportedFormatException
from shared_functions.dmis_logger import datetime, dms_info, dms_warning

from se_api.constants import CLASSIFICATION, CONTENT, CONVERTABLE_TYPES, MAX_PENDING_CONTENT_SIZE, MAX_QUEUE_LENGTH, UNIQUE_POINTER
from se_api.services.classifier import Classifier
from se_api.services.connector import Connector
from se_api.services.search_engine import SearchEngine

async def index_pipeline(search_engine: SearchEngine, connector: Connector, classifier: Classifier):
    dms_info("Indexing started.")
    start = datetime.now()

    fetch_queue: Queue = await connector.connector_fetch()
    decode_queue: Queue = Queue()
    index_queue: Queue = Queue()
    lookup_queue: Queue = Queue()
    classify_queue: Queue = Queue(10)
    reindex_queue: Queue = Queue()

    fetch_tasks: list = [create_task(_ingest_fetch(fetch_queue, decode_queue, connector)) for _ in range(8)]
    decode_tasks: list = [create_task(_ingest_decode(decode_queue, index_queue)) for _ in range(8)]
    create_task(_ingest_index(index_queue, lookup_queue, search_engine))

    create_task(_classifier_load_index(lookup_queue, classify_queue, search_engine))
    classify_tasks: list = [create_task(_classifier_execute(classify_queue, reindex_queue, classifier)) for _ in range(8)]
    create_task(_classifier_refresh_index(reindex_queue, search_engine))

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
    dms_info(f"Ingestion stage completed.")

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
    dms_info(f"Ingestion stage completed.")

async def _ingest_fetch(fetch_queue: Queue, decode_queue: Queue, connector: Connector) -> None:
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
            async for file in connector.stream(stream_url):
                await decode_queue.put(file)
        except httpx.HTTPError:
            dms_warning(f"Failed to connect to {stream_url}.")
        fetch_queue.task_done()

async def _ingest_decode(decode_queue: Queue, index_queue: Queue) -> None:
    """Format and transfer file to search engine indexing queue.

    index_queue: queue containing all the ready files to index.
    transfer_queue: queue of raw dicts with file data.
    """
    while True:
        file: dict | None = await decode_queue.get()
        if file is None:
            break
        file, raw_content = await _decode_base64(file)
        if file is None or raw_content is None:
            continue
        file[CONTENT] = await _convert_content(raw_content)
        file[CLASSIFICATION] = "Pending"
        await index_queue.put(file)
        decode_queue.task_done()

async def _ingest_index(index_queue: Queue, classify_queue: Queue, search_engine: SearchEngine):
    content_total_size: int = 0
    batch: list[dict] = []
    while True:
        file: dict | None = await index_queue.get()
        if file is not None:
            size = file.get("size", 0)
            batch.append(file)
            content_total_size += int(size)
        if content_total_size >= MAX_PENDING_CONTENT_SIZE or file is None:
            await _index_batch(search_engine, batch)
            dms_info(f"Ingest: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
            for item in batch:
                unique_pointer: str = item.get(UNIQUE_POINTER, "")
                await classify_queue.put(unique_pointer)
            batch = []
            content_total_size = 0
        index_queue.task_done()
        if file is None:
            break

# Classification stage

async def _classification_stage(search_engine: SearchEngine, classifer: Classifier, fetch_queue: Queue):
    dms_info("Classification stage started.")
    start = datetime.now()

    classify_queue: Queue = Queue(maxsize=MAX_QUEUE_LENGTH)
    index_queue: Queue = Queue()

    create_task(_classifier_load_index(fetch_queue, classify_queue, search_engine))
    classify_tasks: list = [create_task(_classifier_execute(classify_queue, index_queue, classifer)) for _ in range(8)]
    create_task(_classifier_refresh_index(index_queue, search_engine))

    # Wait for fetching job to finish.
    await fetch_queue.join()
    await fetch_queue.put(None)
    await fetch_queue.join()
    dms_info(f"Finished fetching, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

    # Wait for classification job to finish.
    await classify_queue.join()
    for _ in classify_tasks:
        await classify_queue.put(None)
    await classify_queue.join()
    dms_info(f"Finished classifying, time: {round((datetime.now() - start).total_seconds(), 3)}s.")

    # Wait for reindex job to finish.
    await index_queue.join()
    await index_queue.put(None)
    await index_queue.join()
    dms_info(f"Finished indexing, time: {round((datetime.now() - start).total_seconds(), 3)}s.")
    dms_info(f"Ingestion stage completed.")

async def _classifier_load_index(fetch_queue: Queue, classify_queue: Queue, search_engine: SearchEngine):
    while True:
        pointer: str | None = await fetch_queue.get()
        if pointer is None:
            break
        file: dict = await _grab_file_from_index(search_engine, pointer)
        await classify_queue.put(file)
        fetch_queue.task_done()

async def _classifier_execute(classify_queue: Queue, index_queue: Queue, classifier: Classifier):
    batch: list = []
    while True:
        file: dict | None = await classify_queue.get()
        if file is not None:
            batch.append(file)
        if len(batch) >= classifier.BATCH_SIZE or file is None:
            await classifier.classify(batch)
            for file in batch:
                await index_queue.put(file)
            batch = []
        classify_queue.task_done()
        if file is None:
            break

async def _classifier_refresh_index(index_queue: Queue, search_engine: SearchEngine):
    content_total_size: int = 0
    batch: list[dict] = []
    while True:
        file: dict | None = await index_queue.get()
        if file is not None:
            size = file.get("size", 0)
            batch.append(file)
            content_total_size += int(size)
        if content_total_size >= MAX_PENDING_CONTENT_SIZE or file is None:
            await _index_batch(search_engine, batch)
            dms_info(f"Classification: Batch of {len(batch)} ({round(content_total_size/1024, 2)}KB) commited.")
            batch = []
            content_total_size = 0
        index_queue.task_done()
        if file is None:
            break

# Util

async def _grab_file_from_index(search_engine: SearchEngine, pointer: str) -> dict:
    def task() -> dict:
        return search_engine.grab_file(pointer)
    loop = get_event_loop()
    return await loop.run_in_executor(None, task)

async def _index_batch(search_engine: SearchEngine, files: list[dict]):
    def task(): 
        with search_engine.open_writer() as writer:
            for file in files:
                search_engine.add_file(file, writer)

    loop = get_event_loop()
    await loop.run_in_executor(None, task)

async def _decode_base64(file: dict) -> tuple[dict | None, bytes | None]:
    """Decode file content.

    Args:
        file: dict containing the content in base64.
    Returns: dict with decoded file content, or none on failure.
    """ 
    def task() -> tuple[dict | None, bytes | None]:
        flat_file: dict = _flatten_dict(file)
        content: str | None = flat_file.get(CONTENT)
        if content is None:
            dms_warning("File is missing content.")
            return (None, None)
        content_bytes = base64.b64decode(content)
        flat_file[CONTENT] = ""
        return flat_file, content_bytes

    loop = get_event_loop()
    return await loop.run_in_executor(None, task)

async def _convert_content(content: bytes) -> str:
    """Try to convert content into markdown.

    Args:
        content: file content as bytes.
        file_type: the files type.
    Returns: File content as markdown, str
    """
    def task() -> str:
        decoded_content: str | None = ""
        if _is_convertable(content):
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

    loop = get_event_loop()
    return await loop.run_in_executor(None, task)

def _flatten_dict(d: dict) -> dict:
    """Flatten the dict.

    Args:
        d: dict to flatten.
    Return: a flat dict.
    """

    flat: dict = {}

    for key, val in d.items():
        if isinstance(val, dict):
            flat.update(_flatten_dict(val))
        else:
            flat.update({key: str(val)})
    return flat

def _is_convertable(content: bytes) -> bool:
    for convertable in CONVERTABLE_TYPES:
        if content[: int(len(convertable) / 2)].hex() == convertable:
            return True
    return False

