"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime
from pydantic import BaseModel


class Metadata(BaseModel):
    """Object containging file metadata."""

    unique_pointer: str
    name: str | None = None
    edited: datetime | None = None
    size: int | None = None
    type: str | None = None


class Query(BaseModel):
    """Query object."""

    user_id: str
    query: str | None = None
    metadata: Metadata | None = None


class File(BaseModel):
    """File object with content and metadata."""

    content: str
    metadata: Metadata
