from .models import Log
from .database import database_get_logs, database_add_log
from datetime import datetime, timedelta

def handel_get_logs(start: datetime | None, end: datetime | None) -> list[Log] | None:
    if start is None:
        start = datetime.now() + timedelta(hours=-1)
    if end is None:
        end = datetime.now()

    log = Log(
        service="llm",
        message="hello",
        event_type="ERROR",
        occured=datetime.now()
    )

    database_get_logs()
 
    return [log]

def handel_add_log(log: Log) -> Log:
    return database_add_log(log)
