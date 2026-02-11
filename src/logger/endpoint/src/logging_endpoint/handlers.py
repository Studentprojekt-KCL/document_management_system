"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime, timedelta
from .models import Log
from .database import database_get_logs, database_add_log


def handel_get_logs(start: datetime | None, end: datetime | None) -> list[Log] | None:
    """Get logs from the database, returns a list.

    Keyword arguments:
    start -- Start timestamp for grab.
    end -- End timestamp for grab.
    """

    if start is None:
        start = datetime.now() + timedelta(hours=-1)
    if end is None:
        end = datetime.now()

    log = Log(service="llm", message="hello", event_type="ERROR", occured=datetime.now())

    database_get_logs()

    return [log]


def handel_add_log(log: Log) -> Log:
    """Add a log to the database and return it."""

    return database_add_log(log)
