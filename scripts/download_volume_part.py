from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import random
from urllib.parse import urljoin, urlparse
import uuid

import aiohttp
from bs4 import BeautifulSoup
import markdownify

# Configuration
DATA_DIR = Path("data")
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"
USCIS_FORMS_DIR = DATA_DIR / "uscis_forms"

# Ensure directories exist
USCIS_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
USCIS_FORMS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()


async def fetch_url(session, url):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.uscis.gov/",
    }
    try:
        await asyncio.sleep(random.uniform(1, 3))  # Polite delay
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            logger.error(f"❌ Failed to fetch {url}: {response.status}")
            return None
    except Exception as e:
        logger.error(f"❌ Error fetching {url}: {e}")
        return None


async def download_pdf(session, url, filename):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    filepath = USCIS_FORMS_DIR / filename
    if filepath.exists():
        logger.info(f"ℹ️  PDF already exists: {filename}")
        return

    headers = {"User-Agent": random.choice(user_agents)}
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                with open(filepath, "wb") as f:
                    f.write(content)
                logger.info(f"📥 Downloaded PDF: {filename}")
            else:
                logger.error(f"❌ Failed to download PDF {url}: {response.status}")
    except Exception as e:
        logger.error(f"❌ Error downloading PDF {url}: {e}")


async def process_page(session, url, visited):
    if url in visited:
        return
    visited.add(url)

    logger.info(f"Processing: {url}")
    html = await fetch_url(session, url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # 1. Save Page Content
    title = soup.title.string if soup.title else url
    main_content = soup.find("main") or soup.body
    markdown = markdownify.markdownify(str(main_content), heading_style="ATX")

    file_id = str(uuid.uuid4())
    with open(USCIS_CONTENT_DIR / f"{file_id}.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "url": url,
                "title": title.strip(),
                "content": markdown,
                "crawled_at": "targeted_download",
                "source_domain": "www.uscis.gov",
            },
            f,
            indent=2,
        )
    logger.info(f"✅ Saved content: {title.strip()}")

    # 2. Find and Download Attachments (PDFs)
    # Look for links ending in .pdf or with 'document' in path (common for USCIS)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(url, href)

        if full_url.lower().endswith(".pdf") or "/document/" in full_url:
            # Check if it's likely a file
            if "/document/" in full_url or full_url.lower().endswith(".pdf"):
                filename = Path(urlparse(full_url).path).name
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                await download_pdf(session, full_url, filename)

    # 3. Find Child Pages (Chapters)
    # Logic: Look for links that are sub-paths of the current URL or relevant chapters
    # For "volume-6-part-b", we want "volume-6-part-b-chapter-X"
    base_path = urlparse(url).path
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)

        # Check if it's a USCIS policy manual link
        if "uscis.gov/policy-manual" in full_url:
            # Check if it is a child or related chapter
            # Example: /policy-manual/volume-6-part-b-chapter-1
            if base_path in parsed_url.path or "volume-6-part-b-chapter" in parsed_url.path:
                if full_url not in visited:
                    await process_page(session, full_url, visited)


async def main():
    target_url = "https://www.uscis.gov/policy-manual/volume-6-part-b"
    visited = set()

    async with aiohttp.ClientSession() as session:
        await process_page(session, target_url, visited)


if __name__ == "__main__":
    asyncio.run(main())
