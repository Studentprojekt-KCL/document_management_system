"""Main interface for search engine to interact with connectors to source systems"""

import uvicorn
import fastapi
from typing import Annotated

from fastapi import Header
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from connector_gateway.connector_client import ConnectorClient
from connector_gateway.refreshservice_client import RefreshServiceClient

from shared_functions.initialisation_tools import read_env_variable, read_int_env_variable, read_port
from shared_functions.dmis_logger import dms_warning


class API:
    """Gateway interface for Search engine"""

    app = fastapi.FastAPI()

    def __init__(self) -> None:
        self.timeout: int = int(read_int_env_variable("CONGATEWAY_REQUEST_TIMEOUT"))

        self.down_stream_client = ConnectorClient(
            read_env_variable("CONGATEWAY_CONFIG_FILE_PATH", required=True), self.timeout  # type: ignore
        )
        self.refresh_client = RefreshServiceClient(read_env_variable("CONGATEWAY_REFRESH_SERVICE_URL"), self.timeout)

        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])
        self.app.add_api_route("/defined_fields", self.defined_fields, methods=["GET"])
        self.app.add_api_route("/get_auth_user_urls", self.get_auth_user_urls, methods=["GET"])
        self.app.add_api_route("/auth_user", self.auth_user, methods=["GET"], response_model=None)
        self.app.add_api_route("/callback_token", self.callback_token, methods=["POST"])

    async def get_files(
        self,
        file_pointers: dict[str, list],
        include_content: bool = False,
        include_last_edit_date: bool = True,
        authorization: str | None = Header(default=None),
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
        split_pointers = self.down_stream_client.split_pointers(file_pointers.get("file_pointers"))  # noqa
        services = [service.get("name").lower() if isinstance(service.get("name"), str) else "" for service in split_pointers]
        headers = {"authorization": authorization.strip()} if authorization else None
        authentication_tokens = await self.refresh_client.send_post_request(
            "/get_session_tokens", params=None, headers=headers, body=services
        )
        if not isinstance(authentication_tokens, dict):
            raise HTTPException(status_code=400)

        return await self.down_stream_client.fetch_files_metadata(
            split_pointers, include_content, include_last_edit_date, authentication_tokens
        )

    async def stream_files_to_index(self, authorization: str | None = Header(default=None)) -> list[dict]:
        """Returns list with proto://<connector-host>/stream_files_to_index"""
        connectors = await self.down_stream_client.fetch_start_of_streams()
        #services = [service.get("name") for service in connectors]
        services = [service.get("name").lower() if isinstance(service.get("name"), str) else "" for service in connectors]
        headers: dict = {"authorization": authorization.strip()} if authorization else {}
        authentication_tokens: dict = {}

        if authorization:
            tokens = await self.refresh_client.send_post_request("/get_session_tokens", params=None, headers=headers, body=services)
            if isinstance(tokens, dict):
                authentication_tokens = tokens
            else:
                dms_warning(f"Recieved unexpeced structure from refresh-service (expected dict): git({type(tokens)})")

        stream_references: list = []

        for service in connectors:
            service_name = service.get("name").lower() if isinstance(service.get("name"), str) else ""
            service_token = authentication_tokens.get(service_name)
            headers_to_set: dict = {}
            if service_token:
                headers_to_set |= {service.get("authentication_header"): f"{service.get('token_type')} {service_token}"}
            stream_references.append({"stream_url": service.get("stream_url"), "required_headers": headers_to_set})

        return stream_references

    async def connected_source_systems(self) -> list[str]:
        """Returns list with names of all connected source systems"""
        return await self.down_stream_client.get_source_system_names()

    async def defined_fields(self) -> list[str]:
        """Retrieve a unions of all defined fields from defined connectors."""
        return await self.down_stream_client.retrieve_defined_fields()

    async def get_auth_user_urls(self) -> list[dict]:
        """returns names of source systems and auth_user entrypoints"""
        return await self.down_stream_client.get_auth_urls()

    async def auth_user(self, source_system: str, authorization: str | None = Header(None), x_connector_authorization: Annotated[str | None, Header()] = None, referer: Annotated[str | None, Header()] = None):
        """Returns redirect to source system to authenticate."""
        source_system_info = self.down_stream_client.find_service(source_system)

        if source_system_info.get("authentication_method") == "BA":
            body = {"refresh_url": "", "session_variables": {"access_token": x_connector_authorization.lstrip(f"{source_system_info.get('token_type')} ")}}
            response = await self.refresh_client.send_post_request(
                "add_session_token", params={"service_name": source_system}, headers={"authorization": authorization}, body=body
            )
            return response
        if source_system_info.get("source_system") == "session":
            pass #TODO, redirect system.

        if not isinstance(source_system, str) or referer is None:
            dms_warning(
                "No {issue} provided to gateway auth_user".format(  # pylint: disable=C0209
                    issue="referer" if referer is None else "source_system"
                )
            )
            raise HTTPException(status_code=400)

        return await self.down_stream_client.get_auth_redirect(source_system, referer)


    async def callback_token(self, body: dict, service_name: str, authorization: str | None = Header(None)) -> dict | list:
        """Callback endpoint to insert service session token."""
        return await self.refresh_client.send_post_request(
            "add_session_token", params={"service_name": service_name}, headers={"authorization": authorization}, body=body
        )


def run() -> None:
    """Initiate FastAPI using Uvicorn."""

    api = API()

    uvicorn.run(
        api.app,
        host=read_env_variable("CONGATEWAY_FASTAPI_BIND_ADDR", required=True),  # type: ignore
        port=read_port("CONGATEWAY_FASTAPI_BIND_PORT"),
        log_level=read_env_variable("CONGATEWAY_FASTAPI_LOG_LEVEL"),
    )
