"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from asyncio import Event, get_running_loop, wait_for
import dbm
from os import path, remove
import shelve

from dmis_logger import dms_error, dms_info
from initialisation_tools import read_env_variable


class ClassifierCache:
    """Classifier Cache class"""

    CACHE_FILE: str = "classification_cache"
    SYNC_INTERVAL: int = 600

    cache: dict[str, dict]
    close_event: Event
    cache_file: str

    def __init__(self) -> None:
        """Constructor"""
        cache_directory: str = read_env_variable("SE_API_CACHE_DIRECTORY")
        self.cache_file: str = f"{cache_directory.rstrip('/')}/{ClassifierCache.CACHE_FILE}"
        try:
            with shelve.open(self.cache_file) as f:
                self.cache = f.get("classification", {})
        except OSError:
            dms_error(f"Failed to open file: {self.cache_file}.")
        except dbm.error:
            dms_error(f"Failed opening file: {self.cache_file}")
        self.close_event = Event()
        loop = get_running_loop()
        self.sync_thread = loop.create_task(self._cache_sync())

    def delete_cache_file(self) -> None:
        """Delete the cache file."""
        if path.exists(self.cache_file):
            remove(self.cache_file)

    async def close(self) -> None:
        """Clean up"""
        self.close_event.set()
        await self.sync_thread

    async def _cache_sync(self) -> None:
        """Sync cache file with in memory cache.

        Args:
            close_event: exits the thread when the event is set.
            cache: in memory cache.
        """
        dms_info("Launching sync thread.")
        while not self.close_event.is_set():
            try:
                await wait_for(self.close_event.wait(), timeout=ClassifierCache.SYNC_INTERVAL)
            except TimeoutError:
                dms_info("Syncing cache file.")
                with shelve.open(self.cache_file) as f:
                    f["classification"] = self.cache
        dms_info("Closing sync thread.")

    def set_classification(self, pointer: str, classification: str) -> dict | None:
        """Set classification of a file.

        Args:
            pointer: file unique pointer.
            classification: new classification
        Return: None on failure otherwise CacheModel
        """

        file: dict | None = self.cache.get(pointer)
        if file is None:
            return None

        file["classification"] = classification
        file["edited"] = True

        return file

    def add_classification(self, pointer: str, classification: str) -> None:
        """Add classification to cache.

        Args:
            poiner: unique pointer
            classification: the assigned classification.
        """

        file: dict | None = self.cache.get(pointer)
        if file is None or not file.get("edited", False):
            self.cache[pointer] = {"classification": classification, "unique_pointer": pointer, "edited": False}

    def remove_classification(self, pointer: str) -> None:
        """Remove classification from cache.

        Args:
            poiner: unique pointer
        """

        self.cache.pop(pointer)

    def remove_classifications(self, files: list[dict[str, str]]) -> None:
        """Remove a list classifications from cache.

        Args:
            files: list of file dics.
        """

        for file in files:
            if not self.cache:
                break
            pointer: str | None = file.get("unique_pointer")
            if pointer is not None:
                self.cache.pop(pointer)

    def fetch_classification(self, pointer: str) -> str | None:
        """Fetch a classification.

        Args:
            pointer: unique pointer.
        Returns: classification string or None."""
        file: dict | None = self.cache.get(pointer)
        if file is None:
            return None
        return file.get("classification")
