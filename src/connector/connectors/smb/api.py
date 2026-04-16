"""SMB API matching GitLab connector exactly."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import argparse
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from smb import SMBCollector


from pydantic import BaseModel


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


MAX_BATCH_SIZE = _env_int("SMB_MAX_BATCH_SIZE", 50)
MAX_WORKERS = _env_int("SMB_API_MAX_WORKERS", 8)
SMB_HOST = os.environ.get("SMB_CONNECTOR_HOST", "0.0.0.0")


class BatchFileRequest(BaseModel):
    """Request model for batch file fetching."""

    paths: List[str]
    include_content: bool = True


class API:
    """SMB API matching GitLab connector exactly."""

    log_level: str | None = None

    def __init__(self) -> None:
        """Create API app, collector and route bindings."""
        self.app = FastAPI()
        self.collector = SMBCollector()

        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)

        self.app.add_api_route("/files", self.files, methods=["GET"])
        self.app.add_api_route("/file", self.file, methods=["GET"])
        self.app.add_api_route("/files_to_index", self.files_to_index, methods=["GET"])
        self.app.add_api_route("/files/batch", self.files_batch, methods=["POST"])

    # =========================
    # ERROR HANDLER (same as GitLab)
    # =========================

    async def validation_exception_handler(self, _: Request, exc: Exception) -> JSONResponse:
        """Return normalized 422 response for validation errors."""
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

        raw_metadata = file_data.get("metadata")

        metadata: Dict[str, Any] = {}
        if isinstance(raw_metadata, dict):
            metadata = raw_metadata

        normalized: Dict[str, Any] = {
            "metadata": {
                "unique_pointer": metadata.get("unique_pointer"),
                "name": metadata.get("name"),
                "size": str(metadata.get("size")),  # GitLab = string
                "last_edit_date": self._to_iso(metadata.get("last_edit_date")),
                "type": "source_file",
                "clickable_url": None,
            }
        }

        if "content" in file_data:
            normalized["content"] = file_data.get("content")

        return normalized

    def _to_iso(self, timestamp: Any) -> str:
        """Convert SMB timestamp → GitLab ISO8601."""
        try:
            return datetime.utcfromtimestamp(float(timestamp)).isoformat() + "Z"
        except (ValueError, TypeError, OSError):
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

        return {"file_pointers": result.get("file_pointers", []), "subdata": result.get("subdata")}

    async def file(self, file_pointer: str, include_content: bool = True) -> dict:
        """
        SAME as GitLab /file
        """

        # SMB → internal processing
        raw = self.collector.get_file(file_pointer, include_content)

        if not include_content:
            raw.pop("content", None)

        return self._normalize_file(raw)

    async def files_to_index(self, subdata: Optional[str] = None) -> dict:
        """
        SAME as GitLab:
        returns files + deleted + subdata
        """

        result = self.collector.files_to_index(subdata)

        normalized_files = [self._normalize_file(f) for f in result.get("files", [])]

        return {"files": normalized_files, "deleted": result.get("deleted", []), "subdata": result.get("subdata")}

    async def files_batch(self, req: BatchFileRequest) -> dict:
        """Fetch multiple files concurrently in one request."""

        if not req.paths:
            return {"files": [], "errors": []}

        if len(req.paths) > MAX_BATCH_SIZE:
            raise HTTPException(status_code=400, detail="Too many files")

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.collector.get_file, path, req.include_content): path for path in req.paths}

            for future in as_completed(futures):
                path = futures[future]

                try:
                    file_data = future.result()
                    file_data = self._normalize_file(file_data)
                    results.append(file_data)

                except (OSError, ValueError, TypeError, KeyError) as e:
                    errors.append({"path": path, "error": str(e)})

        return {"files": results, "errors": errors}


# =========================
# RUN (same style as GitLab)
# =========================


def run() -> None:
    """Start SMB FastAPI service using environment configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()

    api = API()

    if args.dev:
        api.log_level = "debug"

    port = os.environ.get("SMB_CONNECTOR_PORT")

    if port is None or not port.isdigit():
        logging.error("SMB_CONNECTOR_PORT not set")
        return

    uvicorn.run(api.app, host=SMB_HOST, port=int(port), log_level=api.log_level or "info")


if __name__ == "__main__":
    run()
app = API().app
