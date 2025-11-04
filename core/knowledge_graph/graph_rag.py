"""Graph-Enhanced RAG Query System.

This module integrates knowledge graphs with vector search for enhanced retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .graph_store import GraphStore


@dataclass
class GraphRAGResult:
    """Result from graph-enhanced RAG query."""

    query: str
    direct_results: list[dict[str, Any]]
    graph_expanded: list[dict[str, Any]]
    reranked_results: list[dict[str, Any]]
    graph_context: dict[str, Any]
    metadata: dict[str, Any]


class GraphRAGQuery:
    """
    Graph-enhanced RAG query system.

    Combines vector search with knowledge graph traversal
    to provide context-aware retrieval.

    Features:
    - Entity extraction from queries
    - Graph-based query expansion
    - Result re-ranking using graph relationships
    - Multi-hop reasoning

    Example:
        >>> query_system = GraphRAGQuery(graph_store)
        >>> results = await query_system.query("Tell me about John Doe")
    """

    def __init__(
        self,
        graph_store: GraphStore,
        vector_retriever: Any | None = None,
    ):
        """
        Initialize graph RAG query system.

        Args:
            graph_store: Knowledge graph store
            vector_retriever: Optional vector search retriever
        """
        self.graph_store = graph_store
        self.vector_retriever = vector_retriever

    async def query(
        self,
        query: str,
        top_k: int = 10,
        expand_hops: int = 2,
        rerank: bool = True,
    ) -> GraphRAGResult:
        """
        Execute graph-enhanced RAG query.

        Args:
            query: User query
            top_k: Number of results to return
            expand_hops: Maximum hops for graph expansion
            rerank: Whether to rerank results using graph

        Returns:
            GraphRAGResult with enhanced results
        """
        # Extract entities from query
        query_entities = self._extract_query_entities(query)

        # Get direct vector search results
        direct_results = []
        if self.vector_retriever:
            direct_results = await self._vector_search(query, top_k)

        # Expand query using graph
        graph_expanded = self._expand_with_graph(
            query_entities,
            expand_hops,
            top_k,
        )

        # Get graph context
        graph_context = self._build_graph_context(query_entities, expand_hops)

        # Combine and rerank
        combined = self._combine_results(direct_results, graph_expanded)

        if rerank:
            reranked = self._rerank_with_graph(
                combined,
                query_entities,
                graph_context,
            )
        else:
            reranked = combined[:top_k]

        return GraphRAGResult(
            query=query,
            direct_results=direct_results,
            graph_expanded=graph_expanded,
            reranked_results=reranked[:top_k],
            graph_context=graph_context,
            metadata={
                "query_entities": query_entities,
                "expand_hops": expand_hops,
                "reranked": rerank,
            },
        )

    def _extract_query_entities(self, query: str) -> list[str]:
        """
        Extract entities from query.

        In production, would use NER model.
        For now, simple pattern matching.
        """
        # Simple capitalized word detection
        import re

        words = query.split()
        entities = []

        # Look for capitalized sequences
        current_entity = []
        for word in words:
            clean = re.sub(r"[^\w\s]", "", word)
            if clean and clean[0].isupper():
                current_entity.append(clean)
            elif current_entity:
                entities.append(" ".join(current_entity))
                current_entity = []

        if current_entity:
            entities.append(" ".join(current_entity))

        return entities

    async def _vector_search(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Execute vector search."""
        if not self.vector_retriever:
            return []

        # Call vector retriever
        # Implementation depends on vector store
        results = await self.vector_retriever.search(query, top_k)

        return results

    def _expand_with_graph(
        self,
        entities: list[str],
        max_hops: int,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Expand query using graph traversal.

        Finds related entities and their context.
        """
        expanded = []

        for entity in entities:
            # Normalize entity
            entity_norm = entity.strip().lower()

            # Find in graph
            for node_id, attrs in self.graph_store.graph.nodes(data=True):
                node_label = attrs.get("label", "").lower()

                if entity_norm in node_label or node_label in entity_norm:
                    # Get related entities
                    related = self.graph_store.get_related_entities(
                        node_id,
                        max_hops,
                    )

                    # Build context
                    for rel_id in related:
                        rel_attrs = self.graph_store.get_node(rel_id)
                        if rel_attrs:
                            expanded.append(
                                {
                                    "entity": rel_attrs.get("label"),
                                    "type": rel_attrs.get("node_type"),
                                    "source_entity": entity,
                                    "hops": related[rel_id],
                                    "node_id": rel_id,
                                },
                            )

        # Sort by hops (closer entities first)
        expanded.sort(key=lambda x: x.get("hops", 999))

        return expanded[:top_k]

    def _build_graph_context(
        self,
        entities: list[str],
        max_hops: int,
    ) -> dict[str, Any]:
        """Build graph context for entities."""
        context: dict[str, Any] = {
            "entities": {},
            "relationships": [],
            "subgraph_stats": {},
        }

        for entity in entities:
            entity_norm = entity.strip().lower()

            # Find entity in graph
            for node_id, attrs in self.graph_store.graph.nodes(data=True):
                node_label = attrs.get("label", "").lower()

                if entity_norm in node_label or node_label in entity_norm:
                    # Get neighbors
                    neighbors = self.graph_store.get_neighbors(node_id)

                    # Get relationships
                    for neighbor_id in neighbors:
                        edges = self.graph_store.graph[node_id][neighbor_id]
                        for relation in edges:
                            neighbor_attrs = self.graph_store.get_node(
                                neighbor_id,
                            )
                            context["relationships"].append(
                                {
                                    "subject": attrs.get("label"),
                                    "relation": relation,
                                    "object": (
                                        neighbor_attrs.get("label")
                                        if neighbor_attrs
                                        else neighbor_id
                                    ),
                                },
                            )

                    # Store entity context
                    context["entities"][entity] = {
                        "node_id": node_id,
                        "label": attrs.get("label"),
                        "type": attrs.get("node_type"),
                        "neighbors_count": len(neighbors),
                    }

        return context

    def _combine_results(
        self,
        direct: list[dict[str, Any]],
        graph: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Combine vector and graph results."""
        combined = []

        # Add direct results with high score
        for result in direct:
            result["source"] = "vector"
            result["base_score"] = result.get("score", 0.8)
            combined.append(result)

        # Add graph results with medium score
        for result in graph:
            # Check if not already in combined
            is_duplicate = False
            for existing in combined:
                if existing.get("entity") == result.get("entity"):
                    is_duplicate = True
                    break

            if not is_duplicate:
                result["source"] = "graph"
                # Score based on hop distance
                hops = result.get("hops", 2)
                result["base_score"] = max(0.5 - (hops * 0.1), 0.1)
                combined.append(result)

        return combined

    def _rerank_with_graph(
        self,
        results: list[dict[str, Any]],
        query_entities: list[str],
        graph_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Rerank results using graph relationships.

        Boosts results that have strong connections
        to query entities in the graph.
        """
        for result in results:
            base_score = result.get("base_score", 0.5)

            # Boost if entity appears in graph context
            entity = result.get("entity", "")
            boost = 0.0

            # Check relationships
            for rel in graph_context.get("relationships", []):
                if entity in [rel["subject"], rel["object"]]:
                    boost += 0.1

            # Check direct entity match
            if entity in graph_context.get("entities", {}):
                boost += 0.2

            result["graph_boost"] = boost
            result["final_score"] = base_score + boost

        # Sort by final score
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        return results

    def get_entity_subgraph(
        self,
        entity: str,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        """
        Extract subgraph around entity.

        Useful for visualization and context display.

        Args:
            entity: Entity to center subgraph on
            max_hops: Maximum distance from entity

        Returns:
            Subgraph data (nodes, edges)
        """
        entity_norm = entity.strip().lower()

        # Find entity node
        entity_node = None
        for node_id, attrs in self.graph_store.graph.nodes(data=True):
            node_label = attrs.get("label", "").lower()
            if entity_norm in node_label or node_label in entity_norm:
                entity_node = node_id
                break

        if not entity_node:
            return {"nodes": [], "edges": [], "found": False}

        # Get subgraph
        subgraph = self.graph_store.get_subgraph([entity_node], max_hops)

        # Convert to serializable format
        nodes = []
        edges = []

        for node_id, attrs in subgraph.nodes(data=True):
            nodes.append(
                {
                    "id": node_id,
                    "label": attrs.get("label"),
                    "type": attrs.get("node_type"),
                },
            )

        for source, target, attrs in subgraph.edges(data=True):
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": attrs.get("relation"),
                },
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "found": True,
            "center_entity": entity,
        }

    def explain_result(
        self,
        result: dict[str, Any],
        query: str,
    ) -> str:
        """
        Generate explanation for why result was retrieved.

        Args:
            result: RAG result
            query: Original query

        Returns:
            Human-readable explanation
        """
        explanation_parts = []

        # Source
        source = result.get("source", "unknown")
        explanation_parts.append(f"Retrieved from {source} search")

        # Score breakdown
        base_score = result.get("base_score", 0)
        graph_boost = result.get("graph_boost", 0)
        final_score = result.get("final_score", base_score)

        explanation_parts.append(
            f"Base relevance: {base_score:.2f}",
        )

        if graph_boost > 0:
            explanation_parts.append(
                f"Graph relationship boost: +{graph_boost:.2f}",
            )

        explanation_parts.append(f"Final score: {final_score:.2f}")

        # Entity connections
        if result.get("source") == "graph":
            source_entity = result.get("source_entity")
            hops = result.get("hops", "unknown")
            if source_entity:
                explanation_parts.append(
                    f"Connected to '{source_entity}' via {hops} hop(s) in knowledge graph",
                )

        return ". ".join(explanation_parts) + "."


class HybridRAG:
    """
    Hybrid RAG system combining multiple retrieval strategies.

    Strategies:
    - Dense vector search (semantic similarity)
    - Sparse keyword search (BM25)
    - Knowledge graph traversal
    - Hybrid fusion

    Example:
        >>> hybrid = HybridRAG(vector_store, bm25_index, graph_store)
        >>> results = await hybrid.retrieve(query, strategy="hybrid")
    """

    def __init__(
        self,
        vector_store: Any | None = None,
        bm25_index: Any | None = None,
        graph_store: GraphStore | None = None,
    ):
        """
        Initialize hybrid RAG system.

        Args:
            vector_store: Dense vector retriever
            bm25_index: Sparse keyword retriever
            graph_store: Knowledge graph
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.graph_rag = GraphRAGQuery(graph_store) if graph_store else None

    async def retrieve(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Retrieve using specified strategy.

        Args:
            query: User query
            strategy: Retrieval strategy (dense, sparse, graph, hybrid)
            top_k: Number of results
            **kwargs: Additional parameters

        Returns:
            Retrieved results
        """
        if strategy == "dense":
            return await self._dense_retrieve(query, top_k)
        if strategy == "sparse":
            return await self._sparse_retrieve(query, top_k)
        if strategy == "graph":
            return await self._graph_retrieve(query, top_k)
        if strategy == "hybrid":
            return await self._hybrid_retrieve(query, top_k, **kwargs)

        msg = f"Unknown strategy: {strategy}"
        raise ValueError(msg)

    async def _dense_retrieve(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Dense vector search."""
        if not self.vector_store:
            return []

        results = await self.vector_store.search(query, top_k)
        for r in results:
            r["retrieval_method"] = "dense"
        return results

    async def _sparse_retrieve(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Sparse keyword search (BM25)."""
        if not self.bm25_index:
            return []

        results = self.bm25_index.search(query, top_k)
        for r in results:
            r["retrieval_method"] = "sparse"
        return results

    async def _graph_retrieve(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Graph-based retrieval."""
        if not self.graph_rag:
            return []

        result = await self.graph_rag.query(query, top_k)
        return result.reranked_results

    async def _hybrid_retrieve(
        self,
        query: str,
        top_k: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Hybrid retrieval with fusion.

        Combines dense, sparse, and graph retrieval
        using reciprocal rank fusion.
        """
        # Get results from all methods
        dense_results = await self._dense_retrieve(query, top_k * 2)
        sparse_results = await self._sparse_retrieve(query, top_k * 2)
        graph_results = await self._graph_retrieve(query, top_k * 2)

        # Reciprocal rank fusion
        fusion_scores: dict[str, float] = {}
        k = 60  # RRF constant

        def add_scores(results: list[dict[str, Any]]) -> None:
            for rank, result in enumerate(results):
                doc_id = result.get("id") or result.get("entity") or str(result)
                score = 1.0 / (k + rank + 1)
                fusion_scores[doc_id] = fusion_scores.get(doc_id, 0.0) + score

        add_scores(dense_results)
        add_scores(sparse_results)
        add_scores(graph_results)

        # Combine all results
        all_results = dense_results + sparse_results + graph_results

        # Deduplicate and add fusion scores
        seen = set()
        fused = []
        for result in all_results:
            doc_id = result.get("id") or result.get("entity") or str(result)
            if doc_id not in seen:
                seen.add(doc_id)
                result["fusion_score"] = fusion_scores.get(doc_id, 0.0)
                fused.append(result)

        # Sort by fusion score
        fused.sort(key=lambda x: x["fusion_score"], reverse=True)

        return fused[:top_k]
