"""Hybrid RAG Retrieval System.

Combines multiple retrieval strategies:
- Dense retrieval (embedding similarity)
- Sparse retrieval (BM25/keyword)
- Graph-based retrieval (knowledge graph traversal)
- Cross-encoder reranking

Provides unified interface for hybrid search.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RetrievalStrategy(str, Enum):
    """Available retrieval strategies."""

    DENSE = "dense"  # Embedding similarity
    SPARSE = "sparse"  # BM25/keyword
    GRAPH = "graph"  # Knowledge graph
    HYBRID = "hybrid"  # Combination of all


@dataclass(slots=True)
class RetrievalResult:
    """Single retrieval result."""

    id: str
    content: str
    score: float
    source: str = ""
    strategy: RetrievalStrategy = RetrievalStrategy.DENSE
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def combined_score(self) -> float:
        """Get combined score from metadata or default score."""
        return self.metadata.get("combined_score", self.score)


@dataclass
class HybridSearchResult:
    """Result of hybrid search."""

    results: list[RetrievalResult]
    total_found: int
    strategies_used: list[RetrievalStrategy]
    execution_time_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval."""

    # Strategy weights (must sum to 1.0)
    dense_weight: float = 0.5
    sparse_weight: float = 0.3
    graph_weight: float = 0.2

    # Top-k settings
    dense_top_k: int = 20
    sparse_top_k: int = 20
    graph_top_k: int = 10
    final_top_k: int = 10

    # Reranking
    use_reranker: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Thresholds
    min_score: float = 0.3
    dedup_threshold: float = 0.95  # Similarity for dedup


class DenseRetriever:
    """Dense retrieval using embeddings."""

    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]] | None = None,
        vector_store: Any = None,
    ) -> None:
        self.embedding_fn = embedding_fn
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve using dense embeddings."""
        try:
            if self.vector_store is None:
                # Fallback to Supabase
                from core.storage.supabase_client import get_supabase_client

                client = get_supabase_client()

                # Get embedding
                if self.embedding_fn:
                    query_embedding = self.embedding_fn(query)
                else:
                    from knowledge_base.embedding_utils import aembed

                    embeddings = await aembed([query])
                    query_embedding = embeddings[0]

                # Search using RPC function
                response = client.rpc(
                    "match_documents",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.3,
                        "match_count": top_k,
                    },
                ).execute()

                results = []
                for item in response.data or []:
                    results.append(
                        RetrievalResult(
                            id=item.get("id", ""),
                            content=item.get("content", ""),
                            score=item.get("similarity", 0.0),
                            source=item.get("source", ""),
                            strategy=RetrievalStrategy.DENSE,
                            metadata=item.get("metadata", {}),
                        )
                    )

                return results

            # Use provided vector store
            results = await self.vector_store.similarity_search(query, k=top_k, filter=filters)
            return [
                RetrievalResult(
                    id=str(i),
                    content=r.page_content if hasattr(r, "page_content") else str(r),
                    score=r.score if hasattr(r, "score") else 0.5,
                    strategy=RetrievalStrategy.DENSE,
                    metadata=r.metadata if hasattr(r, "metadata") else {},
                )
                for i, r in enumerate(results)
            ]

        except Exception as e:
            logger.warning("dense_retrieval.failed", error=str(e))
            return []


class SparseRetriever:
    """Sparse retrieval using BM25/keyword matching."""

    def __init__(self, index: Any = None) -> None:
        self.index = index
        self._bm25 = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve using BM25/keyword search."""
        try:
            # Try Supabase full-text search
            from core.storage.supabase_client import get_supabase_client

            client = get_supabase_client()

            # Use PostgreSQL full-text search
            response = client.rpc(
                "search_documents_fts",
                {
                    "search_query": query,
                    "match_count": top_k,
                },
            ).execute()

            results = []
            for item in response.data or []:
                results.append(
                    RetrievalResult(
                        id=item.get("id", ""),
                        content=item.get("content", ""),
                        score=item.get("rank", 0.0),
                        source=item.get("source", ""),
                        strategy=RetrievalStrategy.SPARSE,
                        metadata=item.get("metadata", {}),
                    )
                )

            return results

        except Exception as e:
            logger.warning("sparse_retrieval.failed", error=str(e))
            return []


class GraphRetriever:
    """Graph-based retrieval using knowledge graph."""

    def __init__(self, graph_store: Any = None) -> None:
        self.graph_store = graph_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        hop_depth: int = 2,
    ) -> list[RetrievalResult]:
        """Retrieve using knowledge graph traversal."""
        try:
            if self.graph_store is None:
                # Try to use existing graph RAG
                from knowledge_base.knowledge_store import KnowledgeStore

                store = KnowledgeStore()
                # Extract entities from query
                entities = self._extract_entities(query)

                if not entities:
                    return []

                # Traverse graph from entities
                results = []
                for entity in entities[:3]:  # Limit entities
                    related = await store.get_related_documents(
                        entity, depth=hop_depth, limit=top_k // 3
                    )
                    for doc in related:
                        results.append(
                            RetrievalResult(
                                id=doc.get("id", ""),
                                content=doc.get("content", ""),
                                score=doc.get("relevance", 0.5),
                                source=doc.get("source", "graph"),
                                strategy=RetrievalStrategy.GRAPH,
                                metadata={"entity": entity, **doc.get("metadata", {})},
                            )
                        )

                return results[:top_k]

            # Use provided graph store
            return await self.graph_store.query(query, top_k=top_k, depth=hop_depth)

        except Exception as e:
            logger.warning("graph_retrieval.failed", error=str(e))
            return []

    def _extract_entities(self, query: str) -> list[str]:
        """Extract potential entities from query."""
        # Simple extraction - in production use NER
        import re

        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', query)

        # Extract capitalized words (potential proper nouns)
        words = query.split()
        capitalized = [w for w in words if w[0].isupper() and len(w) > 2]

        return list(set(quoted + capitalized))[:5]


class CrossEncoderReranker:
    """Cross-encoder reranking for improved relevance."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self) -> None:
        """Lazy load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
            except ImportError:
                logger.warning(
                    "cross_encoder.import_failed",
                    hint="Install sentence-transformers for reranking",
                )
                self._model = None

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Rerank results using cross-encoder."""
        if not results:
            return []

        self._load_model()

        if self._model is None:
            # Fallback: return sorted by original score
            return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]

        try:
            # Prepare pairs for cross-encoder
            pairs = [(query, r.content[:512]) for r in results]

            # Score pairs
            scores = self._model.predict(pairs)

            # Update scores
            for result, score in zip(results, scores, strict=False):
                result.metadata["original_score"] = result.score
                result.metadata["rerank_score"] = float(score)
                result.score = float(score)

            # Sort and return top-k
            reranked = sorted(results, key=lambda r: r.score, reverse=True)
            return reranked[:top_k]

        except Exception as e:
            logger.warning("reranking.failed", error=str(e))
            return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]


class HybridRetriever:
    """Hybrid retriever combining multiple strategies.

    Features:
    - Dense + Sparse + Graph retrieval
    - Score fusion with configurable weights
    - Cross-encoder reranking
    - Deduplication

    Usage:
        retriever = HybridRetriever()

        results = await retriever.search(
            query="EB-1A extraordinary ability requirements",
            top_k=10,
        )

        for result in results.results:
            print(f"{result.score:.3f}: {result.content[:100]}")
    """

    def __init__(
        self,
        config: HybridConfig | None = None,
        dense_retriever: DenseRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        graph_retriever: GraphRetriever | None = None,
        reranker: CrossEncoderReranker | None = None,
    ) -> None:
        self.config = config or HybridConfig()
        self.dense = dense_retriever or DenseRetriever()
        self.sparse = sparse_retriever or SparseRetriever()
        self.graph = graph_retriever or GraphRetriever()
        self.reranker = reranker or CrossEncoderReranker(self.config.reranker_model)

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        strategies: list[RetrievalStrategy] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> HybridSearchResult:
        """Perform hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            strategies: Which strategies to use (default: all)
            filters: Optional filters

        Returns:
            HybridSearchResult with combined results
        """
        import time

        start_time = time.perf_counter()

        top_k = top_k or self.config.final_top_k
        strategies = strategies or [
            RetrievalStrategy.DENSE,
            RetrievalStrategy.SPARSE,
            RetrievalStrategy.GRAPH,
        ]

        # Run retrievers in parallel
        tasks = []
        strategies_used = []

        if RetrievalStrategy.DENSE in strategies:
            tasks.append(self.dense.retrieve(query, self.config.dense_top_k, filters))
            strategies_used.append(RetrievalStrategy.DENSE)

        if RetrievalStrategy.SPARSE in strategies:
            tasks.append(self.sparse.retrieve(query, self.config.sparse_top_k, filters))
            strategies_used.append(RetrievalStrategy.SPARSE)

        if RetrievalStrategy.GRAPH in strategies:
            tasks.append(self.graph.retrieve(query, self.config.graph_top_k))
            strategies_used.append(RetrievalStrategy.GRAPH)

        # Gather results
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter errors
        combined: list[RetrievalResult] = []
        for i, results in enumerate(all_results):
            if isinstance(results, Exception):
                logger.warning(
                    "hybrid_retrieval.strategy_failed",
                    strategy=strategies_used[i].value,
                    error=str(results),
                )
                continue
            combined.extend(results)

        # Deduplicate
        combined = self._deduplicate(combined)

        # Normalize and fuse scores
        combined = self._fuse_scores(combined)

        # Filter by minimum score
        combined = [r for r in combined if r.score >= self.config.min_score]

        # Rerank if enabled
        if self.config.use_reranker and combined:
            combined = await self.reranker.rerank(query, combined, top_k * 2)

        # Final sort and top-k
        combined = sorted(combined, key=lambda r: r.score, reverse=True)[:top_k]

        elapsed = (time.perf_counter() - start_time) * 1000

        logger.info(
            "hybrid_retrieval.complete",
            query_length=len(query),
            results_count=len(combined),
            strategies=len(strategies_used),
            time_ms=elapsed,
        )

        return HybridSearchResult(
            results=combined,
            total_found=len(combined),
            strategies_used=strategies_used,
            execution_time_ms=elapsed,
            metadata={
                "query": query,
                "config": {
                    "dense_weight": self.config.dense_weight,
                    "sparse_weight": self.config.sparse_weight,
                    "graph_weight": self.config.graph_weight,
                },
            },
        )

    def _deduplicate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Remove duplicate results based on content similarity."""
        seen_hashes: set[int] = set()
        unique: list[RetrievalResult] = []

        for result in results:
            # Hash first 200 chars for dedup
            content_hash = hash(result.content[:200].lower().strip())

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(result)

        return unique

    def _fuse_scores(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Fuse scores from different strategies using Reciprocal Rank Fusion."""
        # Group by content (for multi-strategy hits)
        content_map: dict[str, list[RetrievalResult]] = {}

        for result in results:
            key = result.content[:200]
            if key not in content_map:
                content_map[key] = []
            content_map[key].append(result)

        # Fuse scores using RRF
        k = 60  # RRF constant
        fused_results: list[RetrievalResult] = []

        for _key, group in content_map.items():
            # Calculate RRF score
            rrf_score = 0.0
            strategies_hit = set()

            for i, result in enumerate(group):
                rank = i + 1
                weight = self._get_strategy_weight(result.strategy)
                rrf_score += weight / (k + rank)
                strategies_hit.add(result.strategy)

            # Use first result as base
            base = group[0]
            base.metadata["rrf_score"] = rrf_score
            base.metadata["strategies_hit"] = [s.value for s in strategies_hit]
            base.metadata["combined_score"] = rrf_score
            base.score = rrf_score

            fused_results.append(base)

        return fused_results

    def _get_strategy_weight(self, strategy: RetrievalStrategy) -> float:
        """Get weight for a retrieval strategy."""
        weights = {
            RetrievalStrategy.DENSE: self.config.dense_weight,
            RetrievalStrategy.SPARSE: self.config.sparse_weight,
            RetrievalStrategy.GRAPH: self.config.graph_weight,
        }
        return weights.get(strategy, 0.33)


# Convenience functions
def create_hybrid_retriever(
    dense_weight: float = 0.5,
    sparse_weight: float = 0.3,
    graph_weight: float = 0.2,
    use_reranker: bool = True,
) -> HybridRetriever:
    """Create configured hybrid retriever."""
    config = HybridConfig(
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
        graph_weight=graph_weight,
        use_reranker=use_reranker,
    )
    return HybridRetriever(config=config)


async def hybrid_search(
    query: str,
    top_k: int = 10,
    **kwargs: Any,
) -> HybridSearchResult:
    """Convenience function for hybrid search."""
    retriever = create_hybrid_retriever(**kwargs)
    return await retriever.search(query, top_k=top_k)
