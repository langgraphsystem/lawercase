"""RAG pipeline orchestration: ingestion, hybrid retrieval, re-ranking, context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .context import ContextBuilder
from .hybrid import HybridRetriever, ScoredChunk
from .ingestion import (Document, DocumentChunk, DocumentIngestion,
                        DocumentStore)
from .rerank import Reranker


class SimpleEmbedder:
    """Simple random embedder used for development/testing."""

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim = embedding_dim

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        rng = np.random.default_rng(seed=42)
        return rng.random((len(texts), self.embedding_dim)).tolist()


@dataclass
class RAGResult:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict
    score: float
    keyword_score: float
    semantic_score: float


class RAGPipeline:
    """High-level RAG pipeline with ingestion -> hybrid search -> re-ranking -> context."""

    def __init__(
        self,
        *,
        embedder: SimpleEmbedder | None = None,
        alpha: float = 0.6,
    ) -> None:
        self.embedder = embedder or SimpleEmbedder()
        self.store = DocumentStore()
        self.ingestion = DocumentIngestion(store=self.store, embedder=self.embedder)
        self.retriever = HybridRetriever(store=self.store, embedder=self.embedder, alpha=alpha)
        self.reranker = Reranker()
        self.context_builder = ContextBuilder()

    async def ingest(self, documents: list[Document]) -> list[DocumentChunk]:
        return await self.ingestion.ingest(documents)

    async def query(
        self,
        query: str,
        *,
        top_k: int = 5,
        context_tokens: int = 600,
    ) -> dict[str, Any]:
        preliminary = await self.retriever.search(query, top_k=top_k * 2)
        reranked = self.reranker.rerank(query, preliminary)
        top_results = reranked[:top_k]

        context = self.context_builder.build(top_results, max_tokens=context_tokens)
        results = [self._to_result(sc) for sc in top_results]
        return {"results": results, "context": context}

    def _to_result(self, scored: ScoredChunk) -> RAGResult:
        return RAGResult(
            chunk_id=scored.chunk.chunk_id,
            doc_id=scored.chunk.doc_id,
            text=scored.chunk.text,
            metadata=scored.chunk.metadata,
            score=scored.combined_score,
            keyword_score=scored.keyword_score,
            semantic_score=scored.semantic_score,
        )


# Legacy exports kept for backwards compatibility in tests/imports.
__all__ = [
    "Document",
    "DocumentChunk",
    "RAGPipeline",
    "RAGResult",
    "SimpleEmbedder",
]
