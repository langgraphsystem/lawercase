from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import random
from urllib.parse import urlparse
import uuid

import aiohttp
from bs4 import BeautifulSoup
import markdownify

# Configuration
DATA_DIR = Path("data")
EXTERNAL_CONTENT_DIR = DATA_DIR / "external_content"
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


async def download_single_url(url):
    logger.info(f"⬇️  Downloading: {url}")

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"❌ Failed to fetch: {response.status}")
                    return

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string if soup.title else url
                main_content = soup.find("main") or soup.body
                markdown = markdownify.markdownify(str(main_content), heading_style="ATX")

                file_id = str(uuid.uuid4())
                is_uscis = "uscis.gov" in urlparse(url).netloc
                save_dir = USCIS_CONTENT_DIR if is_uscis else EXTERNAL_CONTENT_DIR

                save_dir.mkdir(parents=True, exist_ok=True)

                filepath = save_dir / f"{file_id}.json"

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "url": url,
                            "title": title.strip() if title else "No Title",
                            "content": markdown,
                            "crawled_at": "manual_download",
                            "source_domain": urlparse(url).netloc,
                        },
                        f,
                        indent=2,
                    )

                logger.info(f"✅ Saved to: {filepath}")
                logger.info(f"Title: {title.strip()}")

        except Exception as e:
            logger.error(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
        asyncio.run(download_single_url(url))
    else:
        print("Usage: python scripts/download_single_url.py <URL>")
