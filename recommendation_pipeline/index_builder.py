"""Exhibits index builder CLI.

Example:
    python -m recommendation_pipeline.index_builder --in out/Exhibit_*.pdf --out out/exhibits_index.json
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from anyio import to_thread
import orjson
import structlog
import typer

from recommendation_pipeline.schemas.exhibits import ExhibitMeta, ExhibitsIndex
from recommendation_pipeline.utils import io_utils, pdf_utils

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Build exhibits index JSON from processed PDF exhibits.")


async def build_index(pdf_paths: list[Path], index_out: Path) -> ExhibitsIndex:
    """Build an exhibits index using metadata JSON alongside each PDF."""
    if not pdf_paths:
        raise ValueError("At least one exhibit PDF is required")

    pdf_paths = sorted(pdf_paths)
    total_pages = 0
    items: list[ExhibitMeta] = []
    for pdf_path in pdf_paths:
        pdf_bytes = io_utils.read_bytes(pdf_path)
        page_count = await to_thread.run_sync(pdf_utils.pdf_page_count, pdf_bytes)
        meta_path = pdf_path.with_suffix(".json")
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata JSON not found for {pdf_path}")
        raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        exhibit_id = raw_meta.get("exhibit_id") or pdf_path.stem
        title = raw_meta.get("summary") or exhibit_id.replace("_", " ").title()
        keywords = raw_meta.get("keywords") or []
        issuer = (raw_meta.get("inferred") or {}).get("issuer")
        date_str = (raw_meta.get("inferred") or {}).get("date")
        exhibit_meta = ExhibitMeta(
            exhibit_id=exhibit_id,
            title=title,
            date=date_str or None,
            issuer=issuer,
            doc_type=raw_meta.get("doc_type"),
            keywords=keywords,
            page_start=total_pages + 1,
            page_end=total_pages + page_count,
        )
        total_pages += page_count
        items.append(exhibit_meta)
    index = ExhibitsIndex(items=items, total_pages=total_pages)
    io_utils.ensure_directory(index_out.parent)
    index_out.write_bytes(orjson.dumps(index.model_dump()))
    logger.info("index_builder.success", count=len(items), out=str(index_out))
    return index


@cli.command()
def main(
    input_glob: str = typer.Option(..., "--in", help="Glob for exhibit PDFs"),
    out: Path = typer.Option(..., "--out", help="Output exhibits_index.json"),
) -> None:
    """CLI entrypoint."""
    try:
        pdf_paths = [Path(p) for p in sorted(Path().glob(input_glob))]
        asyncio.run(build_index(pdf_paths, out))
    except Exception as exc:
        logger.exception("index_builder.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
