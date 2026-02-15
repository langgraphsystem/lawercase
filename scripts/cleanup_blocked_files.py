from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

# Configuration
EXTERNAL_CONTENT_DIR = "data/external_content"
STATE_FILE = "data/ingestion_state.json"

# Blocking Keywords (Case Insensitive)
BLOCK_KEYWORDS = [
    "Request Access",
    "Access Denied",
    "403 Forbidden",
    "Cloudflare",
    "Please verify you are a human",
    "Attention Required! | Cloudflare",
    "Just a moment...",
]

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def cleanup():
    logger.info("🧹 Starting Cleanup of Blocked Files...")

    deleted_urls = set()
    files_deleted = 0

    # 1. Scan and Delete Files
    content_dir = Path(EXTERNAL_CONTENT_DIR)
    if content_dir.exists():
        for filepath in content_dir.iterdir():
            if filepath.suffix != ".json":
                continue

            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                content = data.get("content", "")
                title = data.get("title", "")
                url = data.get("url", "")

                # Check for blocking keywords
                is_blocked = False
                for keyword in BLOCK_KEYWORDS:
                    if keyword.lower() in content.lower() or keyword.lower() in title.lower():
                        is_blocked = True
                        break

                if is_blocked:
                    logger.warning(f"🚫 Detected blocked content in {filepath.name} ({url})")
                    filepath.unlink()
                    deleted_urls.add(url)
                    files_deleted += 1

            except Exception as e:
                logger.error(f"Error reading {filepath.name}: {e}")

    logger.info(f"🗑️  Deleted {files_deleted} blocked files.")

    # 2. Update State (Remove from visited_urls)
    state_path = Path(STATE_FILE)
    if state_path.exists() and deleted_urls:
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)

            visited = set(state.get("visited_urls", []))
            original_count = len(visited)

            # Remove deleted URLs from visited set
            visited -= deleted_urls

            # Also add them back to the queue
            queue = state.get("queue", [])
            for url in deleted_urls:
                if not any(q["url"] == url for q in queue):
                    try:
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = "unknown"

                    queue.append({"url": url, "depth": 1, "source_domain": domain})

            state["visited_urls"] = list(visited)
            state["queue"] = queue

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            logger.info(
                f"🔄 Updated state: Removed {len(deleted_urls)} URLs from visited list and re-queued them."
            )

        except Exception as e:
            logger.error(f"Failed to update state file: {e}")

    logger.info("✅ Cleanup Complete.")


if __name__ == "__main__":
    cleanup()
