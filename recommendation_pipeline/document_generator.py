"""Document generator CLI: HTML+CSS → PDF using DocRaptor.

Example:
    python -m recommendation_pipeline.document_generator --html data/Petition.html --css data/styles.css --out out/EB1A_text.pdf
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
import typer

from config.logging import setup_logging
from config.settings import AppSettings, get_settings
from recommendation_pipeline.clients.docraptor_client import DocRaptorClient
from recommendation_pipeline.schemas.exhibits import DocGenRequest
from recommendation_pipeline.utils import io_utils

logger = structlog.get_logger(__name__)
cli = typer.Typer(help="Generate EB-1A textual PDF via DocRaptor.")


async def generate_document(request: DocGenRequest, settings: AppSettings | None = None) -> Path:
    settings = settings or get_settings()
    client = DocRaptorClient(api_key=settings.doc_raptor_api_key, timeout=60.0)
    try:
        html = io_utils.read_text(request.html_path)
        css = io_utils.read_text(request.css_path) if request.css_path else None
        logger.info("document_generator.render.start", html=str(request.html_path), css=bool(css))
        pdf_bytes = await client.ahtml_to_pdf(html=html, css=css)
        io_utils.write_bytes(request.out_pdf, pdf_bytes)
        logger.info("document_generator.render.success", out=str(request.out_pdf))
        return request.out_pdf
    finally:
        await client.aclose()


@cli.command()
def main(
    html: Path = typer.Option(..., "--html", exists=True, readable=True, help="Input HTML file"),
    css: Path | None = typer.Option(
        None, "--css", exists=True, readable=True, help="Optional CSS file"
    ),
    out: Path = typer.Option(..., "--out", help="Output PDF path"),
) -> None:
    """CLI entrypoint."""
    settings = get_settings()
    setup_logging(settings.log_level)
    try:
        asyncio.run(
            generate_document(DocGenRequest(html_path=html, css_path=css, out_pdf=out), settings)
        )
    except Exception as exc:
        logger.exception("document_generator.error", error=str(exc))
        raise typer.Exit(code=1) from exc
    raise typer.Exit(code=0)


if __name__ == "__main__":
    main()
