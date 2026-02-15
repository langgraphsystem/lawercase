from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import random
import sys
from urllib.parse import urljoin, urlparse
import uuid

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import markdownify

# --- Configuration ---
BASE_URL = "https://www.uscis.gov/policy-manual"
START_URL = "https://www.uscis.gov/policy-manual"
CONTENT_DIR = "data/uscis_content"
FORMS_DIR = "data/uscis_forms"
EXTERNAL_CONTENT_DIR = "data/external_content"
EXTERNAL_FILES_DIR = "data/external_files"
STATE_FILE = "data/ingestion_state.json"
CATALOG_FILE = "data/forms_catalog.json"

# Crawl Settings
MAX_EXTERNAL_DEPTH = 2  # How deep to go into external sites (0 = just the linked page)
MAX_CONCURRENT_REQUESTS = 5

# User Agents for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

# Import core modules (Mocking if not available for standalone testing, but assuming they exist)
try:
    from core.memory.memory_manager_v2 import MemoryManager, MemoryRecord
    from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore
    from core.rag.chunking import SemanticChunker
except ImportError:
    logger.warning("Core modules not found. Embedding mode will fail.")


class USCISPolicyCrawler:
    def __init__(self, mode="crawl"):
        self.mode = mode

        # Initialize Core Components (only needed for embed mode)
        if self.mode == "embed":
            self.memory_manager = MemoryManager(semantic=SupabaseSemanticStore())
            self.chunker = SemanticChunker()

        # State
        self.visited_urls = set()
        self.queue = []  # List of dicts: {'url': str, 'depth': int, 'source_domain': str}
        self.forms_catalog = []

        Path(CONTENT_DIR).mkdir(parents=True, exist_ok=True)
        Path(FORMS_DIR).mkdir(parents=True, exist_ok=True)
        Path(EXTERNAL_CONTENT_DIR).mkdir(parents=True, exist_ok=True)
        Path(EXTERNAL_FILES_DIR).mkdir(parents=True, exist_ok=True)

        self.load_state()

    def load_state(self):
        if Path(STATE_FILE).exists():
            try:
                with open(STATE_FILE, encoding="utf-8") as f:
                    state = json.load(f)
                    self.visited_urls = set(state.get("visited_urls", []))

                    raw_queue = state.get("queue", [])
                    if raw_queue and isinstance(raw_queue[0], str):
                        logger.info("Migrating legacy queue format...")
                        self.queue = [
                            {"url": u, "depth": 0, "source_domain": "uscis.gov"} for u in raw_queue
                        ]
                    else:
                        self.queue = raw_queue

                    logger.info(
                        f"Loaded state: {len(self.visited_urls)} visited URLs, {len(self.queue)} in queue."
                    )
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                self.queue = [{"url": START_URL, "depth": 0, "source_domain": "uscis.gov"}]
        else:
            self.queue = [{"url": START_URL, "depth": 0, "source_domain": "uscis.gov"}]

        if Path(CATALOG_FILE).exists():
            try:
                with open(CATALOG_FILE, encoding="utf-8") as f:
                    self.forms_catalog = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load catalog: {e}")

    def save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "visited_urls": list(self.visited_urls),
                        "queue": self.queue,
                        "last_updated": datetime.now(UTC).isoformat(),
                    },
                    f,
                    indent=2,
                )

            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.forms_catalog, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def is_valid_url(self, url, current_depth, source_domain):
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "uscis.gov" in domain and "/policy-manual" in parsed.path:
            return True

        return current_depth < MAX_EXTERNAL_DEPTH

    async def download_file(self, session, url, folder):
        filename = Path(urlparse(url).path).name
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        local_path = Path(folder) / filename

        # Check if already downloaded
        if any(f["url"] == url for f in self.forms_catalog):
            return

        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Referer": "https://www.google.com/",
            }
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(local_path, "wb") as f:
                        f.write(content)

                    logger.info(f"📥 Downloaded file: {filename}")

                    self.forms_catalog.append(
                        {
                            "form_id": filename.replace(".pdf", ""),
                            "title": filename,
                            "url": url,
                            "local_path": str(Path(local_path).resolve()),
                            "downloaded_at": datetime.now(UTC).isoformat(),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to download file {url}: {e}")

    async def process_page(self, session, item):
        url = item["url"]
        depth = item["depth"]
        source_domain = item["source_domain"]

        if url in self.visited_urls:
            return

        logger.info(f"Crawling (Depth {depth}): {url}")

        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            }
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    self.visited_urls.add(url)
                    return

                content_type = response.headers.get("Content-Type", "").lower()

                # Handle PDF directly
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    target_dir = FORMS_DIR if "uscis.gov" in url else EXTERNAL_FILES_DIR
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

                # Save Content
                file_id = str(uuid.uuid4())

                # Determine storage folder
                is_uscis = "uscis.gov" in urlparse(url).netloc
                save_dir = CONTENT_DIR if is_uscis else EXTERNAL_CONTENT_DIR

                with open(Path(save_dir) / f"{file_id}.json", "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "url": url,
                            "title": title.strip() if title else "No Title",
                            "content": markdown,
                            "crawled_at": datetime.now(UTC).isoformat(),
                            "depth": depth,
                            "source_domain": source_domain,
                        },
                        f,
                        indent=2,
                    )

                # Find Links
                # Logic:
                # 1. If on USCIS Policy Manual (Depth 0), we can go to:
                #    - Other Policy Manual pages (Depth 0)
                #    - External Links (Depth 1)
                # 2. If on External Page (Depth 1), we can go to:
                #    - Other pages on SAME external domain (Depth 1? Or 2?) -> Let's say Depth 1 (explore the site a bit)
                #    - Other pages on DIFFERENT external domain (Depth 2)
                #    - Back to USCIS (Depth 0)

                current_is_policy = "uscis.gov/policy-manual" in url

                # If we are at MAX_EXTERNAL_DEPTH, we stop recursion for external links
                if depth >= MAX_EXTERNAL_DEPTH and not current_is_policy:
                    self.visited_urls.add(url)
                    return

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)
                    full_url = full_url.split("#")[0]  # Clean URL

                    if full_url in self.visited_urls:
                        continue

                    next_domain = urlparse(full_url).netloc
                    next_is_policy = "uscis.gov/policy-manual" in full_url

                    if next_is_policy:
                        next_depth = 0
                    elif next_domain == source_domain:
                        next_depth = depth  # Stay at same depth if same domain
                    else:
                        next_depth = depth + 1  # Increase depth if switching domains

                    if self.is_valid_url(full_url, next_depth, source_domain):
                        # Avoid duplicates in queue
                        if not any(q["url"] == full_url for q in self.queue):
                            self.queue.append(
                                {"url": full_url, "depth": next_depth, "source_domain": next_domain}
                            )

                self.visited_urls.add(url)

                # Periodic Save
                if len(self.visited_urls) % 10 == 0:
                    self.save_state()

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self.visited_urls.add(url)

    async def run_crawl(self):
        logger.info("🚀 Starting Deep Context Crawler")
        logger.info(f"   Max External Depth: {MAX_EXTERNAL_DEPTH}")

        async with aiohttp.ClientSession() as session:
            while self.queue:
                item = self.queue.pop(0)

                # Dynamic Headers
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                }

                # Pass headers to process_page (needs signature update or handling inside)
                # Since process_page takes session, we should update session headers or pass them per request.
                # Ideally, we update process_page to use these headers.
                # Let's modify process_page signature or just set default headers on session if we want simple rotation per session (but per request is better).
                # Actually, aiohttp session can take headers per request.
                # I need to update process_page to accept headers or generate them there.

                # Let's update process_page instead.
                await self.process_page(session, item)

                # Random Delay
                delay = random.uniform(2.0, 5.0)
                await asyncio.sleep(delay)

        self.save_state()
        logger.info("✅ Deep Crawl complete!")

    async def run_embed(self):
        logger.info("🧠 Starting Embedding Generation (Ingest Mode)")

        files = []
        for d in [CONTENT_DIR, EXTERNAL_CONTENT_DIR]:
            dir_path = Path(d)
            if dir_path.exists():
                files.extend([str(f) for f in dir_path.iterdir() if f.suffix == ".json"])

        logger.info(f"Found {len(files)} files to process.")

        for filepath in files:
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                markdown_text = data.get("content", "")
                url = data.get("url", "")
                title = data.get("title", "")

                # Chunking
                chunks = self.chunker.chunk_text(markdown_text)
                records = []
                for i, chunk in enumerate(chunks):
                    record = MemoryRecord(
                        text=chunk.content,
                        type="semantic",
                        tags=["policy_manual", "USCIS_Policy", "EB-1A", "External_Context"],
                        metadata={
                            "source": url,
                            "title": title,
                            "chunk_index": i,
                            "ingested_at": datetime.now(UTC).isoformat(),
                            "depth": data.get("depth", 0),
                            "domain": data.get("source_domain", "unknown"),
                        },
                    )
                    records.append(record)

                if records:
                    await self.memory_manager.awrite(records)
                    logger.info(
                        f"   Processed {Path(filepath).name} -> {len(records)} chunks saved to DB"
                    )

            except Exception as e:
                logger.error(f"Failed to process {filepath}: {e}")

        logger.info("✅ Embedding generation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USCIS Policy Ingestion Agent")
    parser.add_argument(
        "--mode",
        choices=["crawl", "embed"],
        default="crawl",
        help="Mode: crawl (download) or embed (process)",
    )
    args = parser.parse_args()

    crawler = USCISPolicyCrawler(mode=args.mode)

    if args.mode == "crawl":
        asyncio.run(crawler.run_crawl())
    elif args.mode == "embed":
        asyncio.run(crawler.run_embed())
