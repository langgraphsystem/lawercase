"""Test the field extraction service locally."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


async def test_extraction():
    """Test field extraction with sample OCR text."""
    # Sample birth certificate OCR text (Russian)
    sample_ocr_text = """
    СВИДЕТЕЛЬСТВО О РОЖДЕНИИ
    Серия II-МЮ № 123456

    Фамилия, имя, отчество: Иванов Иван Иванович
    Дата рождения: 15 марта 1990 года
    Место рождения: город Москва

    Отец: Иванов Пётр Сергеевич
    Мать: Иванова Мария Александровна

    Дата составления записи акта о рождении: 20 марта 1990 года
    Место государственной регистрации: Отдел ЗАГС Центрального района г. Москвы

    Дата выдачи: 25 марта 1990 года
    """

    print("=" * 60)
    print("Testing field extraction service")
    print("=" * 60)

    # Test 1: Check if schema exists
    print("\n1. Checking schema for 'birth_certificate'...")
    try:
        from core.services.extraction_schemas import get_schema_for_document_type

        schema = get_schema_for_document_type("birth_certificate")
        if schema:
            print(f"   ✅ Schema found with {len(schema)} fields:")
            for field in list(schema.keys())[:5]:
                print(f"      - {field}")
        else:
            print("   ❌ No schema found!")
            return
    except Exception as e:
        print(f"   ❌ Error importing schema: {e}")
        return

    # Test 2: Check Gemini API key
    print("\n2. Checking Gemini API key...")
    try:
        from config.settings import get_settings

        settings = get_settings()
        api_key = settings.gemini_api_key
        if api_key:
            print(f"   ✅ API key found: {api_key[:10]}...")
        else:
            print("   ❌ No GEMINI_API_KEY set!")
            return
    except Exception as e:
        print(f"   ❌ Error getting settings: {e}")
        return

    # Test 3: Test extraction
    print("\n3. Testing extraction...")
    try:
        from core.services.field_extractor import extract_fields

        result = await extract_fields(
            ocr_text=sample_ocr_text,
            doc_type_id="birth_certificate",
            doc_type_name="Свидетельство о рождении",
        )

        if result:
            print("   ✅ Extraction successful! Fields extracted:")
            for key, value in result.items():
                if not key.startswith("_"):
                    print(f"      {key}: {value}")
            # Show metadata
            print("\n   Metadata:")
            print(f"      _extraction_method: {result.get('_extraction_method')}")
            print(f"      _extraction_completeness: {result.get('_extraction_completeness')}")
        else:
            print("   ❌ Extraction returned empty result!")
    except Exception as e:
        print(f"   ❌ Extraction error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_extraction())
