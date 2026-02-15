"""Web Search Integration Module.

Provides unified interface for web search across multiple providers:
- Tavily Search API (primary)
- DuckDuckGo (fallback, free)
- arXiv API (scientific papers)

Usage:
    from core.search import SearchAggregator

    aggregator = SearchAggregator()
    results = await aggregator.search("EB-1A visa requirements", top_k=10)
"""

from __future__ import annotations

from .arxiv_client import ArxivClient
from .duckduckgo_client import DuckDuckGoClient
from .search_aggregator import SearchAggregator
from .tavily_client import TavilyClient
from .web_search_provider import SearchResult, WebSearchProvider

__all__ = [
    "ArxivClient",
    "DuckDuckGoClient",
    "SearchAggregator",
    "SearchResult",
    "TavilyClient",
    "WebSearchProvider",
]
