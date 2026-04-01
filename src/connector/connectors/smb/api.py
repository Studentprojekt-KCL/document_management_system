
import os
import argparse
from typing import Any, Optional, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from smb import SMBCollector


from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel


MAX_BATCH_SIZE = 50
MAX_WORKERS = 8


class BatchFileRequest(BaseModel):
    paths: List[str]
    include_content: bool = True

class API:
    """SMB API matching GitLab connector exactly."""

    app = FastAPI()
    log_level: str | None = None

    def __init__(self) -> None:
        self.collector = SMBCollector()

        self.app.add_exception_handler(
            RequestValidationError,
            self.validation_exception_handler
        )


        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])
        self.app.add_api_route("/files/batch",self.files_batch,methods=["POST"]
)

    # =========================
    # ERROR HANDLER (same as GitLab)
    # =========================

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, RequestValidationError):
            errors = {"detail": exc.errors(), "body": exc.body}
        else:
            errors = {"detail": str(exc)}

        if self.log_level == "debug":
            content = jsonable_encoder(errors)
        else:
            content = "ERROR"

        return JSONResponse(status_code=422, content=content)

    # =========================
    # HELPERS (normalization)
    # =========================

    def _normalize_file(self, file_data: dict) -> dict:
        """Make SMB file match GitLab format exactly."""

        metadata = file_data.get("metadata", {})


        normalized = {
            "metadata": {
                "unique_pointer": metadata.get("unique_pointer"),
                "name": metadata.get("name"),
                "size": str(metadata.get("size")),  # GitLab = string
                "last_edit_date": self._to_iso(metadata.get("last_edit_date")),
                "type": "source_file",
                "clickable_url": None,  # GitLab field
            }
        }

        if "content" in file_data:
            normalized["content"] = file_data.get("content")

        return normalized

    def _to_iso(self, timestamp: Any) -> str:
        """Convert SMB timestamp → GitLab ISO8601."""
        try:
            return datetime.utcfromtimestamp(float(timestamp)).isoformat() + "Z"
        except Exception:
            return ""

    # =========================
    # ENDPOINTS (GitLab-compatible)
    # =========================

    async def files(self, subdata: Optional[str] = None) -> dict:
        """
        SAME as GitLab:
        returns only file_pointers + subdata
        """
        result = self.collector.pointers_to_all_files_to_index(subdata)

        return {
            "file_pointers": result.get("file_pointers", []),
            "subdata": result.get("subdata")
        }

    async def file(self, file_pointer: str, include_content: bool = True) -> dict:
        """
        SAME as GitLab /file
        """

        # SMB → internal processing
        raw = self.collector._process_file(file_pointer)

        if not include_content:
            raw.pop("content", None)

        return self._normalize_file(raw)

    async def files_to_index(self, subdata: Optional[str] = None) -> dict:
        """
        SAME as GitLab:
        returns files + subdata (NO deleted)
        """

        result = self.collector.files_to_index(subdata)

        normalized_files = [
            self._normalize_file(f)
            for f in result.get("files", [])
        ]

        return {
            "files": normalized_files,
            "subdata": result.get("subdata")
        }

    async def files_batch(self, req: BatchFileRequest):

        if not req.paths:
            return {"files": [], "errors": []}

        if len(req.paths) > 50:
            raise HTTPException(status_code=400, detail="Too many files")

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    self.collector.get_file,
                    path,
                    req.include_content
                ): path
                for path in req.paths
            }

            for future in as_completed(futures):
                path = futures[future]

                try:
                    file_data = future.result()
                    file_data = self._normalize_file(file_data)
                    results.append(file_data)

                except Exception as e:
                    errors.append({
                        "path": path,
                        "error": str(e)
                    })

        return {
            "files": results,
            "errors": errors
        }

# =========================
# RUN (same style as GitLab)
# =========================

def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()

    if args.dev:
        api.log_level = "debug"

    port = os.environ.get("SMB_CONNECTOR_PORT")

    if port is None or not port.isdigit():
        print("ERROR: SMB_CONNECTOR_PORT not set")
        return

    uvicorn.run(
        api.app,
        host="0.0.0.0",
        port=int(port),
        log_level=api.log_level or "info"
    )


if __name__ == "__main__":
    run()
app = API().app
