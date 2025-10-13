"""Gemini OCR client.

Provides structured OCR metadata for exhibits.

CLI usage (indirect via ocr_runner):
    python -m recommendation_pipeline.ocr_runner --images data/exhibit1/*.jpg --out out/Exhibit_1.pdf --provider gemini --analyze-only
"""

from __future__ import annotations

from typing import Any, Final

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class GeminiOCRError(RuntimeError):
    """Raised when Gemini OCR invocation fails."""


class GeminiOCR:
    """Async client for Gemini OCR analysis."""

    _DEFAULT_ENDPOINT: Final[str] = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
    )

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str | None = None,
        timeout: float = 30.0,
        user_agent: str = "mega-agent-pro/eb1a-pipeline",
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        self._api_key = api_key
        self._endpoint = endpoint or self._DEFAULT_ENDPOINT
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": user_agent, "Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def aanalyze_images(self, images: list[bytes]) -> dict[str, Any]:
        """Analyze a list of image bytes and return structured metadata."""
        if not images:
            raise ValueError("At least one image is required for OCR analysis")

        contents = [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": (
                                image.decode("latin1") if isinstance(image, str) else image.hex()
                            ),
                        }
                    }
                ]
            }
            for image in images
        ]

        payload = {
            "contents": contents,
            "safety_settings": [],
            "generation_config": {"temperature": 0.0},
        }

        params = {"key": self._api_key}

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            retry=retry_if_exception_type((httpx.HTTPError, GeminiOCRError)),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(self._endpoint, json=payload, params=params)
                if response.status_code >= 500:
                    logger.warning("gemini.retry.server_error", status=response.status_code)
                    raise GeminiOCRError(f"Gemini server error: {response.status_code}")
                if response.status_code >= 400:
                    logger.error("gemini.client_error", status=response.status_code)
                    raise GeminiOCRError(f"Gemini error {response.status_code}: {response.text}")
                data = response.json()
                logger.info("gemini.analyze.success")
                return self._normalize(data)
        raise GeminiOCRError("Gemini OCR failed after retries")

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize Gemini response into a predictable structure."""
        candidates = data.get("candidates") or []
        first = candidates[0] if candidates else {}
        content = (first.get("content") or {}).get("parts") or []
        text = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = text.strip()
        return {
            "summary": text,
            "keywords": [],
            "inferred": {"title": None, "issuer": None, "date": None},
        }
