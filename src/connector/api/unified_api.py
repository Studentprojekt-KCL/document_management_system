from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from core.router import FileRouter

app = FastAPI(title="Unified File API", version="1.0")

router = FileRouter()


# =========================
# MODELS
# =========================

class BatchRequest(BaseModel):
    paths: List[str]
    include_content: bool = True


# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# FILE POINTERS
# =========================

@app.get("/files")
def files():
    try:
        return router.get_all_pointers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# SINGLE FILE
# =========================

@app.get("/file")
def file(pointer: str, include_content: bool = True):
    try:
        return router.get_file(pointer, include_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# BATCH
# =========================

@app.post("/files/batch")
def batch(req: BatchRequest):
    try:
        return router.batch(req.paths, req.include_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# FILES TO INDEX
# =========================

@app.get("/files_to_index")
def files_to_index():
    try:
        return router.files_to_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
