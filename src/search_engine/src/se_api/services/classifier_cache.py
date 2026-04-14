"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json

from dmis_logger import dms_error, dms_info, dms_warning
from initialisation_tools import read_env_variable


class ClassifierCache:
    """Classifier Cache class"""

    CACHE_FILE: str = "classification_cache.json"

    cache_directory: str
    cache_file: str
    cache: dict[str, str]

    def __init__(self) -> None:
        """Constructor"""
        cache_directory: str = read_env_variable("SE_API_CACHE_DIRECTORY")
        cache_file: str = f"{cache_directory.rstrip('/')}/{ClassifierCache.CACHE_FILE}"

        try:
            with open(cache_file, encoding="utf=8") as f:
                dms_info(f"Found {cache_file}.")
                cache: dict = json.loads(f.read())
                self.cache = cache
        except OSError:
            try:
                dms_info(f"Creating {cache_file}.")
                with open(cache_file, "x", encoding="utf=8"):
                    self.cache = {}
            except OSError:
                dms_error(f"Failed to create {cache_file}.")
                return
        except json.JSONDecodeError:
            self.cache = {}

        self.cache_file = cache_file

    def reset(self) -> None:
        """Reset cache."""
        self.cache = {}
        self._write_memory()

    def _write_memory(self) -> None:
        """Write current cache to file."""
        try:
            with open(self.cache_file, "w", encoding="utf=8") as f:
                f.write(json.dumps(self.cache))
        except OSError:
            dms_warning(f"Failed to open (write): {self.cache_file}.")
        except json.JSONDecodeError:
            dms_warning("Failed to parse cache dict.")

    def add_classification(self, pointer: str, classification: str) -> None:
        """Add classification to cache.

        Args:
            poiner: unique pointer
            classification: the assigned classification.
        """

        self.cache.update({pointer: classification})
        self._write_memory()

    def remove_classification(self, pointer: str) -> None:
        """Remove classification from cache.

        Args:
            poiner: unique pointer
        """

        self.cache.pop(pointer)
        self._write_memory()

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
        self._write_memory()

    def fetch_classification(self, pointer: str) -> str | None:
        """Fetch a classification.

        Args:
            pointer: unique pointer.
        Returns: classification string or None."""
        return self.cache.get(pointer)
