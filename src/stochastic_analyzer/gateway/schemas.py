"""Definitions for Pydantic schemas used in the gateway API."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, StrictStr


class DocumentObject(BaseModel):
    """Define object for content passing."""

    title: str
    owner: Optional[str] = Field(default="")
    reference: str = Field(...)
    content: str = Field(...)


class RankRequest(BaseModel):
    """Define requests."""

    query: str
    documents: list[DocumentObject]


class ScoredDocument(BaseModel):
    """Definition for similarity scores."""

    score: float
    document: DocumentObject


class RankResponse(BaseModel):
    """Returned response."""

    ranked_results: list[ScoredDocument]


class HealthCheck(BaseModel):
    """Health checks for model and GPU."""

    status: str
    model_loaded: bool
    device: str


class MetadataTemplate(BaseModel):
    """Metadata fields attached to each document input."""

    name: Optional[StrictStr] = None
    author: Optional[StrictStr] = None

    model_config = {"extra": "ignore"}


class InputItem(BaseModel):
    """A single document item submitted for classification."""

    content: StrictStr = Field(..., min_length=1)
    metadata: MetadataTemplate

    model_config = {"extra": "ignore"}


class ClassificationResult(BaseModel):
    """Output schema for a classified document."""

    name: Optional[StrictStr] = None
    security_class: Literal["Public", "Internal", "Sensitive", "Confidential"] = Field(..., alias="Security-class")

    model_config = {"populate_by_name": True}


class SummaryResult(BaseModel):
    """Output schema for a summarized document."""

    summary: StrictStr
