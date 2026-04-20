"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from typing import Any

from requests import exceptions, get, post
from se_api.services.classifier_cache import ClassifierCache
from shared_functions.initialisation_tools import read_env_variable

from shared_functions.dmis_logger import dms_error, dms_warning


class Query:
    """Class handling query connections."""

    classify_url: str
    classifications_url: str
    cache: ClassifierCache
    classifications: list[str]

    def __init__(self) -> None:
        """Constructor."""
        address: str = read_env_variable("SEARCHENG_STOCHAN_URL")

        self.classify_url = address.rstrip("/") + "/classify"
        self.classifications_url = address.rstrip("/") + "/classifications"
        self.cache = ClassifierCache()
        classifications = self._classifications_call()
        if classifications is None:
            dms_error(f"Failed to grab classification categories from: {self.classifications_url}.")
            return
        self.classifications = classifications

    def reset(self) -> None:
        """Reset query service"""
        self.cache.delete_cache_file()

    async def close(self) -> None:
        """Clean up"""
        await self.cache.close()

    def set_classification(self, pointer: str, classification: str) -> dict | None:
        """Set classification of a file.

        Args:
            pointer: file unique pointer.
            classification: new classification
        Return: None on failure otherwise CacheModel
        """
        if classification in self.classifications:
            return self.cache.set_classification(pointer, classification)
        return None

    def classify(self, files: list[dict]) -> dict[str, str]:
        """Classify the files at the pointers.

        Args:
            pointers: list of unique file pointers
        Returns: list of file pointers with their classification.
        """
        classifications: dict[str, str] = {}
        not_cached: list[str] = []
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
                not_cached.append(pointer)

        if not not_cached:
            return classifications

        response: Any | None = self._classify_call(not_cached)

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

    def _classify_call(self, pointers: list[str]) -> Any | None:
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

    def _classifications_call(self) -> list[str] | None:
        try:
            response = get(self.classifications_url, timeout=120).json()
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
