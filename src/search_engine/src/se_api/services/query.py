"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from json import JSONDecodeError
from typing import Any

import httpx

from se_api.services.classifier_cache import ClassifierCache
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_error, dms_warning


class Query:
    """Class handling query connections."""

    CLASSIFICATIONS_ENDPOINT: str = "/classifications"
    CLASSIFY_ENDPOINT: str = "/classify"

    classify_url: str
    classifications_url: str
    cache: ClassifierCache
    classifications: list[str]
    clinet: httpx.AsyncClient

    def __init__(self) -> None:
        """Constructor."""
        address: str = read_env_variable("SE_API_QUERY_ADDRESS")
        query_url = address.rstrip("/")
        self.clinet = httpx.AsyncClient(base_url=query_url)
        self.cache = ClassifierCache()
           
    async def init(self):
        """Init query clients"""
        classifications = await self._classifications_call()
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
        await self.clinet.aclose()

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

    async def classify(self, files: list[dict]) -> dict[str, str]:
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

        response: Any | None = await self._classify_call(not_cached)

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

    async def _classify_call(self, pointers: list[str]) -> Any | None:
        """Grab the classification from the classifier.

        Args:
            pointers: list of pointers.
        Returns: Result or None
        """
        try:
            response = await self.clinet.post(self.CLASSIFY_ENDPOINT, json={"pointers": pointers})
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.classify_url}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.classify_url}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.classify_url}.")
        return None

    async def _classifications_call(self) -> list[str] | None:
        try:
            response = await self.clinet.get(self.CLASSIFICATIONS_ENDPOINT, timeout=120)
            return response.json()
        except httpx.TimeoutException:
            dms_warning(f"Request timed out, url: {self.classify_url}")
        except JSONDecodeError:
            dms_warning(f"Failed to parse JSON, url: {self.classify_url}.")
        except httpx.HTTPError:
            dms_warning(f"Invalid HTTP response, url: {self.classify_url}.")
        return None
