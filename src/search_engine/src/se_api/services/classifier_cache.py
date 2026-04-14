"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from asyncio import Event, get_running_loop, wait_for
import shelve

from dmis_logger import dms_error, dms_info
from initialisation_tools import read_env_variable


class ClassifierCache:
    """Classifier Cache class"""

    CACHE_FILE: str = "classification_cache.json"
    SYNC_INTERVAL: int = 600

    cache: shelve.Shelf[str]
    close_event: Event

    def __init__(self) -> None:
        """Constructor"""
        cache_directory: str = read_env_variable("SE_API_CACHE_DIRECTORY")
        cache_file: str = f"{cache_directory.rstrip('/')}/{ClassifierCache.CACHE_FILE}"
        try:
            self.cache: shelve.Shelf[str] = shelve.open(cache_file, writeback=True)
        except IOError:
            dms_error(f"Failed to open file: {cache_file}.")
        self.close_event = Event()
        loop = get_running_loop()
        self.sync_thread = loop.create_task(ClassifierCache._cache_sync(self.close_event, self.cache))

    async def close(self) -> None:
        """Clean up"""
        self.close_event.set()
        await self.sync_thread
        self.cache.close()

    @staticmethod
    async def _cache_sync(close_event: Event, cache: shelve.Shelf[str]) -> None:
        """Sync cache file with in memory cache.

        Args:
            close_event: exits the thread when the event is set.
            cache: in memory cache.
        """
        dms_info("Launching sync thread.")
        while not close_event.is_set():
            try:
                await wait_for(close_event.wait(), timeout=ClassifierCache.SYNC_INTERVAL)
            except TimeoutError:
                dms_info("Syncing cache file.")
                cache.sync()
        dms_info("Closing sync thread.")

    def add_classification(self, pointer: str, classification: str) -> None:
        """Add classification to cache.

        Args:
            poiner: unique pointer
            classification: the assigned classification.
        """

        self.cache[pointer] = classification

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
        return self.cache.get(pointer)
