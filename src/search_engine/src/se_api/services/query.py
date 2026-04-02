import json
from os import environ
from typing import Any

from dmis_logger import dms_error, dms_warning
from requests import exceptions, get, post


class Query:
    classify_url: str

    def __init__(self) -> None:
        address: str | None = environ.get("SE_API_QUERY_ADDRESS")

        if address is None:
            dms_error("SE_API_QUERY_ADDRESS is not defined.")
            return

        self.classify_url = address.rstrip("/") + "/classify"

    def classify(self, pointers: list[str]) -> list:
        response: Any | None = self._get_classification(pointers)
        if not isinstance(response, list):
            dms_warning(f"Query returned unreqognized structure, url {self.classify_url}.")
            return []

        return response

    def _get_classification(self, pointers: list[str]) -> Any | None:
        try:
            response = post(
                self.classify_url,
                json={"pointers": pointers},
                timeout=120
            ).json()
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

