"""Pydantic schemas for input validation and classification output."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictStr


class MetadataTemplate(BaseModel):
    """Metadata fields attached to each document input."""

    name: Optional[StrictStr] = ...
    author: Optional[StrictStr] = ...
    version: Optional[StrictStr] = ...

    model_config = {"extra": "forbid"}


class InputItem(BaseModel):
    """A single document item submitted for classification."""

    content: StrictStr = Field(..., min_length=1)
    metadata: MetadataTemplate

    model_config = {"extra": "forbid"}


class ClassificationResult(BaseModel):
    """Output schema for a classified document.

    Security-class values:
      Public, Internal, Sensitive, Confidential
    """

    name: Optional[StrictStr]
    security_class: Literal["Public", "Internal", "Sensitive", "Confidential"] = Field(..., alias="Security-class")

    model_config = {"populate_by_name": True}
