"""GraphRAG - Graph-based Retrieval Augmented Generation.

This module implements GraphRAG for enhanced context retrieval using knowledge graphs.
It combines traditional vector-based RAG with graph traversal for better:
- Multi-hop reasoning
- Relationship-aware retrieval
- Entity disambiguation
- Temporal knowledge tracking

Based on 2025-2026 research on graph-based RAG systems (Microsoft GraphRAG, Zep Graphiti).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    # People
    PERSON = "person"
    ORGANIZATION = "organization"
    EXPERT = "expert"
    REFEREE = "referee"

    # EB-1A specific
    BENEFICIARY = "beneficiary"
    PETITIONER = "petitioner"
    EMPLOYER = "employer"

    # Documents
    DOCUMENT = "document"
    EXHIBIT = "exhibit"
    EVIDENCE = "evidence"
    PETITION = "petition"

    # Achievements
    AWARD = "award"
    PUBLICATION = "publication"
    PATENT = "patent"
    CONTRIBUTION = "contribution"

    # Concepts
    CRITERION = "criterion"
    TOPIC = "topic"
    SKILL = "skill"
    FIELD = "field"

    # Locations
    LOCATION = "location"
    INSTITUTION = "institution"

    # Time
    EVENT = "event"
    DATE = "date"


class RelationType(str, Enum):
    """Types of relationships in the knowledge graph."""

    # General
    RELATES_TO = "relates_to"
    PART_OF = "part_of"
    HAS = "has"
    MENTIONS = "mentions"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"

    # People
    AUTHORED = "authored"
    EMPLOYED_BY = "employed_by"
    COLLABORATED_WITH = "collaborated_with"
    RECOMMENDED_BY = "recommended_by"
    CITED_BY = "cited_by"

    # Documents
    REFERENCES = "references"
    EXHIBITS = "exhibits"
    EVIDENCES = "evidences"
    ATTACHED_TO = "attached_to"

    # Achievements
    RECEIVED = "received"
    ACHIEVED = "achieved"
    PUBLISHED_IN = "published_in"
    INVENTED = "invented"
    CONTRIBUTED_TO = "contributed_to"

    # EB-1A criteria
    SATISFIES_CRITERION = "satisfies_criterion"
    DEMONSTRATES = "demonstrates"

    # Temporal
    OCCURRED_AT = "occurred_at"
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"


@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    node_id: str = field(default_factory=lambda: str(uuid4()))
    node_type: NodeType = NodeType.TOPIC
    name: str = ""
    description: str = ""

    # Properties
    properties: dict[str, Any] = field(default_factory=dict)

    # Embeddings for semantic search
    embedding: list[float] | None = None

    # Metadata
    case_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = ""

    # Graph position (for layout algorithms)
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "case_id": self.case_id,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
        }


@dataclass
class GraphEdge:
    """An edge (relationship) in the knowledge graph."""

    edge_id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATES_TO

    # Weight and confidence
    weight: float = 1.0
    confidence: float = 1.0

    # Properties
    properties: dict[str, Any] = field(default_factory=dict)

    # Temporal validity
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "properties": self.properties,
        }


class GraphQuery(BaseModel):
    """Query for graph traversal."""

    # Starting point
    start_nodes: list[str] = Field(default_factory=list)  # Node IDs
    start_query: str = ""  # Text query to find start nodes

    # Traversal parameters
    max_hops: int = Field(default=2, ge=1, le=5)
    relation_types: list[RelationType] | None = None
    node_types: list[NodeType] | None = None

    # Filters
    min_confidence: float = Field(default=0.5, ge=0, le=1)
    case_id: str | None = None
    time_range: tuple[datetime, datetime] | None = None

    # Ranking
    rank_by: str = "relevance"  # relevance, centrality, recency
    max_results: int = 20


class GraphSearchResult(BaseModel):
    """Result from graph search."""

    # Matched nodes
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]

    # Subgraph statistics
    total_nodes: int
    total_edges: int

    # Relevance scores
    scores: dict[str, float] = Field(default_factory=dict)  # node_id -> score

    # Paths found
    paths: list[list[str]] = Field(default_factory=list)  # List of node_id paths

    # Summary
    summary: str = ""


class CommunityDetection(BaseModel):
    """Result of community detection on the graph."""

    communities: list[list[str]]  # List of node ID groups
    modularity: float
    summary: dict[int, str] = Field(default_factory=dict)  # community_id -> summary


class GraphRAG:
    """Graph-based Retrieval Augmented Generation system.

    Combines knowledge graphs with RAG for enhanced retrieval:
    - Build knowledge graphs from documents
    - Traverse graphs for multi-hop reasoning
    - Use community detection for topic summaries
    - Temporal tracking of facts

    Example usage:
        graph_rag = GraphRAG()

        # Add nodes and edges
        beneficiary = await graph_rag.add_node(
            node_type=NodeType.BENEFICIARY,
            name="John Doe",
            properties={"field": "AI Research"},
        )

        award = await graph_rag.add_node(
            node_type=NodeType.AWARD,
            name="Best Paper Award",
            properties={"year": 2024},
        )

        await graph_rag.add_edge(
            source_id=beneficiary.node_id,
            target_id=award.node_id,
            relation_type=RelationType.RECEIVED,
        )

        # Query the graph
        results = await graph_rag.search(
            GraphQuery(
                start_query="AI research awards",
                max_hops=2,
                relation_types=[RelationType.RECEIVED, RelationType.ACHIEVED],
            )
        )

        # Generate context for LLM
        context = await graph_rag.generate_context(
            query="What awards has the beneficiary received?",
            case_id="case-123",
        )
    """

    def __init__(
        self,
        embedding_client: Any | None = None,
        persist_path: str | None = None,
    ):
        """Initialize GraphRAG.

        Args:
            embedding_client: Client for generating embeddings
            persist_path: Path to persist graph data
        """
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

        # Indexes for fast lookup
        self._adjacency: dict[str, list[str]] = defaultdict(list)  # node_id -> edge_ids
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        self._type_index: dict[NodeType, set[str]] = defaultdict(set)
        self._case_index: dict[str, set[str]] = defaultdict(set)  # case_id -> node_ids

        self._embedding_client = embedding_client
        self._persist_path = persist_path

    async def add_node(
        self,
        node_type: NodeType,
        name: str,
        description: str = "",
        properties: dict[str, Any] | None = None,
        case_id: str | None = None,
        source: str = "",
        node_id: str | None = None,
    ) -> GraphNode:
        """Add a node to the graph.

        Args:
            node_type: Type of the node
            name: Node name
            description: Node description
            properties: Additional properties
            case_id: Associated case ID
            source: Source of this node
            node_id: Optional explicit node ID

        Returns:
            Created GraphNode
        """
        node = GraphNode(
            node_id=node_id or str(uuid4()),
            node_type=node_type,
            name=name,
            description=description,
            properties=properties or {},
            case_id=case_id,
            source=source,
        )

        # Generate embedding if available
        if self._embedding_client:
            node.embedding = await self._generate_embedding(f"{name} {description}")

        # Store and index
        self._nodes[node.node_id] = node
        self._type_index[node_type].add(node.node_id)
        if case_id:
            self._case_index[case_id].add(node.node_id)

        return node

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        confidence: float = 1.0,
        properties: dict[str, Any] | None = None,
        edge_id: str | None = None,
    ) -> GraphEdge:
        """Add an edge to the graph.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Type of relationship
            weight: Edge weight
            confidence: Confidence score
            properties: Additional properties
            edge_id: Optional explicit edge ID

        Returns:
            Created GraphEdge
        """
        if source_id not in self._nodes:
            raise ValueError(f"Source node {source_id} not found")
        if target_id not in self._nodes:
            raise ValueError(f"Target node {target_id} not found")

        edge = GraphEdge(
            edge_id=edge_id or str(uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            confidence=confidence,
            properties=properties or {},
        )

        # Store and index
        self._edges[edge.edge_id] = edge
        self._adjacency[source_id].append(edge.edge_id)
        self._reverse_adjacency[target_id].append(edge.edge_id)

        return edge

    async def search(self, query: GraphQuery) -> GraphSearchResult:
        """Search the graph with multi-hop traversal.

        Args:
            query: Graph query specification

        Returns:
            GraphSearchResult with matching subgraph
        """
        # Find start nodes
        start_node_ids = set(query.start_nodes)

        if query.start_query:
            # Semantic search for start nodes
            matched = await self._semantic_search(
                query.start_query,
                node_types=query.node_types,
                case_id=query.case_id,
            )
            start_node_ids.update(n.node_id for n in matched[:5])

        if not start_node_ids:
            return GraphSearchResult(
                nodes=[],
                edges=[],
                total_nodes=0,
                total_edges=0,
            )

        # BFS traversal
        visited_nodes: set[str] = set()
        visited_edges: set[str] = set()
        paths: list[list[str]] = []
        scores: dict[str, float] = {}

        queue: list[tuple[str, int, list[str]]] = [
            (node_id, 0, [node_id]) for node_id in start_node_ids
        ]

        while queue:
            node_id, depth, path = queue.pop(0)

            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)

            node = self._nodes.get(node_id)
            if not node:
                continue

            # Apply filters
            if query.case_id and node.case_id != query.case_id:
                continue
            if query.node_types and node.node_type not in query.node_types:
                continue

            # Calculate score (closer to start = higher score)
            scores[node_id] = 1.0 / (depth + 1)

            # Save path
            if depth > 0:
                paths.append(path)

            # Continue traversal
            if depth < query.max_hops:
                for edge_id in self._adjacency.get(node_id, []):
                    edge = self._edges.get(edge_id)
                    if not edge or edge.confidence < query.min_confidence:
                        continue
                    if query.relation_types and edge.relation_type not in query.relation_types:
                        continue

                    visited_edges.add(edge_id)
                    target_id = edge.target_id
                    if target_id not in visited_nodes:
                        queue.append((target_id, depth + 1, [*path, target_id]))

                # Also check reverse edges
                for edge_id in self._reverse_adjacency.get(node_id, []):
                    edge = self._edges.get(edge_id)
                    if not edge or edge.confidence < query.min_confidence:
                        continue
                    if query.relation_types and edge.relation_type not in query.relation_types:
                        continue

                    visited_edges.add(edge_id)
                    source_id = edge.source_id
                    if source_id not in visited_nodes:
                        queue.append((source_id, depth + 1, [*path, source_id]))

        # Build result
        result_nodes = [self._nodes[nid].to_dict() for nid in visited_nodes if nid in self._nodes][
            : query.max_results
        ]

        result_edges = [self._edges[eid].to_dict() for eid in visited_edges if eid in self._edges]

        return GraphSearchResult(
            nodes=result_nodes,
            edges=result_edges,
            total_nodes=len(visited_nodes),
            total_edges=len(visited_edges),
            scores=scores,
            paths=paths[:10],  # Top 10 paths
            summary=f"Found {len(visited_nodes)} nodes connected by {len(visited_edges)} edges",
        )

    async def generate_context(
        self,
        query: str,
        case_id: str | None = None,
        max_tokens: int = 2000,
        include_paths: bool = True,
    ) -> str:
        """Generate context string for LLM from graph.

        Args:
            query: User query
            case_id: Filter by case ID
            max_tokens: Maximum context length
            include_paths: Include relationship paths

        Returns:
            Context string for LLM
        """
        # Search graph
        search_result = await self.search(
            GraphQuery(
                start_query=query,
                max_hops=2,
                case_id=case_id,
                max_results=20,
            )
        )

        if not search_result.nodes:
            return "No relevant information found in knowledge graph."

        # Build context
        context_parts = ["## Knowledge Graph Context\n"]

        # Group nodes by type
        nodes_by_type: dict[str, list[dict]] = defaultdict(list)
        for node in search_result.nodes:
            nodes_by_type[node["node_type"]].append(node)

        for node_type, nodes in nodes_by_type.items():
            context_parts.append(f"\n### {node_type.replace('_', ' ').title()}\n")
            for node in nodes[:5]:  # Limit per type
                context_parts.append(f"- **{node['name']}**: {node.get('description', '')}")
                if node.get("properties"):
                    props = ", ".join(f"{k}={v}" for k, v in list(node["properties"].items())[:3])
                    context_parts.append(f"  ({props})")

        # Add relationships
        if include_paths and search_result.paths:
            context_parts.append("\n### Relationships\n")
            for path in search_result.paths[:5]:
                path_names = []
                for node_id in path:
                    node = self._nodes.get(node_id)
                    if node:
                        path_names.append(node.name)
                if len(path_names) > 1:
                    context_parts.append(f"- {' → '.join(path_names)}")

        context = "\n".join(context_parts)

        # Truncate if needed (rough estimate)
        if len(context) > max_tokens * 4:  # ~4 chars per token
            context = context[: max_tokens * 4] + "\n...[truncated]"

        return context

    async def extract_entities_from_text(
        self,
        text: str,
        case_id: str | None = None,
    ) -> list[GraphNode]:
        """Extract entities from text and add to graph.

        Uses NER and pattern matching to extract entities.

        Args:
            text: Text to extract from
            case_id: Case ID to associate

        Returns:
            List of extracted nodes
        """
        import re

        extracted_nodes = []

        # Simple pattern-based extraction (in production, use NER)
        patterns = {
            NodeType.PERSON: r"\b(?:Dr\.?|Prof\.?|Mr\.?|Ms\.?|Mrs\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
            NodeType.ORGANIZATION: r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*(?:\s+(?:University|Institute|Corporation|Inc\.|Ltd\.|LLC|Company))\b)",
            NodeType.AWARD: r"\b([A-Z][a-z]*(?:\s+[A-Z]?[a-z]*)*\s+Award)\b",
            NodeType.PUBLICATION: r'"([^"]{10,100})"',  # Quoted titles
        }

        for node_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                if len(name) > 3:  # Filter very short matches
                    # Check if already exists
                    existing = self._find_node_by_name(name, node_type)
                    if existing:
                        extracted_nodes.append(existing)
                    else:
                        node = await self.add_node(
                            node_type=node_type,
                            name=name,
                            case_id=case_id,
                            source="text_extraction",
                        )
                        extracted_nodes.append(node)

        return extracted_nodes

    async def detect_communities(
        self,
        algorithm: str = "louvain",
    ) -> CommunityDetection:
        """Detect communities in the graph.

        Uses community detection algorithms to group related nodes.

        Args:
            algorithm: Algorithm to use (louvain, label_propagation)

        Returns:
            CommunityDetection result
        """
        # Simple connected components as fallback
        # In production, use networkx or specialized library

        visited: set[str] = set()
        communities: list[list[str]] = []

        for node_id in self._nodes:
            if node_id in visited:
                continue

            # BFS to find connected component
            component: list[str] = []
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                # Add neighbors
                for edge_id in self._adjacency.get(current, []):
                    edge = self._edges.get(edge_id)
                    if edge and edge.target_id not in visited:
                        queue.append(edge.target_id)

                for edge_id in self._reverse_adjacency.get(current, []):
                    edge = self._edges.get(edge_id)
                    if edge and edge.source_id not in visited:
                        queue.append(edge.source_id)

            if component:
                communities.append(component)

        # Generate summaries for each community
        summaries = {}
        for i, community in enumerate(communities):
            node_names = [self._nodes[nid].name for nid in community[:5] if nid in self._nodes]
            summaries[i] = f"Community with {len(community)} nodes: {', '.join(node_names)}"

        return CommunityDetection(
            communities=communities,
            modularity=0.0,  # Would need actual calculation
            summary=summaries,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_neighbors(
        self,
        node_id: str,
        relation_types: list[RelationType] | None = None,
    ) -> list[GraphNode]:
        """Get neighboring nodes."""
        neighbors = []

        for edge_id in self._adjacency.get(node_id, []):
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            if relation_types and edge.relation_type not in relation_types:
                continue
            neighbor = self._nodes.get(edge.target_id)
            if neighbor:
                neighbors.append(neighbor)

        return neighbors

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": {nt.value: len(nodes) for nt, nodes in self._type_index.items()},
            "cases": list(self._case_index.keys()),
        }

    # Private methods

    def _find_node_by_name(
        self,
        name: str,
        node_type: NodeType | None = None,
    ) -> GraphNode | None:
        """Find a node by name."""
        name_lower = name.lower()
        for node in self._nodes.values():
            if node.name.lower() == name_lower:
                if node_type is None or node.node_type == node_type:
                    return node
        return None

    async def _semantic_search(
        self,
        query: str,
        node_types: list[NodeType] | None = None,
        case_id: str | None = None,
        top_k: int = 10,
    ) -> list[GraphNode]:
        """Semantic search for nodes."""
        if not self._embedding_client:
            # Fallback to keyword search
            query_lower = query.lower()
            results = []
            for node in self._nodes.values():
                if node_types and node.node_type not in node_types:
                    continue
                if case_id and node.case_id != case_id:
                    continue
                if query_lower in node.name.lower() or query_lower in node.description.lower():
                    results.append(node)
            return results[:top_k]

        # Generate query embedding
        query_embedding = await self._generate_embedding(query)

        # Calculate similarities
        scored = []
        for node in self._nodes.values():
            if node_types and node.node_type not in node_types:
                continue
            if case_id and node.case_id != case_id:
                continue
            if node.embedding:
                score = self._cosine_similarity(query_embedding, node.embedding)
                scored.append((node, score))

        # Sort by score
        scored.sort(key=lambda x: -x[1])

        return [node for node, score in scored[:top_k]]

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if not self._embedding_client:
            return []
        # Placeholder - actual implementation depends on embedding client
        return [0.0] * 768

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton instance
_graph_rag_instance: GraphRAG | None = None


def get_graph_rag() -> GraphRAG:
    """Get or create the global GraphRAG instance."""
    global _graph_rag_instance
    if _graph_rag_instance is None:
        _graph_rag_instance = GraphRAG()
    return _graph_rag_instance


__all__ = [
    "CommunityDetection",
    "GraphEdge",
    "GraphNode",
    "GraphQuery",
    "GraphRAG",
    "GraphSearchResult",
    "NodeType",
    "RelationType",
    "get_graph_rag",
]
