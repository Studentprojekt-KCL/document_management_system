"""Handel endpoints"""

from fastapi import FastAPI
from datetime import datetime
from .models import Log
from .handlers import handel_get_logs, handel_add_log

app = FastAPI()


@app.get("/logs")
async def get_logs(start: datetime | None = None, end: datetime | None = None) -> list[Log] | None:
    """Get logs, either returns a list or None, crazy"""
    return handel_get_logs(start, end)


@app.post("/logs")
async def add_log(log: Log):
    """Add a log to the database, returns the Log."""
    return handel_add_log(log)
