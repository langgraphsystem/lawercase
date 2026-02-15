"""Search Aggregator - unified interface for all search providers.

Combines results from multiple providers with:
- Automatic fallback chain
- Result deduplication
- Score normalization
- Caching
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import time
from typing import Any

from .arxiv_client import ArxivClient
from .duckduckgo_client import DuckDuckGoClient
from .tavily_client import TavilyClient
from .web_search_provider import (
    SearchProviderType,
    SearchResponse,
    SearchResult,
    WebSearchProvider,
)


@dataclass
class SearchConfig:
    """Configuration for search aggregation."""

    # Provider priority (first available is used)
    provider_priority: list[SearchProviderType] = field(
        default_factory=lambda: [
            SearchProviderType.TAVILY,
            SearchProviderType.DUCKDUCKGO,
        ]
    )

    # Use multiple providers and merge results
    use_multiple_providers: bool = False

    # Include arXiv for academic queries
    include_arxiv: bool = True

    # Deduplicate results by URL
    deduplicate: bool = True

    # Cache TTL in seconds (0 = disabled)
    cache_ttl: int = 3600  # 1 hour

    # Max concurrent provider calls
    max_concurrency: int = 3


class SearchAggregator:
    """Unified search interface across multiple providers.

    Features:
    - Automatic fallback: Tavily → DuckDuckGo
    - Academic search via arXiv
    - Result deduplication and ranking
    - In-memory caching
    - Concurrent multi-provider search

    Usage:
        aggregator = SearchAggregator()

        # Simple search (uses best available provider)
        results = await aggregator.search("EB-1A visa requirements")

        # Multi-provider search
        results = await aggregator.search_all("machine learning", top_k=20)

        # Academic search only
        results = await aggregator.search_academic("transformer architecture")
    """

    def __init__(
        self,
        config: SearchConfig | None = None,
        tavily_api_key: str | None = None,
    ) -> None:
        """Initialize search aggregator.

        Args:
            config: Search configuration
            tavily_api_key: Tavily API key (optional, uses env var)
        """
        self.config = config or SearchConfig()

        # Initialize providers
        self.providers: dict[SearchProviderType, WebSearchProvider] = {
            SearchProviderType.TAVILY: TavilyClient(api_key=tavily_api_key),
            SearchProviderType.DUCKDUCKGO: DuckDuckGoClient(),
            SearchProviderType.ARXIV: ArxivClient(),
        }

        # Simple in-memory cache
        self._cache: dict[str, tuple[float, SearchResponse]] = {}

    def _get_available_providers(self) -> list[WebSearchProvider]:
        """Get list of available providers in priority order."""
        available = []
        for provider_type in self.config.provider_priority:
            provider = self.providers.get(provider_type)
            if provider and provider.is_available():
                available.append(provider)
        return available

    def _cache_key(self, query: str, provider: str, **kwargs: Any) -> str:
        """Generate cache key."""
        key_data = f"{query}:{provider}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def _get_cached(self, cache_key: str) -> SearchResponse | None:
        """Get cached response if not expired."""
        if self.config.cache_ttl <= 0:
            return None

        cached = self._cache.get(cache_key)
        if cached:
            timestamp, response = cached
            if time.time() - timestamp < self.config.cache_ttl:
                response.cached = True
                return response
            del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, response: SearchResponse) -> None:
        """Cache response."""
        if self.config.cache_ttl > 0:
            self._cache[cache_key] = (time.time(), response)

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate results by URL."""
        seen_urls: set[str] = set()
        unique_results = []

        for result in results:
            # Normalize URL
            url = result.url.lower().rstrip("/")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    def _merge_and_rank(
        self,
        all_results: list[list[SearchResult]],
        top_k: int,
    ) -> list[SearchResult]:
        """Merge results from multiple providers and rank by score."""
        # Flatten all results
        merged = []
        for results in all_results:
            merged.extend(results)

        # Deduplicate
        if self.config.deduplicate:
            merged = self._deduplicate_results(merged)

        # Sort by score (descending)
        merged.sort(key=lambda r: r.score, reverse=True)

        return merged[:top_k]

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        **kwargs: Any,
    ) -> SearchResponse:
        """Search using best available provider with fallback.

        Args:
            query: Search query
            top_k: Maximum results
            **kwargs: Provider-specific options

        Returns:
            SearchResponse from first successful provider
        """
        start_time = time.perf_counter()
        providers = self._get_available_providers()

        if not providers:
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider="none",
                error="No search providers available",
            )

        # Try providers in order (fallback chain)
        last_error = None
        for provider in providers:
            cache_key = self._cache_key(query, provider.name, top_k=top_k, **kwargs)

            # Check cache
            cached = self._get_cached(cache_key)
            if cached:
                return cached

            # Execute search
            response = await provider.search(query, top_k=top_k, **kwargs)

            if response.error is None and response.results:
                # Cache successful response
                self._set_cache(cache_key, response)
                return response

            last_error = response.error

        # All providers failed
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return SearchResponse(
            query=query,
            results=[],
            total_results=0,
            provider="aggregator",
            search_time_ms=elapsed_ms,
            error=f"All providers failed. Last error: {last_error}",
        )

    async def search_all(
        self,
        query: str,
        *,
        top_k: int = 20,
        include_arxiv: bool | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """Search all available providers concurrently and merge results.

        Args:
            query: Search query
            top_k: Maximum total results
            include_arxiv: Override config for arXiv inclusion
            **kwargs: Provider-specific options

        Returns:
            Merged SearchResponse from all providers
        """
        start_time = time.perf_counter()

        # Get providers to use
        providers = self._get_available_providers()

        # Optionally add arXiv
        use_arxiv = include_arxiv if include_arxiv is not None else self.config.include_arxiv
        arxiv_provider = self.providers.get(SearchProviderType.ARXIV)
        if use_arxiv and arxiv_provider and arxiv_provider.is_available():
            if arxiv_provider not in providers:
                providers.append(arxiv_provider)

        if not providers:
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider="aggregator",
                error="No providers available",
            )

        # Search all providers concurrently
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        async def search_with_semaphore(provider: WebSearchProvider) -> SearchResponse:
            async with semaphore:
                return await provider.search(query, top_k=top_k, **kwargs)

        tasks = [search_with_semaphore(p) for p in providers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        all_results: list[list[SearchResult]] = []
        errors: list[str] = []
        providers_used: list[str] = []

        for response_item in responses:
            if isinstance(response_item, Exception):
                errors.append(str(response_item))
            elif isinstance(response_item, SearchResponse):
                if response_item.results:
                    all_results.append(response_item.results)
                    providers_used.append(
                        response_item.provider.value
                        if isinstance(response_item.provider, SearchProviderType)
                        else str(response_item.provider)
                    )
                if response_item.error:
                    errors.append(response_item.error)

        # Merge and rank results
        merged_results = self._merge_and_rank(all_results, top_k)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=merged_results,
            total_results=len(merged_results),
            provider=f"aggregator[{','.join(providers_used)}]",
            search_time_ms=elapsed_ms,
            error="; ".join(errors) if errors and not merged_results else None,
        )

    async def search_academic(
        self,
        query: str,
        *,
        top_k: int = 10,
        categories: list[str] | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """Search academic papers via arXiv.

        Args:
            query: Search query
            top_k: Maximum results
            categories: arXiv categories to filter

        Returns:
            SearchResponse with academic papers
        """
        arxiv_client = self.providers.get(SearchProviderType.ARXIV)

        if not arxiv_client or not arxiv_client.is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=SearchProviderType.ARXIV,
                error="arXiv not available. Run: pip install arxiv",
            )

        return await arxiv_client.search(
            query,
            top_k=top_k,
            categories=categories,
            **kwargs,
        )

    async def search_news(
        self,
        query: str,
        *,
        top_k: int = 10,
        timelimit: str = "w",  # d=day, w=week, m=month
        **kwargs: Any,
    ) -> SearchResponse:
        """Search recent news using DuckDuckGo.

        Args:
            query: Search query
            top_k: Maximum results
            timelimit: Time filter (d/w/m/y)

        Returns:
            SearchResponse with news articles
        """
        ddg_client = self.providers.get(SearchProviderType.DUCKDUCKGO)

        if not ddg_client or not ddg_client.is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=SearchProviderType.DUCKDUCKGO,
                error="DuckDuckGo not available. Run: pip install duckduckgo-search",
            )

        return await ddg_client.search(
            query,
            top_k=top_k,
            search_type="news",
            timelimit=timelimit,
            **kwargs,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get aggregator statistics."""
        available = []
        unavailable = []

        for ptype, provider in self.providers.items():
            if provider.is_available():
                available.append(ptype.value)
            else:
                unavailable.append(ptype.value)

        return {
            "available_providers": available,
            "unavailable_providers": unavailable,
            "cache_size": len(self._cache),
            "cache_ttl": self.config.cache_ttl,
        }

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self.providers.values():
            if hasattr(provider, "close"):
                await provider.close()
