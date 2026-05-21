"""File for shared service-level types"""

from pydantic import BaseModel, StrictStr, field_validator


class MetadataTemplate(BaseModel):
    """Metadata schema."""

    unique_pointer: StrictStr
    name: StrictStr | None = None


class InputItem(BaseModel):
    """Schema for content and metadata."""

    content: StrictStr
    metadata: MetadataTemplate


class MarkdownRequest(BaseModel):
    """Request schema for markdown logic."""

    markdown: StrictStr

    @field_validator("markdown")
    @classmethod
    def not_empty(cls, v: str) -> str:
        """Reject empty or whitspace-only markdown"""
        if not v.strip():
            raise ValueError("markdown must not be empty")
        return v


class PointerRequest(BaseModel):
    """Schema for pointer request."""

    pointers: list[StrictStr]
