from fastapi import FastAPI
from .models import Log
from .handlers import handel_get_logs, handel_add_log
from datetime import datetime

app = FastAPI()

@app.get("/logs")
async def get_logs(start: datetime | None = None, end: datetime | None = None) -> list[Log] | None:
    return handel_get_logs(start, end)

@app.post("/logs")
async def add_log(log: Log):
    return handel_add_log(log)
