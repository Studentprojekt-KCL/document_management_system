"""Module for interacting with connectors to source sysetms"""

import asyncio
import json
import httpx

from fastapi.responses import JSONResponse, RedirectResponse
from shared_functions.dmis_logger import dms_error, dms_warning


class ConnectorClient:
    """
    Class for interacing with connectors to source systems
    """

    timeout: int
    source_systems: list[dict]
    http_client: httpx.AsyncClient

    def __init__(self, config_path: str, timeout: int) -> None:
        self.timeout = timeout
        self.http_client = httpx.AsyncClient()
        self.source_systems = self._load_source_systems_from_file(config_path)

        for system in self.source_systems:
            system["connector_url"] = system["connector_url"].rstrip("/")
            system["source_system_url"] = system["source_system_url"].rstrip("/")

    def _load_source_systems_from_file(self, path: str) -> list:
        """Reads config file and loads it into the program"""
        with open(path, encoding="utf-8") as config_file:
            config = json.load(config_file)
        return config

    async def fetch_files_metadata(self, pointers: list[str], include_content: bool, include_last_edit_date: bool) -> list[dict]:
        """Returns meta data about files pointed to by pointers"""
        if not pointers:
            return []
        sorted_pointers: list[list] = self._sort_pointers(pointers)
        meta_data: list = await self._get_file_from_pointer(
            sorted_pointers, include_content, include_last_edit_date, self.http_client
        )
        return meta_data

    def _sort_pointers(self, pointers: list[str]) -> list[list]:
        """Sorts pointers according to host part of pointer URL eg Gitlab, Github etc"""
        sorted_pointers: list[list] = []
        for pointer in pointers:
            if not sorted_pointers:
                sorted_pointers.append([pointer])
                continue
            host = pointer.split("//")[-1].split("/")[0]
            for grouped_pointers in sorted_pointers.copy():
                if host in grouped_pointers[0]:
                    grouped_pointers.append(pointer)
                    break
                sorted_pointers.append([pointer])
        return sorted_pointers

    def _slice_url_to_host_and_proto(self, url: str) -> str:
        """Returns a URL proto:://<host>/path -> proto://<host>"""
        scheme, rest = url.split("//", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}//{host}"

    async def _get_file_from_pointer(
        self, sorted_pointers: list[list], include_content: bool, include_last_edit_date: bool, http_client: httpx.AsyncClient
    ) -> list:
        """makes http requests to all source systems to gather meta data from pointers"""

        # Get hostnames for connectors according to pointers
        source_system_host_list = []
        for grouped_pointers in sorted_pointers:
            for system in self.source_systems:
                if self._slice_url_to_host_and_proto(grouped_pointers[0]) in system["source_system_url"]:
                    source_system_host_list.append({"url": system["connector_url"], "header": system["authorization_header"]})

                    break

        # Send requests to downstream connectors
        try:
            tasks = [
                http_client.post(
                    f"{source_system_host_list[sorted_pointers.index(grouped_pointers)]["url"]}/get_files",
                    params=[
                        ("include_content", include_content),
                        ("include_last_edit_date", include_last_edit_date),
                    ],
                    headers={"Authorization": f"{source_system_host_list[sorted_pointers.index(grouped_pointers)]["header"]}"},
                    json={"file_pointers": grouped_pointers},
                    timeout=self.timeout,
                )
                for grouped_pointers in sorted_pointers
            ]
            responses = await asyncio.gather(*tasks)
            return [item for r in responses for item in r.json()]
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning("Failed to connect to connector.")
        return []

    async def fetch_start_of_streams(self) -> list[str]:
        """returns URL to connector for stream proto://<connector-host>/stream_files_to_index"""
        stream_urls: list[str] = []
        for source_system in self.source_systems:
            proto_host_url = source_system["connector_url"]
            stream_url = f"{proto_host_url}/stream_files_to_index"
            stream_urls.append(stream_url)
        return stream_urls

    async def get_source_system_names(self) -> list[str]:
        """Returns names of source systems according to config file"""
        names_of_source_systems: list[str] = []
        for source_system in self.source_systems:
            names_of_source_systems.append(source_system["name"])
        return names_of_source_systems

    async def retrieve_defined_fields(self) -> list:
        """Retreve a union of all defined fields from defined connectors."""
        defined_fields = []
        for source_system in self.source_systems:
            connector_url = source_system.get("connector_url")
            if not isinstance(connector_url, str):
                dms_error(f"Sourcesystem is missing connector_url for {source_system}")
                return []
            response = await self.http_client.get(f"{connector_url}/defined_fields")
            try:
                list_object = response.json()
                defined_fields.extend(list_object)
            except (json.JSONDecodeError, TypeError) as err:
                dms_warning(f"Recieved unexpected format in /defined_fields response from {source_system}. {err}")
        return defined_fields

    async def get_auth_urls(self) -> list[dict]:
        """Returns list of dicts with name and auth_user url"""
        auth_user_endpoints: list[dict] = []
        for source_system in self.source_systems:
            auth_user_endpoints.append(
                {"name": source_system["name"], "endpoint": f"/auth_user?source_system={source_system['name'].lower()}"}
            )
        return auth_user_endpoints

    def _set_callback_url(self, referer: str) -> str:
        """takes referer header in original request and sets the auth_callback endpoint"""
        return f"{self._slice_url_to_host_and_proto(referer)}/auth_callback"

    async def get_auth_redirect(self, source_system: str, referer: str) -> RedirectResponse | JSONResponse | None:
        """Proxies downstream ``GET /auth_user``.

        OAuth-style connectors answer with ``3xx`` and ``Location``. Token-style connectors answer with
        JSON (``Content-Type: application/json``) — the gateway must not assume every connector redirects.
        """
        auth_url = ""
        for system in self.source_systems:
            if system["name"].lower() == source_system.lower():
                auth_url = f"{system["connector_url"]}/auth_user"
                break
        if not auth_url:
            return None
        get_headers = {"callback-url": f"{self._set_callback_url(referer)}"}
        try:
            response = await self.http_client.get(auth_url, headers=get_headers, follow_redirects=False)
        except httpx.TimeoutException:
            dms_warning("Request timed out")
            return None
        except httpx.HTTPError:
            dms_warning(f"Failed to connect to connector, url: {auth_url} ")
            return None

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                dms_warning(f"Downstream /auth_user returned {response.status_code} without Location for {auth_url}")
                return None
            return RedirectResponse(url=location, status_code=response.status_code)

        content_type = response.headers.get("content-type", "")
        base_ct = content_type.split(";", 1)[0].strip().lower()

        if response.status_code == 200 and base_ct == "application/json":
            try:
                payload = response.json()
            except json.JSONDecodeError:
                dms_warning(f"Downstream /auth_user returned non-JSON body despite content-type / body shape for {auth_url}")
                return None
            if isinstance(payload, dict):
                return JSONResponse(content=payload, status_code=200)
            dms_warning(f"Downstream /auth_user JSON was not an object for {auth_url}")
            return None

        dms_warning(f"Unexpected /auth_user response from {auth_url} (status {response.status_code}, content-type {content_type!r})")
        return None
