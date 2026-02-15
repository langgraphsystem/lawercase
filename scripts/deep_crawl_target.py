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
    handlers=[
        logging.FileHandler("deep_crawl_target.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"
EXTERNAL_CONTENT_DIR = DATA_DIR / "external_content"
USCIS_FORMS_DIR = DATA_DIR / "uscis_forms"
EXTERNAL_FILES_DIR = DATA_DIR / "external_files"

for d in [USCIS_CONTENT_DIR, EXTERNAL_CONTENT_DIR, USCIS_FORMS_DIR, EXTERNAL_FILES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]

TARGET_START_URL = "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-3"
MAX_DEPTH = 4

# Allowed domains for crawling pages (assets are downloaded regardless of domain if they are PDFs)
ALLOWED_DOMAINS = [
    "uscis.gov",
    "ecfr.gov",
    "govinfo.gov",
    "uscode.house.gov",
    "dol.gov",
    "congress.gov",
    "justice.gov",
    "dhs.gov",
    "whitehouse.gov",
]


class DeepTargetCrawler:
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

        for directory in [USCIS_FORMS_DIR, EXTERNAL_FILES_DIR]:
            if directory.exists():
                for _filename in directory.iterdir():
                    pass

        logger.info(f"Loaded {count} previously crawled URLs.")

    async def download_file(self, session, url, target_dir):
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
                return

            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(filepath, "wb") as f:
                        f.write(content)
                    logger.info(f"📥 Downloaded Asset: {filename}")
                else:
                    logger.warning(f"Failed to download asset {url}: {response.status}")

        except Exception as e:
            logger.error(f"Error downloading file {url}: {e}")

    async def process_page(self, session, item):
        url = item["url"]
        depth = item["depth"]

        if url in self.visited_urls:
            return

        logger.info(f"Crawling (Depth {depth}/{MAX_DEPTH}): {url}")

        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    self.visited_urls.add(url)
                    return

                content_type = response.headers.get("Content-Type", "").lower()

                # Handle PDF directly
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    target_dir = USCIS_FORMS_DIR if "uscis.gov" in url else EXTERNAL_FILES_DIR
                    await self.download_file(session, url, target_dir)
                    self.visited_urls.add(url)
                    return

                # Handle HTML
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract Content
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
                            "depth": depth,
                        },
                        f,
                        indent=2,
                    )

                self.visited_urls.add(url)

                # Find Links if depth allows
                if depth < MAX_DEPTH:
                    links_found = 0
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        full_url = urljoin(url, href)
                        full_url = full_url.split("#")[0]  # Clean URL

                        if full_url in self.visited_urls:
                            continue

                        parsed_url = urlparse(full_url)
                        domain = parsed_url.netloc

                        # Check if valid domain
                        is_valid_domain = any(d in domain for d in ALLOWED_DOMAINS)

                        if is_valid_domain:
                            # Avoid duplicates in queue
                            if not any(q["url"] == full_url for q in self.queue):
                                self.queue.append({"url": full_url, "depth": depth + 1})
                                links_found += 1

                    logger.info(f"   Found {links_found} new links to queue.")

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self.visited_urls.add(url)

    async def run_crawl(self):
        # Force crawl start URL even if visited
        if TARGET_START_URL in self.visited_urls:
            self.visited_urls.remove(TARGET_START_URL)
            logger.info(f"Removed {TARGET_START_URL} from visited to force re-crawl.")

        self.queue.append({"url": TARGET_START_URL, "depth": 0})

        async with aiohttp.ClientSession() as session:
            while self.queue:
                # Process in batches to control concurrency
                batch_size = 5
                batch = []

                for _ in range(batch_size):
                    if self.queue:
                        batch.append(self.queue.pop(0))

                if not batch:
                    break

                tasks = [self.process_page(session, item) for item in batch]
                await asyncio.gather(*tasks)

                # Random delay between batches
                await asyncio.sleep(random.uniform(1, 3))


if __name__ == "__main__":
    crawler = DeepTargetCrawler()
    asyncio.run(crawler.run_crawl())
