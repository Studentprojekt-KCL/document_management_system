"""Confluence connector MVP with GitLab-like output format.

Authentication (aligned with GitHub connector pattern):
- Prefer per-request ``email`` + ``api_token`` (Atlassian Cloud: Basic auth).
- If either is omitted, falls back to ``CONFLUENCE_EMAIL`` and ``CONFLUENCE_API_TOKEN``
  in the environment (useful for local scripts / single-tenant containers).
- HTTP API in ``collector_api`` requires ``X-Confluence-Email`` and
  ``X-Confluence-Token`` headers (same idea as ``X-GitHub-Token`` for GitHub).
"""

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
        self.base = self._api_base(self.address)

    @staticmethod
    def _api_base(address: str) -> str:
        if not address:
            return ""
        if address.endswith("/wiki"):
            return f"{address}/rest/api/"
        return f"{address}/wiki/rest/api/"

    def _resolve_auth(self, email: str | None, api_token: str | None) -> tuple[str, str] | None:
        """Resolve (email, token) from arguments or environment."""
        e = (email or os.environ.get("CONFLUENCE_EMAIL") or "").strip()
        raw = api_token or os.environ.get("CONFLUENCE_API_TOKEN")
        t = (raw or "").removeprefix("Bearer ").strip() if raw else ""
        if e and t:
            return e, t
        return None

    @staticmethod
    def _provided_date(subdata: str | None) -> datetime:
        if subdata is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            decoded = base64.b64decode(subdata).decode("utf-8")
            return datetime.fromisoformat(decoded.replace("Z", "+00:00"))
        except (binascii.Error, ValueError, UnicodeDecodeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def _execute_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        email: str | None,
        api_token: str | None,
    ) -> dict[str, Any]:
        if not self.base:
            return {}
        creds = self._resolve_auth(email, api_token)
        if not creds:
            return {}
        user, token = creds
        url = urljoin(self.base, endpoint)
        try:
            response = self.session.get(url, params=params, timeout=120, auth=(user, token))
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
        text = re.sub(r"<[^>]+>", " ", storage_value)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_spaces(self, email: str | None = None, api_token: str | None = None) -> list[dict[str, Any]]:
        """Return Confluence spaces as connector-shaped entries (key, name, URL)."""
        payload = self._execute_request("space", {"limit": 250}, email, api_token)
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

    def _pages_in_space(self, space_key: str, email: str | None = None, api_token: str | None = None) -> list[dict[str, Any]]:
        payload = self._execute_request(
            "content",
            {"spaceKey": space_key, "type": "page", "limit": 1000, "expand": "version"},
            email,
            api_token,
        )
        results = payload.get("results", [])
        if isinstance(results, list):
            return [p for p in results if isinstance(p, dict)]
        return []

    def get_page_ids(self, email: str | None = None, api_token: str | None = None) -> dict[str, str]:
        """Return the latest page edit time per space key (ISO strings)."""
        ids: dict[str, str] = {}
        for space in self.get_spaces(email, api_token):
            key = space.get("key")
            if not isinstance(key, str):
                continue
            pages = self._pages_in_space(key, email, api_token)
            latest = datetime.min.replace(tzinfo=timezone.utc)
            for page in pages:
                when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
                latest = max(latest, when)
            ids[key] = latest.isoformat()
        return ids

    def get_pages_in_space(self, space_key: str, email: str | None = None, api_token: str | None = None) -> list[str]:
        """Return page pointers for one space."""
        pages = self._pages_in_space(space_key, email, api_token)
        pointers: list[str] = []
        for page in pages:
            page_id = page.get("id")
            if isinstance(page_id, str):
                pointers.append(self._pointer(page_id))
        return pointers

    def get_page(
        self,
        file_pointer: str,
        include_content: bool = True,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one page by pointer; metadata plus optional base64-encoded plain text."""
        page_id = file_pointer.split("://", 1)[1] if "://" in file_pointer else file_pointer
        payload = self._execute_request(
            f"content/{page_id}",
            {"expand": "body.storage,version,space"},
            email,
            api_token,
        )
        if not payload:
            return {"metadata": {"unique_pointer": self._pointer(page_id), "type": SOURCE_FILE}}
        return self._format_page_payload(payload, page_id, include_content)

    def _format_page_payload(
        self,
        payload: dict[str, Any],
        page_id: str,
        include_content: bool,
    ) -> dict[str, Any]:
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

    def _space_latest_and_page_ids(
        self,
        space_key: str,
        email: str | None,
        api_token: str | None,
    ) -> tuple[datetime, list[str]]:
        pages = self._pages_in_space(space_key, email, api_token)
        space_latest = datetime.min.replace(tzinfo=timezone.utc)
        page_ids: list[str] = []
        for page in pages:
            page_id = page.get("id")
            if isinstance(page_id, str):
                page_ids.append(page_id)
            when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
            space_latest = max(space_latest, when)
        return space_latest, page_ids

    def pointers_to_all_files_to_index(
        self,
        subdata: str | None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Return pointers for spaces with activity newer than the ``subdata`` checkpoint."""
        if self._resolve_auth(email, api_token) is None:
            return {"subdata": subdata, "file_pointers": []}

        provided = self._provided_date(subdata)
        latest = datetime.min.replace(tzinfo=timezone.utc)
        pointers: list[str] = []

        for space in self.get_spaces(email, api_token):
            key = space.get("key")
            if not isinstance(key, str):
                continue
            space_latest, page_ids = self._space_latest_and_page_ids(key, email, api_token)
            latest = max(latest, space_latest)
            if space_latest > provided:
                pointers.extend([self._pointer(pid) for pid in page_ids])

        token = base64.b64encode(latest.isoformat().encode("utf-8")).decode("utf-8")
        return {"subdata": token, "file_pointers": pointers}

    def files_to_index(
        self,
        subdata: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Expand changed pointers into full ``get_page`` payloads for indexing."""
        if self._resolve_auth(email, api_token) is None:
            return {"subdata": subdata, "files": [], "deleted": []}

        pointer_payload = self.pointers_to_all_files_to_index(subdata, email, api_token)
        pointers = pointer_payload.get("file_pointers", [])
        files: list[dict[str, Any]] = []
        if isinstance(pointers, list):
            for pointer in pointers:
                if isinstance(pointer, str):
                    files.append(self.get_page(pointer, include_content=True, email=email, api_token=api_token))
        return {"subdata": pointer_payload.get("subdata"), "files": files, "deleted": []}
