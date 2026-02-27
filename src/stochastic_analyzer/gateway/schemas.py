"""Definitions for Pydantic schemas used in the embedded rankers API."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, StrictStr


class DocumentObject(BaseModel):
    """Define object for content passing."""

    title: str
    owner: Optional[str] = Field(default="")  # Variable can be str or none
    reference: str = Field(...)  # Hard Ellipsis check due to requiered field
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

#Classification Schemas

class MetadataTemplate(BaseModel):
    """Metadata fields attached to each documents input """

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