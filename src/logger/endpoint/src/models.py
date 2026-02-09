from pydantic import BaseModel
from datetime import datetime

class Log(BaseModel):
    service: str
    message: str
    event_type: str
    occured: datetime
