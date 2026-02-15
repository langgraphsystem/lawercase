from __future__ import annotations

import logging
from pathlib import Path
import shutil

# Configuration
DATA_DIR = Path("data")
DIRS_TO_CLEAN = [
    DATA_DIR / "uscis_content",
    DATA_DIR / "external_content",
    DATA_DIR / "uscis_forms",
    DATA_DIR / "external_files",
]
STATE_FILE = DATA_DIR / "ingestion_state.json"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()


def reset_crawl():
    print("⚠️  WARNING: This will delete all downloaded data and crawl state.")

    # Clean directories
    for directory in DIRS_TO_CLEAN:
        if directory.exists():
            try:
                shutil.rmtree(directory)
                logger.info(f"✅ Deleted directory: {directory}")
            except Exception as e:
                logger.error(f"❌ Error deleting {directory}: {e}")
        else:
            logger.info(f"ℹ️  Directory not found (already clean): {directory}")

    # Delete state file
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
            logger.info(f"✅ Deleted state file: {STATE_FILE}")
        except Exception as e:
            logger.error(f"❌ Error deleting state file: {e}")
    else:
        logger.info("ℹ️  State file not found (already clean)")

    # Re-create empty directories
    for directory in DIRS_TO_CLEAN:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Re-created empty directory: {directory}")

    print("\n🚀 Crawl reset complete. You can now start a fresh crawl.")


if __name__ == "__main__":
    reset_crawl()
