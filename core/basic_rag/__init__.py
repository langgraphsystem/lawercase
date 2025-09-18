"""
Basic RAG Foundation для mega_agent_pro.

Provides essential RAG (Retrieval-Augmented Generation) functionality:
- Document ingestion и processing
- Vector storage и retrieval
- Simple semantic search
- LLM integration for generation
- Document chunking strategies
- Basic query processing
- RAG pipeline orchestration
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core RAG Components
    "BasicRAG",
    "DocumentProcessor",
    "VectorStore",
    "QueryProcessor",
    "RAGPipeline",

    # Models
    "Document",
    "DocumentChunk",
    "RAGQuery",
    "RAGResponse",
    "SearchResult",

    # Enums
    "ChunkingStrategy",
    "SearchType",

    # Factory
    "create_basic_rag",
]

from .basic_rag import (
    BasicRAG,
    DocumentProcessor,
    VectorStore,
    QueryProcessor,
    RAGPipeline,
    Document,
    DocumentChunk,
    RAGQuery,
    RAGResponse,
    SearchResult,
    ChunkingStrategy,
    SearchType,
    create_basic_rag,
)