"""Database representations."""

from datetime import datetime
from pydantic import BaseModel


class Log(BaseModel):
    """Log object representing database table."""

    service: str
    message: str
    event_type: str
    occured: datetime

    def to_string(self) -> str:
        """Get the Log object as a string."""
        date_time = self.occured.strftime("%m/%d/%Y, %H:%M:%S")
        return f"{date_time} [{self.event_type} | {self.service}] {self.message}"

    def to_values(self):
        """Get the log object as an array."""
        return (self.occured, self.message, self.event_type, self.service)
