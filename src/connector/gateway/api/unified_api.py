"""copy right 2024, gpt_index contributors"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.router import FileRouter

app = FastAPI(title="Unified File API", version="1.0")

router = FileRouter()


# =========================
# MODELS
# =========================


class BatchRequest(BaseModel):
    """Request model for batch file retrieval."""

    paths: List[str]
    include_content: bool = True


class SubdataRequest(BaseModel):
    """Request model for files to index retrieval, with optional subdata."""

    subdata: Optional[Dict[str, Any]] = None


# =========================
# HEALTH
# =========================


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


# =========================
# FILE POINTERS
# =========================


@app.get("/files")
def files() -> Dict[str, Any]:
    """Get all file pointers from all connectors."""
    try:
        return router.get_all_pointers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =========================
# SINGLE FILE
# =========================


@app.get("/file")
def file(pointer: str, include_content: bool = True) -> dict:
    """Get a single file by pointer. E.g. smb://path/to/file.txt"""
    try:
        return router.get_file(pointer, include_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =========================
# BATCH
# =========================


@app.post("/files/batch")
def batch(req: BatchRequest) -> Dict[str, Any]:
    """Get multiple files by pointers. E.g. ["smb://path/to/file.txt", "gitlab://repo/path/to/file.md"]"""
    try:
        return router.batch(req.paths, req.include_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# =========================
# FILES TO INDEX (FIXED)
# =========================


@app.post("/files_to_index")
def files_to_index(req: SubdataRequest) -> Dict[str, Any]:
    """Get files to index from all connectors, with optional subdata for
    each connector. Returns combined list of files and deleted pointers."""
    try:
        return router.files_to_index(req.subdata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# OPTIONAL: keep GET for quick manual testing
@app.get("/files_to_index")
def files_to_index_get() -> Dict[str, Any]:
    """Get files to index from all connectors, with optional subdata
    for each connector. Returns combined list of files and deleted pointers."""
    try:
        return router.files_to_index(None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
