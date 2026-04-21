from typing import Any
import argparse

import uvicorn
import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from connector_client import ConnectorClient

from shared_functions.initialisation_tools import read_env_variable, read_port
from shared_functions.file_type_logic import get_file_resource, get_documents_only_rescource

class API:
    """Gateway interface for Search engine"""
    
    app = FastAPI()
    
    log_level: str | None = None
    
    def __init__(self) -> None:
        # Clients
        self.down_stream_client = ConnectorClient()
        # self.gitHubClient = GithubClient()
        # self.smbClient = SmbClient()
        
        # Endpints 
        self.app.add_api_route("/get_files", self.get_files, methods=["POST"])
        # self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])
        # self.app.add_api_route("/connected_source_systems", self.connected_source_systems, methods=["GET"])
        # self.app.add_api_route("/stream_files_to_index", self.stream_files_to_index, methods=["GET"])
        
    async def get_files(
        self, file_pointers: dict[str, list], 
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
        print(include_content)
        print(include_last_edit_date)
        
        files_meta_data = await self.down_stream_client.fetch_files_metadata(
            file_pointers["file_pointers"], 
            include_content,
            include_last_edit_date
        )
        print(files_meta_data)
        return files_meta_data
 
def run() -> None:
    """Initiate FastAPI using Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()
    # if args.dev:
    #     api.log_level = "trace"

    # comments
    uvicorn.run(
        api.app,
        host="127.0.0.1",
        port=8080,
        log_level="trace"
    )
