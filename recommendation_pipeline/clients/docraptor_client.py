"""DocRaptor HTML → PDF client.

CLI example (used indirectly):
    python -m recommendation_pipeline.document_generator --html in.html --out out/EB1A_text.pdf
"""

from __future__ import annotations

import base64
from typing import Any, Final

import httpx
import structlog
from tenacity import (AsyncRetrying, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

logger = structlog.get_logger(__name__)


class DocRaptorError(RuntimeError):
    """Raised when DocRaptor returns an error response."""


class DocRaptorClient:
    """Async client for DocRaptor API."""

    _DEFAULT_BASE_URL: Final[str] = "https://docraptor.com"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        user_agent: str = "mega-agent-pro/eb1a-pipeline",
    ) -> None:
        if not api_key:
            raise ValueError("DocRaptor API key is required")
        self._api_key = api_key
        self._base_url = base_url or self._DEFAULT_BASE_URL
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
            auth=(self._api_key, ""),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def ahtml_to_pdf(self, html: str, css: str | None = None) -> bytes:
        """Render HTML/CSS to PDF bytes using DocRaptor."""
        payload: dict[str, Any] = {
            "doc": {
                "name": "eb1a_document.pdf",
                "document_type": "pdf",
                "document_content": html,
                "test": False,
            }
        }
        if css:
            payload["doc"]["prince_options"] = {
                "style": base64.b64encode(css.encode("utf-8")).decode("ascii"),
                "media": "print",
            }

        logger.debug("docraptor.request", has_css=bool(css))
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((httpx.HTTPError, DocRaptorError)),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post("/docs", json=payload)
                if response.status_code >= 500:
                    logger.warning("docraptor.retry.server_error", status=response.status_code)
                    raise DocRaptorError(f"DocRaptor server error: {response.status_code}")
                if response.status_code >= 400:
                    try:
                        detail = response.json()
                    except ValueError:
                        detail = response.text
                    logger.error("docraptor.client_error", status=response.status_code)
                    raise DocRaptorError(f"DocRaptor error {response.status_code}: {detail}")
                logger.info("docraptor.render.success")
                return response.content
        raise DocRaptorError("DocRaptor render failed after retries")
