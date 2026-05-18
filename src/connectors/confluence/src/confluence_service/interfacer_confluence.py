"""Confluence Cloud REST client: spaces, page listing, full page fetch, incremental index.

Uses OAuth 2.0 Bearer tokens via the Atlassian API gateway (api.atlassian.com), targeting
Confluence REST API v2 (``/wiki/api/v2/``). Pass the access token via ``api_token``; the
HTTP service in ``collector_api`` reads it from the ``X-Confluence-Token`` header.
"""

import base64
import binascii
import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin

import httpx

from shared_functions.initialisation_tools import read_env_variable
from shared_functions.dmis_logger import dms_warning

PROJECT = "project"
SOURCE_FILE = "source_file"
_UTC_OFFSET = "+00:00"
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class GetFilesInput:
    """Arguments for :meth:`ConfluenceInterfacer.get_files`."""

    file_pointers: list[str]
    include_content: bool = False
    include_last_edit_date: bool = True
    api_token: str | None = None


class ConfluenceInterfacer:
    """Confluence methods exposed for connector APIs."""

    def __init__(self) -> None:
        self.session = httpx.AsyncClient(timeout=120.0)
        self.address = read_env_variable("CONCONFLUENCE_CONFLUENCE_URL").rstrip("/")
        cloud_id = read_env_variable("CONCONFLUENCE_CLOUD_ID")
        self._gateway_root = f"https://api.atlassian.com/ex/confluence/{cloud_id}"
        self.base = f"{self._gateway_root}/wiki/api/v2/"
        self.max_concurrency = 20
        self.defined_fields = {
            "content": None,
            "name": None,
            "unique_pointer": None,
            "size": None,
            "source_system": read_env_variable("CONCONFLUENCE_SYSTEM_NAME"),
            "last_edit_date": None,
            "type": None,
            "clickable_url": None,
            "file_type": "confluence",
            "file_type_description": "Confluence document",
        }

    @staticmethod
    def _parse_subdata(subdata: str | None) -> dict:
        if subdata is None:
            return {}
        try:
            subdata_bytes = base64.urlsafe_b64decode(subdata)
        except binascii.Error:
            dms_warning("Request where subdata was invalid base64 encoding made to Confluence connector: %s", subdata)
            return {}
        try:
            subdata_str = subdata_bytes.decode("utf-8")
        except UnicodeDecodeError:
            dms_warning(
                "Request where decoded subdata was not valid UTF-8 made to Confluence connector: %r",
                subdata_bytes[:64],
            )
            return {}
        try:
            return json.loads(subdata_str)
        except json.decoder.JSONDecodeError:
            dms_warning("Request where decoded subdata was invalid json structure made to Confluence connector: %s", subdata_str)
            return {}

    @staticmethod
    def _create_date_object(date_string: str | None) -> datetime:
        if date_string is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        date = datetime.fromisoformat(date_string.replace("Z", _UTC_OFFSET))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date

    @staticmethod
    def _generate_subdata(new_subdata: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(new_subdata).encode("utf-8")).decode()

    def _resolve_auth(self, api_token: str | None) -> str | None:
        token = api_token.removeprefix("Bearer ").strip() if api_token else ""
        return token or None

    def _next_url(self, next_link: str) -> str:
        # v2 _links.next values are root-relative, e.g. /wiki/api/v2/pages?cursor=...
        return next_link if next_link.startswith("http") else self._gateway_root + next_link

    async def _paginate(
        self,
        params: dict[str, Any],
        api_token: str | None,
    ) -> list[dict[str, Any]]:
        """Collect all paginated results from the v2 pages endpoint."""
        url = urljoin(self.base, "pages")
        payload = await self.execute_get_request(url, params, api_token)
        if not isinstance(payload, dict):
            return []
        out: list[dict[str, Any]] = []

        while payload:
            results = payload.get("results", [])
            if isinstance(results, list):
                out.extend([item for item in results if isinstance(item, dict)])
            links = payload.get("_links", {})
            next_link = links.get("next") if isinstance(links, dict) else None
            if not isinstance(next_link, str) or not next_link:
                break
            payload = await self.execute_get_request(self._next_url(next_link), {}, api_token)
            if not isinstance(payload, dict):
                return []

        return out

    @staticmethod
    def _safe_when(value: Any) -> datetime:
        if not isinstance(value, str):
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", _UTC_OFFSET))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _pointer(self, page_id: str) -> str:
        return urljoin(self.base, f"pages/{page_id}")

    @staticmethod
    def _extract_text(storage_value: str) -> str:
        text = _TAG_RE.sub(" ", storage_value)
        text = unescape(text)
        return _SPACE_RE.sub(" ", text).strip()

    async def get_spaces(self, api_token: str | None = None) -> list[dict[str, Any]] | None:
        """Return Confluence spaces (key, id, name, clickable_url), or None if the request failed."""
        url = urljoin(self.base, "spaces")
        payload = await self.execute_get_request(url, {"limit": 250}, api_token)
        if not isinstance(payload, dict):
            return None
        results = payload.get("results", [])
        if not isinstance(results, list):
            return []
        spaces: list[dict[str, Any]] = []
        for space in results:
            if not isinstance(space, dict):
                continue
            key = space.get("key")
            space_id = space.get("id")
            if not isinstance(key, str) or not isinstance(space_id, str):
                continue
            links = space.get("_links", {})
            webui = links.get("webui") if isinstance(links, dict) else None
            spaces.append(
                {
                    "key": key,
                    "id": space_id,
                    "name": space.get("name"),
                    "type": PROJECT,
                    "clickable_url": (urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None),
                }
            )
        return spaces

    async def _pages_in_space(
        self,
        space_id: str,
        api_token: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            {
                "space-id": space_id,
                "limit": 200,
            },
            api_token,
        )

    async def get_files(self, data: GetFilesInput) -> list[dict[str, Any]]:
        """Batch fetch pages by pointer."""
        pointers = [ptr for ptr in data.file_pointers if isinstance(ptr, str)]
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _fetch(ptr: str) -> dict[str, Any]:
            async with semaphore:
                page = await self.get_page(
                    ptr,
                    include_content=data.include_content,
                    api_token=data.api_token,
                )
                if not data.include_last_edit_date:
                    page = dict(page)
                    page.pop("last_edit_date", None)
                return page

        if not pointers:
            return []
        return await asyncio.gather(*[_fetch(ptr) for ptr in pointers])

    async def stream_files_to_index(
        self,
        subdata: str | None = None,
        api_token: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield NDJSON: first object has ``subdata``; then one object per page."""
        if self._resolve_auth(api_token) is None:
            yield json.dumps({"subdata": subdata}).encode("utf-8")
            return
        pointer_payload = await self.pointers_to_all_files_to_index(subdata, api_token)
        new_subdata = pointer_payload.get("subdata")
        yield json.dumps({"subdata": new_subdata}).encode("utf-8")
        pointers = pointer_payload.get("file_pointers", [])
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _fetch(pointer: str) -> dict[str, Any]:
            async with semaphore:
                return await self.get_page(pointer, include_content=True, api_token=api_token)

        tasks = [asyncio.create_task(_fetch(pointer)) for pointer in pointers]
        for task in asyncio.as_completed(tasks):
            page = await task
            yield json.dumps(page).encode("utf-8")

    async def get_page(
        self,
        file_pointer: str,
        include_content: bool = True,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one page by pointer; metadata plus optional base64-encoded plain text."""
        payload = await self.execute_get_request(
            file_pointer,
            {"body-format": "storage"},
            api_token,
        )
        if not isinstance(payload, dict):
            return {}
        return self._format_page_payload(payload, file_pointer, include_content)

    def _format_page_payload(
        self,
        payload: dict[str, Any],
        unique_pointer: str,
        include_content: bool,
    ) -> dict[str, Any]:
        title = payload.get("title")
        raw_version = payload.get("version")
        version = raw_version if isinstance(raw_version, dict) else {}
        when = version.get("createdAt")
        raw_links = payload.get("_links")
        webui = raw_links.get("webui") if isinstance(raw_links, dict) else None
        raw_body = payload.get("body")
        storage = raw_body.get("storage", {}) if isinstance(raw_body, dict) else {}
        raw_html = storage.get("value") if isinstance(storage, dict) else ""
        encoded = (self._extract_text(raw_html) if isinstance(raw_html, str) else "").encode("utf-8")

        out_structure = dict(self.defined_fields)
        out_structure |= {
            "unique_pointer": unique_pointer,
            "name": title,
            "size": len(encoded),
            "last_edit_date": when,
            "type": SOURCE_FILE,
            "clickable_url": (urljoin(self.address + "/", webui.lstrip("/")) if isinstance(webui, str) else None),
        }
        if include_content:
            out_structure["content"] = base64.b64encode(encoded).decode("utf-8")
        return out_structure

    async def _space_latest_and_page_ids(
        self,
        space_id: str,
        since: datetime,
        api_token: str | None,
    ) -> tuple[datetime, list[str]]:
        pages = await self._pages_in_space(space_id, api_token)
        space_latest = datetime.min.replace(tzinfo=timezone.utc)
        page_ids: list[str] = []
        for page in pages:
            page_id = page.get("id")
            version = page.get("version")
            when = self._safe_when(version.get("createdAt") if isinstance(version, dict) else None)
            space_latest = max(space_latest, when)
            if isinstance(page_id, str) and when > since:
                page_ids.append(page_id)
        return space_latest, page_ids

    async def pointers_to_all_files_to_index(
        self,
        subdata: str | None,
        api_token: str | None = None,
    ) -> dict[str, Any]:
        """Return pointers for spaces with activity newer than the ``subdata`` checkpoint."""
        if self._resolve_auth(api_token) is None:
            return {"subdata": subdata, "file_pointers": []}
        pointers: list[str] = []
        decoded_subdata = self._parse_subdata(subdata)

        spaces = await self.get_spaces(api_token)
        if spaces is None:
            return {"subdata": subdata, "file_pointers": []}

        async def _process_space(space: dict[str, Any]) -> tuple[str, datetime | None, list[str]]:
            key = space.get("key")
            space_id = space.get("id")
            if not isinstance(key, str) or not isinstance(space_id, str):
                return "", None, []
            date_object = self._create_date_object(decoded_subdata.get(key))
            space_latest, page_ids = await self._space_latest_and_page_ids(space_id, date_object, api_token)
            if space_latest > date_object:
                return key, space_latest, page_ids
            return key, None, []

        for key, space_latest, page_ids in await asyncio.gather(*[_process_space(s) for s in spaces]):
            if key and space_latest is not None:
                pointers.extend([self._pointer(pid) for pid in page_ids])
                decoded_subdata[key] = space_latest.isoformat(timespec="milliseconds").replace(_UTC_OFFSET, "Z")

        new_subdata = self._generate_subdata(decoded_subdata)
        return {"subdata": new_subdata, "file_pointers": pointers}

    async def execute_get_request(self, url: str, params: dict, api_token: str | None) -> dict[str, Any] | list:
        """Execute request to URL."""
        token = self._resolve_auth(api_token)
        if not token:
            return {}
        try:
            response = await self.session.get(
                url, params=params, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, (dict, list)) and payload:
                return payload
        except (httpx.HTTPError, ValueError) as err:
            dms_warning(f"Request to {url} was not successful due to: {err}")
        return {}
