"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""
from pydantic import BaseModel

from se_api.models.metadata import Metadata


class File(BaseModel):
    """File object with content and metadata."""

    content: str
    metadata: Metadata
