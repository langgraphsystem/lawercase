"""PDF utilities for EB-1A pipeline."""

from __future__ import annotations

from io import BytesIO

import img2pdf
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

from recommendation_pipeline.schemas.exhibits import ExhibitMeta


def images_to_pdf(images: list[bytes]) -> bytes:
    """Convert a list of image bytes into a PDF."""
    streams = [BytesIO(image) for image in images]
    output = img2pdf.convert(streams)  # type: ignore[arg-type]
    return output


def merge_pdfs(parts: list[bytes]) -> bytes:
    """Merge PDFs together preserving order."""
    merger = PdfMerger()
    for part in parts:
        merger.append(BytesIO(part))
    buffer = BytesIO()
    merger.write(buffer)
    merger.close()
    return buffer.getvalue()


def add_bookmarks(pdf_bytes: bytes, metas: list[ExhibitMeta]) -> bytes:
    """Add bookmarks for exhibits according to metadata."""
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for meta in metas:
        page_index = max(0, meta.page_start - 1)
        writer.add_outline_item(meta.title, page_index)
    buffer = BytesIO()
    writer.write(buffer)
    writer.close()
    return buffer.getvalue()


def pdf_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return len(reader.pages)
