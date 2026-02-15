from __future__ import annotations

import json
import logging
from pathlib import Path

# Configuration
DATA_DIR = Path("data")
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"
EXTERNAL_CONTENT_DIR = DATA_DIR / "external_content"
USCIS_FORMS_DIR = DATA_DIR / "uscis_forms"
EXTERNAL_FILES_DIR = DATA_DIR / "external_files"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

ERROR_PATTERNS = [
    "Access Denied",
    "Request Access",
    "403 Forbidden",
    "404 Not Found",
    "Cloudflare",
    "Please enable cookies",
]


def check_json_dir(directory, name):
    logger.info(f"--- Checking {name} ({directory}) ---")
    if not directory.exists():
        logger.warning(f"Directory not found: {directory}")
        return

    files = [f for f in directory.iterdir() if f.suffix == ".json"]
    logger.info(f"Total JSON files: {len(files)}")

    empty_count = 0
    error_count = 0
    small_count = 0

    for filepath in files:
        try:
            if filepath.stat().st_size < 100:
                small_count += 1

            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                content = data.get("content", "")

                if not content.strip():
                    empty_count += 1

                for pattern in ERROR_PATTERNS:
                    if pattern.lower() in content.lower() and len(content) < 2000:
                        error_count += 1
                        break

        except Exception as e:
            logger.error(f"Error reading {filepath.name}: {e}")

    if empty_count > 0:
        logger.warning(f"⚠️  Empty content files: {empty_count}")
    if error_count > 0:
        logger.warning(f"⚠️  Files with error patterns: {error_count}")
    if small_count > 0:
        logger.warning(f"⚠️  Suspiciously small files (<100 bytes): {small_count}")

    if empty_count == 0 and error_count == 0 and small_count == 0:
        logger.info("✅ No obvious issues found.")


def check_pdf_dir(directory, name):
    logger.info(f"--- Checking {name} ({directory}) ---")
    if not directory.exists():
        logger.warning(f"Directory not found: {directory}")
        return

    files = [f for f in directory.iterdir() if f.suffix == ".pdf"]
    logger.info(f"Total PDF files: {len(files)}")

    invalid_count = 0
    for filepath in files:
        try:
            if filepath.stat().st_size < 1000:
                invalid_count += 1
        except Exception:
            pass

    if invalid_count > 0:
        logger.warning(f"⚠️  Suspiciously small PDFs: {invalid_count}")
    else:
        logger.info("✅ PDF sizes look reasonable.")


if __name__ == "__main__":
    print("🔍 Starting Data Integrity Check...")
    check_json_dir(USCIS_CONTENT_DIR, "USCIS Content")
    check_json_dir(EXTERNAL_CONTENT_DIR, "External Content")
    check_pdf_dir(USCIS_FORMS_DIR, "USCIS Forms")
    check_pdf_dir(EXTERNAL_FILES_DIR, "External Files")
    print("\nCheck Complete.")
