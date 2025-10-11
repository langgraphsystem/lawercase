"""Knowledge Graph Store Implementation.

This module provides graph storage using NetworkX with optional Neo4j backend
for production use.
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx

from .entities import KnowledgeTriple


class GraphStore:
    """
    Knowledge Graph storage using NetworkX.

    Features:
    - In-memory graph storage
    - Node and edge CRUD operations
    - Graph traversal and queries
    - Subgraph extraction
    - Graph serialization

    Example:
        >>> store = GraphStore()
        >>> store.add_node("person_1", "John Doe", "Person")
        >>> store.add_edge("person_1", "company_1", "works_at")
        >>> neighbors = store.get_neighbors("person_1")
    """

    def __init__(self):
        """Initialize graph store."""
        self.graph = nx.MultiDiGraph()  # Directed graph with multiple edges

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str = "entity",
        **metadata: Any,
    ) -> None:
        """
        Add a node to the graph.

        Args:
            node_id: Unique node identifier
            label: Human-readable label
            node_type: Type of node (entity, concept, etc.)
            **metadata: Additional node attributes
        """
        self.graph.add_node(
            node_id,
            label=label,
            node_type=node_type,
            **metadata,
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        **metadata: Any,
    ) -> None:
        """
        Add an edge between two nodes.

        Args:
            source: Source node ID
            target: Target node ID
            relation: Relationship type
            **metadata: Additional edge attributes
        """
        self.graph.add_edge(
            source,
            target,
            key=relation,
            relation=relation,
            **metadata,
        )

    def add_triple(self, triple: KnowledgeTriple) -> None:
        """Add a knowledge triple (subject-relation-object)."""
        # Ensure nodes exist
        if triple.subject not in self.graph:
            self.add_node(triple.subject, triple.subject)
        if triple.obj not in self.graph:
            self.add_node(triple.obj, triple.obj)

        # Add edge
        self.add_edge(
            triple.subject,
            triple.obj,
            triple.relation,
            **triple.metadata,
        )

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Get node attributes."""
        if node_id in self.graph:
            return dict(self.graph.nodes[node_id])
        return None

    def get_edge(
        self,
        source: str,
        target: str,
        relation: str | None = None,
    ) -> dict[str, Any] | None:
        """Get edge attributes."""
        if self.graph.has_edge(source, target):
            if relation:
                return dict(self.graph[source][target].get(relation, {}))
            # Return first edge if relation not specified
            edges = self.graph[source][target]
            if edges:
                return dict(next(iter(edges.values())))
        return None

    def get_neighbors(
        self,
        node_id: str,
        relation: str | None = None,
    ) -> list[str]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node to get neighbors for
            relation: Optional filter by relation type

        Returns:
            List of neighbor node IDs
        """
        if node_id not in self.graph:
            return []

        if relation:
            neighbors = []
            for _, target, edge_data in self.graph.out_edges(node_id, data=True):
                if edge_data.get("relation") == relation:
                    neighbors.append(target)
            return neighbors

        return list(self.graph.successors(node_id))

    def get_paths(
        self,
        source: str,
        target: str,
        max_length: int = 3,
    ) -> list[list[str]]:
        """
        Find all paths between two nodes.

        Args:
            source: Source node ID
            target: Target node ID
            max_length: Maximum path length

        Returns:
            List of paths (each path is a list of node IDs)
        """
        if source not in self.graph or target not in self.graph:
            return []

        try:
            paths = nx.all_simple_paths(
                self.graph,
                source,
                target,
                cutoff=max_length,
            )
            return list(paths)
        except nx.NetworkXNoPath:
            return []

    def get_subgraph(
        self,
        node_ids: list[str],
        include_neighbors: bool = False,
    ) -> nx.MultiDiGraph:
        """
        Extract a subgraph.

        Args:
            node_ids: Nodes to include
            include_neighbors: Whether to include direct neighbors

        Returns:
            Subgraph
        """
        if include_neighbors:
            # Add neighbors
            extended_nodes = set(node_ids)
            for node_id in node_ids:
                if node_id in self.graph:
                    extended_nodes.update(self.graph.neighbors(node_id))
            node_ids = list(extended_nodes)

        return self.graph.subgraph(node_ids).copy()

    def query_by_pattern(
        self,
        pattern: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Query nodes by pattern matching.

        Args:
            pattern: Pattern dict (e.g., {"node_type": "Person", "company": "Acme"})

        Returns:
            List of matching nodes with attributes
        """
        results = []
        for node_id, attrs in self.graph.nodes(data=True):
            match = all(attrs.get(key) == value for key, value in pattern.items())
            if match:
                results.append({"node_id": node_id, **attrs})

        return results

    def get_related_entities(
        self,
        node_id: str,
        max_hops: int = 2,
    ) -> list[tuple[str, int]]:
        """
        Get entities within N hops.

        Args:
            node_id: Starting node
            max_hops: Maximum number of hops

        Returns:
            List of (node_id, distance) tuples
        """
        if node_id not in self.graph:
            return []

        # BFS to find nodes within max_hops
        distances = nx.single_source_shortest_path_length(
            self.graph,
            node_id,
            cutoff=max_hops,
        )

        # Remove the source node itself
        distances.pop(node_id, None)

        return list(distances.items())

    def count_nodes(self, node_type: str | None = None) -> int:
        """Count nodes, optionally filtered by type."""
        if node_type:
            return sum(
                1 for _, attrs in self.graph.nodes(data=True) if attrs.get("node_type") == node_type
            )
        return self.graph.number_of_nodes()

    def count_edges(self, relation: str | None = None) -> int:
        """Count edges, optionally filtered by relation."""
        if relation:
            return sum(
                1
                for _, _, attrs in self.graph.edges(data=True)
                if attrs.get("relation") == relation
            )
        return self.graph.number_of_edges()

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        node_types = {}
        for _, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        relations = {}
        for _, _, attrs in self.graph.edges(data=True):
            relation = attrs.get("relation", "unknown")
            relations[relation] = relations.get(relation, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "relations": relations,
            "is_directed": self.graph.is_directed(),
            "is_multigraph": self.graph.is_multigraph(),
        }

    def export_to_dict(self) -> dict[str, Any]:
        """Export graph to dictionary."""
        nodes = [{"id": node_id, **attrs} for node_id, attrs in self.graph.nodes(data=True)]

        edges = [
            {
                "source": source,
                "target": target,
                "relation": attrs.get("relation"),
                **{k: v for k, v in attrs.items() if k != "relation"},
            }
            for source, target, attrs in self.graph.edges(data=True)
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": self.get_stats(),
        }

    def export_to_json(self, filepath: str) -> None:
        """Export graph to JSON file."""
        data = self.export_to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def import_from_dict(self, data: dict[str, Any]) -> None:
        """Import graph from dictionary."""
        self.graph.clear()

        # Add nodes
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            self.add_node(node_id, node.get("label", node_id), **node)

        # Add edges
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            relation = edge.pop("relation", "related")
            self.add_edge(source, target, relation, **edge)

    def import_from_json(self, filepath: str) -> None:
        """Import graph from JSON file."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.import_from_dict(data)

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self.graph.clear()


# Global singleton
_graph_store: GraphStore | None = None


def get_graph_store() -> GraphStore:
    """
    Get global graph store instance.

    Returns:
        GraphStore instance
    """
    global _graph_store

    if _graph_store is None:
        _graph_store = GraphStore()

    return _graph_store
