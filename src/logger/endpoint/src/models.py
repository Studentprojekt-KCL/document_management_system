"""Database representations."""

from datetime import datetime
from pydantic import BaseModel


class Log(BaseModel):
    """Log object representing database table."""

    service: str
    message: str
    event_type: str
    occured: datetime
