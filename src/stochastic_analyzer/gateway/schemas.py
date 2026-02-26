"""Definitions for Pydantic schemas used in the embedded rankers API."""

from typing import Optional
from pydantic import BaseModel, Field


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
