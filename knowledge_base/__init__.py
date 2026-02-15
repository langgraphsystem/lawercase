"""Knowledge Base Package.

Provides RAG and retrieval capabilities:
- HybridRetriever: Dense + Sparse + Graph retrieval
- ContextualChunker: Semantic document chunking
- CrossEncoderReranker: Reranking for improved relevance
- KnowledgeGraph: Entity and relation graph construction
- GraphRAG: Graph-enhanced retrieval augmented generation

Usage:
    from knowledge_base import (
        HybridRetriever,
        hybrid_search,
        chunk_document,
        rerank_documents,
        GraphConstructor,
        GraphRAG,
    )

    # Hybrid search
    results = await hybrid_search("EB-1A requirements", top_k=10)

    # Chunk document
    chunks = chunk_document(text, strategy=ChunkingStrategy.SEMANTIC)

    # Rerank results
    reranked = await rerank_documents(query, documents, top_k=5)

    # Knowledge Graph
    constructor = create_graph_constructor()
    graph = await constructor.construct_from_documents(docs)

    # Graph RAG
    graph_rag = create_graph_rag(graph)
    context = await graph_rag.retrieve(query, mode=RetrievalMode.HYBRID)
"""

from __future__ import annotations

from .contextual_chunking import (
    Chunk,
    ChunkingConfig,
    ChunkingResult,
    ChunkingStrategy,
    ContextualChunker,
    chunk_document,
    chunk_for_embedding,
)
from .cross_encoder_reranker import (
    CrossEncoderReranker,
    MultiStageReranker,
    RerankerConfig,
    RerankerModel,
    RerankResponse,
    RerankResult,
    create_reranker,
    rerank_documents,
)
from .entity_linker import (
    ContextAnalysisStrategy,
    CorefCluster,
    CorefResolver,
    DisambiguationMethod,
    DisambiguationStrategy,
    EmbeddingSimilarityStrategy,
    EntityCandidate,
    EntityLink,
    EntityLinker,
    EntityMention,
    EntityNormalizer,
    ExactMatchStrategy,
    FuzzyMatchStrategy,
    LinkConfidence,
    LLMDisambiguationStrategy,
    TypeConstraintStrategy,
    create_coref_resolver,
    create_entity_linker,
    create_normalizer,
)
from .graph_constructor import (
    Community,
    Entity,
    EntityExtractor,
    EntityType,
    GraphConstructor,
    KnowledgeGraph,
    Relation,
    RelationExtractor,
    RelationType,
    create_graph_constructor,
)
from .graph_rag import (
    GraphContext,
    GraphRAG,
    GraphRAGPipeline,
    GraphRAGResult,
    RetrievalMode,
    create_graph_rag,
)
from .hybrid_retrieval import (
    DenseRetriever,
    GraphRetriever,
    HybridConfig,
    HybridRetriever,
    HybridSearchResult,
    RetrievalResult,
    RetrievalStrategy,
    SparseRetriever,
    create_hybrid_retriever,
    hybrid_search,
)

__all__ = [
    "Chunk",
    "ChunkingConfig",
    "ChunkingResult",
    "ChunkingStrategy",
    "Community",
    "ContextAnalysisStrategy",
    # Contextual Chunking
    "ContextualChunker",
    "CorefCluster",
    "CorefResolver",
    # Reranking
    "CrossEncoderReranker",
    "DenseRetriever",
    "DisambiguationMethod",
    "DisambiguationStrategy",
    "EmbeddingSimilarityStrategy",
    "Entity",
    # Entity Linker
    "EntityCandidate",
    "EntityExtractor",
    "EntityLink",
    "EntityLinker",
    "EntityMention",
    "EntityNormalizer",
    # Knowledge Graph
    "EntityType",
    "ExactMatchStrategy",
    "FuzzyMatchStrategy",
    "GraphConstructor",
    "GraphContext",
    "GraphRAG",
    "GraphRAGPipeline",
    "GraphRAGResult",
    "GraphRetriever",
    "HybridConfig",
    # Hybrid Retrieval
    "HybridRetriever",
    "HybridSearchResult",
    "KnowledgeGraph",
    "LLMDisambiguationStrategy",
    "LinkConfidence",
    "MultiStageReranker",
    "Relation",
    "RelationExtractor",
    "RelationType",
    "RerankResponse",
    "RerankResult",
    "RerankerConfig",
    "RerankerModel",
    # Graph RAG
    "RetrievalMode",
    "RetrievalResult",
    "RetrievalStrategy",
    "SparseRetriever",
    "TypeConstraintStrategy",
    "chunk_document",
    "chunk_for_embedding",
    "create_coref_resolver",
    "create_entity_linker",
    "create_graph_constructor",
    "create_graph_rag",
    "create_hybrid_retriever",
    "create_normalizer",
    "create_reranker",
    "hybrid_search",
    "rerank_documents",
]
