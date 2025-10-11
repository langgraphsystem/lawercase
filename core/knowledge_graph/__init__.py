"""Knowledge Graph package: entities, storage, ingestion, retrieval.

This package provides a complete knowledge graph system with:
- Entity and relation extraction
- Graph storage and querying
- Graph-enhanced RAG
- Hybrid retrieval strategies
"""

from __future__ import annotations

from .entities import (EntityMention, KGEdge, KGNode, KnowledgeTriple,
                       RelationMention)
from .graph_constructor import (EntityExtractor, GraphConstructor,
                                RelationExtractor, get_graph_constructor)
from .graph_rag import GraphRAGQuery, GraphRAGResult, HybridRAG
from .graph_store import GraphStore, GraphStoreStats, Neo4jGraphStore

__all__ = [
    # Entities
    "KGNode",
    "KGEdge",
    "KnowledgeTriple",
    "EntityMention",
    "RelationMention",
    # Graph Store
    "GraphStore",
    "GraphStoreStats",
    "Neo4jGraphStore",
    # Construction
    "EntityExtractor",
    "RelationExtractor",
    "GraphConstructor",
    "get_graph_constructor",
    # RAG
    "GraphRAGQuery",
    "GraphRAGResult",
    "HybridRAG",
]
