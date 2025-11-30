"""BM25-based sparse retrieval for hybrid RAG pipeline.

Implements Best Matching 25 (BM25) Okapi algorithm for keyword-based document retrieval.
Complements dense retrieval (vector search) in hybrid search systems.

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from rank_bm25 import BM25Okapi


def default_tokenizer(text: str) -> list[str]:
    """Default tokenizer: lowercase + split on whitespace.

    Args:
        text: Input text to tokenize

    Returns:
        List of tokens
    """
    return text.lower().split()


class BM25Retriever:
    """BM25 sparse retriever for keyword-based search.

    Uses BM25 Okapi algorithm for scoring documents based on term frequency
    and inverse document frequency. Ideal for exact keyword matching and
    complement to dense retrieval.

    Attributes:
        documents: Original document texts
        tokenized_corpus: Pre-tokenized documents for BM25
        bm25: BM25Okapi scorer instance
        tokenizer: Function to tokenize text

    Example:
        >>> documents = [
        ...     "Contract law governs agreements between parties",
        ...     "Immigration law deals with visa requirements"
        ... ]
        >>> retriever = BM25Retriever(documents)
        >>> results = await retriever.asearch("visa requirements", top_k=1)
        >>> print(results[0][0])  # Immigration law document
    """

    def __init__(
        self,
        documents: list[str],
        tokenizer: Callable[[str], list[str]] | None = None,
    ) -> None:
        """Initialize BM25 retriever.

        Args:
            documents: List of document texts to index
            tokenizer: Optional tokenizer function (default: whitespace split)
        """
        self.documents = documents
        self.tokenizer = tokenizer or default_tokenizer

        # Tokenize corpus
        self.tokenized_corpus = [self.tokenizer(doc) for doc in documents]

        # Initialize BM25
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    async def asearch(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Asynchronously search for relevant documents using BM25.

        Args:
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of (document, score) tuples, sorted by score descending

        Example:
            >>> retriever = BM25Retriever(documents)
            >>> results = await retriever.asearch("immigration visa", top_k=3)
            >>> for doc, score in results:
            ...     print(f"Score: {score:.2f} - {doc[:50]}")
        """
        # Tokenize query
        tokenized_query = self.tokenizer(query)

        # Get BM25 scores (run in executor for async)
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, self.bm25.get_scores, tokenized_query)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]

        # Return documents with scores
        return [(self.documents[i], float(scores[i])) for i in top_indices]

    async def aupdate_index(self, new_docs: list[str]) -> None:
        """Asynchronously update BM25 index with new documents.

        Args:
            new_docs: List of new document texts to add

        Example:
            >>> await retriever.aupdate_index([
            ...     "Employment law covers workplace regulations",
            ...     "Tax law deals with federal and state taxes"
            ... ])
        """
        # Add new documents
        self.documents.extend(new_docs)

        # Tokenize new docs
        new_tokenized = [self.tokenizer(doc) for doc in new_docs]
        self.tokenized_corpus.extend(new_tokenized)

        # Rebuild BM25 index
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._rebuild_index,
        )

    def _rebuild_index(self) -> None:
        """Rebuild BM25 index with current corpus."""
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    async def asearch_batch(
        self,
        queries: list[str],
        top_k: int = 10,
    ) -> list[list[tuple[str, float]]]:
        """Search multiple queries in batch.

        Args:
            queries: List of search queries
            top_k: Number of results per query

        Returns:
            List of result lists (one per query)

        Example:
            >>> queries = ["contract law", "immigration visa"]
            >>> results = await retriever.asearch_batch(queries, top_k=3)
            >>> len(results)  # One result list per query
            2
        """
        # Run searches concurrently
        tasks = [self.asearch(q, top_k) for q in queries]
        return await asyncio.gather(*tasks)

    def get_document_count(self) -> int:
        """Get total number of indexed documents.

        Returns:
            Number of documents in index
        """
        return len(self.documents)

    def get_avg_doc_length(self) -> float:
        """Get average document length (in tokens).

        Returns:
            Average number of tokens per document
        """
        if not self.tokenized_corpus:
            return 0.0
        return sum(len(doc) for doc in self.tokenized_corpus) / len(self.tokenized_corpus)

    async def aget_stats(self) -> dict[str, Any]:
        """Get retriever statistics.

        Returns:
            Dictionary with stats:
                - document_count: Number of indexed documents
                - avg_doc_length: Average tokens per document
                - total_tokens: Total tokens across corpus

        Example:
            >>> stats = await retriever.aget_stats()
            >>> print(f"Indexed {stats['document_count']} documents")
        """
        return {
            "document_count": self.get_document_count(),
            "avg_doc_length": self.get_avg_doc_length(),
            "total_tokens": sum(len(doc) for doc in self.tokenized_corpus),
        }


async def create_bm25_retriever(
    documents: list[str],
    tokenizer: Callable[[str], list[str]] | None = None,
) -> BM25Retriever:
    """Factory function to create BM25 retriever.

    Args:
        documents: List of document texts to index
        tokenizer: Optional custom tokenizer

    Returns:
        Initialized BM25Retriever instance

    Example:
        >>> documents = load_documents()
        >>> retriever = await create_bm25_retriever(documents)
        >>> results = await retriever.asearch("search query")
    """
    return BM25Retriever(documents, tokenizer)


__all__ = [
    "BM25Retriever",
    "create_bm25_retriever",
    "default_tokenizer",
]
