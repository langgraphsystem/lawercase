from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import random
from urllib.parse import unquote, urljoin, urlparse
import uuid

import aiohttp
from bs4 import BeautifulSoup
import markdownify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("crawl_flat.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"
EXTERNAL_CONTENT_DIR = DATA_DIR / "external_content"
USCIS_FORMS_DIR = DATA_DIR / "uscis_forms"
EXTERNAL_FILES_DIR = DATA_DIR / "external_files"
EXTRACTED_LINKS_FILE = DATA_DIR / "extracted_links.json"

for d in [USCIS_CONTENT_DIR, EXTERNAL_CONTENT_DIR, USCIS_FORMS_DIR, EXTERNAL_FILES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class FlatCrawler:
    def __init__(self):
        self.visited_urls = set()
        self.queue = []
        self.load_state()

    def load_state(self):
        logger.info("Loading existing file state...")
        count = 0
        for directory in [USCIS_CONTENT_DIR, EXTERNAL_CONTENT_DIR]:
            if directory.exists():
                for filename in directory.iterdir():
                    if filename.suffix == ".json":
                        try:
                            with open(filename, encoding="utf-8") as f:
                                data = json.load(f)
                                if "url" in data:
                                    self.visited_urls.add(data["url"])
                                    count += 1
                        except Exception:
                            pass
        logger.info(f"Loaded {count} previously crawled URLs.")

    async def fetch_with_retry(self, session, url, headers=None, retries=3):
        for attempt in range(retries):
            try:
                current_headers = headers or {}
                current_headers["User-Agent"] = random.choice(USER_AGENTS)

                async with session.get(url, headers=current_headers) as response:
                    if response.status in [200, 404]:
                        return response, await response.read()
                    if response.status in [403, 429, 500, 502, 503, 504]:
                        logger.warning(
                            f"⚠️  Got {response.status} for {url}. Retrying ({attempt + 1}/{retries})..."
                        )
                        await asyncio.sleep(random.uniform(2, 5) * (attempt + 1))
                        continue
                    return response, None
            except Exception as e:
                logger.warning(f"Error fetching {url}: {e}. Retrying...")
                await asyncio.sleep(random.uniform(1, 3))
        return None, None

    async def download_asset(self, session, url, target_dir):
        if url in self.visited_urls:
            return

        try:
            filename = Path(urlparse(url).path).name
            if not filename:
                filename = f"file_{uuid.uuid4()}.pdf"
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            filename = unquote(filename)
            filename = "".join(
                [c for c in filename if c.isalpha() or c.isdigit() or c in (" ", ".", "-", "_")]
            ).strip()

            filepath = target_dir / filename

            if filepath.exists():
                logger.info(f"⏭️  Skipping existing file: {filename}")
                self.visited_urls.add(url)
                return

            response, content = await self.fetch_with_retry(session, url)

            if response and response.status == 200 and content:
                with open(filepath, "wb") as f:
                    f.write(content)
                logger.info(f"📥 Downloaded Asset: {filename}")
                self.visited_urls.add(url)
            else:
                logger.warning(f"Failed to download asset {url}")

        except Exception as e:
            logger.error(f"Error downloading asset {url}: {e}")

    async def process_page(self, session, url):
        if url in self.visited_urls:
            return

        logger.info(f"Processing Page: {url}")

        try:
            response, content_bytes = await self.fetch_with_retry(session, url)

            if not response or response.status != 200:
                logger.warning(f"Failed to fetch {url}")
                self.visited_urls.add(url)
                return

            content_type = response.headers.get("Content-Type", "").lower()

            # If the start URL itself is a PDF/File, download it
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                target_dir = USCIS_FORMS_DIR if "uscis.gov" in url else EXTERNAL_FILES_DIR
                await self.download_asset(session, url, target_dir)
                return

            # Handle HTML
            html = content_bytes.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            # Save Page Content
            title = soup.title.string if soup.title else url
            main_content = soup.find("main") or soup.body
            markdown = markdownify.markdownify(str(main_content), heading_style="ATX")

            file_id = str(uuid.uuid4())
            is_uscis = "uscis.gov" in urlparse(url).netloc
            save_dir = USCIS_CONTENT_DIR if is_uscis else EXTERNAL_CONTENT_DIR

            with open(save_dir / f"{file_id}.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "url": url,
                        "title": title.strip() if title else "No Title",
                        "content": markdown,
                        "crawled_at": datetime.now(UTC).isoformat(),
                        "depth": 0,
                    },
                    f,
                    indent=2,
                )

            self.visited_urls.add(url)

            # Look for ASSETS only (PDFs, etc.) on this page
            assets_found = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(url, href)
                full_url = full_url.split("#")[0]

                lower_url = full_url.lower()
                is_file = (
                    lower_url.endswith((".pdf", ".docx"))
                    or "/download" in lower_url
                    or "files/form" in lower_url
                )  # Common USCIS form pattern

                if is_file:
                    target_dir = USCIS_FORMS_DIR if "uscis.gov" in full_url else EXTERNAL_FILES_DIR
                    await self.download_asset(session, full_url, target_dir)
                    assets_found += 1

            if assets_found > 0:
                logger.info(f"   Found and downloaded {assets_found} assets from page.")

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self.visited_urls.add(url)

    async def run_crawl(self):
        if not EXTRACTED_LINKS_FILE.exists():
            logger.error(f"Extracted links file not found: {EXTRACTED_LINKS_FILE}")
            return

        with open(EXTRACTED_LINKS_FILE, encoding="utf-8") as f:
            start_urls = json.load(f)

        logger.info(f"Loaded {len(start_urls)} start URLs from {EXTRACTED_LINKS_FILE}")

        async with aiohttp.ClientSession() as session:
            for url in start_urls:
                await self.process_page(session, url)
                await asyncio.sleep(random.uniform(1, 3))


if __name__ == "__main__":
    crawler = FlatCrawler()
    asyncio.run(crawler.run_crawl())
