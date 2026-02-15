from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

# Настройка логирования
structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
    logger_factory=structlog.PrintLoggerFactory(),
)

from core.services.case_site_generator import site_generator


async def test_site_generation():
    case_id = "e01cbc87-e008-409d-8464-0064792a816d"

    # Имитируем данные, которые обычно приходят из БД
    # В реальности они берутся из state.case_result
    mock_case_data = {
        "case_id": case_id,
        "field": "Artificial Intelligence",
        "status": "active",
        "criteria": ["awards", "membership", "judging"],
        "evidence": [
            {"type": "award", "description": "NeurIPS Best Paper"},
            {"type": "membership", "description": "IEEE Senior Member"},
        ],
    }

    mock_user_data = {"full_name": "Dr. Alan Turing", "email": "alan.turing@example.com"}

    print(f"🚀 Starting site generation for case: {case_id}")

    try:
        # Прямой вызов генератора
        site_path = site_generator.generate_site(
            case_id=case_id, case_data=mock_case_data, user_data=mock_user_data
        )

        print(f"✅ Site successfully generated at: {site_path}")

        # Проверка наличия файлов
        path = Path(site_path)
        expected_files = [
            "index.html",
            "forms/index.html",
            "petition/index.html",
            "exhibits/index.html",
            "assets/css",
            "assets/js",
        ]

        all_exist = True
        for f in expected_files:
            if (path / f).exists():
                print(f"  - Found: {f}")
            else:
                print(f"  ❌ MISSING: {f}")
                all_exist = False

        if all_exist:
            print("\n🎉 All expected files verified!")

    except Exception as e:
        print(f"❌ Error during generation: {e}")


if __name__ == "__main__":
    asyncio.run(test_site_generation())
