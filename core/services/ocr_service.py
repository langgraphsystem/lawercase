"""
OCR service for extracting text from images and scanned documents.

Uses OpenAI Vision API for OCR processing.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class OCRService:
    """Service for OCR text extraction from images and documents."""

    def __init__(self, openai_api_key: str | None = None):
        """Initialize OCR service.

        Args:
            openai_api_key: OpenAI API key. If not provided, will try to get from settings.
        """
        self._api_key = openai_api_key
        self._client = None

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                if not self._api_key:
                    from config.settings import get_settings

                    settings = get_settings()
                    self._api_key = settings.openai_api_key

                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                logger.error("ocr.openai_not_installed")
                raise RuntimeError("OpenAI package not installed")
        return self._client

    async def extract_text_from_image(
        self,
        image_bytes: bytes,
        file_name: str = "image",
        language_hint: str = "Russian and English",
    ) -> dict[str, Any]:
        """Extract text from an image using Vision API.

        Args:
            image_bytes: Raw image bytes
            file_name: Original filename for context
            language_hint: Expected languages in the document

        Returns:
            Dictionary with extracted_text, confidence, and metadata
        """
        try:
            client = self._get_client()

            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Determine mime type from file extension
            mime_type = "image/jpeg"
            if file_name.lower().endswith(".png"):
                mime_type = "image/png"
            elif file_name.lower().endswith(".gif"):
                mime_type = "image/gif"
            elif file_name.lower().endswith(".webp"):
                mime_type = "image/webp"

            # OCR prompt optimized for document text extraction
            ocr_prompt = f"""You are an OCR system. Extract ALL text from this image accurately.

Document type hint: {file_name}
Expected languages: {language_hint}

Instructions:
1. Extract ALL visible text from the image, preserving the structure
2. Maintain paragraph breaks and list formatting where visible
3. For tables, use | separators
4. For forms, extract field names and their values
5. If text is unclear, indicate with [unclear] but try your best
6. Include any stamps, signatures descriptions, dates, and numbers
7. Do NOT add commentary or interpretation - just extract the text

Output the extracted text directly, preserving original formatting as much as possible."""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ocr_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                    "detail": "high",  # High detail for better OCR
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4096,
                temperature=0,  # Deterministic output for OCR
            )

            extracted_text = response.choices[0].message.content or ""

            logger.info(
                "ocr.extraction_complete",
                file_name=file_name,
                text_length=len(extracted_text),
                model="gpt-4o-mini",
            )

            return {
                "extracted_text": extracted_text,
                "confidence": "high" if len(extracted_text) > 50 else "low",
                "source_file": file_name,
                "method": "openai_vision",
                "model": "gpt-4o-mini",
            }

        except Exception as e:
            logger.exception("ocr.extraction_failed", error=str(e), file_name=file_name)
            return {
                "extracted_text": "",
                "confidence": "failed",
                "source_file": file_name,
                "error": str(e),
            }

    async def extract_text_from_pdf(
        self,
        pdf_bytes: bytes,
        file_name: str = "document.pdf",
        max_pages: int = 10,
    ) -> dict[str, Any]:
        """Extract text from PDF, using OCR for scanned pages.

        Args:
            pdf_bytes: Raw PDF bytes
            file_name: Original filename
            max_pages: Maximum pages to process

        Returns:
            Dictionary with extracted_text and metadata
        """
        all_text = []
        page_results = []

        try:
            # First try text extraction with PyPDF2
            try:
                from PyPDF2 import PdfReader

                pdf_reader = PdfReader(BytesIO(pdf_bytes))
                text_pages = []

                for i, page in enumerate(pdf_reader.pages[:max_pages]):
                    page_text = page.extract_text() or ""
                    text_pages.append(page_text)
                    if page_text.strip():
                        all_text.append(f"--- Страница {i + 1} ---\n{page_text}")

                # If we got substantial text, it's not a scanned PDF
                total_text = "\n".join(all_text)
                if len(total_text.strip()) > 100:
                    logger.info(
                        "ocr.pdf_text_extracted",
                        file_name=file_name,
                        pages=len(text_pages),
                        text_length=len(total_text),
                    )
                    return {
                        "extracted_text": total_text,
                        "confidence": "high",
                        "source_file": file_name,
                        "method": "pypdf2_text",
                        "pages_processed": len(text_pages),
                    }

            except ImportError:
                logger.warning("ocr.pypdf2_not_installed")
            except Exception as e:
                logger.warning("ocr.pypdf2_failed", error=str(e))

            # If text extraction failed or got little text, try OCR on pages
            try:
                from pdf2image import convert_from_bytes

                images = convert_from_bytes(
                    pdf_bytes,
                    first_page=1,
                    last_page=max_pages,
                    dpi=200,  # Good balance of quality and speed
                )

                for i, image in enumerate(images):
                    # Convert PIL image to bytes
                    img_buffer = BytesIO()
                    image.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()

                    # OCR each page
                    page_result = await self.extract_text_from_image(
                        img_bytes,
                        f"{file_name}_page_{i + 1}.png",
                    )

                    if page_result.get("extracted_text"):
                        all_text.append(
                            f"--- Страница {i + 1} ---\n{page_result['extracted_text']}"
                        )
                        page_results.append(page_result)

                total_text = "\n\n".join(all_text)
                logger.info(
                    "ocr.pdf_ocr_complete",
                    file_name=file_name,
                    pages=len(images),
                    text_length=len(total_text),
                )

                return {
                    "extracted_text": total_text,
                    "confidence": "medium",
                    "source_file": file_name,
                    "method": "vision_ocr",
                    "pages_processed": len(images),
                }

            except ImportError:
                logger.warning("ocr.pdf2image_not_installed")
                return {
                    "extracted_text": "",
                    "confidence": "failed",
                    "source_file": file_name,
                    "error": "pdf2image not installed - cannot OCR scanned PDF",
                }

        except Exception as e:
            logger.exception("ocr.pdf_processing_failed", error=str(e), file_name=file_name)
            return {
                "extracted_text": "",
                "confidence": "failed",
                "source_file": file_name,
                "error": str(e),
            }

    async def process_document(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str,
    ) -> dict[str, Any]:
        """Process any document type and extract text.

        Args:
            file_bytes: Raw file bytes
            file_name: Original filename
            file_type: MIME type of the file

        Returns:
            Dictionary with extracted_text and metadata
        """
        # Determine processing method based on file type
        is_image = file_type.startswith("image/") or file_name.lower().endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        )
        is_pdf = file_type == "application/pdf" or file_name.lower().endswith(".pdf")

        if is_image:
            return await self.extract_text_from_image(file_bytes, file_name)
        if is_pdf:
            return await self.extract_text_from_pdf(file_bytes, file_name)
        # For other file types, try basic text extraction
        logger.info("ocr.unsupported_type", file_type=file_type, file_name=file_name)
        return {
            "extracted_text": "",
            "confidence": "skipped",
            "source_file": file_name,
            "reason": f"Unsupported file type: {file_type}",
        }


# Global instance for convenience
_ocr_service: OCRService | None = None


def get_ocr_service() -> OCRService:
    """Get or create global OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
