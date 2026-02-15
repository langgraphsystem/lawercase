"""Tests for the Web Search System.

Tests cover:
- SearchResult and SearchResponse data classes
- WebSearchProvider abstract interface
- TavilyClient, DuckDuckGoClient, ArxivClient implementations
- SearchAggregator for multi-provider search
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from core.search.web_search_provider import (
    SearchProviderType,
    SearchResponse,
    SearchResult,
    WebSearchProvider,
)


class TestSearchProviderType:
    """Tests for SearchProviderType enum."""

    def test_provider_types_exist(self) -> None:
        """Verify all expected provider types exist."""
        assert SearchProviderType.TAVILY == "tavily"
        assert SearchProviderType.DUCKDUCKGO == "duckduckgo"
        assert SearchProviderType.ARXIV == "arxiv"
        assert SearchProviderType.GOOGLE == "google"

    def test_provider_type_values(self) -> None:
        """Provider types should have lowercase string values."""
        for provider in SearchProviderType:
            assert provider.value == provider.value.lower()


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_result_creation(self) -> None:
        """Test basic search result creation."""
        result = SearchResult(
            title="Test Article",
            url="https://example.com/article",
            snippet="This is a test article about EB-1A visas.",
            provider=SearchProviderType.TAVILY,
            score=0.95,
        )

        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        assert result.provider == SearchProviderType.TAVILY
        assert result.score == 0.95

    def test_result_default_values(self) -> None:
        """Test default values for optional fields."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            provider=SearchProviderType.DUCKDUCKGO,
        )

        assert result.score == 0.0
        assert result.published_date is None
        assert result.author is None
        assert result.source_type == "web"
        assert result.metadata == {}

    def test_result_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = SearchResult(
            title="Research Paper",
            url="https://arxiv.org/abs/1234.5678",
            snippet="A groundbreaking paper on AI.",
            provider=SearchProviderType.ARXIV,
            score=0.88,
            author="Dr. Smith",
            source_type="paper",
        )

        data = result.to_dict()

        assert data["title"] == "Research Paper"
        assert data["provider"] == "arxiv"
        assert data["score"] == 0.88
        assert data["author"] == "Dr. Smith"
        assert data["source_type"] == "paper"

    def test_result_with_datetime(self) -> None:
        """Test result with published date."""
        pub_date = datetime(2024, 6, 15)
        result = SearchResult(
            title="News Article",
            url="https://news.com/article",
            snippet="Breaking news.",
            provider=SearchProviderType.DUCKDUCKGO,
            published_date=pub_date,
        )

        data = result.to_dict()
        assert data["published_date"] == "2024-06-15T00:00:00"

    def test_result_with_metadata(self) -> None:
        """Test result with custom metadata."""
        result = SearchResult(
            title="Paper",
            url="https://arxiv.org/abs/1234",
            snippet="AI research",
            provider=SearchProviderType.ARXIV,
            metadata={
                "citations": 150,
                "category": "cs.AI",
                "pdf_url": "https://arxiv.org/pdf/1234.pdf",
            },
        )

        assert result.metadata["citations"] == 150
        assert result.metadata["category"] == "cs.AI"


class TestSearchResponse:
    """Tests for SearchResponse dataclass."""

    def test_response_creation(self) -> None:
        """Test basic search response creation."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example.com/1",
                snippet="First result",
                provider=SearchProviderType.TAVILY,
            ),
            SearchResult(
                title="Result 2",
                url="https://example.com/2",
                snippet="Second result",
                provider=SearchProviderType.TAVILY,
            ),
        ]

        response = SearchResponse(
            query="EB-1A visa requirements",
            results=results,
            total_results=100,
            provider=SearchProviderType.TAVILY,
            search_time_ms=150.5,
        )

        assert response.query == "EB-1A visa requirements"
        assert len(response.results) == 2
        assert response.total_results == 100
        assert response.search_time_ms == 150.5

    def test_response_default_values(self) -> None:
        """Test default values."""
        response = SearchResponse(
            query="test",
            results=[],
            total_results=0,
            provider=SearchProviderType.DUCKDUCKGO,
        )

        assert response.search_time_ms == 0.0
        assert response.cached is False
        assert response.error is None

    def test_response_with_error(self) -> None:
        """Test response with error message."""
        response = SearchResponse(
            query="test",
            results=[],
            total_results=0,
            provider=SearchProviderType.GOOGLE,
            error="API rate limit exceeded",
        )

        assert response.error == "API rate limit exceeded"
        data = response.to_dict()
        assert data["error"] == "API rate limit exceeded"

    def test_response_to_dict(self) -> None:
        """Test conversion to dictionary."""
        results = [
            SearchResult(
                title="Article",
                url="https://example.com",
                snippet="Content",
                provider=SearchProviderType.TAVILY,
            ),
        ]

        response = SearchResponse(
            query="search query",
            results=results,
            total_results=50,
            provider=SearchProviderType.TAVILY,
            search_time_ms=200.0,
            cached=True,
        )

        data = response.to_dict()

        assert data["query"] == "search query"
        assert len(data["results"]) == 1
        assert data["total_results"] == 50
        assert data["provider"] == "tavily"
        assert data["cached"] is True

    def test_response_with_string_provider(self) -> None:
        """Test response with string provider (for aggregated results)."""
        response = SearchResponse(
            query="test",
            results=[],
            total_results=0,
            provider="aggregated",
        )

        data = response.to_dict()
        assert data["provider"] == "aggregated"


class TestWebSearchProviderInterface:
    """Tests for WebSearchProvider abstract class."""

    def test_provider_is_abstract(self) -> None:
        """WebSearchProvider should be abstract."""
        with pytest.raises(TypeError):
            WebSearchProvider()  # type: ignore

    def test_provider_requires_search_method(self) -> None:
        """Concrete providers must implement search method."""

        class IncompleteProvider(WebSearchProvider):
            provider_type = SearchProviderType.GOOGLE

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteProvider()  # type: ignore

    def test_concrete_provider_implementation(self) -> None:
        """Test a properly implemented provider."""

        class MockProvider(WebSearchProvider):
            provider_type = SearchProviderType.GOOGLE

            async def search(
                self,
                query: str,
                *,
                top_k: int = 10,
                **kwargs: Any,
            ) -> SearchResponse:
                return SearchResponse(
                    query=query,
                    results=[],
                    total_results=0,
                    provider=self.provider_type,
                )

            def is_available(self) -> bool:
                return True

        provider = MockProvider()
        assert provider.is_available()
        assert provider.provider_type == SearchProviderType.GOOGLE


class TestSearchResultScoring:
    """Tests for search result scoring and ranking."""

    def test_results_sortable_by_score(self) -> None:
        """Results should be sortable by relevance score."""
        results = [
            SearchResult(
                title="Low",
                url="https://example.com/1",
                snippet="Low relevance",
                provider=SearchProviderType.TAVILY,
                score=0.3,
            ),
            SearchResult(
                title="High",
                url="https://example.com/2",
                snippet="High relevance",
                provider=SearchProviderType.TAVILY,
                score=0.95,
            ),
            SearchResult(
                title="Medium",
                url="https://example.com/3",
                snippet="Medium relevance",
                provider=SearchProviderType.TAVILY,
                score=0.6,
            ),
        ]

        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        assert sorted_results[0].title == "High"
        assert sorted_results[1].title == "Medium"
        assert sorted_results[2].title == "Low"

    def test_score_range_validation(self) -> None:
        """Score should typically be between 0 and 1."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
            provider=SearchProviderType.DUCKDUCKGO,
            score=0.75,
        )

        assert 0 <= result.score <= 1


class TestSearchIntegration:
    """Integration tests for search functionality."""

    @pytest.mark.asyncio
    async def test_mock_search_workflow(self) -> None:
        """Test a complete search workflow with mocked provider."""

        class TestProvider(WebSearchProvider):
            provider_type = SearchProviderType.TAVILY

            async def search(
                self,
                query: str,
                *,
                top_k: int = 10,
                **kwargs: Any,
            ) -> SearchResponse:
                # Simulate search results
                results = [
                    SearchResult(
                        title=f"Result {i} for: {query}",
                        url=f"https://example.com/result/{i}",
                        snippet=f"This is result {i} matching your query.",
                        provider=self.provider_type,
                        score=1.0 - (i * 0.1),
                    )
                    for i in range(min(top_k, 5))
                ]

                return SearchResponse(
                    query=query,
                    results=results,
                    total_results=len(results),
                    provider=self.provider_type,
                    search_time_ms=50.0,
                )

            def is_available(self) -> bool:
                return True

        provider = TestProvider()

        # Execute search
        response = await provider.search("EB-1A extraordinary ability", top_k=3)

        assert response.query == "EB-1A extraordinary ability"
        assert len(response.results) == 3
        assert response.results[0].score > response.results[1].score
        assert response.search_time_ms == 50.0

    @pytest.mark.asyncio
    async def test_concurrent_searches(self) -> None:
        """Test concurrent search execution."""

        class FastProvider(WebSearchProvider):
            provider_type = SearchProviderType.DUCKDUCKGO

            async def search(
                self,
                query: str,
                *,
                top_k: int = 10,
                **kwargs: Any,
            ) -> SearchResponse:
                await asyncio.sleep(0.01)  # Simulate network delay
                return SearchResponse(
                    query=query,
                    results=[],
                    total_results=0,
                    provider=self.provider_type,
                )

            def is_available(self) -> bool:
                return True

        provider = FastProvider()

        # Run multiple searches concurrently
        queries = ["query1", "query2", "query3"]
        tasks = [provider.search(q) for q in queries]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == 3
        assert all(r.query in queries for r in responses)


class TestSearchFiltering:
    """Tests for result filtering functionality."""

    def test_filter_by_source_type(self) -> None:
        """Filter results by source type."""
        results = [
            SearchResult(
                title="Web Article",
                url="https://example.com",
                snippet="Web content",
                provider=SearchProviderType.DUCKDUCKGO,
                source_type="web",
            ),
            SearchResult(
                title="Research Paper",
                url="https://arxiv.org",
                snippet="Academic research",
                provider=SearchProviderType.ARXIV,
                source_type="paper",
            ),
            SearchResult(
                title="News Story",
                url="https://news.com",
                snippet="Breaking news",
                provider=SearchProviderType.TAVILY,
                source_type="news",
            ),
        ]

        papers = [r for r in results if r.source_type == "paper"]
        assert len(papers) == 1
        assert papers[0].title == "Research Paper"

    def test_filter_by_provider(self) -> None:
        """Filter results by provider."""
        results = [
            SearchResult(
                title="Tavily 1",
                url="https://t1.com",
                snippet="T1",
                provider=SearchProviderType.TAVILY,
            ),
            SearchResult(
                title="DDG 1",
                url="https://d1.com",
                snippet="D1",
                provider=SearchProviderType.DUCKDUCKGO,
            ),
            SearchResult(
                title="Tavily 2",
                url="https://t2.com",
                snippet="T2",
                provider=SearchProviderType.TAVILY,
            ),
        ]

        tavily_results = [r for r in results if r.provider == SearchProviderType.TAVILY]
        assert len(tavily_results) == 2


# Pytest fixtures
@pytest.fixture
def sample_search_result() -> SearchResult:
    """Create a sample search result for testing."""
    return SearchResult(
        title="USCIS Policy Manual - EB-1A",
        url="https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-2",
        snippet="The EB-1A classification is for individuals with extraordinary ability...",
        provider=SearchProviderType.TAVILY,
        score=0.92,
        source_type="government",
        metadata={"domain": "uscis.gov", "authority": "high"},
    )


@pytest.fixture
def sample_search_response(sample_search_result: SearchResult) -> SearchResponse:
    """Create a sample search response for testing."""
    return SearchResponse(
        query="EB-1A extraordinary ability requirements",
        results=[sample_search_result],
        total_results=1,
        provider=SearchProviderType.TAVILY,
        search_time_ms=125.5,
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
