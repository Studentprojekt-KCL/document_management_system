"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import json
from os import path

from dmis_logger import dms_error, dms_info
from initialisation_tools import read_env_variable

from search_engine.classifier.writer import Writer


class Cache:
    """Classifier Cache class"""

    CACHE_FILE: str = "classification_cache.json"

    cache_directory: str
    cache_file: str
    cache: dict[str, str]

    write_queue: list[dict[str, str]]
    writer: Writer

    def __init__(self) -> None:
        """Constructor"""
        self.cache_directory: str = read_env_variable("SE_API_CACHE_DIRECTORY")
        self.cache_file: str = f"{self.cache_directory.rstrip('/')}/{Cache.CACHE_FILE}"
        self.cache = {}

        if not path.isdir(self.cache_directory):
            dms_error(f"{self.cache_directory} is not a directory.")
        elif path.isfile(self.cache_file):
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    for line in f.readlines():
                        classification: dict[str, str] = json.loads(line.strip().replace("'", '"'))
                        self.cache.update(classification)
                dms_info(f"Found file: {self.cache_file}.")
            except OSError:
                dms_error(f"Failed reading file: {self.cache_file}.")
            except json.JSONDecodeError as e:
                print(e.msg)
                dms_error(f"Failed parsing file: {self.cache_file}.")
        elif path.exists(self.cache_file):
            dms_error(f"{self.cache_file} is not a file.")
        else:
            try:
                with open(self.cache_file, "x", encoding="utf-8") as f:
                    dms_info(f"Created file: {self.cache_file}.")
            except OSError:
                dms_error(f"Failed reading file: {self.cache_file}.")

        self.writer = Writer(self.cache_file)
        self.writer.start()

    def reset(self) -> None:
        """Reset cache."""
        self.cache = {}

    def add_classification(self, pointer: str, classification: str) -> None:
        """Add classification to cache.

        Args:
            poiner: unique pointer
            classification: the assigned classification.
        """

        if pointer not in self.cache.keys():
            self.writer.add({pointer: classification})
        self.cache.update({pointer: classification})

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

