from typing import Any

import uvicorn
import fastapi

from connector_gateway.connector_client import ConnectorClient

from shared_functions.initialisation_tools import read_env_variable, read_port

class API:
    """Gateway interface for Search engine"""

    app = fastapi.FastAPI()

    def __init__(self) -> None:
        self.down_stream_client = ConnectorClient()

        # Endpints 
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])

    async def get_files(self, 
        file_pointers: dict[str, list], 
        include_content: bool = False, 
        include_last_edit_date: bool = True
    ) -> Any:
        """Endpoint for retrieving specific file.
        Example request:
            curl -X 'POST' \
            '<HOST>/get_files?include_content=false&include_last_edit_date=true' \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
            "file_pointers": ["<FILE_PTR>"]
            }'
        """
        files_meta_data = await self.down_stream_client.fetch_files_metadata(
            file_pointers["file_pointers"], 
            include_content,
            include_last_edit_date
        )
        return files_meta_data

    def stream_files_to_index(self) -> list[str]:
        stream_urls: list[str] = self.down_stream_client.fetch_start_of_streams()
        return stream_urls

    def connected_source_systems(self) -> list[str]:
        names_of_source_systems: list[str] = self.down_stream_client.get_source_system_names()
        return names_of_source_systems
 
def run() -> None:
    """Initiate FastAPI using Uvicorn."""

    api = API()

    uvicorn.run(
        api.app,
        host = read_env_variable("CONGATEWAY_FASTAPI_BIND_ADDR"),
        port = read_port("CONGATEWAY_FASTAPI_BIND_PORT"),
        log_level = read_env_variable("CONGATEWAY_FASTAPI_LOG_LEVEL")
    )
