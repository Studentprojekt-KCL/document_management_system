from os import environ
from typing import Any
import httpx
import asyncio

# from shared_functions.dmis_logger import dms_error, dms_warning

class ConnectorClient:
    TIMEOUT: int = 

    source_systems: list[dict] # List of dicts of subsytems
    source_systems_names: list[dict] | None
    subdata: str | None

    get_files_urls: list[str]  # URls to /get_files endpoints 

    def __init__(self) -> None:
        self.source_systems = [
            {
                "name":"Gitlab", 
                "connector_url":"http://connector-gitlab.dev.dms-lookup.com", 
                "source_system_url":"https://gitlab.dms-lookup.com"
            },
            {
                "name":"Github", 
                "connector_url":"http://connector-github.dev.dms-lookup.com",
                "source_system_url":"https://github.com"
            },
            {
                "name":"Confluence", 
                "connector_url": "http://connector-confluence.dev.dms-lookup.com",
                "source_system_url":"https://confluence.com"
            }
        ]
        self.subdata = None
        if self.source_systems == [{}]:
            return
        for system in self.source_systems:
            system["connector_url"] = system["connector_url"].rstrip("/")
            system["source_system_url"] = system["source_system_url"].rstrip("/")
         
        
    async def fetch_files_metadata(self, 
        pointers: list[str], 
        include_content, 
        include_last_edit_date
    ) -> list[dict]:
        if pointers == []:
            return []
        sorted_pointers: list[list] = self._sort_pointers(pointers)
        response = await self._get_file_from_pointer(
            sorted_pointers, 
            include_content, 
            include_last_edit_date
        )
        return response
        
    def _sort_pointers(self, pointers: list[str]) -> list[list]: 
        """Sorts pointers according to host part pointer URL eg Gitlab, Github etc""" 
        if pointers == []:
            return []
        sorted_pointers = []
        
        for pointer in pointers:
            if sorted_pointers == []:
                sorted_pointers.append([pointer])
                continue
                
            host = pointer.split("//")[-1].split("/")[0]
            for grouped_pointers in sorted_pointers:
                if host in grouped_pointers[0]:
                    grouped_pointers.append(pointer)
                    continue
                sorted_pointers.append([pointer])
                
        return sorted_pointers
        
    def _slice_url_to_host_and_proto(self, url):
        scheme, rest = url.split("://", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}://{host}"
            
    async def _get_file_from_pointer(self, 
        sorted_pointers: list[list], 
        include_content, 
        include_last_edit_date 
    ) -> Any | None:
        # Get hostnames for connectors according to pointers
        source_system_host_list = []
        for grouped_pointers in sorted_pointers:
            for system in self.source_systems:
                if self._slice_url_to_host_and_proto(grouped_pointers[0]) in system["source_system_url"]:
                    source_system_host_list.append(system["connector_url"])
                    continue
                return # return if source url could not be found
                
        # Send requests to downstream connectors
        async with httpx.AsyncClient() as client:
            tasks = [client.post(
                f"{source_system_host_list[sorted_pointers.index(grouped_pointers)]}/get_files",
                params=[("include_content", include_content), ("include_last_edit_date", include_last_edit_date)],
                json={"file_pointers": grouped_pointers},
                timeout=ConnectorClient.TIMEOUT,
            ) for grouped_pointers in sorted_pointers]
            responses = await asyncio.gather(*tasks) 
            return [item for r in responses for item in r.json()]
            
    def fetch_start_of_streams(self) -> list[str]: 
        stream_urls: list[str] = []
        for source_system in self.source_systems:
            proto_host_url = source_system["connector_url"] 
            stream_url = f"{proto_host_url}/stream_files_to_index"
            stream_urls.append(stream_url)
        return stream_urls
        
    def get_source_system_names(self) -> list[str]: 
        names_of_source_systems: list[str] = []
        for source_system in self.source_systems:
            names_of_source_systems.append(source_system["name"])
        return names_of_source_systems
