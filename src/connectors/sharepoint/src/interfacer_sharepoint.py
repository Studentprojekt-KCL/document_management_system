"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import asyncio
import base64
import binascii
import gzip
import json
from collections.abc import AsyncGenerator
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlparse

import httpx

from shared_functions.dmis_logger import dms_info, dms_warning
from shared_functions.file_type_logic import determine_file_type, get_file_resource
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.variables import SOURCE_FILE

REQUEST_TIMEOUT = 120
MAX_CONCURRENT_REQUESTS = 20
MAX_RETRIES = 3


class _HttpCtx(NamedTuple):
    """Bundles the three request-scoped values threaded through all private methods. (Happy pylint (: )"""

    client: httpx.AsyncClient
    sem: asyncio.Semaphore
    token: str | None


class SharePoint:
    """SharePoint connector methods using Microsoft Graph API with delta queries."""

    graph_base: str
    source_system: str
    file_extensions: list
    extension_descriptions: dict

    def __init__(self) -> None:
        """Constructor."""
        self.graph_base = read_env_variable("CONSHAREPOINT_GRAPH_BASE").strip().rstrip("/")
        self.source_system = read_env_variable("CONSHAREPOINT_SYSTEM_NAME")
        file_type_resource = get_file_resource()
        self.file_extensions = [t.get("extension") for t in file_type_resource]
        self.extension_descriptions = {t.get("extension"): t.get("description") for t in file_type_resource}

    @staticmethod
    async def _request_with_retry(ctx: _HttpCtx, url: str, method: str = "get", **kwargs: Any) -> httpx.Response:
        """HTTP request with semaphore-limited concurrency and 429 Retry-After handling.

        The semaphore is released before sleeping so the slot is not held during backoff.
        Returns the final response after retries are exhausted; caller handles non-200.
        """
        headers = {"Authorization": f"Bearer {ctx.token}"} if isinstance(ctx.token, str) else {}
        kwargs.setdefault("headers", headers)
        last_response: httpx.Response
        for attempt in range(MAX_RETRIES):
            async with ctx.sem:
                last_response = await getattr(ctx.client, method)(url, **kwargs)
            if last_response.status_code != httpx.codes.TOO_MANY_REQUESTS:
                return last_response
            raw = last_response.headers.get("Retry-After", "5")
            retry_after = int(raw) if raw.isdigit() else 5
            dms_warning(f"SharePoint: rate limited, retrying in {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(retry_after)
        return last_response

    async def _get_sites(self, ctx: _HttpCtx) -> list[dict]:
        """Retrieve all SharePoint sites accessible to the authenticated user via Microsoft Search.

        Uses POST /search/query so only sites the user can actually access are returned,
        avoiding the 403 noise that comes from enumerating all tenant sites with sites?search=*.
        """
        url = f"{self.graph_base}/search/query"
        sites: list[dict] = []
        page_size = 500
        from_index = 0

        while True:
            body = {
                "requests": [
                    {
                        "entityTypes": ["site"],
                        "query": {"queryString": "*"},
                        "from": from_index,
                        "size": page_size,
                    }
                ]
            }
            response = await self._request_with_retry(ctx, url, method="post", json=body, timeout=REQUEST_TIMEOUT)
            if response.status_code != httpx.codes.OK:
                dms_warning(f"SharePoint: site search failed with status {response.status_code}")
                break
            containers = response.json().get("value", [{}])[0].get("hitsContainers", [])
            if not containers:
                break
            container = containers[0]
            for hit in container.get("hits", []):
                resource = hit.get("resource", {})
                if resource.get("id"):
                    sites.append(resource)
            if not container.get("moreResultsAvailable", False):
                break
            from_index += page_size

        return sites

    async def _get_drives(self, ctx: _HttpCtx, site_id: str) -> list[dict]:
        """Retrieve all document library drives for a site."""
        url = f"{self.graph_base}/sites/{site_id}/drives"
        response = await self._request_with_retry(ctx, url, timeout=REQUEST_TIMEOUT)
        if response.status_code == httpx.codes.FORBIDDEN:
            dms_info("SharePoint: drive listing denied (403) — site not accessible to this user")
            return []
        if response.status_code != httpx.codes.OK:
            dms_warning(f"SharePoint: drive listing failed with status {response.status_code}")
            return []
        return response.json().get("value", [])

    async def _run_delta_query(self, ctx: _HttpCtx, url: str) -> tuple[list[dict], str]:
        """Run a paginated delta query. Returns (items, new_delta_link)."""
        items: list[dict] = []
        delta_link: str = ""
        current_url: str | None = url
        while current_url:
            response = await self._request_with_retry(ctx, current_url, timeout=REQUEST_TIMEOUT)
            if response.status_code != httpx.codes.OK:
                dms_warning(f"SharePoint: delta query failed with status {response.status_code}")
                break
            data = response.json()
            items.extend(data.get("value", []))
            if "@odata.deltaLink" in data:
                delta_link = data["@odata.deltaLink"]
                current_url = None
            else:
                current_url = data.get("@odata.nextLink")
        return items, delta_link

    @staticmethod
    def _decode_subdata(subdata: str | None) -> dict[str, str]:
        """Decode base64 subdata string to {drive_id: delta_token} dict."""
        if subdata is None:
            return {}
        try:
            decoded = gzip.decompress(base64.urlsafe_b64decode(subdata)).decode("utf-8")
            result = json.loads(decoded)
            if isinstance(result, dict):
                return result
        except (binascii.Error, json.JSONDecodeError, OSError, UnicodeDecodeError):
            dms_info("SharePoint: could not decode subdata, starting fresh")
        return {}

    @staticmethod
    def _encode_subdata(delta_map: dict[str, str]) -> str:
        """Encode {drive_id: delta_token} dict to gzip-compressed base64 subdata string."""
        return base64.urlsafe_b64encode(gzip.compress(json.dumps(delta_map).encode("utf-8"))).decode("utf-8")

    def _build_file_record(self, item: dict, drive_id: str) -> dict | None:
        """Build a streaming file record from a Graph API drive item.

        Returns None if the item is a folder or deletion tombstone.
        """
        if item.get("deleted") is not None or "folder" in item:
            return None
        name: str | None = item.get("name")
        extension = determine_file_type(name, self.file_extensions, self.extension_descriptions)
        if extension.get("file_type") == "Unknown":
            dms_info(f"SharePoint: indexing file with unrecognised extension: {repr(name)}")
        item_id = item.get("id", "")
        return {
            "metadata": {
                "unique_pointer": f"{self.graph_base}/drives/{drive_id}/items/{item_id}",
                "name": name,
                "size": item.get("size", 0),
                "type": SOURCE_FILE,
                "source_system": self.source_system,
                "last_edit_date": item.get("lastModifiedDateTime"),
                "clickable_url": item.get("webUrl", ""),
            }
            | extension,
        }

    async def _fetch_record_content(self, ctx: _HttpCtx, record: dict) -> None:
        """Fetch file bytes and base64-encode them into record['content'] in-place."""
        record["content"] = None
        content_url = f"{record['metadata']['unique_pointer']}/content"
        response = await self._request_with_retry(ctx, content_url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        if response.status_code == httpx.codes.OK:
            record["content"] = base64.b64encode(response.content).decode("utf-8")
        else:
            dms_warning(f"SharePoint: could not fetch content for {record['metadata'].get('name')}")

    async def _process_drive(self, ctx: _HttpCtx, drive_id: str, delta_url: str) -> tuple[str, list[dict], str]:
        """Run delta query for one drive. Returns (drive_id, qualifying_records, new_delta_link)."""
        items, new_delta_link = await self._run_delta_query(ctx, delta_url)
        records: list[dict] = []
        for item in items:
            record = self._build_file_record(item, drive_id)
            if record is not None:
                records.append(record)
        return drive_id, records, new_delta_link

    async def _collect_drive_tasks(self, ctx: _HttpCtx, delta_map: dict[str, str]) -> list[tuple[str, str]]:
        """Return (drive_id, delta_url) pairs for all accessible drives across all sites.

        Site pagination is sequential; _get_drives calls for all sites run in parallel.
        """
        sites = await self._get_sites(ctx)
        site_ids = [site_id for site in sites if isinstance(site_id := site.get("id"), str) and site_id]
        drives_results = await asyncio.gather(
            *[self._get_drives(ctx, site_id) for site_id in site_ids],
            return_exceptions=True,
        )
        drive_tasks: list[tuple[str, str]] = []
        for drives in drives_results:
            if isinstance(drives, BaseException):
                dms_warning(f"SharePoint: skipping inaccessible site ({type(drives).__name__})")
                continue
            for drive in drives:
                drive_id = drive.get("id", "")
                if not drive_id:
                    continue
                stored = delta_map.get(drive_id)
                delta_url = (
                    f"{self.graph_base}/drives/{drive_id}/root/delta?token={stored}"
                    if stored
                    else f"{self.graph_base}/drives/{drive_id}/root/delta"
                )
                drive_tasks.append((drive_id, delta_url))
        return drive_tasks

    async def stream_files_to_index(self, subdata: str | None = None, token: str | None = None) -> AsyncGenerator[bytes]:
        """Stream all qualifying documents for indexing.

        Yields a JSON subdata header first, then one JSON-encoded file record per document.
        Delta queries for all drives run in parallel before yielding begins, as the new
        delta tokens are required for the subdata header.
        """
        delta_map = self._decode_subdata(subdata)
        async with httpx.AsyncClient(cookies={}) as client:
            ctx = _HttpCtx(client, asyncio.Semaphore(MAX_CONCURRENT_REQUESTS), token)
            drive_tasks = await self._collect_drive_tasks(ctx, delta_map)
            raw = await asyncio.gather(
                *[self._process_drive(ctx, drive_id, delta_url) for drive_id, delta_url in drive_tasks],
                return_exceptions=True,
            )
            results = []
            for outcome in raw:
                if isinstance(outcome, BaseException):
                    dms_warning(f"SharePoint: skipping drive due to processing error ({type(outcome).__name__})")
                else:
                    results.append(outcome)
            await asyncio.gather(*[self._fetch_record_content(ctx, r) for _, records, _ in results for r in records])
        new_delta_map = {
            drive_id: tok for drive_id, _, lnk in results if lnk and (tok := parse_qs(urlparse(lnk).query).get("token", [""])[0])
        }

        yield json.dumps({"subdata": self._encode_subdata(new_delta_map)}).encode("utf-8")

        for _, records, _ in results:
            for record in records:
                yield json.dumps(record).encode("utf-8")

    async def _get_file(
        self,
        ctx: _HttpCtx,
        unique_pointer: str,
        include_content: bool = False,
        include_last_edit_date: bool = True,
    ) -> dict:
        """Fetch metadata (and optionally content) for a single file using the provided client.

        Returns {} if metadata cannot be read.
        """
        response = await self._request_with_retry(ctx, unique_pointer, timeout=REQUEST_TIMEOUT)
        if response.status_code != httpx.codes.OK:
            dms_warning(f"SharePoint: file metadata request failed with status {response.status_code}")
            return {}
        item = response.json()

        name = item.get("name")
        extension = determine_file_type(name, self.file_extensions, self.extension_descriptions)
        if extension.get("file_type") == "Unknown":
            dms_info(f"SharePoint: fetching file with unrecognised extension: {repr(name)}")
        result: dict[str, Any] = {
            "unique_pointer": unique_pointer,
            "name": name,
            "size": item.get("size"),
            "type": SOURCE_FILE,
            "source_system": self.source_system,
            "clickable_url": item.get("webUrl", ""),
        } | extension

        if include_last_edit_date:
            result["last_edit_date"] = item.get("lastModifiedDateTime")

        if include_content:
            content_url = f"{unique_pointer}/content"
            content_response = await self._request_with_retry(ctx, content_url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            if content_response.status_code == httpx.codes.OK:
                result["content"] = base64.b64encode(content_response.content).decode("utf-8")
            else:
                dms_warning("SharePoint: could not fetch file content")
                result["content"] = None

        return result

    async def get_files(
        self,
        pointers: list,
        token: str | None = None,
        include_content: bool = False,
        include_last_edit_date: bool = True,
    ) -> list:
        """Retrieve information for each file in a list of unique pointers."""
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        async with httpx.AsyncClient(cookies={}) as client:
            ctx = _HttpCtx(client, sem, token)
            return list(
                await asyncio.gather(*[self._get_file(ctx, ptr, include_content, include_last_edit_date) for ptr in pointers])
            )

    async def _check_drive_delta(self, ctx: _HttpCtx, delta_link: str) -> bool:
        """Return True if this drive has changes or its delta token is invalid/expired."""
        response = await self._request_with_retry(ctx, delta_link, timeout=REQUEST_TIMEOUT)
        if response.status_code != httpx.codes.OK:
            return True
        return bool(response.json().get("value"))

    async def check_index_needed(self, subdata: str | None, token: str | None = None) -> dict[str, bool]:
        """Check whether any files have changed since the last sync."""
        delta_map = self._decode_subdata(subdata)
        if not delta_map:
            return {"index_needed": True}
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        async with httpx.AsyncClient(cookies={}) as client:
            ctx = _HttpCtx(client, sem, token)
            results = await asyncio.gather(
                *[
                    self._check_drive_delta(ctx, f"{self.graph_base}/drives/{drive_id}/root/delta?token={tok}")
                    for drive_id, tok in delta_map.items()
                ],
                return_exceptions=True,
            )
        if any(r is True or isinstance(r, BaseException) for r in results):
            return {"index_needed": True}
        return {"index_needed": False}
