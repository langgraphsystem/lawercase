"""Pydantic schemas for EB-1A pipeline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import (BaseModel, ConfigDict, Field, ValidationInfo,
                      field_validator)


class ExhibitMeta(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    exhibit_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    date: date | None = None
    issuer: str | None = None
    doc_type: str | None = None
    keywords: list[str] = Field(default_factory=list)
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)

    @field_validator("page_end")
    @classmethod
    def _validate_page_end(cls, v: int, info: ValidationInfo) -> int:
        start = info.data.get("page_start")
        if start is not None and v < start:
            raise ValueError("page_end must be >= page_start")
        return v


class ExhibitsIndex(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    items: list[ExhibitMeta] = Field(default_factory=list)
    total_pages: int = Field(..., ge=0)


class DocGenRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    html_path: Path = Field(...)
    css_path: Path | None = Field(default=None)
    out_pdf: Path = Field(...)
