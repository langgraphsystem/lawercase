#!/usr/bin/env python3
"""
Railway Configuration Verification Script
Проверяет что все необходимые файлы для Railway деплоймента на месте.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, required: bool = True) -> bool:
    """Проверка наличия файла."""
    exists = Path(filepath).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_text = "REQUIRED" if required else "OPTIONAL"
    print(f"{status} {filepath:<30} [{req_text}]")
    return exists or not required


def check_file_executable(filepath: str) -> bool:
    """Проверка что файл имеет права на выполнение."""
    path = Path(filepath)
    if not path.exists():
        return False
    is_executable = os.access(path, os.X_OK)
    status = "✓" if is_executable else "✗"
    print(f"  {status} Executable permissions: {filepath}")
    return is_executable


def validate_railway_json() -> bool:
    """Проверка корректности railway.json."""
    try:
        with open("railway.json", encoding="utf-8") as f:
            config = json.load(f)

        # Проверка обязательных полей
        required_fields = ["build", "deploy"]
        missing = [f for f in required_fields if f not in config]

        if missing:
            print(f"  ✗ Missing fields in railway.json: {missing}")
            return False

        # Проверка build конфигурации
        if config["build"].get("builder") != "DOCKERFILE":
            print(f"  ⚠ Builder is not DOCKERFILE: {config['build'].get('builder')}")

        if config["build"].get("buildTarget") != "api":
            print(f"  ⚠ Build target is not 'api': {config['build'].get('buildTarget')}")

        # Проверка deploy конфигурации
        if "/bin/bash start_api.sh" not in config["deploy"].get("startCommand", ""):
            print("  ⚠ Start command doesn't use start_api.sh")

        if config["deploy"].get("healthcheckPath") != "/health":
            print("  ⚠ Health check path is not '/health'")

        print("  ✓ railway.json structure is valid")
        return True

    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON in railway.json: {e}")
        return False
    except FileNotFoundError:
        print("  ✗ railway.json not found")
        return False


def check_dockerfile_stages() -> bool:
    """Проверка multi-stage Dockerfile."""
    try:
        with open("Dockerfile", encoding="utf-8") as f:
            content = f.read()

        # Проверка наличия всех stages
        stages = ["base", "builder", "api", "bot", "worker"]
        missing_stages = []

        for stage in stages:
            if (
                f"FROM base AS {stage}" not in content
                and f"FROM python:3.11-slim AS {stage}" not in content
            ):
                if stage != "base":  # base stage uses different FROM
                    missing_stages.append(stage)

        if missing_stages:
            print(f"  ✗ Missing Docker stages: {missing_stages}")
            return False

        # Проверка что start_api.sh копируется
        if "COPY start_api.sh" not in content:
            print("  ✗ start_api.sh is not copied in Dockerfile")
            return False

        # Проверка CMD
        if 'CMD ["/bin/bash", "/app/start_api.sh"]' not in content:
            print("  ⚠ API stage doesn't use start_api.sh in CMD")

        print("  ✓ Dockerfile has all required stages")
        return True

    except FileNotFoundError:
        print("  ✗ Dockerfile not found")
        return False


def check_start_script() -> bool:
    """Проверка start_api.sh скрипта."""
    try:
        with open("start_api.sh", encoding="utf-8") as f:
            content = f.read()

        # Проверка использования переменной PORT
        if "PORT=${PORT:-8000}" not in content:
            print("  ✗ start_api.sh doesn't use PORT environment variable")
            return False

        # Проверка uvicorn команды
        if "uvicorn api.main_production:app" not in content:
            print("  ✗ start_api.sh doesn't start api.main_production:app")
            return False

        # Проверка --port "$PORT"
        if '--port "$PORT"' not in content:
            print("  ✗ start_api.sh doesn't pass $PORT to uvicorn")
            return False

        print("  ✓ start_api.sh is correctly configured")
        return True

    except FileNotFoundError:
        print("  ✗ start_api.sh not found")
        return False


def check_dockerignore() -> bool:
    """Проверка .dockerignore."""
    try:
        with open(".dockerignore", encoding="utf-8") as f:
            content = f.read()

        # Важные исключения
        important = [".git/", "__pycache__/", "*.pyc", ".env", "tests/", "*.md"]
        missing = [item for item in important if item not in content]

        if missing:
            print(f"  ⚠ .dockerignore missing recommended entries: {missing}")
        else:
            print("  ✓ .dockerignore has all recommended entries")

        return True

    except FileNotFoundError:
        print("  ⚠ .dockerignore not found (recommended)")
        return False


def check_requirements() -> bool:
    """Проверка requirements.txt."""
    try:
        with open("requirements.txt", encoding="utf-8") as f:
            content = f.read()

        # Критически важные зависимости
        critical = ["fastapi", "uvicorn", "pydantic", "openai", "python-telegram-bot"]
        missing = [dep for dep in critical if dep not in content.lower()]

        if missing:
            print(f"  ✗ requirements.txt missing critical dependencies: {missing}")
            return False

        print("  ✓ requirements.txt has all critical dependencies")
        return True

    except FileNotFoundError:
        print("  ✗ requirements.txt not found")
        return False


def main():
    """Основная функция проверки."""
    print("=" * 70)
    print("Railway Configuration Verification")
    print("=" * 70)
    print()

    all_checks_passed = True

    # 1. Проверка основных файлов
    print("📁 Required Files:")
    print("-" * 70)
    all_checks_passed &= check_file_exists("Dockerfile", required=True)
    all_checks_passed &= check_file_exists("requirements.txt", required=True)
    all_checks_passed &= check_file_exists("start_api.sh", required=True)
    all_checks_passed &= check_file_exists("railway.json", required=True)
    check_file_exists("railway.toml", required=False)
    check_file_exists(".dockerignore", required=False)
    print()

    # 2. Проверка прав доступа
    print("🔐 File Permissions:")
    print("-" * 70)
    if Path("start_api.sh").exists():
        # На Windows права могут не работать, показываем предупреждение
        if sys.platform == "win32":
            print("  ⚠ On Windows, executable permissions will be set in Dockerfile")
        else:
            check_file_executable("start_api.sh")
    print()

    # 3. Проверка конфигурации
    print("⚙️  Configuration Validation:")
    print("-" * 70)
    all_checks_passed &= validate_railway_json()
    all_checks_passed &= check_dockerfile_stages()
    all_checks_passed &= check_start_script()
    check_dockerignore()
    all_checks_passed &= check_requirements()
    print()

    # 4. Проверка структуры приложения
    print("📦 Application Structure:")
    print("-" * 70)
    all_checks_passed &= check_file_exists("api/main_production.py", required=True)
    check_file_exists("telegram_interface/bot.py", required=False)
    check_file_exists("core/config/production_settings.py", required=True)
    print()

    # Итоговый результат
    print("=" * 70)
    if all_checks_passed:
        print("✅ All critical checks PASSED!")
        print("   Your application is ready for Railway deployment.")
        print()
        print("Next steps:")
        print("  1. Push to GitHub")
        print("  2. Connect Railway to your repo")
        print("  3. Set environment variables in Railway dashboard")
        print("  4. Deploy!")
        print()
        print("See RAILWAY_DEPLOYMENT.md for detailed instructions.")
    else:
        print("❌ Some checks FAILED!")
        print("   Please fix the issues above before deploying to Railway.")
        print()
        print("See RAILWAY_DEPLOYMENT.md for troubleshooting.")
    print("=" * 70)

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
