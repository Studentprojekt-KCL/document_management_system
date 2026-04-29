"""File for shared service-level types"""

from pydantic import BaseModel, StrictStr


class MetadataTemplate(BaseModel):
    unique_pointer: StrictStr
    name: StrictStr | None = None


class InputItem(BaseModel):
    content: StrictStr
    metadata: MetadataTemplate


class MarkdownRequest(BaseModel):
    """Request schema for markdown logic."""

    markdown: StrictStr
