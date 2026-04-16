"""Confluence connector MVP with GitLab-like output format."""

import base64
import binascii
import os
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin

import requests


PROJECT = "project"
SOURCE_FILE = "source_file"


class ConfluenceInterfacer:
    """Confluence methods exposed for connector APIs."""

    def __init__(self) -> None:
        self.session = requests.session()
        self.address = os.environ.get("CONFLUENCE_ADDRESS", "").rstrip("/")
        self.email = os.environ.get("CONFLUENCE_EMAIL")
        self.api_token = os.environ.get("CONFLUENCE_API_TOKEN")
        if self.email and self.api_token:
            self.session.auth = (self.email, self.api_token)
        self.base = self._api_base(self.address)

    @staticmethod
    def _api_base(address: str) -> str:
        if not address:
            return ""
        if address.endswith("/wiki"):
            return f"{address}/rest/api/"
        return f"{address}/wiki/rest/api/"

    @staticmethod
    def _provided_date(subdata: str | None) -> datetime:
        if subdata is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            decoded = base64.b64decode(subdata).decode("utf-8")
            return datetime.fromisoformat(decoded.replace("Z", "+00:00"))
        except (binascii.Error, ValueError, UnicodeDecodeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def _execute_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.base:
            return {}
        url = urljoin(self.base, endpoint)
        try:
            response = self.session.get(url, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        except (requests.RequestException, ValueError):
            return {}

    @staticmethod
    def _safe_when(value: Any) -> datetime:
        if not isinstance(value, str):
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    @staticmethod
    def _pointer(page_id: str) -> str:
        return f"confluence://{page_id}"

    @staticmethod
    def _extract_text(storage_value: str) -> str:
        # MVP: strip XHTML tags and decode entities.
        text = re.sub(r"<[^>]+>", " ", storage_value)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_spaces(self) -> list[dict[str, Any]]:
        payload = self._execute_request("space", params={"limit": 250})
        results = payload.get("results", [])
        if not isinstance(results, list):
            return []
        spaces: list[dict[str, Any]] = []
        for space in results:
            if not isinstance(space, dict):
                continue
            key = space.get("key")
            if not isinstance(key, str):
                continue
            links = space.get("_links", {})
            webui = links.get("webui") if isinstance(links, dict) else None
            spaces.append(
                {
                    "key": key,
                    "name": space.get("name"),
                    "type": PROJECT,
                    "clickable_url": urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None,
                }
            )
        return spaces

    def _pages_in_space(self, space_key: str) -> list[dict[str, Any]]:
        payload = self._execute_request(
            "content",
            params={"spaceKey": space_key, "type": "page", "limit": 1000, "expand": "version"},
        )
        results = payload.get("results", [])
        if isinstance(results, list):
            return [p for p in results if isinstance(p, dict)]
        return []

    def get_page_ids(self) -> dict[str, str]:
        ids: dict[str, str] = {}
        for space in self.get_spaces():
            key = space.get("key")
            if not isinstance(key, str):
                continue
            pages = self._pages_in_space(key)
            latest = datetime.min.replace(tzinfo=timezone.utc)
            for page in pages:
                when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
                latest = max(latest, when)
            ids[key] = latest.isoformat()
        return ids

    def get_pages_in_space(self, space_key: str) -> list[str]:
        pages = self._pages_in_space(space_key)
        pointers: list[str] = []
        for page in pages:
            page_id = page.get("id")
            if isinstance(page_id, str):
                pointers.append(self._pointer(page_id))
        return pointers

    def get_page(self, file_pointer: str, include_content: bool = True) -> dict[str, Any]:
        page_id = file_pointer.split("://", 1)[1] if "://" in file_pointer else file_pointer
        payload = self._execute_request(f"content/{page_id}", params={"expand": "body.storage,version,space"})
        if not payload:
            return {"metadata": {"unique_pointer": self._pointer(page_id), "type": SOURCE_FILE}}

        title = payload.get("title")
        version = payload.get("version", {}) if isinstance(payload.get("version"), dict) else {}
        when = version.get("when")
        links = payload.get("_links", {}) if isinstance(payload.get("_links"), dict) else {}
        webui = links.get("webui")
        storage = payload.get("body", {}).get("storage", {}) if isinstance(payload.get("body"), dict) else {}
        raw_html = storage.get("value") if isinstance(storage, dict) else ""
        text = self._extract_text(raw_html) if isinstance(raw_html, str) else ""

        out: dict[str, Any] = {
            "metadata": {
                "unique_pointer": self._pointer(str(payload.get("id", page_id))),
                "name": title,
                "last_edit_date": when,
                "type": SOURCE_FILE,
                "clickable_url": urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None,
            }
        }
        if include_content:
            out["content"] = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return out

    def pointers_to_all_files_to_index(self, subdata: str | None) -> dict[str, Any]:
        provided = self._provided_date(subdata)
        latest = datetime.min.replace(tzinfo=timezone.utc)
        pointers: list[str] = []

        for space in self.get_spaces():
            key = space.get("key")
            if not isinstance(key, str):
                continue
            pages = self._pages_in_space(key)
            space_latest = datetime.min.replace(tzinfo=timezone.utc)
            page_ids: list[str] = []
            for page in pages:
                page_id = page.get("id")
                if isinstance(page_id, str):
                    page_ids.append(page_id)
                when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
                space_latest = max(space_latest, when)
            latest = max(latest, space_latest)
            if space_latest > provided:
                pointers.extend([self._pointer(pid) for pid in page_ids])

        token = base64.b64encode(latest.isoformat().encode("utf-8")).decode("utf-8")
        return {"subdata": token, "file_pointers": pointers}

    def files_to_index(self, subdata: str | None = None) -> dict[str, Any]:
        pointer_payload = self.pointers_to_all_files_to_index(subdata)
        pointers = pointer_payload.get("file_pointers", [])
        files: list[dict[str, Any]] = []
        if isinstance(pointers, list):
            for pointer in pointers:
                if isinstance(pointer, str):
                    files.append(self.get_page(pointer, include_content=True))
        return {"subdata": pointer_payload.get("subdata"), "files": files, "deleted": []}
