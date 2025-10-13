"""Adobe PDF Services OCR client.

CLI usage (indirect via ocr_runner/pdf_finalize):
    python -m recommendation_pipeline.ocr_runner --in Exhibit.pdf --out Exhibit_ocr.pdf --provider adobe --finalize
"""

from __future__ import annotations

from typing import Final

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class AdobePDFServicesError(RuntimeError):
    """Raised when Adobe PDF Services request fails."""


class AdobePDFServices:
    """Async client for Adobe PDF Services OCR."""

    _DEFAULT_ENDPOINT: Final[str] = "https://api.pdfservices.adobe.com/operation/ocr"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str | None = None,
        timeout: float = 60.0,
        user_agent: str = "mega-agent-pro/eb1a-pipeline",
    ) -> None:
        if not api_key:
            raise ValueError("Adobe OCR API key is required")
        self._api_key = api_key
        self._endpoint = endpoint or self._DEFAULT_ENDPOINT
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": user_agent,
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/pdf",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def aocr_pdf(self, pdf: bytes) -> bytes:
        """Run OCR on PDF bytes using Adobe PDF Services."""
        if not pdf:
            raise ValueError("PDF payload cannot be empty")

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.HTTPError, AdobePDFServicesError)),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(self._endpoint, content=pdf)
                if response.status_code >= 500:
                    logger.warning("adobe.retry.server_error", status=response.status_code)
                    raise AdobePDFServicesError(f"Adobe server error: {response.status_code}")
                if response.status_code >= 400:
                    logger.error("adobe.client_error", status=response.status_code)
                    raise AdobePDFServicesError(
                        f"Adobe error {response.status_code}: {response.text}"
                    )
                logger.info("adobe.ocr.success")
                return response.content
        raise AdobePDFServicesError("Adobe OCR failed after retries")
