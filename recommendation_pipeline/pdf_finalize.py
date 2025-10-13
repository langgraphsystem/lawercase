"""PDF finalize CLI.

Example:
    python -m recommendation_pipeline.pdf_finalize --in out/EB1A_master.pdf --ocr adobe --out out/EB1A_master_OCR.pdf
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
import typer

from config.settings import AppSettings, get_settings
from recommendation_pipeline.clients.adobe_pdf_services_client import AdobePDFServices
from recommendation_pipeline.utils import io_utils

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Finalize EB-1A master PDF with optional OCR/compression.")


async def finalize_master_pdf(
    in_pdf: Path,
    out_pdf: Path,
    *,
    provider: str | None = None,
    settings: AppSettings | None = None,
) -> Path:
    settings = settings or get_settings()
    pdf_bytes = io_utils.read_bytes(in_pdf)
    size_mb = len(pdf_bytes) / (1024 * 1024)
    should_ocr = provider == "adobe" or (
        settings.eb1a_pdf_max_mb is not None and size_mb > settings.eb1a_pdf_max_mb
    )
    if should_ocr:
        client = AdobePDFServices(api_key=settings.adobe_ocr_api_key)
        try:
            pdf_bytes = await client.aocr_pdf(pdf_bytes)
            logger.info("pdf_finalize.ocr_applied", provider="adobe")
        finally:
            await client.aclose()
    io_utils.write_bytes(out_pdf, pdf_bytes)
    logger.info("pdf_finalize.success", out=str(out_pdf), size_mb=size_mb)
    return out_pdf


@cli.command()
def main(
    in_pdf: Path = typer.Option(..., "--in", exists=True, readable=True, help="Input master PDF"),
    out: Path = typer.Option(..., "--out", help="Output finalized PDF"),
    ocr: str | None = typer.Option(None, "--ocr", help="OCR provider (adobe)"),
) -> None:
    """CLI entrypoint."""
    try:
        asyncio.run(finalize_master_pdf(in_pdf, out, provider=ocr))
    except Exception as exc:
        logger.exception("pdf_finalize.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
