from __future__ import annotations

import json
from pathlib import Path

import pytest
from PyPDF2 import PdfReader, PdfWriter

from recommendation_pipeline.pdf_assembler import assemble_master_pdf
from recommendation_pipeline.schemas.exhibits import ExhibitMeta, ExhibitsIndex


def _write_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as fh:
        writer.write(fh)
    writer.close()


@pytest.mark.asyncio
async def test_assemble_master_pdf(tmp_path: Path) -> None:
    text_pdf = tmp_path / "text.pdf"
    exhibit_pdf = tmp_path / "exhibit.pdf"

    _write_pdf(text_pdf, 1)
    _write_pdf(exhibit_pdf, 2)

    index = ExhibitsIndex(
        items=[
            ExhibitMeta(
                exhibit_id="E1",
                title="Exhibit 1",
                date=None,
                issuer=None,
                doc_type=None,
                keywords=[],
                page_start=2,
                page_end=3,
            )
        ],
        total_pages=3,
    )

    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index.model_dump()), encoding="utf-8")

    out_pdf = tmp_path / "master.pdf"
    await assemble_master_pdf(text_pdf, [exhibit_pdf], index_path, out_pdf)

    reader = PdfReader(str(out_pdf))
    assert len(reader.pages) == 3
    assert reader.outline
