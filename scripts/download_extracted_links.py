from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import random
from urllib.parse import unquote, urljoin, urlparse
import uuid

import aiohttp
from bs4 import BeautifulSoup
import markdownify

# Configuration
DATA_DIR = Path("data")
EXTERNAL_CONTENT_DIR = DATA_DIR / "external_content"
USCIS_CONTENT_DIR = DATA_DIR / "uscis_content"
USCIS_FORMS_DIR = DATA_DIR / "uscis_forms"
EXTERNAL_FILES_DIR = DATA_DIR / "external_files"
LINKS_FILE = DATA_DIR / "extracted_links.json"
STATE_FILE = DATA_DIR / "extracted_links_state.json"

# Ensure directories exist
for d in [EXTERNAL_CONTENT_DIR, USCIS_CONTENT_DIR, USCIS_FORMS_DIR, EXTERNAL_FILES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

processed_urls = set()


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(list(processed_urls), f)


async def download_asset(session, url, referer_domain):
    if url in processed_urls:
        return

    try:
        # Determine target directory
        filename = Path(urlparse(url).path).name
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        filename = unquote(filename)

        is_uscis = "uscis.gov" in urlparse(url).netloc
        save_dir = USCIS_FORMS_DIR if is_uscis else EXTERNAL_FILES_DIR
        filepath = save_dir / filename

        if filepath.exists():
            logger.info(f"⏭️  Skipping existing asset: {filename}")
            processed_urls.add(url)
            return

        headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": referer_domain}

        await asyncio.sleep(random.uniform(0.5, 2))  # Polite delay

        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status == 200:
                content = await response.read()
                with open(filepath, "wb") as f:
                    f.write(content)
                logger.info(f"📥 Downloaded Asset: {filename}")
                processed_urls.add(url)
            else:
                logger.warning(f"Failed to download asset {url}: {response.status}")

    except Exception as e:
        logger.error(f"Error downloading asset {url}: {e}")


async def download_url(session, url, semaphore):
    if url in processed_urls:
        logger.info(f"⏭️  Skipping processed URL: {url}")
        return

    async with semaphore:
        domain = urlparse(url).netloc

        # Filter relevant domains
        if not any(
            d in domain
            for d in [
                "uscis.gov",
                "ecfr.gov",
                "govinfo.gov",
                "uscode.house.gov",
                "dol.gov",
                "congress.gov",
            ]
        ):
            logger.info(f"Skipping irrelevant domain: {url}")
            return

        logger.info(f"Processing: {url}")

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            await asyncio.sleep(random.uniform(1, 3))

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed {response.status}: {url}")
                    return

                content_type = response.headers.get("Content-Type", "").lower()

                # Handle PDF directly
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    await download_asset(session, url, domain)
                    processed_urls.add(url)
                    return

                # Handle HTML
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # 1. Save the Page Content
                title = soup.title.string if soup.title else url
                main_content = soup.find("main") or soup.body

                if main_content:
                    markdown = markdownify.markdownify(str(main_content), heading_style="ATX")
                    file_id = str(uuid.uuid4())
                    is_uscis = "uscis.gov" in domain
                    save_dir = USCIS_CONTENT_DIR if is_uscis else EXTERNAL_CONTENT_DIR

                    # Check if we already have this content (optional optimization, but for now just save)
                    # To avoid duplicates, we could check URL in metadata, but simple append is safer for now.

                    filepath = save_dir / f"{file_id}.json"
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "url": url,
                                "title": title.strip() if title else "No Title",
                                "content": markdown,
                                "crawled_at": "batch_download_deep",
                                "source_domain": domain,
                            },
                            f,
                            indent=2,
                        )
                    logger.info(f"✅ Saved HTML: {title.strip()[:50]}...")

                # 2. Find and Download Nested Assets (PDFs, Instructions) & Footnotes
                logger.info(f"🔎 Scanning for assets and footnotes in: {url}")
                assets_to_download = []

                # Helper to process links
                def process_link(a_tag, source_type="Link"):
                    href = a_tag["href"]
                    full_url = urljoin(url, href)
                    link_text = a_tag.get_text().lower()

                    # Criteria for assets (PDFs)
                    is_pdf = full_url.lower().endswith(".pdf")
                    # Criteria for instructions
                    is_instruction = (
                        any(kw in link_text for kw in ["instruction", "form", "guide", "manual"])
                        and "uscis.gov" in full_url
                    )

                    if is_pdf or (is_instruction and "pdf" in full_url.lower()):
                        if full_url not in processed_urls:
                            assets_to_download.append(full_url)
                            logger.info(f"   Found {source_type} (Asset): {full_url}")

                    # Criteria for Footnote/Reference Webpages (must be relevant domain)
                    elif any(
                        d in urlparse(full_url).netloc
                        for d in [
                            "uscis.gov",
                            "ecfr.gov",
                            "govinfo.gov",
                            "uscode.house.gov",
                            "dol.gov",
                            "congress.gov",
                        ]
                    ):
                        if full_url not in processed_urls:
                            # For webpages, we treat them as assets to be downloaded/crawled if they are from footnotes
                            if source_type == "Footnote":
                                assets_to_download.append(full_url)
                                logger.info(f"   Found {source_type} (Page): {full_url}")

                # A. Scan General Links
                for a in soup.find_all("a", href=True):
                    process_link(a, "Link")

                # B. Scan Footnotes Specifically (to ensure we catch them even if logic above missed something, or to prioritize)
                # Common patterns for footnotes containers
                footnote_containers = soup.find_all(class_=lambda x: x and "footnote" in x.lower())
                footnote_containers += soup.find_all(id=lambda x: x and "footnote" in x.lower())

                # Also look for headers named "Footnotes" and get following content
                for header in soup.find_all(["h2", "h3", "h4", "h5", "h6"]):
                    if "footnote" in header.get_text().lower():
                        # Get next sibling div or list
                        sibling = header.find_next_sibling()
                        while sibling:
                            if sibling.name in ["div", "ul", "ol", "p"]:
                                footnote_containers.append(sibling)
                            if sibling.name in [
                                "h2",
                                "h3",
                                "h4",
                                "h5",
                                "h6",
                            ]:  # Stop at next header
                                break
                            sibling = sibling.find_next_sibling()

                for container in footnote_containers:
                    for a in container.find_all("a", href=True):
                        process_link(a, "Footnote")

                # Download found assets (Files and Footnote Pages)
                for asset_url in assets_to_download:
                    # If it's a PDF, download as asset
                    if asset_url.lower().endswith(".pdf"):
                        await download_asset(session, asset_url, url)
                    else:
                        # If it's a webpage found in footnotes, we recursively download it as a page
                        # We use a separate semaphore or just call download_url recursively?
                        # To avoid infinite recursion loops, we rely on processed_urls.
                        # We'll just call download_url.
                        await download_url(session, asset_url, semaphore)

                processed_urls.add(url)

                if len(processed_urls) % 5 == 0:
                    save_state()

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")


async def main():
    global processed_urls
    processed_urls = load_state()

    if not LINKS_FILE.exists():
        logger.error(f"Links file not found: {LINKS_FILE}")
        return

    with open(LINKS_FILE, encoding="utf-8") as f:
        links = json.load(f)

    logger.info(f"Loaded {len(links)} links. Already processed {len(processed_urls)}.")

    semaphore = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        tasks = [download_url(session, link, semaphore) for link in links]
        await asyncio.gather(*tasks)

    save_state()
    logger.info("🎉 Deep crawl complete.")


if __name__ == "__main__":
    asyncio.run(main())
