"""arXiv API client for scientific paper search.

arXiv provides free access to scientific papers in physics,
mathematics, computer science, and more.
API Docs: https://info.arxiv.org/help/api/
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
    import arxiv

    ARXIV_AVAILABLE = True
except ImportError:
    arxiv = None  # type: ignore
    ARXIV_AVAILABLE = False


class ArxivClient(WebSearchProvider):
    """arXiv API client for scientific paper search.

    Features:
    - Free, no API key required
    - Access to 2M+ scientific papers
    - Full metadata (authors, abstract, PDF)
    - Category filtering

    Install:
        pip install arxiv
    """

    provider_type = SearchProviderType.ARXIV

    def __init__(
        self,
        timeout: float = 30.0,
        delay_seconds: float = 3.0,  # arXiv rate limit
    ) -> None:
        """Initialize arXiv client.

        Args:
            timeout: Request timeout in seconds
            delay_seconds: Delay between requests (rate limit)
        """
        self.timeout = timeout
        self.delay_seconds = delay_seconds

    def is_available(self) -> bool:
        """Check if arxiv library is installed."""
        return ARXIV_AVAILABLE

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        sort_by: str = "relevance",  # relevance, lastUpdatedDate, submittedDate
        sort_order: str = "descending",
        categories: list[str] | None = None,  # e.g., ["cs.AI", "cs.CL"]
        **kwargs: Any,
    ) -> SearchResponse:
        """Search arXiv papers.

        Args:
            query: Search query (supports arXiv query syntax)
            top_k: Max results to return
            sort_by: Sort criteria
            sort_order: ascending or descending
            categories: Filter by arXiv categories

        Returns:
            SearchResponse with paper results
        """
        if not self.is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                provider=self.provider_type,
                error="arxiv library not installed. Run: pip install arxiv",
            )

        start_time = time.perf_counter()

        try:
            # Build query with category filter
            full_query = query
            if categories:
                cat_filter = " OR ".join(f"cat:{cat}" for cat in categories)
                full_query = f"({query}) AND ({cat_filter})"

            # Run sync arxiv search in thread pool
            results = await asyncio.to_thread(
                self._sync_search,
                query=full_query,
                top_k=top_k,
                sort_by=sort_by,
                sort_order=sort_order,
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
                error=f"arXiv error: {e!s}",
            )

    def _sync_search(
        self,
        query: str,
        top_k: int,
        sort_by: str,
        sort_order: str,
    ) -> list[SearchResult]:
        """Synchronous search (called in thread)."""
        results = []

        # Map sort options
        sort_criterion = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
        }.get(sort_by, arxiv.SortCriterion.Relevance)

        sort_ord = (
            arxiv.SortOrder.Descending if sort_order == "descending" else arxiv.SortOrder.Ascending
        )

        # Create search client
        client = arxiv.Client(
            page_size=top_k,
            delay_seconds=self.delay_seconds,
            num_retries=3,
        )

        search = arxiv.Search(
            query=query,
            max_results=top_k,
            sort_by=sort_criterion,
            sort_order=sort_ord,
        )

        for paper in client.results(search):
            # Parse published date
            published_date = None
            if paper.published:
                published_date = paper.published

            # Get authors
            authors = ", ".join(author.name for author in paper.authors[:5])
            if len(paper.authors) > 5:
                authors += f" et al. ({len(paper.authors)} authors)"

            results.append(
                SearchResult(
                    title=paper.title,
                    url=paper.entry_id,
                    snippet=(
                        paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary
                    ),
                    provider=self.provider_type,
                    score=0.8,  # arXiv doesn't provide relevance scores
                    published_date=published_date,
                    author=authors,
                    source_type="paper",
                    metadata={
                        "arxiv_id": paper.get_short_id(),
                        "pdf_url": paper.pdf_url,
                        "categories": paper.categories,
                        "primary_category": paper.primary_category,
                        "comment": paper.comment,
                        "journal_ref": paper.journal_ref,
                        "doi": paper.doi,
                    },
                )
            )

        return results

    async def get_paper(self, arxiv_id: str) -> SearchResult | None:
        """Get a specific paper by arXiv ID.

        Args:
            arxiv_id: arXiv paper ID (e.g., "2301.00001")

        Returns:
            SearchResult or None if not found
        """
        if not self.is_available():
            return None

        try:
            paper = await asyncio.to_thread(self._sync_get_paper, arxiv_id)
            return paper
        except Exception:
            return None

    def _sync_get_paper(self, arxiv_id: str) -> SearchResult | None:
        """Get single paper synchronously."""
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])

        for paper in client.results(search):
            authors = ", ".join(author.name for author in paper.authors[:5])

            return SearchResult(
                title=paper.title,
                url=paper.entry_id,
                snippet=paper.summary,
                provider=self.provider_type,
                score=1.0,
                published_date=paper.published,
                author=authors,
                source_type="paper",
                metadata={
                    "arxiv_id": paper.get_short_id(),
                    "pdf_url": paper.pdf_url,
                    "categories": paper.categories,
                },
            )

        return None
