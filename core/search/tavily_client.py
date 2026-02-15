"""Tavily Search API client.

Tavily is the primary search provider for deep research tasks.
API Docs: https://docs.tavily.com/
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .web_search_provider import (
    SearchProviderType,
    SearchResponse,
    SearchResult,
    WebSearchProvider,
)


class TavilyClient(WebSearchProvider):
    """Tavily Search API client for high-quality web search.

    Features:
    - AI-optimized search results
    - Content extraction and summarization
    - Domain filtering
    - Time-based filtering

    Environment:
        TAVILY_API_KEY: API key for Tavily
    """

    provider_type = SearchProviderType.TAVILY
    BASE_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize Tavily client.

        Args:
            api_key: Tavily API key (or set TAVILY_API_KEY env var)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    def is_available(self) -> bool:
        """Check if Tavily API key is configured."""
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        search_depth: str = "advanced",  # "basic" or "advanced"
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
        max_results: int | None = None,
        **kwargs: Any,
    ) -> SearchResponse:
        """Search using Tavily API.

        Args:
            query: Search query
            top_k: Max results to return
            search_depth: "basic" (faster) or "advanced" (better quality)
            include_domains: Only search these domains
            exclude_domains: Exclude these domains
            include_answer: Include AI-generated answer
            include_raw_content: Include full page content
            max_results: Override top_k for API call

        Returns:
            SearchResponse with results
        """
        if not self.is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=self.provider_type,
                error="Tavily API key not configured",
            )

        start_time = time.perf_counter()

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results or top_k,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", [])[:top_k]:
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            provider=self.provider_type,
                            score=item.get("score", 0.0),
                            source_type="web",
                            metadata={
                                "raw_content": item.get("raw_content"),
                                "answer": data.get("answer"),
                            },
                        )
                    )

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return SearchResponse(
                    query=query,
                    results=results,
                    total_results=len(results),
                    provider=self.provider_type,
                    search_time_ms=elapsed_ms,
                )

            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    return SearchResponse(
                        query=query,
                        results=[],
                        total_results=0,
                        provider=self.provider_type,
                        error=f"Tavily API error: {e.response.status_code}",
                    )
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return SearchResponse(
                        query=query,
                        results=[],
                        total_results=0,
                        provider=self.provider_type,
                        error=f"Tavily error: {e!s}",
                    )

        return SearchResponse(
            query=query,
            results=[],
            total_results=0,
            provider=self.provider_type,
            error="Max retries exceeded",
        )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
