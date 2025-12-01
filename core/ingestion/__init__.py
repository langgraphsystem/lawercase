"""PDF and document ingestion module for knowledge base.

Provides services to parse, chunk, tag, and store documents in semantic memory.
"""

from __future__ import annotations

from .pdf_ingestion_service import (
    EB1A_CRITERIA_KEYWORDS,
    IngestionResult,
    PDFIngestionService,
)

__all__ = [
    "EB1A_CRITERIA_KEYWORDS",
    "IngestionResult",
    "PDFIngestionService",
]
