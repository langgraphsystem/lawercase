"""Recommendation pipeline package exposing EB-1A PDF utilities."""

from __future__ import annotations

from .document_generator import generate_document
from .index_builder import build_index
from .ocr_runner import analyze_images, finalize_pdf
from .pdf_assembler import assemble_master_pdf
from .pdf_finalize import finalize_master_pdf

__all__ = [
    "analyze_images",
    "assemble_master_pdf",
    "build_index",
    "finalize_master_pdf",
    "finalize_pdf",
    "generate_document",
]
