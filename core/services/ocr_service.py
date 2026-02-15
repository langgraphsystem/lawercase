"""
OCR service for extracting text from images and scanned documents.

Uses Google Gemini 3 Flash Vision API for OCR processing (new google.genai SDK).
"""

from __future__ import annotations

import asyncio
from io import BytesIO
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Gemini 3 model for OCR (fast, vision-capable)
GEMINI_OCR_MODEL = "gemini-3-flash-preview"

# Timeout settings (seconds)
OCR_TIMEOUT_SECONDS = 120  # 2 minutes for large documents
OCR_MAX_RETRIES = 2


class OCRService:
    """Service for OCR text extraction from images and documents using Gemini 3."""

    def __init__(self, gemini_api_key: str | None = None):
        """Initialize OCR service.

        Args:
            gemini_api_key: Gemini API key. If not provided, will try to get from env/settings.
        """
        self._api_key = gemini_api_key
        self._client = None

    def _get_client(self):
        """Get or create Gemini client using new google.genai SDK."""
        if self._client is None:
            try:
                from google import genai
                from google.genai import types

                # Try multiple sources for API key
                if not self._api_key:
                    self._api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

                if not self._api_key:
                    from config.settings import get_settings

                    settings = get_settings()
                    self._api_key = settings.gemini_api_key

                if not self._api_key:
                    raise RuntimeError(
                        "GEMINI_API_KEY not configured. Set in .env or pass to OCRService."
                    )

                # Initialize new google.genai client
                self._client = genai.Client(api_key=self._api_key)
                self._types = types
                logger.info("ocr.gemini_initialized", model=GEMINI_OCR_MODEL, sdk="google.genai")
            except ImportError:
                logger.error("ocr.google_genai_not_installed")
                raise RuntimeError(
                    "google-genai package not installed. Run: pip install google-genai"
                )
        return self._client

    async def extract_text_from_image(
        self,
        image_bytes: bytes,
        file_name: str = "image",
        language_hint: str = "Russian and English",
    ) -> dict[str, Any]:
        """Extract text from an image using Gemini 3 Flash Vision API.

        Args:
            image_bytes: Raw image bytes
            file_name: Original filename for context
            language_hint: Expected languages in the document

        Returns:
            Dictionary with extracted_text, confidence, and metadata
        """
        try:
            client = self._get_client()

            # Determine mime type from file extension
            mime_type = "image/jpeg"
            lower_name = file_name.lower()
            if lower_name.endswith(".png"):
                mime_type = "image/png"
            elif lower_name.endswith(".gif"):
                mime_type = "image/gif"
            elif lower_name.endswith(".webp"):
                mime_type = "image/webp"
            elif lower_name.endswith(".bmp"):
                mime_type = "image/bmp"

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

            # Create image part using new SDK format
            image_part = self._types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )

            # Generate response with Gemini 3 Flash using new SDK
            # Wrap in asyncio.to_thread with timeout for large documents
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=GEMINI_OCR_MODEL,
                        contents=[ocr_prompt, image_part],
                        config=self._types.GenerateContentConfig(
                            temperature=0,
                            max_output_tokens=4096,
                        ),
                    ),
                    timeout=OCR_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning(
                    "ocr.timeout",
                    file_name=file_name,
                    timeout_seconds=OCR_TIMEOUT_SECONDS,
                )
                return {
                    "extracted_text": "",
                    "confidence": "timeout",
                    "source_file": file_name,
                    "error": f"OCR timed out after {OCR_TIMEOUT_SECONDS} seconds",
                }

            extracted_text = response.text or ""

            logger.info(
                "ocr.extraction_complete",
                file_name=file_name,
                text_length=len(extracted_text),
                model=GEMINI_OCR_MODEL,
            )

            return {
                "extracted_text": extracted_text,
                "confidence": "high" if len(extracted_text) > 50 else "low",
                "source_file": file_name,
                "method": "gemini_vision",
                "model": GEMINI_OCR_MODEL,
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
        max_pages: int = 1000,  # Increased from 10 to handle large documents
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

    async def extract_text_from_docx(
        self,
        file_bytes: bytes,
        file_name: str = "document.docx",
    ) -> dict[str, Any]:
        """Extract text from DOCX file.

        Args:
            file_bytes: Raw DOCX bytes
            file_name: Original filename

        Returns:
            Dictionary with extracted_text and metadata
        """
        try:
            from docx import Document

            doc = Document(BytesIO(file_bytes))

            all_text = []

            # Extract text from paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    all_text.append(para.text)

            # Extract text from tables
            for table in doc.tables:
                table_rows = []
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        table_rows.append(row_text)
                if table_rows:
                    all_text.append("\n[Таблица]\n" + "\n".join(table_rows))

            extracted_text = "\n\n".join(all_text)

            logger.info(
                "ocr.docx_extracted",
                file_name=file_name,
                text_length=len(extracted_text),
                paragraphs=len(doc.paragraphs),
                tables=len(doc.tables),
            )

            return {
                "extracted_text": extracted_text,
                "confidence": "high" if len(extracted_text) > 50 else "low",
                "source_file": file_name,
                "method": "python_docx",
                "paragraphs": len(doc.paragraphs),
                "tables": len(doc.tables),
            }

        except ImportError:
            logger.error("ocr.python_docx_not_installed")
            return {
                "extracted_text": "",
                "confidence": "failed",
                "source_file": file_name,
                "error": "python-docx not installed. Run: pip install python-docx",
            }
        except Exception as e:
            logger.exception("ocr.docx_extraction_failed", error=str(e), file_name=file_name)
            return {
                "extracted_text": "",
                "confidence": "failed",
                "source_file": file_name,
                "error": str(e),
            }

    async def extract_text_from_xlsx(
        self,
        file_bytes: bytes,
        file_name: str = "document.xlsx",
        max_sheets: int = 10,
    ) -> dict[str, Any]:
        """Extract text from XLSX/XLS file.

        Args:
            file_bytes: Raw Excel bytes
            file_name: Original filename
            max_sheets: Maximum sheets to process

        Returns:
            Dictionary with extracted_text and metadata
        """
        try:
            from openpyxl import load_workbook

            wb = load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)

            all_text = []
            sheets_processed = 0

            for sheet_name in wb.sheetnames[:max_sheets]:
                sheet = wb[sheet_name]
                sheet_text = [f"--- Лист: {sheet_name} ---"]

                for row in sheet.iter_rows(values_only=True):
                    # Filter out None values and convert to strings
                    row_values = [str(cell) for cell in row if cell is not None]
                    if row_values:
                        sheet_text.append(" | ".join(row_values))

                if len(sheet_text) > 1:  # More than just header
                    all_text.append("\n".join(sheet_text))
                    sheets_processed += 1

            wb.close()

            extracted_text = "\n\n".join(all_text)

            logger.info(
                "ocr.xlsx_extracted",
                file_name=file_name,
                text_length=len(extracted_text),
                sheets=sheets_processed,
            )

            return {
                "extracted_text": extracted_text,
                "confidence": "high" if len(extracted_text) > 50 else "low",
                "source_file": file_name,
                "method": "openpyxl",
                "sheets_processed": sheets_processed,
            }

        except ImportError:
            logger.error("ocr.openpyxl_not_installed")
            return {
                "extracted_text": "",
                "confidence": "failed",
                "source_file": file_name,
                "error": "openpyxl not installed. Run: pip install openpyxl",
            }
        except Exception as e:
            logger.exception("ocr.xlsx_extraction_failed", error=str(e), file_name=file_name)
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
        lower_name = file_name.lower()

        # Determine processing method based on file type
        is_image = file_type.startswith("image/") or lower_name.endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        )
        is_pdf = file_type == "application/pdf" or lower_name.endswith(".pdf")
        is_docx = (
            file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or lower_name.endswith(".docx")
        )
        is_doc = file_type == "application/msword" or lower_name.endswith(".doc")
        is_xlsx = (
            file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            or lower_name.endswith(".xlsx")
        )
        is_xls = file_type == "application/vnd.ms-excel" or lower_name.endswith(".xls")

        if is_image:
            return await self.extract_text_from_image(file_bytes, file_name)
        if is_pdf:
            return await self.extract_text_from_pdf(file_bytes, file_name)
        if is_docx:
            return await self.extract_text_from_docx(file_bytes, file_name)
        if is_doc:
            # Old .doc format - try to process as docx, may fail
            logger.warning("ocr.doc_format_legacy", file_name=file_name)
            return {
                "extracted_text": "",
                "confidence": "skipped",
                "source_file": file_name,
                "reason": "Legacy .doc format not supported. Please convert to .docx",
            }
        if is_xlsx:
            return await self.extract_text_from_xlsx(file_bytes, file_name)
        if is_xls:
            # Old .xls format
            logger.warning("ocr.xls_format_legacy", file_name=file_name)
            return {
                "extracted_text": "",
                "confidence": "skipped",
                "source_file": file_name,
                "reason": "Legacy .xls format not supported. Please convert to .xlsx",
            }

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
