"""Graph-Enhanced RAG for Knowledge-Augmented Retrieval.

Combines vector retrieval with graph traversal for enhanced context:
- Entity-aware retrieval
- Graph-guided expansion
- Multi-hop reasoning
- Community-based summarization
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any

from .graph_constructor import (
    Entity,
    EntityType,
    KnowledgeGraph,
    Relation,
    RelationType,
)

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    """Graph RAG retrieval modes."""

    LOCAL = "local"  # Retrieve from local neighborhood
    GLOBAL = "global"  # Use community summaries
    HYBRID = "hybrid"  # Combine local and global
    MULTI_HOP = "multi_hop"  # Follow relation chains


@dataclass
class GraphContext:
    """Context retrieved from knowledge graph."""

    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    text_chunks: list[str] = field(default_factory=list)
    community_summaries: list[str] = field(default_factory=list)
    relevance_scores: dict[str, float] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert to text for LLM prompt."""
        parts = []

        if self.entities:
            entity_text = "Relevant Entities:\n"
            for e in self.entities[:10]:  # Limit entities
                entity_text += f"- {e.name} ({e.entity_type.value})\n"
            parts.append(entity_text)

        if self.relations:
            relation_text = "Key Relationships:\n"
            for r in self.relations[:10]:  # Limit relations
                parts.append(f"- {r.source_id} --[{r.relation_type.value}]--> {r.target_id}")
            parts.append(relation_text)

        if self.community_summaries:
            summary_text = "Topic Summaries:\n"
            for s in self.community_summaries[:3]:
                summary_text += f"- {s}\n"
            parts.append(summary_text)

        if self.text_chunks:
            chunk_text = "Relevant Text:\n"
            for chunk in self.text_chunks[:5]:
                chunk_text += f"---\n{chunk[:500]}...\n"
            parts.append(chunk_text)

        return "\n\n".join(parts)


@dataclass
class GraphRAGResult:
    """Result from Graph RAG retrieval."""

    query: str
    context: GraphContext
    mode: RetrievalMode
    hops: int = 0
    retrieval_time_ms: float = 0
    entities_found: int = 0
    relations_found: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode.value,
            "hops": self.hops,
            "retrieval_time_ms": self.retrieval_time_ms,
            "entities_found": self.entities_found,
            "relations_found": self.relations_found,
        }


class GraphRAG:
    """Graph-enhanced Retrieval Augmented Generation."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        vector_retriever: (
            Callable[[str, int], Coroutine[Any, Any, list[tuple[str, float]]]] | None
        ) = None,
        embedder: Callable[[str], Coroutine[Any, Any, list[float]]] | None = None,
        entity_matcher: Callable[[str, list[Entity]], list[Entity]] | None = None,
    ):
        self.graph = graph
        self.vector_retriever = vector_retriever
        self.embedder = embedder
        self.entity_matcher = entity_matcher or self._default_entity_matcher

        self._stats = {
            "queries_processed": 0,
            "avg_entities_retrieved": 0,
            "avg_relations_retrieved": 0,
        }

    def _default_entity_matcher(
        self,
        query: str,
        entities: list[Entity],
    ) -> list[Entity]:
        """Simple keyword-based entity matching."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        matched = []
        for entity in entities:
            entity_words = set(entity.name.lower().split())
            if query_words & entity_words:
                matched.append(entity)

        return matched

    async def retrieve(
        self,
        query: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 10,
        max_hops: int = 2,
        entity_types: list[EntityType] | None = None,
        relation_types: list[RelationType] | None = None,
    ) -> GraphRAGResult:
        """Retrieve context using graph-enhanced RAG."""
        import time

        start_time = time.monotonic()

        context = GraphContext()

        if mode == RetrievalMode.LOCAL:
            context = await self._local_retrieval(
                query, top_k, max_hops, entity_types, relation_types
            )
        elif mode == RetrievalMode.GLOBAL:
            context = await self._global_retrieval(query, top_k)
        elif mode == RetrievalMode.MULTI_HOP:
            context = await self._multi_hop_retrieval(
                query, top_k, max_hops, entity_types, relation_types
            )
        else:  # HYBRID
            local_ctx = await self._local_retrieval(
                query, top_k // 2, max_hops, entity_types, relation_types
            )
            global_ctx = await self._global_retrieval(query, top_k // 2)
            context = self._merge_contexts(local_ctx, global_ctx)

        retrieval_time = (time.monotonic() - start_time) * 1000

        # Update stats
        self._stats["queries_processed"] += 1
        self._update_avg_stats(len(context.entities), len(context.relations))

        return GraphRAGResult(
            query=query,
            context=context,
            mode=mode,
            hops=max_hops,
            retrieval_time_ms=retrieval_time,
            entities_found=len(context.entities),
            relations_found=len(context.relations),
        )

    async def _local_retrieval(
        self,
        query: str,
        top_k: int,
        max_hops: int,
        entity_types: list[EntityType] | None,
        relation_types: list[RelationType] | None,
    ) -> GraphContext:
        """Local neighborhood retrieval."""
        context = GraphContext()

        # Find seed entities from query
        all_entities = list(self.graph._entities.values())
        if entity_types:
            all_entities = [e for e in all_entities if e.entity_type in entity_types]

        seed_entities = self.entity_matcher(query, all_entities)

        if not seed_entities:
            # Fall back to vector retrieval if available
            if self.vector_retriever:
                doc_results = await self.vector_retriever(query, top_k)
                context.text_chunks = [doc for doc, _ in doc_results]
            return context

        # Expand from seed entities
        context.entities = seed_entities[:top_k]
        seen_entity_ids = {e.id for e in context.entities}

        for seed in seed_entities[:5]:  # Limit expansion seeds
            neighbors = self.graph.get_neighbors(
                seed.id,
                relation_types=relation_types,
                max_hops=max_hops,
            )
            for neighbor in neighbors:
                if neighbor.id not in seen_entity_ids and len(context.entities) < top_k:
                    context.entities.append(neighbor)
                    seen_entity_ids.add(neighbor.id)

        # Get relations between entities
        entity_ids = [e.id for e in context.entities]
        _, relations = self.graph.get_subgraph(entity_ids, max_hops=1)
        context.relations = relations[:top_k]

        # Calculate relevance scores
        for entity in context.entities:
            context.relevance_scores[entity.id] = self._calculate_relevance(query, entity)

        return context

    async def _global_retrieval(
        self,
        query: str,
        top_k: int,
    ) -> GraphContext:
        """Global community-based retrieval."""
        context = GraphContext()

        # Get community summaries
        for community in self.graph._communities.values():
            if community.summary:
                context.community_summaries.append(community.summary)

        # Also retrieve relevant text chunks if vector retriever available
        if self.vector_retriever:
            doc_results = await self.vector_retriever(query, top_k)
            context.text_chunks = [doc for doc, _ in doc_results]

        return context

    async def _multi_hop_retrieval(
        self,
        query: str,
        top_k: int,
        max_hops: int,
        entity_types: list[EntityType] | None,
        relation_types: list[RelationType] | None,
    ) -> GraphContext:
        """Multi-hop reasoning retrieval."""
        context = GraphContext()

        # Parse query to identify relation chain
        # Simplified: just do iterative expansion
        all_entities = list(self.graph._entities.values())
        seed_entities = self.entity_matcher(query, all_entities)

        if not seed_entities:
            return context

        # BFS expansion
        current_level = {e.id for e in seed_entities[:3]}
        all_entity_ids: set[str] = set(current_level)
        paths: list[list[str]] = [[eid] for eid in current_level]

        for _hop in range(max_hops):
            next_level: set[str] = set()
            new_paths: list[list[str]] = []

            for eid in current_level:
                neighbors = self.graph.get_neighbors(
                    eid,
                    relation_types=relation_types,
                    max_hops=1,
                )
                for neighbor in neighbors:
                    if neighbor.id not in all_entity_ids:
                        next_level.add(neighbor.id)
                        all_entity_ids.add(neighbor.id)
                        # Track path
                        for path in paths:
                            if path[-1] == eid:
                                new_paths.append([*path, neighbor.id])

            current_level = next_level
            paths.extend(new_paths)

            if len(all_entity_ids) >= top_k:
                break

        # Collect entities
        context.entities = [
            self.graph._entities[eid]
            for eid in list(all_entity_ids)[:top_k]
            if eid in self.graph._entities
        ]

        # Get relations
        _, relations = self.graph.get_subgraph(list(all_entity_ids)[:top_k], max_hops=1)
        context.relations = relations

        return context

    def _merge_contexts(
        self,
        ctx1: GraphContext,
        ctx2: GraphContext,
    ) -> GraphContext:
        """Merge two contexts."""
        merged = GraphContext()

        # Deduplicate entities
        seen_ids: set[str] = set()
        for entity in ctx1.entities + ctx2.entities:
            if entity.id not in seen_ids:
                merged.entities.append(entity)
                seen_ids.add(entity.id)

        # Deduplicate relations
        seen_rel_ids: set[str] = set()
        for relation in ctx1.relations + ctx2.relations:
            if relation.id not in seen_rel_ids:
                merged.relations.append(relation)
                seen_rel_ids.add(relation.id)

        # Combine text chunks and summaries
        merged.text_chunks = ctx1.text_chunks + ctx2.text_chunks
        merged.community_summaries = ctx1.community_summaries + ctx2.community_summaries

        # Merge relevance scores
        merged.relevance_scores = {**ctx1.relevance_scores, **ctx2.relevance_scores}

        return merged

    def _calculate_relevance(self, query: str, entity: Entity) -> float:
        """Calculate relevance score for an entity."""
        query_lower = query.lower()
        entity_name_lower = entity.name.lower()

        # Simple keyword overlap
        query_words = set(query_lower.split())
        entity_words = set(entity_name_lower.split())

        overlap = len(query_words & entity_words)
        total = len(query_words | entity_words)

        return overlap / total if total > 0 else 0.0

    def _update_avg_stats(self, entities: int, relations: int) -> None:
        """Update running average statistics."""
        n = self._stats["queries_processed"]
        if n == 1:
            self._stats["avg_entities_retrieved"] = entities
            self._stats["avg_relations_retrieved"] = relations
        else:
            # Running average
            self._stats["avg_entities_retrieved"] = (
                self._stats["avg_entities_retrieved"] * (n - 1) + entities
            ) / n
            self._stats["avg_relations_retrieved"] = (
                self._stats["avg_relations_retrieved"] * (n - 1) + relations
            ) / n

    def get_stats(self) -> dict[str, Any]:
        """Get retrieval statistics."""
        return {
            **self._stats,
            "graph_stats": self.graph.get_stats(),
        }


class GraphRAGPipeline:
    """Complete pipeline combining graph construction and retrieval."""

    def __init__(
        self,
        graph_rag: GraphRAG,
        llm_caller: Callable[[str, str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.graph_rag = graph_rag
        self.llm_caller = llm_caller

    async def query(
        self,
        question: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 10,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        """Execute complete RAG pipeline."""
        # Retrieve context
        result = await self.graph_rag.retrieve(
            question,
            mode=mode,
            top_k=top_k,
            max_hops=max_hops,
        )

        # Format context
        context_text = result.context.to_prompt_context()

        # Generate answer if LLM available
        answer = None
        if self.llm_caller:
            prompt = f"""Based on the following context, answer the question.

Context:
{context_text}

Question: {question}

Answer:"""
            answer = await self.llm_caller("system", prompt)

        return {
            "question": question,
            "answer": answer,
            "context": context_text,
            "retrieval_result": result.to_dict(),
        }


# Factory functions
def create_graph_rag(
    graph: KnowledgeGraph,
    vector_retriever: (
        Callable[[str, int], Coroutine[Any, Any, list[tuple[str, float]]]] | None
    ) = None,
) -> GraphRAG:
    """Create a Graph RAG instance."""
    return GraphRAG(graph=graph, vector_retriever=vector_retriever)


__all__ = [
    "GraphContext",
    "GraphRAG",
    "GraphRAGPipeline",
    "GraphRAGResult",
    "RetrievalMode",
    "create_graph_rag",
]
