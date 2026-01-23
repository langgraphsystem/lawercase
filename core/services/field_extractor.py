"""
Structured field extraction service for documents.

Uses Gemini to extract structured data from OCR text based on document type schemas.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from .extraction_schemas import get_schema_for_document_type

logger = structlog.get_logger(__name__)


def build_extraction_prompt(ocr_text: str, schema: dict[str, str], doc_type_name: str = "") -> str:
    """Build prompt for Gemini to extract structured fields."""
    fields_description = "\n".join(
        f'- "{field}": {description}' for field, description in schema.items()
    )

    prompt = f"""Извлеки структурированные данные из текста документа.

Тип документа: {doc_type_name}

Поля для извлечения:
{fields_description}

Текст документа (OCR):
---
{ocr_text[:8000]}
---

ВАЖНО:
1. Верни ТОЛЬКО валидный JSON объект с указанными полями
2. Если поле не найдено в тексте - используй null
3. Даты должны быть в формате YYYY-MM-DD
4. Числа должны быть без кавычек
5. Не добавляй поля, которых нет в списке
6. Не добавляй комментарии или пояснения

Пример ответа:
{{"full_name": "Иванов Иван Иванович", "date_of_birth": "1990-01-15", "passport_number": "1234567890"}}

JSON:"""

    return prompt


def clean_json_response(response: str) -> str:
    """Clean LLM response to extract valid JSON."""
    # Remove markdown code blocks
    response = re.sub(r"```json\s*", "", response)
    response = re.sub(r"```\s*", "", response)

    # Find JSON object
    match = re.search(r"\{[\s\S]*\}", response)
    if match:
        return match.group(0)

    return response.strip()


def parse_extracted_fields(raw_response: str, schema: dict[str, str]) -> dict[str, Any]:
    """Parse and validate extracted fields from LLM response."""
    try:
        cleaned = clean_json_response(raw_response)
        data = json.loads(cleaned)

        # Validate and clean fields
        result = {}
        for field in schema:
            if field in data:
                value = data[field]
                # Convert empty strings to None
                if value in {"", "null", "N/A"}:
                    value = None
                result[field] = value
            else:
                result[field] = None

        return result

    except json.JSONDecodeError as e:
        logger.warning(
            "field_extractor.json_parse_error", error=str(e), response=raw_response[:200]
        )
        return {}
    except Exception as e:
        logger.warning("field_extractor.parse_error", error=str(e))
        return {}


async def extract_fields_with_gemini(
    ocr_text: str,
    doc_type_id: str,
    doc_type_name: str = "",
) -> dict[str, Any]:
    """Extract structured fields from OCR text using Gemini.

    Args:
        ocr_text: OCR extracted text from document
        doc_type_id: Document type ID (e.g., "passport", "birth_certificate")
        doc_type_name: Human readable document type name

    Returns:
        Dictionary with extracted fields or empty dict if extraction fails
    """
    schema = get_schema_for_document_type(doc_type_id)
    if not schema:
        logger.info("field_extractor.no_schema", doc_type_id=doc_type_id)
        return {}

    if not ocr_text or len(ocr_text.strip()) < 20:
        logger.info(
            "field_extractor.insufficient_text", text_length=len(ocr_text) if ocr_text else 0
        )
        return {}

    try:
        # Import Gemini client
        from google import genai

        from config.settings import get_settings

        settings = get_settings()
        api_key = settings.gemini_api_key

        if not api_key:
            logger.warning("field_extractor.no_api_key")
            return {}

        # Build prompt
        prompt = build_extraction_prompt(ocr_text, schema, doc_type_name)

        # Call Gemini
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "temperature": 0,
                "max_output_tokens": 2048,
            },
        )

        if not response or not response.text:
            logger.warning("field_extractor.empty_response")
            return {}

        # Parse response
        extracted = parse_extracted_fields(response.text, schema)

        # Add metadata
        if extracted:
            extracted["_extraction_method"] = "gemini-2.0-flash"
            extracted["_doc_type_id"] = doc_type_id

            # Count non-null fields
            non_null = sum(
                1 for k, v in extracted.items() if v is not None and not k.startswith("_")
            )
            total = len(schema)
            extracted["_extraction_completeness"] = round(non_null / total, 2) if total > 0 else 0

        logger.info(
            "field_extractor.success",
            doc_type_id=doc_type_id,
            fields_extracted=len([k for k, v in extracted.items() if v and not k.startswith("_")]),
            total_fields=len(schema),
        )

        return extracted

    except Exception as e:
        logger.exception("field_extractor.error", error=str(e), doc_type_id=doc_type_id)
        return {}


async def extract_fields(
    ocr_text: str,
    doc_type_id: str,
    doc_type_name: str = "",
) -> dict[str, Any]:
    """Main entry point for field extraction.

    Args:
        ocr_text: OCR extracted text from document
        doc_type_id: Document type ID
        doc_type_name: Human readable document type name

    Returns:
        Dictionary with extracted fields
    """
    return await extract_fields_with_gemini(ocr_text, doc_type_id, doc_type_name)


# Convenience functions for specific document types


async def extract_passport_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from passport."""
    return await extract_fields(ocr_text, "passport", "Паспорт")


async def extract_birth_certificate_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from birth certificate."""
    return await extract_fields(ocr_text, "birth_certificate", "Свидетельство о рождении")


async def extract_diploma_fields(ocr_text: str, degree_type: str = "bachelor") -> dict[str, Any]:
    """Extract fields from diploma."""
    doc_type_id = f"{degree_type}_diploma"
    return await extract_fields(ocr_text, doc_type_id, f"Диплом ({degree_type})")


async def extract_award_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from award certificate."""
    return await extract_fields(ocr_text, "award_certificate", "Награда")


async def extract_publication_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from scientific publication."""
    return await extract_fields(ocr_text, "publication", "Научная публикация")


async def extract_salary_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from salary document."""
    return await extract_fields(ocr_text, "salary_document", "Документ о зарплате")


async def extract_recommendation_fields(ocr_text: str) -> dict[str, Any]:
    """Extract fields from recommendation letter."""
    return await extract_fields(ocr_text, "recommendation_letter", "Рекомендательное письмо")
