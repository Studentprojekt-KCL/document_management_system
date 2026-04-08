"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from os import environ
from typing import Any

from dmis_logger import dms_error, dms_info, dms_warning
from requests import exceptions, post

from se_api.services.classifier_cache import ClassifierCache


class Query:
    """Class handling query connections."""

    classify_url: str
    cache: ClassifierCache

    def __init__(self) -> None:
        address: str | None = environ.get("SE_API_QUERY_ADDRESS")

        if address is None:
            dms_error("SE_API_QUERY_ADDRESS is not defined.")
            return

        self.classify_url = address.rstrip("/") + "/classify"
        self.cache = ClassifierCache()

    def classify(self, pointers: list[str]) -> dict[str, str]:
        """Classify the files at the pointers.

        Args:
            pointers: list of unique file pointers
        Returns: list of file pointers with their classification.
        """
        classifications: dict[str, str] = {}

        for pointer in pointers:
            dms_info(f"Checking {pointer}")
            classification: str | None = self.cache.fetch_classification(pointer)
            if classification is not None:
                classifications.update({pointer: classification})
                pointers.remove(pointer)
            else:
                dms_info(f"Cache not found {pointer}")

        response: Any | None = self._get_classification(pointers)
        if not isinstance(response, list):
            dms_warning(f"Query returned unreqognized structure, url {self.classify_url}.")
            return {}


        for r in response:
            if not isinstance(r, dict):
                dms_warning("Returned invalid response from classifier, expected list of dicts.")
                continue
            unique_pointer: str | None = r.get("unique_pointer")
            classification: str | None = r.get("Security-class")
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
