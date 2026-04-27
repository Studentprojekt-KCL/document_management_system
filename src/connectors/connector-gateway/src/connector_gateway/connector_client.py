"""Module for interacting with connectors to source sysetms"""

import asyncio
import json
import httpx


class ConnectorClient:
    """
    Class for interacing with connectors to source systems
    """

    timeout: int
    source_systems: list[dict]

    def __init__(self, config_path: str, timeout: int) -> None:

        self.timeout = timeout
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

        meta_data: list = await self._get_file_from_pointer(sorted_pointers, include_content, include_last_edit_date)
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
        scheme, rest = url.split("://", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}://{host}"

    async def _get_file_from_pointer(
        self, sorted_pointers: list[list], include_content: bool, include_last_edit_date: bool
    ) -> list:
        """makes http requests to all source systems to gather meta data from pointers"""

        # Get hostnames for connectors according to pointers
        source_system_host_list = []
        for grouped_pointers in sorted_pointers:
            for system in self.source_systems:
                if self._slice_url_to_host_and_proto(grouped_pointers[0]) in system["source_system_url"]:
                    source_system_host_list.append(system["connector_url"])
                    break

        # Send requests to downstream connectors
        async with httpx.AsyncClient() as client:
            tasks = [
                client.post(
                    f"{source_system_host_list[sorted_pointers.index(grouped_pointers)]}/get_files",
                    params=[
                        ("include_content", include_content),
                        ("include_last_edit_date", include_last_edit_date),
                    ],
                    json={"file_pointers": grouped_pointers},
                    timeout=self.timeout,
                )
                for grouped_pointers in sorted_pointers
            ]
            responses = await asyncio.gather(*tasks)
            return [item for r in responses for item in r.json()]

    def fetch_start_of_streams(self) -> list[str]:
        """returns URL to connector for stream proto://<connector-host>/stream_files_to_index"""
        stream_urls: list[str] = []
        for source_system in self.source_systems:
            proto_host_url = source_system["connector_url"]
            stream_url = f"{proto_host_url}/stream_files_to_index"
            stream_urls.append(stream_url)
        return stream_urls

    def get_source_system_names(self) -> list[str]:
        """Returns names of source systems according to config file"""
        names_of_source_systems: list[str] = []
        for source_system in self.source_systems:
            names_of_source_systems.append(source_system["name"])
        return names_of_source_systems
