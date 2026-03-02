"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""
from pydantic import BaseModel
from tantivy import tantivy

from se_api.models.metadata import Metadata

class Query(BaseModel):
    """Query object."""

    user_id: str
    query: str | None = None
    metadata: Metadata | None = None
