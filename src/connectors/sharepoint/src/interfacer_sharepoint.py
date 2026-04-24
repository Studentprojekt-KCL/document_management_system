"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import asyncio
import base64
import binascii
import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from shared_functions.dmis_logger import dms_info, dms_warning
from shared_functions.file_type_logic import determine_file_type, get_documents_only_rescource
from shared_functions.initialisation_tools import read_env_variable
from shared_functions.variables import SOURCE_FILE

HTTP_OK = 200
REQUEST_TIMEOUT = 120


class SharePoint:
    """SharePoint connector methods using Microsoft Graph API with delta queries."""

    GRAPH_BASE: str = "https://graph.microsoft.com/v1.0"
    source_system: str
    file_extensions: list = []
    extension_descriptions: dict = {}

    def __init__(self) -> None:
        """Constructor."""
        self.source_system = read_env_variable("CONSHAREPOINT_SYSTEM_NAME")
        resource = get_documents_only_rescource()
        self.file_extensions = [ext for t in resource for ext in t["extension"]]
        self.extension_descriptions = {ext: t["description"] for t in resource for ext in t["extension"]}

    @staticmethod
    def _get_headers(token: str | None = None) -> dict:
        if isinstance(token, str):
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def _get_sites(self, token: str | None = None) -> list[dict]:
        """Retrieve all accessible SharePoint sites."""
        sites: list[dict] = []
        url: str | None = f"{self.GRAPH_BASE}/sites?search=*"
        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(url, headers=self._get_headers(token), timeout=REQUEST_TIMEOUT)
                if response.status_code != HTTP_OK:
                    dms_warning(f"SharePoint: GET {url} returned {response.status_code}")
                    break
                data = response.json()
                sites.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
        return sites

    async def _get_drives(self, site_id: str, token: str | None = None) -> list[dict]:
        """Retrieve all document library drives for a site."""
        url = f"{self.GRAPH_BASE}/sites/{site_id}/drives"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._get_headers(token), timeout=REQUEST_TIMEOUT)
            if response.status_code != HTTP_OK:
                dms_warning(f"SharePoint: GET {url} returned {response.status_code}")
                return []
        return response.json().get("value", [])

    async def _run_delta_query(self, url: str, token: str | None = None) -> tuple[list[dict], str]:
        """Run a paginated delta query. Returns (items, new_delta_link)."""
        items: list[dict] = []
        delta_link: str = ""
        current_url: str | None = url
        async with httpx.AsyncClient() as client:
            while current_url:
                response = await client.get(current_url, headers=self._get_headers(token), timeout=REQUEST_TIMEOUT)
                if response.status_code != HTTP_OK:
                    dms_warning(f"SharePoint: delta query {current_url} returned {response.status_code}")
                    break
                data = response.json()
                items.extend(data.get("value", []))
                if "@odata.deltaLink" in data:
                    delta_link = data["@odata.deltaLink"]
                    current_url = None
                else:
                    current_url = data.get("@odata.nextLink")
        return items, delta_link

    def _decode_subdata(self, subdata: str | None) -> dict[str, str]:
        """Decode base64 subdata string to {drive_id: delta_link} dict."""
        if subdata is None:
            return {}
        try:
            decoded = base64.urlsafe_b64decode(subdata).decode("utf-8")
            result = json.loads(decoded)
            if isinstance(result, dict):
                return result
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
            dms_info(f"SharePoint: could not decode subdata: {subdata}")
        return {}

    @staticmethod
    def _encode_subdata(delta_map: dict[str, str]) -> str:
        """Encode {drive_id: delta_link} dict to base64 subdata string."""
        return base64.urlsafe_b64encode(json.dumps(delta_map).encode("utf-8")).decode("utf-8")

    def _build_file_record(self, item: dict, drive_id: str) -> dict | None:
        """Build a streaming file record from a Graph API drive item.

        Returns None if the item is a folder, deletion tombstone, or non-qualifying file type.
        """
        if item.get("deleted") is not None or "folder" in item:
            return None
        name: str | None = item.get("name")
        extension = determine_file_type(name, self.file_extensions, self.extension_descriptions)
        if extension.get("file_type") == "Unknown":
            return None
        item_id = item.get("id", "")
        return {
            "content": None,
            "metadata": {
                "unique_pointer": f"{self.GRAPH_BASE}/drives/{drive_id}/items/{item_id}",
                "name": name,
                "size": item.get("size", 0),
                "type": SOURCE_FILE,
                "source_system": self.source_system,
                "last_edit_date": item.get("lastModifiedDateTime"),
                "clickable_url": item.get("webUrl", ""),
            }
            | extension,
        }

    async def _process_drive(self, drive_id: str, delta_url: str, token: str | None) -> tuple[str, list[dict], str]:
        """Run delta query for one drive. Returns (drive_id, qualifying_records, new_delta_link)."""
        items, new_delta_link = await self._run_delta_query(delta_url, token)
        records = [r for item in items if (r := self._build_file_record(item, drive_id)) is not None]
        return drive_id, records, new_delta_link

    async def _collect_drive_tasks(self, token: str | None, delta_map: dict[str, str]) -> list[tuple[str, str]]:
        """Return (drive_id, delta_url) pairs for all accessible drives across all sites."""
        drive_tasks: list[tuple[str, str]] = []
        for site in await self._get_sites(token):
            site_id = site.get("id", "")
            for drive in await self._get_drives(site_id, token):
                drive_id = drive.get("id", "")
                if not drive_id:
                    continue
                delta_url = delta_map.get(drive_id, f"{self.GRAPH_BASE}/drives/{drive_id}/root/delta")
                drive_tasks.append((drive_id, delta_url))
        return drive_tasks

    async def stream_files_to_index(self, subdata: str | None = None, token: str | None = None) -> AsyncGenerator[bytes]:
        """Stream all qualifying documents for indexing.

        Yields a JSON subdata header first, then one JSON-encoded file record per document.
        Delta queries for all drives run in parallel before yielding begins, as the new
        delta tokens are required for the subdata header.
        """
        delta_map = self._decode_subdata(subdata)
        drive_tasks = await self._collect_drive_tasks(token, delta_map)
        results = await asyncio.gather(*[self._process_drive(drive_id, delta_url, token) for drive_id, delta_url in drive_tasks])
        new_delta_map = {drive_id: lnk for drive_id, _, lnk in results if lnk}

        yield json.dumps({"subdata": self._encode_subdata(new_delta_map)}).encode("utf-8")

        for _, records, _ in results:
            for record in records:
                yield json.dumps(record).encode("utf-8")

    async def get_file(
        self,
        unique_pointer: str,
        token: str | None = None,
        include_content: bool = False,
        include_last_edit_date: bool = True,
    ) -> dict:
        """Fetch metadata (and optionally content) for a single file by unique pointer."""
        async with httpx.AsyncClient() as client:
            response = await client.get(unique_pointer, headers=self._get_headers(token), timeout=REQUEST_TIMEOUT)
            if response.status_code != HTTP_OK:
                dms_warning(f"SharePoint: GET {unique_pointer} returned {response.status_code}")
                return {}
            item = response.json()

        name = item.get("name")
        extension = determine_file_type(name, self.file_extensions, self.extension_descriptions)
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
            async with httpx.AsyncClient() as client:
                content_response = await client.get(
                    content_url, headers=self._get_headers(token), timeout=REQUEST_TIMEOUT, follow_redirects=True
                )
                if content_response.status_code == HTTP_OK:
                    result["content"] = base64.b64encode(content_response.content).decode("utf-8")
                else:
                    dms_warning(f"SharePoint: could not fetch content for {unique_pointer}")
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
        return list(await asyncio.gather(*[self.get_file(ptr, token, include_content, include_last_edit_date) for ptr in pointers]))

    async def check_index_needed(self, subdata: str | None, token: str | None = None) -> dict[str, bool]:
        """Check whether any files have changed since the last sync."""
        delta_map = self._decode_subdata(subdata)
        if not delta_map:
            return {"index_needed": True}

        async with httpx.AsyncClient() as client:
            for delta_link in delta_map.values():
                response = await client.get(
                    delta_link,
                    headers=self._get_headers(token),
                    params={"$select": "id,deleted"},
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code != HTTP_OK:
                    dms_warning(f"SharePoint: delta check returned {response.status_code}")
                    continue
                if response.json().get("value"):
                    return {"index_needed": True}

        return {"index_needed": False}
