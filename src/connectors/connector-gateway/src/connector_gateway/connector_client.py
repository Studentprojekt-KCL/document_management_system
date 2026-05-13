"""Module for interacting with connectors to source sysetms"""

import asyncio
import json
import httpx

from fastapi.responses import JSONResponse
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
        source_systems = self._load_source_systems_from_file(config_path)
        source_system_structure: dict = {}

        for system in source_systems:
            system["connector_url"] = system["connector_url"].rstrip("/")
            system["source_system_url"] = system["source_system_url"].rstrip("/")
            source_system_structure[system.get("source_system_url")] = system

        self.source_systems: list[dict] = source_systems  # NOTE; Try to depricate this.
        self.source_system_structure = source_system_structure

    def find_service(self, service_value: str) -> dict:
        """Retrieve specific service for any value specified in source_systems."""
        for service in self.source_systems:
            if service_value.lower() in [v.lower() if isinstance(v, str) else v for v in service.values()]:
                return service
        return {}

    def _load_source_systems_from_file(self, path: str) -> list:
        """Reads config file and loads it into the program"""
        with open(path, encoding="utf-8") as config_file:
            config = json.load(config_file)
        return config

    def split_pointers(self, pointers: list[str] | None) -> list[dict]:
        """Split pointers based on head service and retrieve names of required services.

        ADR:
            Instead of indexing based on urlsplit.netloc,
              it was determined that the current solution is more dynamic when integrating new connectors.
        """
        if not pointers:
            return []
        system_pointers: dict = {}
        for pointer in pointers:
            for system in self.source_system_structure:
                if system not in pointer:
                    continue
                if system in system_pointers:
                    system_pointers[system].append(pointer)
                    break
                if not isinstance(system_pointers.get(system), list):
                    system_pointers[system] = [pointer]
                    break
            else:
                dms_warning(f"No source system found for {pointer}")
        system_list: list = []
        for system, file_pointers in system_pointers.items():
            source = self.source_system_structure.get(system)
            if not isinstance(source, dict):
                continue
            system_list.append(
                {
                    "source_system_url": system,
                    "name": source.get("name"),
                    "file_pointers": file_pointers,
                    "connector_url": source.get("connector_url"),
                    "authentication_header": source.get("authentication_header"),
                    "token_type": source.get("token_type"),
                }
            )
        return system_list

    def _slice_url_to_host_and_port(self, url: str) -> str:
        """Returns a URL proto:://<host>/path -> proto://<host>"""
        scheme, rest = url.split("//", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}//{host}"

    async def fetch_files_metadata(
        self, pointers: list[dict], include_content: bool, include_last_edit_date: bool, authentication_tokens: dict[str, str]
    ) -> list:
        """makes http requests to all source systems to gather meta data from pointers"""
        tasks: list = []
        try:
            for system in pointers:
                system_name = system.get("name") if isinstance(system.get("name"), str) else ""
                auth_header = authentication_tokens.get(system_name.lower())  # type: ignore
                response = self.http_client.post(
                    f"{system.get("connector_url")}/get_files",
                    params=[
                        ("include_content", include_content),
                        ("include_last_edit_date", include_last_edit_date),
                    ],
                    json={"file_pointers": system.get("file_pointers")},
                    headers=(
                        {system.get("authentication_header"): f"{system.get('token_type')} {auth_header}"} if auth_header else None
                    ),
                    timeout=self.timeout,
                )
                tasks.append(response)

            responses = await asyncio.gather(*tasks)
            return [item for r in responses for item in r.json()]
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning("Failed to connect to connector.")
        return []

    async def fetch_start_of_streams(self) -> list[dict]:
        """returns URL to connector for stream proto://<connector-host>/stream_files_to_index"""
        stream_requirements: list[dict] = []
        for source_system in self.source_systems:
            stream_requirements.append(
                {
                    "stream_url": f"{source_system.get("connector_url")}/stream_files_to_index",
                    "name": source_system.get("name"),
                    "authentication_header": source_system.get("authentication_header"),
                    "token_type": source_system.get("token_type"),
                }
            )

        return stream_requirements

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
            system_name: str = source_system["name"]
            auth_user_endpoints.append(
                {
                    "name": system_name,
                    "endpoint": f"/auth_user?source_system={system_name.lower()}",
                    "authentication_method": source_system.get("authentication_method"),
                }
            )
        return auth_user_endpoints

    def _set_callback_url(self, referer: str) -> str:
        """takes referer header in original request and sets the auth_callback endpoint"""
        return f"{self._slice_url_to_host_and_port(referer)}/auth_callback"

    async def get_auth_redirect(self, source_system: str, referer: str) -> JSONResponse | None:
        """redirects user to source system for authentication"""
        auth_url: str = ""
        for system in self.source_systems:
            if system["name"].lower() == source_system.lower():
                auth_url = f"{system["connector_url"]}/auth_user"
                break
        if not isinstance(auth_url, str):
            return
        get_headers = {"callback-url": f"{self._set_callback_url(referer)}"}
        try:
            response = await self.http_client.get(auth_url, headers=get_headers, follow_redirects=False)
            return JSONResponse(content=response.json(), status_code=307)
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning(f"Failed to connect to connector, url: {auth_url} ")
        return None

    async def auth_code_callback(self, service_url: str, code: str) -> dict:
        """Callback to connector layer service."""
        url = f"{service_url}/callback?{code}"
        try:
            response = await self.http_client.get(url, follow_redirects=False)
        except httpx.TimeoutException:
            dms_warning("Request timed out")
        except httpx.HTTPError:
            dms_warning(f"Failed to connect to connector, url: {url} ")

        try:
            return response.json()
        except json.JSONDecodeError:
            return {}
