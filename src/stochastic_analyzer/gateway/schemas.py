"""Definitions for Pydantic schemas used in the gateway API."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, StrictStr


class ScoredPointer(BaseModel):
    """A pointer with its relevance score."""

    score: float
    pointer: StrictStr


class RankResponse(BaseModel):
    """Returned response."""

    ranked_results: list[ScoredPointer]


class HealthCheck(BaseModel):
    """Health checks for model and GPU."""

    status: str
    model_loaded: bool
    device: str


class MetadataTemplate(BaseModel):
    """Metadata fields attached to each document input."""

    name: Optional[StrictStr] = None
    unique_pointer: Optional[StrictStr] = None
    author: Optional[StrictStr] = None

    model_config = {"extra": "ignore"}


class InputItem(BaseModel):
    """A single document item submitted for classification."""

    content: StrictStr = Field(..., min_length=1)
    metadata: MetadataTemplate

    model_config = {"extra": "ignore"}


class ClassificationResult(BaseModel):
    """Output schema for a classified document."""

    unique_pointer: Optional[StrictStr] = None
    security_class: Literal["Public", "Internal", "Sensitive", "Confidential"] = Field(..., alias="Security-class")

    model_config = {"populate_by_name": True}


class PointerRequest(BaseModel):
    """Request schema for pointer-based endpoints."""

    pointers: list[StrictStr] = Field(..., min_length=1)


class RerankRequest(BaseModel):
    """Request schema for pointer-based reranking."""

    reference: StrictStr = Field(...)
    pointers: list[StrictStr] = Field(..., min_length=1)


class SummaryResult(BaseModel):
    """Output schema for a summarized document."""

    summary: StrictStr
