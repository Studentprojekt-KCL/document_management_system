"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from datetime import datetime
from pydantic import BaseModel


class Metadata(BaseModel):
    """Object containging file metadata."""

    name: str | None = None
    creator: str | None = None
    created: datetime | None = None
    edited: datetime | None = None


class Query(BaseModel):
    """Query object."""

    user_id: str
    query: str | None = None
    metadata: Metadata | None = None


class File(BaseModel):
    """File object with content and metadata."""

    content: str
    metadata: Metadata
