"""DuckDuckGo Search client (free fallback).

Uses duckduckgo-search library for free web search.
No API key required.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .web_search_provider import (
    SearchProviderType,
    SearchResponse,
    SearchResult,
    WebSearchProvider,
)

# Optional dependency
try:
    from duckduckgo_search import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None  # type: ignore
    DDGS_AVAILABLE = False


class DuckDuckGoClient(WebSearchProvider):
    """DuckDuckGo search client (free, no API key).

    Features:
    - Free unlimited searches
    - No authentication required
    - Text, news, and image search
    - Region and time filtering

    Install:
        pip install duckduckgo-search
    """

    provider_type = SearchProviderType.DUCKDUCKGO

    def __init__(
        self,
        timeout: float = 30.0,
        proxy: str | None = None,
    ) -> None:
        """Initialize DuckDuckGo client.

        Args:
            timeout: Request timeout in seconds
            proxy: Optional proxy URL
        """
        self.timeout = timeout
        self.proxy = proxy

    def is_available(self) -> bool:
        """Check if duckduckgo-search is installed."""
        return DDGS_AVAILABLE

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        region: str = "wt-wt",  # Worldwide
        safesearch: str = "moderate",  # off, moderate, strict
        timelimit: str | None = None,  # d (day), w (week), m (month), y (year)
        search_type: str = "text",  # text, news, images
        **kwargs: Any,
    ) -> SearchResponse:
        """Search using DuckDuckGo.

        Args:
            query: Search query
            top_k: Max results to return
            region: Region code (wt-wt = worldwide)
            safesearch: Safe search level
            timelimit: Time filter (d/w/m/y)
            search_type: Type of search (text/news/images)

        Returns:
            SearchResponse with results
        """
        if not self.is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=self.provider_type,
                error="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )

        start_time = time.perf_counter()

        try:
            # Run sync DDGS in thread pool
            results = await asyncio.to_thread(
                self._sync_search,
                query=query,
                top_k=top_k,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                search_type=search_type,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                provider=self.provider_type,
                search_time_ms=elapsed_ms,
            )

        except Exception as e:
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=self.provider_type,
                error=f"DuckDuckGo error: {e!s}",
            )

    def _sync_search(
        self,
        query: str,
        top_k: int,
        region: str,
        safesearch: str,
        timelimit: str | None,
        search_type: str,
    ) -> list[SearchResult]:
        """Synchronous search (called in thread)."""
        results = []

        with DDGS(timeout=self.timeout, proxy=self.proxy) as ddgs:
            if search_type == "text":
                raw_results = ddgs.text(
                    query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=top_k,
                )
            elif search_type == "news":
                raw_results = ddgs.news(
                    query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=top_k,
                )
            else:
                raw_results = ddgs.text(query, max_results=top_k)

            for item in raw_results:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("href") or item.get("url", ""),
                        snippet=item.get("body") or item.get("description", ""),
                        provider=self.provider_type,
                        score=0.5,  # DDG doesn't provide relevance scores
                        source_type="news" if search_type == "news" else "web",
                        metadata={
                            "source": item.get("source"),
                            "date": item.get("date"),
                        },
                    )
                )

        return results
