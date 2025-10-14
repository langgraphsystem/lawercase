"""PDF assembler CLI.

Example:
    python -m recommendation_pipeline.pdf_assembler --text out/EB1A_text.pdf --exhibits "out/Exhibit_*.pdf" --index out/exhibits_index.json --out out/EB1A_master.pdf
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog
import typer

from config.logging import setup_logging
from recommendation_pipeline.schemas.exhibits import ExhibitsIndex
from recommendation_pipeline.utils import io_utils, pdf_utils

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Assemble EB-1A master PDF from textual and exhibit PDFs.")


async def assemble_master_pdf(
    text_pdf: Path,
    exhibits: list[Path],
    index_path: Path,
    out_pdf: Path,
) -> Path:
    text_bytes = io_utils.read_bytes(text_pdf)
    exhibits_bytes = [io_utils.read_bytes(path) for path in exhibits]
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    index = ExhibitsIndex.model_validate(index_data)

    expected_total = pdf_utils.pdf_page_count(text_bytes)
    for exhibit_meta in index.items:
        expected_total = max(expected_total, exhibit_meta.page_end)
    merged = pdf_utils.merge_pdfs([text_bytes, *exhibits_bytes])

    total_pages = pdf_utils.pdf_page_count(merged)
    if total_pages < index.total_pages:
        raise ValueError("Merged PDF has fewer pages than index specifies")

    merged_with_bookmarks = pdf_utils.add_bookmarks(merged, index.items)
    io_utils.write_bytes(out_pdf, merged_with_bookmarks)
    logger.info("pdf_assembler.success", out=str(out_pdf), total_pages=total_pages)
    return out_pdf


@cli.command()
def main(
    text: Path = typer.Option(..., "--text", exists=True, readable=True, help="Textual PDF"),
    exhibits: str = typer.Option(..., "--exhibits", help="Glob for exhibit PDFs"),
    index: Path = typer.Option(..., "--index", exists=True, readable=True, help="Index JSON"),
    out: Path = typer.Option(..., "--out", help="Output master PDF path"),
) -> None:
    """CLI entrypoint."""
    setup_logging()
    try:
        exhibit_paths = [Path(p) for p in sorted(Path().glob(exhibits))]
        asyncio.run(assemble_master_pdf(text, exhibit_paths, index, out))
    except Exception as exc:
        logger.exception("pdf_assembler.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
