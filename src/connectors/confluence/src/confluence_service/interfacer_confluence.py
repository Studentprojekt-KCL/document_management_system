"""Confluence Cloud REST client: spaces, page listing, full page fetch, incremental index.

HTTP is done with ``httpx.AsyncClient`` (async). Calls use Basic auth (email + API token).
Pass credentials as method arguments, or set ``CONFLUENCE_EMAIL`` and
``CONFLUENCE_API_TOKEN`` for scripts. The HTTP service in ``collector_api`` reads
``X-Confluence-Email`` and ``X-Confluence-Token``.

Set ``CONFLUENCE_ADDRESS`` to the site root (e.g. ``https://tenant.atlassian.net``).
"""

import base64
import binascii
import asyncio
import json
import os
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin

import httpx

from shared_functions.initialisation_tools import read_env_variable

PROJECT = "project"
SOURCE_FILE = "source_file"


@dataclass(frozen=True, slots=True)
class GetFilesInput:
    """Arguments for :meth:`ConfluenceInterfacer.get_files`."""

    file_pointers: list[str]
    include_content: bool = False
    include_last_edit_date: bool = True
    email: str | None = None
    api_token: str | None = None


class ConfluenceInterfacer:
    """Confluence methods exposed for connector APIs."""

    def __init__(self) -> None:
        self.session = httpx.AsyncClient(timeout=120.0)
        self.address = read_env_variable("CONCONFLUENCE_CONFLUENCE_ADDR", "").rstrip("/")
        self.base = self._api_base(self.address)
        self.max_concurrency = 20

    @staticmethod
    def _api_base(address: str) -> str:
        if not address:
            return ""
        if address.endswith("/wiki"):
            return f"{address}/rest/api/"
        return f"{address}/wiki/rest/api/"

    def _resolve_auth(self, email: str | None, api_token: str | None) -> tuple[str, str] | None: #TODO, remove this function
        """Resolve (email, token) from arguments or environment."""
        token = (api_token or "").removeprefix("Bearer ").strip() if api_token else ""
        if email and token:
            return email, token
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

    async def _execute_request(
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
            response = await self.session.get(url, params=params, auth=(user, token))
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        except (httpx.HTTPError, ValueError):
            return {}

    async def _execute_url_request(self, url: str, email: str | None, api_token: str | None) -> dict[str, Any]:
        """Execute request to absolute or relative URL (used for pagination links)."""
        if not self.base:
            return {}
        creds = self._resolve_auth(email, api_token)
        if not creds:
            return {}
        user, token = creds
        target_url = urljoin(self.base, url)
        try:
            response = await self.session.get(target_url, auth=(user, token))
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        except (httpx.HTTPError, ValueError):
            return {}

    async def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        email: str | None,
        api_token: str | None,
    ) -> list[dict[str, Any]]:
        """Collect all paginated results by following ``_links.next``."""
        payload = await self._execute_request(endpoint, params, email, api_token)
        out: list[dict[str, Any]] = []

        while payload:
            results = payload.get("results", [])
            if isinstance(results, list):
                out.extend([item for item in results if isinstance(item, dict)])
            links = payload.get("_links", {})
            next_link = links.get("next") if isinstance(links, dict) else None
            if not isinstance(next_link, str) or not next_link:
                break
            payload = await self._execute_url_request(next_link, email, api_token)

        return out

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

    async def get_spaces(self, email: str | None = None, api_token: str | None = None) -> list[dict[str, Any]]:
        """Return Confluence spaces as connector-shaped entries (key, name, URL)."""
        payload = await self._execute_request("space", {"limit": 250}, email, api_token)
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
                    "clickable_url": (urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None),
                }
            )
        return spaces

    async def _pages_in_space(
        self,
        space_key: str,
        email: str | None = None,
        api_token: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            "content",
            {"spaceKey": space_key, "type": "page", "limit": 200, "expand": "version"},
            email,
            api_token,
        )

    async def get_page_ids(self, email: str | None = None, api_token: str | None = None) -> dict[str, str]:
        """Return the latest page edit time per space key (ISO strings)."""
        ids: dict[str, str] = {}
        for space in await self.get_spaces(email, api_token):
            key = space.get("key")
            if not isinstance(key, str):
                continue
            pages = await self._pages_in_space(key, email, api_token)
            latest = datetime.min.replace(tzinfo=timezone.utc)
            for page in pages:
                when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
                latest = max(latest, when)
            ids[key] = latest.isoformat()
        return ids

    async def get_pages_in_space(
        self,
        space_key: str,
        email: str | None = None,
        api_token: str | None = None,
    ) -> list[str]:
        """Return page pointers for one space."""
        pages = await self._pages_in_space(space_key, email, api_token)
        pointers: list[str] = []
        for page in pages:
            page_id = page.get("id")
            if isinstance(page_id, str):
                pointers.append(self._pointer(page_id))
        return pointers

    async def get_files(self, data: GetFilesInput) -> list[dict[str, Any]]:
        """Batch fetch by pointer; same shape as :meth:`get_page` per item (DMS ``get_files``)."""
        pointers = [ptr for ptr in data.file_pointers if isinstance(ptr, str)]
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _fetch(ptr: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    page = await self.get_page(
                        ptr,
                        include_content=data.include_content,
                        email=data.email,
                        api_token=data.api_token,
                    )
                except (httpx.HTTPError, ValueError, TypeError):
                    return {"metadata": {"unique_pointer": ptr, "type": SOURCE_FILE}}
                if not data.include_last_edit_date and isinstance(page.get("metadata"), dict):
                    page = dict(page)
                    meta = dict(page["metadata"])
                    meta.pop("last_edit_date", None)
                    page["metadata"] = meta
                return page

        if not pointers:
            return []
        return await asyncio.gather(*[_fetch(ptr) for ptr in pointers])

    async def check_index_needed(
        self,
        subdata: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Return whether new content should be indexed (DMS ``index_needed_bool``)."""
        if self._resolve_auth(email, api_token) is None:
            return {"index_needed": False}
        payload = await self.pointers_to_all_files_to_index(subdata, email, api_token)
        pointers = payload.get("file_pointers", [])
        n = len(pointers) if isinstance(pointers, list) else 0
        return {"index_needed": n > 0}

    async def stream_files_to_index(
        self,
        subdata: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield chunks: first JSON object has ``subdata``; then one JSON object per page.

        Matches DMS ``stream_files_to_index`` shape.
        """
        if self._resolve_auth(email, api_token) is None:
            yield json.dumps({"subdata": subdata}).encode("utf-8")
            return
        pointer_payload = await self.pointers_to_all_files_to_index(subdata, email, api_token)
        new_subdata = pointer_payload.get("subdata")
        yield json.dumps({"subdata": new_subdata}).encode("utf-8")
        pointers = pointer_payload.get("file_pointers", [])
        if not isinstance(pointers, list):
            return
        valid_pointers = [ptr for ptr in pointers if isinstance(ptr, str)]
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _fetch(pointer: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.get_page(pointer, include_content=True, email=email, api_token=api_token)
                except (httpx.HTTPError, ValueError, TypeError):
                    return {"metadata": {"unique_pointer": pointer, "type": SOURCE_FILE}}

        tasks = [asyncio.create_task(_fetch(pointer)) for pointer in valid_pointers]
        for task in asyncio.as_completed(tasks):
            page = await task
            yield json.dumps(page).encode("utf-8")

    async def get_page(
        self,
        file_pointer: str,
        include_content: bool = True,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one page by pointer; metadata plus optional base64-encoded plain text."""
        page_id = file_pointer.split("://", 1)[1] if "://" in file_pointer else file_pointer
        payload = await self._execute_request(
            f"content/{page_id}",
            {"expand": "body.storage,version,space"},
            email,
            api_token,
        )
        if not payload:
            return {
                "metadata": {
                    "unique_pointer": self._pointer(page_id),
                    "type": SOURCE_FILE,
                }
            }
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
                "clickable_url": (urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None),
            }
        }
        if include_content:
            out["content"] = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return out

    async def _space_latest_and_page_ids(
        self,
        space_key: str,
        email: str | None,
        api_token: str | None,
    ) -> tuple[datetime, list[str]]:
        pages = await self._pages_in_space(space_key, email, api_token)
        space_latest = datetime.min.replace(tzinfo=timezone.utc)
        page_ids: list[str] = []
        for page in pages:
            page_id = page.get("id")
            if isinstance(page_id, str):
                page_ids.append(page_id)
            when = self._safe_when(page.get("version", {}).get("when") if isinstance(page.get("version"), dict) else None)
            space_latest = max(space_latest, when)
        return space_latest, page_ids

    async def pointers_to_all_files_to_index(
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

        for space in await self.get_spaces(email, api_token):
            key = space.get("key")
            if not isinstance(key, str):
                continue
            space_latest, page_ids = await self._space_latest_and_page_ids(key, email, api_token)
            latest = max(latest, space_latest)
            if space_latest > provided:
                pointers.extend([self._pointer(pid) for pid in page_ids])

        token = base64.b64encode(latest.isoformat().encode("utf-8")).decode("utf-8")
        return {"subdata": token, "file_pointers": pointers}

    async def files_to_index(
        self,
        subdata: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Expand changed pointers into full ``get_page`` payloads for indexing."""
        if self._resolve_auth(email, api_token) is None:
            return {
                "subdata": subdata,
                "files": [],
                "deleted": [],
                "index_needed": False,
            }

        pointer_payload = await self.pointers_to_all_files_to_index(subdata, email, api_token)
        pointers = pointer_payload.get("file_pointers", [])
        files: list[dict[str, Any]] = []
        if isinstance(pointers, list):
            files = await self.get_files(
                GetFilesInput(
                    file_pointers=pointers,
                    include_content=True,
                    include_last_edit_date=True,
                    email=email,
                    api_token=api_token,
                )
            )
        return {
            "subdata": pointer_payload.get("subdata"),
            "files": files,
            "deleted": [],
            "index_needed": bool(files),
        }
