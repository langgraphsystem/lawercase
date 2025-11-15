"""OCR runner CLI.

Examples:
    python -m recommendation_pipeline.ocr_runner --images data/exhibit1/*.jpg --out out/Exhibit_1.pdf --provider gemini --analyze-only
    python -m recommendation_pipeline.ocr_runner --in out/Exhibit_1.pdf --out out/Exhibit_1_ocr.pdf --provider adobe --finalize
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
import json
from pathlib import Path

from anyio import to_thread
import structlog
import typer

from config.logging import setup_logging
from config.settings import AppSettings, get_settings
from recommendation_pipeline.clients.adobe_pdf_services_client import AdobePDFServices
from recommendation_pipeline.clients.gemini_ocr_client import GeminiOCR
from recommendation_pipeline.utils import io_utils, pdf_utils

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="OCR and exhibit preparation utilities.")


async def analyze_images(
    image_paths: Sequence[Path],
    out_pdf: Path,
    *,
    meta_path: Path | None = None,
    settings: AppSettings | None = None,
) -> tuple[Path, Path]:
    settings = settings or get_settings()
    if not image_paths:
        raise ValueError("At least one image is required")
    client = GeminiOCR(api_key=settings.gemini_api_key)
    try:
        images = [io_utils.read_bytes(path) for path in image_paths]
        pdf_bytes = await to_thread.run_sync(pdf_utils.images_to_pdf, images)
        io_utils.write_bytes(out_pdf, pdf_bytes)

        metadata = await client.aanalyze_images(images)
        meta_path = meta_path or out_pdf.with_suffix(".json")
        io_utils.ensure_directory(meta_path.parent)
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info("ocr_runner.analyze.success", out=str(out_pdf), meta=str(meta_path))
        return out_pdf, meta_path
    finally:
        await client.aclose()


async def finalize_pdf(
    in_pdf: Path,
    out_pdf: Path,
    *,
    settings: AppSettings | None = None,
) -> Path:
    settings = settings or get_settings()
    pdf_bytes = io_utils.read_bytes(in_pdf)
    client = AdobePDFServices(api_key=settings.adobe_ocr_api_key)
    try:
        processed = await client.aocr_pdf(pdf_bytes)
        io_utils.write_bytes(out_pdf, processed)
        logger.info("ocr_runner.finalize.success", out=str(out_pdf))
        return out_pdf
    finally:
        await client.aclose()


def _resolve_images(pattern_or_dir: str) -> Iterable[Path]:
    path = Path(pattern_or_dir)
    if path.is_dir():
        return sorted(path.glob("*"))
    # For glob patterns, use Path.parent with glob
    base_path = Path(pattern_or_dir).parent
    pattern = Path(pattern_or_dir).name
    if base_path.exists() and base_path.is_dir():
        return sorted(base_path.glob(pattern))
    # Fallback: try current directory
    return sorted(Path().glob(pattern_or_dir))


@cli.command()
def main(
    images: str | None = typer.Option(None, "--images", help="Directory or glob of images"),
    in_pdf: Path | None = typer.Option(
        None, "--in", exists=True, readable=True, help="Input PDF for finalize"
    ),
    out: Path = typer.Option(..., "--out", help="Output PDF path"),
    provider: str = typer.Option("gemini", "--provider", help="Provider: gemini|adobe"),
    analyze_only: bool = typer.Option(False, "--analyze-only", help="Perform image analysis only"),
    finalize: bool = typer.Option(False, "--finalize", help="Finalize OCR using Adobe"),
) -> None:
    """CLI entrypoint."""
    settings = get_settings()
    setup_logging(settings.log_level)
    try:
        if analyze_only:
            if not images:
                raise ValueError("--images is required for analyze-only mode")
            image_paths = list(_resolve_images(images))
            asyncio.run(analyze_images(image_paths, out, settings=settings))
        elif finalize:
            if not in_pdf:
                raise ValueError("--in is required for finalize mode")
            asyncio.run(finalize_pdf(in_pdf, out, settings=settings))
        else:
            raise ValueError("Specify either --analyze-only or --finalize")
    except Exception as exc:
        logger.exception("ocr_runner.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
