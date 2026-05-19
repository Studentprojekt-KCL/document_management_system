"""File for shared service-level types"""

from pydantic import BaseModel, Field, StrictStr


class MetadataTemplate(BaseModel):
    """Metadata schema."""

    unique_pointer: StrictStr
    name: StrictStr | None = None


class InputItem(BaseModel):
    """Schema for content and metadata."""

    content: StrictStr
    metadata: MetadataTemplate


class MarkdownRequest(BaseModel):
    """Request schema for markdown logic.

    Validation rules:
    - `markdown` must be a UTF-8 string (enforced by FastAPI's JSON decoder).
    - Must be a string, not bool/int/float (enforced by StrictStr).
    - Must not be empty.
    """

    markdown: StrictStr = Field(
        ...,
        min_length=1,
        description="Markdown content to convert to PDF. UTF-8, non-empty.",
    )


class PointerRequest(BaseModel):
    """Schema for pointer request."""

    pointers: list[StrictStr]
