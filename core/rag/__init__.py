"""
RAG (Retrieval-Augmented Generation) pipeline components.

This module provides:
- Main RAG pipeline orchestration
- Sparse retrieval (BM25)
- Hybrid search (Dense + Sparse)
- Cross-encoder reranking
- Contextual chunking
- Document parsing
- Memory store adapters

Phase 3: Hybrid RAG Pipeline
"""

from __future__ import annotations

from .adapters import (MemoryManagerAdapter, SemanticStoreAdapter,
                       create_memory_adapter)
from .chunking import (ChunkingStrategy, ContextualChunker, DocumentChunk,
                       FixedSizeChunker, RecursiveChunker, SemanticChunker,
                       create_chunker)
from .document_parser import (DocumentFormat, DocumentIngestionPipeline,
                              MarkitdownParser, ParsedDocument,
                              create_document_parser)
from .fusion import (HybridRetriever, ReciprocalRankFusion,
                     create_hybrid_retriever)
from .pipeline import (Document, DocumentStore, RAGPipeline, RAGResult,
                       create_rag_pipeline)
from .reranker import (CrossEncoderReranker, HybridRetrieverWithReranking,
                       create_reranker)
from .sparse_retrieval import BM25Retriever, create_bm25_retriever

__all__ = [
    "BM25Retriever",
    "ChunkingStrategy",
    "ContextualChunker",
    "CrossEncoderReranker",
    "Document",
    "DocumentChunk",
    "DocumentFormat",
    "DocumentIngestionPipeline",
    "DocumentStore",
    "FixedSizeChunker",
    "HybridRetriever",
    "HybridRetrieverWithReranking",
    "MarkitdownParser",
    "MemoryManagerAdapter",
    "ParsedDocument",
    "RAGPipeline",
    "RAGResult",
    "ReciprocalRankFusion",
    "RecursiveChunker",
    "SemanticChunker",
    "SemanticStoreAdapter",
    "create_bm25_retriever",
    "create_chunker",
    "create_document_parser",
    "create_hybrid_retriever",
    "create_memory_adapter",
    "create_rag_pipeline",
    "create_reranker",
]
