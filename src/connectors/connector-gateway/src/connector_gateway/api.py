"""Main interface for search engine to interact with connectors to source systems"""

import uvicorn
import fastapi

from fastapi import Header
from fastapi.responses import RedirectResponse
from connector_gateway.connector_client import ConnectorClient

from shared_functions.initialisation_tools import read_env_variable, read_int_env_variable, read_port


class API:
    """Gateway interface for Search engine"""

    app = fastapi.FastAPI()

    def __init__(self) -> None:
        self.down_stream_client = ConnectorClient(
            read_env_variable("CONGATEWAY_CONFIG_FILE_PATH", required=True), # type: ignore
            read_int_env_variable("CONGATEWAY_REQUEST_TIMEOUT")
        )

        # Endpints
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])
        self.app.add_api_route("/defined_fields", self.defined_fields, methods=["GET"])
        self.app.add_api_route("/get_auth_user_urls", self.get_auth_user_urls, methods=["GET"])
        self.app.add_api_route("/auth_user", self.auth_user, methods=["GET"], response_model=None)

    async def get_files(
        self, file_pointers: dict[str, list], include_content: bool = False, include_last_edit_date: bool = True
    ) -> list:
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
        return await self.down_stream_client.fetch_files_metadata(
            file_pointers["file_pointers"], include_content, include_last_edit_date
        )

    async def stream_files_to_index(self) -> list[str]:
        """Returns list with proto://<connector-host>/stream_files_to_index"""
        return await self.down_stream_client.fetch_start_of_streams()

    async def connected_source_systems(self) -> list[str]:
        """Returns list with names of all connected source systems"""
        return await self.down_stream_client.get_source_system_names()

    async def defined_fields(self) -> list[str]:
        """Retrieve a unions of all defined fields from defined connectors."""
        return await self.down_stream_client.retrieve_defined_fields()

    async def get_auth_user_urls(self) -> list[dict]:
        """returns names of source systems and auth_user entrypoints"""
        return await self.down_stream_client.get_auth_urls()

    async def auth_user(self, source_system: str, referer: str = Header(None)) -> RedirectResponse | None:
        """returns redirect to source system to authenitacte"""
        if not isinstance(source_system, str):
            return
        return await self.down_stream_client.get_auth_redirect(source_system, referer)


def run() -> None:
    """Initiate FastAPI using Uvicorn."""

    api = API()

    uvicorn.run(
        api.app,
        host=read_env_variable("CONGATEWAY_FASTAPI_BIND_ADDR", required=True), # type: ignore
        port=read_port("CONGATEWAY_FASTAPI_BIND_PORT"),
        log_level=read_env_variable("CONGATEWAY_FASTAPI_LOG_LEVEL"),
    )
