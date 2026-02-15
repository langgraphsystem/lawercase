"""Base classes for web search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SearchProviderType(str, Enum):
    """Available search provider types."""

    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    ARXIV = "arxiv"
    GOOGLE = "google"


@dataclass(slots=True)
class SearchResult:
    """Single search result from any provider."""

    title: str
    url: str
    snippet: str
    provider: SearchProviderType
    score: float = 0.0  # Relevance score (0-1)
    published_date: datetime | None = None
    author: str | None = None
    source_type: str = "web"  # web, paper, news, etc.
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "provider": self.provider.value,
            "score": self.score,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "author": self.author,
            "source_type": self.source_type,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SearchResponse:
    """Aggregated search response."""

    query: str
    results: list[SearchResult]
    total_results: int
    provider: SearchProviderType | str
    search_time_ms: float = 0.0
    cached: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "provider": (
                self.provider.value
                if isinstance(self.provider, SearchProviderType)
                else self.provider
            ),
            "search_time_ms": self.search_time_ms,
            "cached": self.cached,
            "error": self.error,
        }


class WebSearchProvider(ABC):
    """Abstract base class for web search providers."""

    provider_type: SearchProviderType

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        **kwargs: Any,
    ) -> SearchResponse:
        """Execute search query.

        Args:
            query: Search query string
            top_k: Maximum number of results to return
            **kwargs: Provider-specific parameters

        Returns:
            SearchResponse with results
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return self.provider_type.value
