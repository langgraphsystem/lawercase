"""Hybrid search fusion using Reciprocal Rank Fusion (RRF).

Combines results from multiple retrieval methods (sparse + dense) into unified ranking.
RRF is parameter-free and proven effective for hybrid search.

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

# Type aliases for clarity
DocumentID = str  # Unique identifier for document
Score = float  # Relevance score
RankedResult = tuple[DocumentID, Score]  # (doc_id, score) pair
RankedResults = list[RankedResult]  # List of ranked results


class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (RRF) for hybrid search.

    RRF combines rankings from multiple retrieval systems without requiring
    score normalization. It's robust and parameter-free (except k constant).

    Algorithm:
        RRF_score(d) = Σ_i (1 / (k + rank_i(d)))

    where:
        k = 60 (standard constant, can be tuned)
        rank_i(d) = position of document d in ranking i (1-indexed)

    Attributes:
        k: RRF constant (default: 60)
        weights: Optional weights for each retrieval method

    Example:
        >>> fusion = ReciprocalRankFusion()
        >>> sparse_results = [("doc1", 0.9), ("doc2", 0.7)]
        >>> dense_results = [("doc2", 0.95), ("doc3", 0.8)]
        >>> fused = await fusion.fuse([sparse_results, dense_results])
        >>> print(fused[0][0])  # doc2 (appears in both)
    """

    def __init__(
        self,
        k: int = 60,
        weights: list[float] | None = None,
    ) -> None:
        """Initialize RRF fusion.

        Args:
            k: RRF constant (higher = less emphasis on top ranks)
            weights: Optional weights for each retrieval method.
                     If None, all methods weighted equally.
                     Must match number of input rankings.

        Example:
            >>> # Equal weights
            >>> fusion = ReciprocalRankFusion()
            >>>
            >>> # Prefer dense retrieval (vector search)
            >>> fusion = ReciprocalRankFusion(weights=[0.3, 0.7])  # sparse, dense
        """
        self.k = k
        self.weights = weights

    async def fuse(
        self,
        rankings: list[RankedResults],
        top_k: int | None = None,
    ) -> RankedResults:
        """Fuse multiple rankings using RRF algorithm.

        Args:
            rankings: List of rankings from different retrieval methods.
                      Each ranking is a list of (doc_id, score) tuples.
            top_k: Optional limit on number of results to return.
                   If None, returns all documents.

        Returns:
            Fused ranking as list of (doc_id, fused_score) tuples,
            sorted by fused_score descending.

        Example:
            >>> sparse = [("doc1", 0.9), ("doc2", 0.7), ("doc3", 0.5)]
            >>> dense = [("doc2", 0.95), ("doc4", 0.8), ("doc1", 0.6)]
            >>> fused = await fusion.fuse([sparse, dense], top_k=3)
            >>> len(fused)
            3
        """
        # Validate weights
        if self.weights is not None and len(self.weights) != len(rankings):
            raise ValueError(
                f"Number of weights ({len(self.weights)}) must match "
                f"number of rankings ({len(rankings)})"
            )

        # Use equal weights if not specified
        weights = self.weights or [1.0] * len(rankings)

        # Compute RRF scores
        rrf_scores: dict[DocumentID, float] = defaultdict(float)

        for ranking_idx, ranking in enumerate(rankings):
            weight = weights[ranking_idx]

            for rank, (doc_id, _original_score) in enumerate(ranking, start=1):
                # RRF formula: 1 / (k + rank)
                rrf_score = weight * (1.0 / (self.k + rank))
                rrf_scores[doc_id] += rrf_score

        # Sort by fused score (descending)
        fused_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Apply top_k limit if specified
        if top_k is not None:
            fused_results = fused_results[:top_k]

        return fused_results

    async def fuse_with_metadata(
        self,
        rankings: list[list[tuple[DocumentID, Score, dict[str, Any]]]],
        top_k: int | None = None,
    ) -> list[tuple[DocumentID, Score, dict[str, Any]]]:
        """Fuse rankings with document metadata preserved.

        Args:
            rankings: List of rankings with metadata.
                      Each ranking is list of (doc_id, score, metadata) tuples.
            top_k: Optional limit on results.

        Returns:
            Fused ranking with metadata from first occurrence of each document.

        Example:
            >>> sparse = [("doc1", 0.9, {"source": "bm25"})]
            >>> dense = [("doc1", 0.95, {"source": "vector"})]
            >>> fused = await fusion.fuse_with_metadata([sparse, dense])
            >>> fused[0][2]["source"]  # "bm25" (first occurrence)
        """
        # Extract rankings without metadata for RRF
        simple_rankings = [
            [(doc_id, score) for doc_id, score, _meta in ranking] for ranking in rankings
        ]

        # Compute RRF scores
        fused_simple = await self.fuse(simple_rankings, top_k=None)

        # Build metadata map (first occurrence wins)
        metadata_map: dict[DocumentID, dict[str, Any]] = {}
        for ranking in rankings:
            for doc_id, _score, metadata in ranking:
                if doc_id not in metadata_map:
                    metadata_map[doc_id] = metadata

        # Combine fused scores with metadata
        fused_with_meta = [
            (doc_id, score, metadata_map.get(doc_id, {})) for doc_id, score in fused_simple
        ]

        # Apply top_k limit
        if top_k is not None:
            fused_with_meta = fused_with_meta[:top_k]

        return fused_with_meta


class HybridRetriever:
    """Hybrid retriever combining sparse (BM25) and dense (vector) search.

    Orchestrates parallel retrieval from multiple sources and fuses results
    using Reciprocal Rank Fusion.

    Attributes:
        sparse_retriever: BM25-based sparse retriever
        dense_retriever: Vector-based dense retriever
        fusion: RRF fusion algorithm
        sparse_weight: Weight for sparse retrieval (default: 0.5)
        dense_weight: Weight for dense retrieval (default: 0.5)

    Example:
        >>> from core.rag.sparse_retrieval import BM25Retriever
        >>> from core.memory.stores.semantic_store import SemanticMemoryStore
        >>>
        >>> sparse = BM25Retriever(documents)
        >>> dense = SemanticMemoryStore()
        >>> hybrid = HybridRetriever(sparse, dense)
        >>> results = await hybrid.search("immigration visa requirements")
    """

    def __init__(
        self,
        sparse_retriever: Any,  # BM25Retriever
        dense_retriever: Any,  # SemanticMemoryStore or similar
        sparse_weight: float = 0.5,
        dense_weight: float = 0.5,
        rrf_k: int = 60,
    ) -> None:
        """Initialize hybrid retriever.

        Args:
            sparse_retriever: BM25-based keyword retriever
            dense_retriever: Vector-based semantic retriever
            sparse_weight: Weight for sparse results (0.0-1.0)
            dense_weight: Weight for dense results (0.0-1.0)
            rrf_k: RRF constant for fusion

        Example:
            >>> # Prefer semantic search
            >>> hybrid = HybridRetriever(
            ...     sparse, dense,
            ...     sparse_weight=0.3,
            ...     dense_weight=0.7
            ... )
        """
        self.sparse_retriever = sparse_retriever
        self.dense_retriever = dense_retriever

        # Normalize weights
        total_weight = sparse_weight + dense_weight
        self.sparse_weight = sparse_weight / total_weight
        self.dense_weight = dense_weight / total_weight

        # Initialize fusion
        self.fusion = ReciprocalRankFusion(
            k=rrf_k,
            weights=[self.sparse_weight, self.dense_weight],
        )

    async def search(
        self,
        query: str,
        top_k: int = 10,
        sparse_top_k: int | None = None,
        dense_top_k: int | None = None,
    ) -> RankedResults:
        """Hybrid search combining sparse and dense retrieval.

        Args:
            query: Search query string
            top_k: Number of final results to return
            sparse_top_k: Number of sparse results to retrieve.
                          If None, uses top_k * 2 (over-retrieve for fusion)
            dense_top_k: Number of dense results to retrieve.
                         If None, uses top_k * 2

        Returns:
            Fused ranking as list of (doc_id, fused_score) tuples

        Example:
            >>> results = await hybrid.search("EB-1A criteria", top_k=5)
            >>> for doc_id, score in results:
            ...     print(f"{doc_id}: {score:.3f}")
        """
        # Over-retrieve to improve fusion quality
        sparse_k = sparse_top_k or (top_k * 2)
        dense_k = dense_top_k or (top_k * 2)

        # Parallel retrieval
        sparse_task = self.sparse_retriever.asearch(query, top_k=sparse_k)
        dense_task = self.dense_retriever.asearch(query, top_k=dense_k)

        sparse_results, dense_results = await asyncio.gather(
            sparse_task,
            dense_task,
        )

        # Fuse results
        fused = await self.fusion.fuse(
            rankings=[sparse_results, dense_results],
            top_k=top_k,
        )

        return fused

    async def search_batch(
        self,
        queries: list[str],
        top_k: int = 10,
    ) -> list[RankedResults]:
        """Batch hybrid search for multiple queries.

        Args:
            queries: List of search queries
            top_k: Number of results per query

        Returns:
            List of fused rankings (one per query)

        Example:
            >>> queries = ["EB-1A criteria", "visa requirements"]
            >>> results = await hybrid.search_batch(queries, top_k=5)
            >>> len(results)
            2
        """
        tasks = [self.search(q, top_k=top_k) for q in queries]
        return await asyncio.gather(*tasks)

    def get_weights(self) -> dict[str, float]:
        """Get current retrieval weights.

        Returns:
            Dictionary with sparse and dense weights

        Example:
            >>> weights = hybrid.get_weights()
            >>> print(f"Sparse: {weights['sparse']:.2f}")
        """
        return {
            "sparse": self.sparse_weight,
            "dense": self.dense_weight,
        }


async def create_hybrid_retriever(
    sparse_retriever: Any,
    dense_retriever: Any,
    sparse_weight: float = 0.5,
    dense_weight: float = 0.5,
) -> HybridRetriever:
    """Factory function to create hybrid retriever.

    Args:
        sparse_retriever: BM25-based retriever
        dense_retriever: Vector-based retriever
        sparse_weight: Weight for sparse retrieval
        dense_weight: Weight for dense retrieval

    Returns:
        Initialized HybridRetriever instance

    Example:
        >>> from core.rag.sparse_retrieval import create_bm25_retriever
        >>>
        >>> sparse = await create_bm25_retriever(documents)
        >>> dense = get_semantic_memory_store()
        >>> hybrid = await create_hybrid_retriever(sparse, dense)
    """
    return HybridRetriever(
        sparse_retriever,
        dense_retriever,
        sparse_weight,
        dense_weight,
    )


__all__ = [
    "DocumentID",
    "HybridRetriever",
    "RankedResult",
    "RankedResults",
    "ReciprocalRankFusion",
    "Score",
    "create_hybrid_retriever",
]
