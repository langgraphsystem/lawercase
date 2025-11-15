from __future__ import annotations

import json
from pathlib import Path

from PyPDF2 import PdfWriter
import pytest

from recommendation_pipeline.index_builder import build_index
from recommendation_pipeline.schemas.exhibits import ExhibitsIndex


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as fh:
        writer.write(fh)
    writer.close()


@pytest.mark.asyncio
async def test_build_index(tmp_path: Path) -> None:
    exhibit1 = tmp_path / "Exhibit_1.pdf"
    exhibit2 = tmp_path / "Exhibit_2.pdf"
    _make_pdf(exhibit1, 2)
    _make_pdf(exhibit2, 3)

    meta1 = {"exhibit_id": "E1", "summary": "Exhibit 1", "keywords": ["a"], "inferred": {}}
    meta2 = {"exhibit_id": "E2", "summary": "Exhibit 2", "keywords": ["b"], "inferred": {}}
    (exhibit1.with_suffix(".json")).write_text(json.dumps(meta1), encoding="utf-8")
    (exhibit2.with_suffix(".json")).write_text(json.dumps(meta2), encoding="utf-8")

    index_path = tmp_path / "exhibits_index.json"
    await build_index([exhibit1, exhibit2], index_path)
    data = json.loads(index_path.read_text(encoding="utf-8"))
    index = ExhibitsIndex.model_validate(data)
    assert index.total_pages == 5
    assert index.items[0].page_start == 1
    assert index.items[0].page_end == 2
    assert index.items[1].page_start == 3
    assert index.items[1].page_end == 5
