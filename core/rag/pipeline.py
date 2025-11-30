"""RAG Pipeline - Main orchestration class for Retrieval-Augmented Generation.

Integrates all RAG components:
- Document parsing and chunking
- Sparse retrieval (BM25)
- Dense retrieval (vector embeddings)
- Hybrid fusion (RRF)
- Cross-encoder reranking

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import time
from typing import Any

import structlog

from .chunking import ChunkingStrategy, DocumentChunk, create_chunker
from .fusion import HybridRetriever, ReciprocalRankFusion
from .reranker import CrossEncoderReranker
from .sparse_retrieval import BM25Retriever

logger = structlog.get_logger(__name__)


@dataclass
class Document:
    """Input document for RAG pipeline.

    Attributes:
        text: Document content
        metadata: Document metadata (source, title, etc.)
        doc_id: Unique document identifier (auto-generated if not provided)

    Example:
        >>> doc = Document(
        ...     text="EB-1A visa requires extraordinary ability...",
        ...     metadata={"source": "uscis.gov", "category": "immigration"}
        ... )
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str | None = None

    def __post_init__(self) -> None:
        """Generate doc_id if not provided."""
        if self.doc_id is None:
            # Generate ID from content hash (not for security, just for unique ID)
            content_hash = hashlib.md5(self.text.encode(), usedforsecurity=False).hexdigest()[:12]
            self.doc_id = f"doc_{content_hash}"


@dataclass
class RAGResult:
    """Result from RAG retrieval.

    Attributes:
        chunk_id: Unique chunk identifier
        text: Retrieved text content
        score: Relevance score (0.0 to 1.0)
        metadata: Additional metadata

    Example:
        >>> result = RAGResult(
        ...     chunk_id="doc_abc123_chunk_0",
        ...     text="Immigration law requires...",
        ...     score=0.85,
        ...     metadata={"source": "doc1.pdf"}
        ... )
    """

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentStore:
    """In-memory document store for RAG pipeline.

    Stores documents and chunks for retrieval.
    Supports iteration and lookup by ID.

    Example:
        >>> store = DocumentStore()
        >>> store.add_document(doc)
        >>> store.add_chunks(chunks)
        >>> content = store.get_content("chunk_id")
    """

    def __init__(self) -> None:
        """Initialize empty document store."""
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}
        self._chunk_to_doc: dict[str, str] = {}

    def add_document(self, doc: Document) -> None:
        """Add document to store.

        Args:
            doc: Document to add
        """
        self._documents[doc.doc_id] = doc

    def add_chunks(self, chunks: list[DocumentChunk], doc_id: str) -> None:
        """Add chunks to store.

        Args:
            chunks: List of document chunks
            doc_id: Parent document ID
        """
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._chunk_to_doc[chunk.chunk_id] = doc_id

    def get_document(self, doc_id: str) -> Document | None:
        """Get document by ID."""
        return self._documents.get(doc_id)

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        """Get chunk by ID."""
        return self._chunks.get(chunk_id)

    def get_content(self, chunk_id: str) -> str:
        """Get chunk content by ID."""
        chunk = self._chunks.get(chunk_id)
        return chunk.content if chunk else ""

    def get_all_texts(self) -> list[str]:
        """Get all chunk texts for indexing."""
        return [chunk.content for chunk in self._chunks.values()]

    def get_chunk_ids(self) -> list[str]:
        """Get all chunk IDs."""
        return list(self._chunks.keys())

    def get_content_map(self) -> dict[str, str]:
        """Get mapping from chunk_id to content."""
        return {cid: chunk.content for cid, chunk in self._chunks.items()}

    def iter_chunks(self) -> Iterator[DocumentChunk]:
        """Iterate over all chunks."""
        return iter(self._chunks.values())

    def __len__(self) -> int:
        """Get number of chunks."""
        return len(self._chunks)


class RAGPipeline:
    """Main RAG Pipeline orchestrating all retrieval components.

    Provides:
    - Document ingestion (parse, chunk, index)
    - Hybrid retrieval (sparse + dense + fusion)
    - Cross-encoder reranking
    - Context assembly for LLM

    Attributes:
        store: Document store
        chunker: Document chunker
        sparse_retriever: BM25 retriever
        dense_retriever: Vector retriever (optional)
        reranker: Cross-encoder reranker (optional)
        use_hybrid: Enable hybrid retrieval
        use_reranking: Enable cross-encoder reranking

    Example:
        >>> pipeline = RAGPipeline()
        >>> chunks = await pipeline.ingest([doc1, doc2])
        >>> results = await pipeline.query("What are visa requirements?")
    """

    def __init__(
        self,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        chunk_size: int = 1000,
        use_hybrid: bool = True,
        use_reranking: bool = False,
        reranker_model: str = "BAAI/bge-reranker-base",
        sparse_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> None:
        """Initialize RAG Pipeline.

        Args:
            chunking_strategy: Strategy for document chunking
            chunk_size: Target chunk size in characters
            use_hybrid: Enable hybrid retrieval (sparse + dense)
            use_reranking: Enable cross-encoder reranking
            reranker_model: HuggingFace model for reranking
            sparse_weight: Weight for sparse (BM25) retrieval
            dense_weight: Weight for dense (vector) retrieval

        Example:
            >>> # Basic pipeline
            >>> pipeline = RAGPipeline()
            >>>
            >>> # Full pipeline with reranking
            >>> pipeline = RAGPipeline(
            ...     use_hybrid=True,
            ...     use_reranking=True,
            ...     reranker_model="BAAI/bge-reranker-large"
            ... )
        """
        self.store = DocumentStore()
        self.chunker = create_chunker(strategy=chunking_strategy, chunk_size=chunk_size)

        self.use_hybrid = use_hybrid
        self.use_reranking = use_reranking
        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight

        # Initialize components lazily
        self._sparse_retriever: BM25Retriever | None = None
        self._dense_retriever: Any = None  # Vector store
        self._hybrid_retriever: HybridRetriever | None = None
        self._reranker: CrossEncoderReranker | None = None
        self._fusion = ReciprocalRankFusion()

        if use_reranking:
            self._reranker = CrossEncoderReranker(model_name=reranker_model)

        # Statistics
        self._stats = {
            "documents_ingested": 0,
            "chunks_created": 0,
            "queries_processed": 0,
            "avg_query_time_ms": 0.0,
        }

        self.logger = logger.bind(component="rag_pipeline")

    async def ingest(
        self,
        documents: list[Document],
        rebuild_index: bool = True,
    ) -> list[DocumentChunk]:
        """Ingest documents into the pipeline.

        Args:
            documents: List of documents to ingest
            rebuild_index: Whether to rebuild search indices

        Returns:
            List of created document chunks

        Example:
            >>> docs = [Document(text="Document 1..."), Document(text="Document 2...")]
            >>> chunks = await pipeline.ingest(docs)
            >>> print(f"Created {len(chunks)} chunks")
        """
        self.logger.info("ingest_start", document_count=len(documents))
        start_time = time.time()

        all_chunks: list[DocumentChunk] = []

        for doc in documents:
            # Store document
            self.store.add_document(doc)

            # Chunk document
            chunks = self.chunker.chunk_text(
                text=doc.text,
                doc_id=doc.doc_id,
                base_metadata=doc.metadata,
            )

            # Store chunks
            self.store.add_chunks(chunks, doc.doc_id)
            all_chunks.extend(chunks)

            self._stats["documents_ingested"] += 1
            self._stats["chunks_created"] += len(chunks)

        # Rebuild indices if requested
        if rebuild_index and all_chunks:
            await self._rebuild_indices()

        elapsed = (time.time() - start_time) * 1000
        self.logger.info(
            "ingest_complete",
            chunks_created=len(all_chunks),
            elapsed_ms=elapsed,
        )

        return all_chunks

    async def _rebuild_indices(self) -> None:
        """Rebuild all search indices."""
        texts = self.store.get_all_texts()

        if not texts:
            return

        # Rebuild BM25 index
        self._sparse_retriever = BM25Retriever(documents=texts)

        # If hybrid enabled and dense retriever available, rebuild hybrid
        if self.use_hybrid and self._dense_retriever is not None:
            self._hybrid_retriever = HybridRetriever(
                sparse_retriever=self._sparse_retriever,
                dense_retriever=self._dense_retriever,
                sparse_weight=self.sparse_weight,
                dense_weight=self.dense_weight,
            )

        self.logger.info("indices_rebuilt", document_count=len(texts))

    def set_dense_retriever(self, dense_retriever: Any) -> None:
        """Set dense retriever for hybrid search.

        Args:
            dense_retriever: Vector-based retriever with asearch() method

        Example:
            >>> from core.memory.stores.semantic_store import SemanticMemoryStore
            >>> pipeline.set_dense_retriever(SemanticMemoryStore())
        """
        self._dense_retriever = dense_retriever

        # Rebuild hybrid retriever if sparse is ready
        if self._sparse_retriever is not None and self.use_hybrid:
            self._hybrid_retriever = HybridRetriever(
                sparse_retriever=self._sparse_retriever,
                dense_retriever=dense_retriever,
                sparse_weight=self.sparse_weight,
                dense_weight=self.dense_weight,
            )

    async def query(
        self,
        query: str,
        top_k: int = 10,
        rerank_top_k: int = 50,
    ) -> dict[str, Any]:
        """Query the RAG pipeline.

        Args:
            query: Search query string
            top_k: Number of final results to return
            rerank_top_k: Number of candidates for reranking

        Returns:
            Dictionary with:
                - results: List of RAGResult objects
                - context: Assembled context for LLM
                - query_time_ms: Query processing time

        Example:
            >>> result = await pipeline.query("What are EB-1A requirements?")
            >>> for r in result["results"]:
            ...     print(f"{r.score:.2f}: {r.text[:50]}...")
        """
        if self._sparse_retriever is None:
            return {"results": [], "context": None, "query_time_ms": 0}

        self.logger.info("query_start", query=query[:100], top_k=top_k)
        start_time = time.time()

        # Step 1: Retrieve candidates
        if self._hybrid_retriever is not None:
            # Hybrid retrieval (sparse + dense + RRF fusion)
            raw_results = await self._hybrid_retriever.search(
                query=query,
                top_k=rerank_top_k if self.use_reranking else top_k,
            )
        else:
            # Sparse-only retrieval
            raw_results = await self._sparse_retriever.asearch(
                query=query,
                top_k=rerank_top_k if self.use_reranking else top_k,
            )

        # Convert to chunk IDs and scores
        chunk_ids = self.store.get_chunk_ids()
        texts = self.store.get_all_texts()

        # Map text back to chunk_id
        text_to_chunk: dict[str, str] = {}
        for cid, text in zip(chunk_ids, texts, strict=False):
            text_to_chunk[text] = cid

        # Build candidates for reranking
        candidates: list[tuple[str, float, str]] = []
        for text, score in raw_results:
            chunk_id = text_to_chunk.get(text, "")
            if chunk_id:
                candidates.append((chunk_id, score, text))

        # Step 2: Rerank if enabled
        if self.use_reranking and self._reranker and candidates:
            reranked = await self._reranker.rerank(
                query=query,
                candidates=candidates,
                top_k=top_k,
            )
            final_results = list(reranked)
        else:
            final_results = candidates[:top_k]

        # Step 3: Build RAGResult objects
        results: list[RAGResult] = []
        for chunk_id, score, content in final_results:
            chunk = self.store.get_chunk(chunk_id)
            metadata = chunk.metadata if chunk else {}
            results.append(
                RAGResult(
                    chunk_id=chunk_id,
                    text=content,
                    score=float(score),
                    metadata=metadata,
                )
            )

        # Step 4: Assemble context
        context = self._assemble_context(query, results)

        # Update stats
        elapsed_ms = (time.time() - start_time) * 1000
        self._stats["queries_processed"] += 1
        self._update_avg_query_time(elapsed_ms)

        self.logger.info(
            "query_complete",
            results_count=len(results),
            elapsed_ms=elapsed_ms,
        )

        return {
            "results": results,
            "context": context,
            "query_time_ms": elapsed_ms,
        }

    def _assemble_context(
        self,
        query: str,
        results: list[RAGResult],
    ) -> dict[str, Any]:
        """Assemble context for LLM from results.

        Args:
            query: Original query
            results: Retrieved results

        Returns:
            Context dictionary with text and metadata
        """
        if not results:
            return {"text": "", "sources": [], "query": query}

        # Build context text
        context_parts = []
        sources = []

        for i, result in enumerate(results, 1):
            context_parts.append(f"[{i}] {result.text}")
            sources.append(
                {
                    "index": i,
                    "chunk_id": result.chunk_id,
                    "score": result.score,
                    "metadata": result.metadata,
                }
            )

        return {
            "text": "\n\n".join(context_parts),
            "sources": sources,
            "query": query,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    def _update_avg_query_time(self, elapsed_ms: float) -> None:
        """Update average query time with exponential moving average."""
        alpha = 0.1
        self._stats["avg_query_time_ms"] = (
            alpha * elapsed_ms + (1 - alpha) * self._stats["avg_query_time_ms"]
        )

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics.

        Returns:
            Dictionary with pipeline stats

        Example:
            >>> stats = pipeline.get_stats()
            >>> print(f"Processed {stats['queries_processed']} queries")
        """
        return {
            **self._stats,
            "store_size": len(self.store),
            "hybrid_enabled": self.use_hybrid,
            "reranking_enabled": self.use_reranking,
        }

    async def clear(self) -> None:
        """Clear all data and indices."""
        self.store = DocumentStore()
        self._sparse_retriever = None
        self._hybrid_retriever = None
        self._stats = {
            "documents_ingested": 0,
            "chunks_created": 0,
            "queries_processed": 0,
            "avg_query_time_ms": 0.0,
        }
        self.logger.info("pipeline_cleared")


async def create_rag_pipeline(
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    chunk_size: int = 1000,
    use_hybrid: bool = True,
    use_reranking: bool = False,
) -> RAGPipeline:
    """Factory function to create RAG pipeline.

    Args:
        chunking_strategy: Chunking strategy
        chunk_size: Target chunk size
        use_hybrid: Enable hybrid retrieval
        use_reranking: Enable reranking

    Returns:
        Initialized RAGPipeline instance

    Example:
        >>> pipeline = await create_rag_pipeline(
        ...     use_hybrid=True,
        ...     use_reranking=True
        ... )
    """
    return RAGPipeline(
        chunking_strategy=chunking_strategy,
        chunk_size=chunk_size,
        use_hybrid=use_hybrid,
        use_reranking=use_reranking,
    )


__all__ = [
    "Document",
    "DocumentStore",
    "RAGPipeline",
    "RAGResult",
    "create_rag_pipeline",
]
