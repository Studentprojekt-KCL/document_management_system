"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

import logging
from multiprocessing import Process
from multiprocessing.connection import Connection
from typing import Any

from dmis_logger import dms_info, dms_warning
from requests import exceptions, post
from initialisation_tools import read_env_variable

from search_engine.classifier.cache import Cache


class Classifier:
    """Class handling query connections."""

    classify_url: str
    cache: Cache

    def __init__(self) -> None:
        """Constructor."""
        super().__init__()
        address: str = read_env_variable("SE_API_QUERY_ADDRESS")

        self.classify_url = address.rstrip("/") + "/classify"
        self.cache = Cache()

    def classify(self, files: list[dict]) -> dict[str, str]:
        """Classify the files at the pointers.

        Args:
            pointers: list of unique file pointers
        Returns: list of file pointers with their classification.
        """
        classifications: dict[str, str] = {}
        none_cached: list[str] = []
        pointers: list[str] = []
        classification: str | None = None

        for file in files:
            pointer: str | None = file.get("unique_pointer")
            if pointer is None:
                continue
            pointers.append(pointer)

        for pointer in pointers:
            classification = self.cache.fetch_classification(pointer)
            if classification is not None:
                classifications.update({pointer: classification})
            else:
                none_cached.append(pointer)

        if not none_cached:
            return classifications

        response: Any | None = self._get_classification(none_cached)

        if not isinstance(response, list):
            dms_warning("Returned invalid response from classifier, expected list.")
            return {}

        for r in response:
            if not isinstance(r, dict):
                dms_warning("Returned invalid response from classifier, expected list of dicts.")
                continue
            unique_pointer: str | None = r.get("unique_pointer")
            classification = r.get("Security-class")
            if unique_pointer is None or classification is None:
                dms_warning("Returned invalid response from classifier, neither unique_pointer or Security-class does not exist.")
                continue
            classifications.update({unique_pointer: classification})
            self.cache.add_classification(unique_pointer, classification)

        return classifications

    def _get_classification(self, pointers: list[str]) -> Any | None:
        """Grab the classification from the classifier.

        Args:
            pointers: list of pointers.
        Returns: Result or None
        """
        try:
            response = post(self.classify_url, json={"pointers": pointers}, timeout=120).json()
            return response
        except exceptions.ConnectionError:
            dms_warning(f"Failed to connect, url: {self.classify_url}.")
        except exceptions.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.classify_url}.")
        except exceptions.Timeout:
            dms_warning(f"Request timed out, url: {self.classify_url}")
        except exceptions.JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.classify_url}.")
        except exceptions.RequestException:
            dms_warning(f"Something went wrong, url: {self.classify_url}.")
        return None
