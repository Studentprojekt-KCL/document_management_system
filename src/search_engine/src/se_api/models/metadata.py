"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""
from datetime import datetime
from pydantic import BaseModel


class Metadata(BaseModel):
    """Object containging file metadata."""

    unique_pointer: str | None = None
    name: str | None = None
    edited: datetime | None = None
    size: int | None = None
    type: str | None = None
