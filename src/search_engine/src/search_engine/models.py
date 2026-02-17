"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""

from pydantic import BaseModel

class Metadata(BaseModel):
    name: str | None = None
    author: str | None = None
    version: str | None = None

class Query(BaseModel):
    user_id: str
    query: str | None = None
    metadata: Metadata | None = None


