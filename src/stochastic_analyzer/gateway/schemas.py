"""Definitions for Pydantic schemas used in the gateway API."""

from typing import Literal
from pydantic import BaseModel, Field, StrictStr


class FileMetadata(BaseModel):
    """File metadata enriched with a similarity score, as returned to the frontend.

    Optional fields mirror the connector response shape; missing fields
    are accepted gracefully rather than raising validation errors.
    """

    score: float
    unique_pointer: StrictStr
    name: StrictStr | None = None
    size: StrictStr | None = None
    type: StrictStr | None = None
    source_system: StrictStr | None = None
    file_type: StrictStr | None = None
    file_type_description: StrictStr | None = None
    last_edit_date: StrictStr | None = None
    clickable_url: StrictStr | None = None

    model_config = {"extra": "ignore"}


class RankResponse(BaseModel):
    """Returned response for similarity search, ordered by descending score."""

    ranked_results: list[FileMetadata]


class HealthCheck(BaseModel):
    """Health checks for model and GPU."""

    status: str
    model_loaded: bool


class MetadataTemplate(BaseModel):
    """Metadata fields attached to each document input."""

    name: StrictStr | None = None
    unique_pointer: StrictStr | None = None
    author: StrictStr | None = None

    model_config = {"extra": "ignore"}


class InputItem(BaseModel):
    """A single document item submitted for classification."""

    content: StrictStr = Field(..., min_length=1)
    metadata: MetadataTemplate

    model_config = {"extra": "ignore"}


class ClassificationResult(BaseModel):
    """Output schema for a classified document."""

    unique_pointer: StrictStr | None = None
    security_class: Literal["Public", "Internal", "Sensitive", "Confidential"] = Field(..., alias="Security-class")

    model_config = {"populate_by_name": True}


class PointerRequest(BaseModel):
    """Request schema for pointer-based endpoints."""

    pointers: list[StrictStr] = Field(..., min_length=1)


class SummaryResult(BaseModel):
    """Output schema for a summarized document."""

    summary: StrictStr
