"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime
from pydantic import BaseModel


class Log(BaseModel):
    """Log object representing database table."""

    id: int | None = None
    service: str
    message: str
    event_type: str
    occured: datetime

    def to_string(self) -> str:
        """Get the Log object as a string."""
        date_time = self.occured.strftime("%m/%d/%Y, %H:%M:%S")
        return f"{date_time} [{self.id}: {self.service} {self.event_type}] {self.message}"

    def to_values(self) -> tuple[datetime, str, str, str]:
        """Get the log object as an array."""
        return (self.occured, self.message, self.event_type, self.service)


class LogsResponse(BaseModel):
    "Paginated logs response"

    logs: list[Log]
    total: int
