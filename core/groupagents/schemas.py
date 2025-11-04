"""Data schemas for group agents."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocumentType(BaseModel):
    """Represents the type of document to be generated."""

    name: str = Field(..., description="The name of the document type, e.g., 'EB-1A'.")


class ComplexDocumentResult(BaseModel):
    """Represents the result of the document generation process."""

    document: dict[str, Any] = Field(..., description="The final assembled document.")
    validation: dict[str, Any] = Field(..., description="The results of the quality check.")
