"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime
from fastapi import FastAPI # , Request
import uvicorn
# from fastapi.encoders import jsonable_encoder
# from fastapi.exceptions import RequestValidationError
from .models import Log
# from fastapi.responses import JSONResponse
from .handlers import handel_get_logs, handel_add_log
# from typing import Any

app = FastAPI()

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(_: Request, exc: RequestValidationError):
#     content: Any = ""
#     if sys.argv[1] == "dev":
#         content = jsonable_encoder({"detail": exc.errors(), "body": exc.body})
#     else:
#         content = ""
#
#     return JSONResponse(
#         status_code=422,
#         content = content,
#     )

@app.get("/logs")
async def get_logs(start: datetime | None = None, end: datetime | None = None) -> list[Log] | None:
    """Get logs, either returns a list or None"""
    return handel_get_logs(start, end)


@app.post("/logs")
async def add_log(log: Log):
    """Add a log to the database, returns the Log."""
    print(log.to_string())
    return handel_add_log(log)

def run():
    uvicorn.run(app, host = "0.0.0.0")
