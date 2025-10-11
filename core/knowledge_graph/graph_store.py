"""Knowledge graph storage utilities built on top of official graph libraries.

The in-memory implementation leverages NetworkX' MultiDiGraph for flexible
triple storage, while providing helpers to interoperate with RDFLib graphs
and optional Neo4j backends for production deployments.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import threading
from typing import Any

import networkx as nx

from .entities import KGEdge, KGNode, KnowledgeTriple

try:  # Optional dependency – only required for RDF import/export.
    import rdflib
    from rdflib import BNode, Graph as RDFGraph, Literal, Namespace
    from rdflib.namespace import RDF, RDFS
except ImportError:  # pragma: no cover - exercised in environments without rdflib
    rdflib = None  # type: ignore
    RDFGraph = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class GraphStoreStats:
    """Summary statistics for the knowledge graph."""

    num_nodes: int
    num_edges: int
    density: float
    average_degree: float
    node_types: dict[str, int]
    relations: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_nodes": self.num_nodes,
            "num_edges": self.num_edges,
            "density": self.density,
            "average_degree": self.average_degree,
            "node_types": dict(self.node_types),
            "relations": dict(self.relations),
        }


class GraphStore:
    """Thread-safe NetworkX-backed knowledge graph store."""

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._lock = threading.RLock()

    # --------------------------------------------------------------------- #
    # Node operations
    # --------------------------------------------------------------------- #
    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str = "entity",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Add or update a node."""
        with self._lock:
            attributes = {
                "label": label,
                "node_type": node_type,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if metadata:
                attributes["metadata"] = dict(metadata)
            if node_id not in self.graph:
                attributes["created_at"] = datetime.utcnow().isoformat()
            self.graph.add_node(node_id, **attributes)

    def upsert_node(self, node: KGNode) -> None:
        """Persist a `KGNode` dataclass instance."""
        self.add_node(
            node.node_id,
            node.label,
            node.node_type,
            metadata=node.metadata,
        )

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Return node attributes if present."""
        with self._lock:
            if node_id not in self.graph:
                return None
            return dict(self.graph.nodes[node_id])

    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges."""
        with self._lock:
            if node_id in self.graph:
                self.graph.remove_node(node_id)

    def find_nodes_by_type(self, node_type: str) -> list[str]:
        """Return all node identifiers matching a type."""
        with self._lock:
            return [
                node_id
                for node_id, attrs in self.graph.nodes(data=True)
                if attrs.get("node_type") == node_type
            ]

    def find_nodes_by_pattern(
        self,
        *,
        node_type: str | None = None,
        label_contains: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> list[str]:
        """Find nodes matching optional filters."""
        with self._lock:
            results: list[str] = []
            for node_id, attrs in self.graph.nodes(data=True):
                if node_type and attrs.get("node_type") != node_type:
                    continue
                if label_contains and label_contains.lower() not in attrs.get("label", "").lower():
                    continue
                if metadata:
                    node_meta = attrs.get("metadata") or {}
                    if not all(node_meta.get(k) == v for k, v in metadata.items()):
                        continue
                results.append(node_id)
            return results

    # --------------------------------------------------------------------- #
    # Edge operations
    # --------------------------------------------------------------------- #
    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        weight: float | None = None,
    ) -> None:
        """Add a directed relation."""
        with self._lock:
            attributes: dict[str, Any] = {"relation": relation}
            if metadata:
                attributes["metadata"] = dict(metadata)
            if weight is not None:
                attributes["weight"] = float(weight)
            attributes.setdefault("created_at", datetime.utcnow().isoformat())
            self.graph.add_edge(source, target, key=relation, **attributes)

    def upsert_edge(self, edge: KGEdge) -> None:
        """Persist a `KGEdge` dataclass instance."""
        self.add_edge(
            edge.source,
            edge.target,
            edge.relation,
            metadata=edge.metadata,
            weight=edge.weight,
        )

    def add_triple(self, triple: KnowledgeTriple) -> None:
        """Add a knowledge triple (subject, relation, object)."""
        self.add_node(triple.subject, triple.subject, metadata=triple.metadata)
        self.add_node(triple.obj, triple.obj, metadata=triple.metadata)
        edge_metadata = dict(triple.metadata)
        edge_metadata["confidence"] = triple.confidence
        self.add_edge(
            triple.subject,
            triple.obj,
            triple.relation,
            metadata=edge_metadata,
        )

    def get_edge(
        self,
        source: str,
        target: str,
        relation: str | None = None,
    ) -> dict[str, Any] | None:
        """Return a single edge matching the relation."""
        for edge in self.get_edges(source, target, relation=relation):
            return edge
        return None

    def get_edges(
        self,
        source: str,
        target: str,
        relation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all edges between two nodes."""
        with self._lock:
            if not self.graph.has_edge(source, target):
                return []
            edges: list[dict[str, Any]] = []
            data = self.graph.get_edge_data(source, target) or {}
            for key, attrs in data.items():
                if relation and key != relation:
                    continue
                record = {"relation": key}
                record.update(attrs)
                edges.append(record)
            return edges

    def remove_edge(
        self,
        source: str,
        target: str,
        relation: str | None = None,
    ) -> None:
        """Remove edges between two nodes."""
        with self._lock:
            if not self.graph.has_edge(source, target):
                return
            if relation:
                if relation in self.graph[source][target]:
                    del self.graph[source][target][relation]
            else:
                self.graph.remove_edges_from(
                    [(source, target, k) for k in list(self.graph[source][target].keys())]
                )

    # --------------------------------------------------------------------- #
    # Graph queries
    # --------------------------------------------------------------------- #
    def get_neighbors(
        self,
        node_id: str,
        relation: str | None = None,
        include_direction: bool = False,
    ) -> list[str] | list[tuple[str, str]]:
        """Return neighbors optionally filtered by relation."""
        with self._lock:
            if node_id not in self.graph:
                return []  # type: ignore[return-value]

            outgoing = [
                (neighbor, "out")
                for _, neighbor, key in self.graph.out_edges(node_id, keys=True)
                if not relation or key == relation
            ]
            incoming = [
                (neighbor, "in")
                for neighbor, _, key in self.graph.in_edges(node_id, keys=True)
                if not relation or key == relation
            ]

            if include_direction:
                return [*outgoing, *incoming]  # type: ignore[return-value]

            dedup: set[str] = {neighbor for neighbor, _ in outgoing + incoming}
            return list(dedup)

    def get_paths(
        self,
        source: str,
        target: str,
        max_length: int = 3,
    ) -> list[list[str]]:
        """Find simple paths up to a maximum number of hops."""
        with self._lock:
            if source not in self.graph or target not in self.graph:
                return []
            paths = []
            try:
                for path in nx.all_simple_paths(
                    self.graph,
                    source=source,
                    target=target,
                    cutoff=max_length,
                ):
                    paths.append(list(path))
            except nx.NetworkXNoPath:
                return []
            return paths

    def get_related_entities(
        self,
        node_id: str,
        max_hops: int = 2,
    ) -> dict[str, int]:
        """Return related entities up to N hops away."""
        with self._lock:
            if node_id not in self.graph:
                return {}
            distances = nx.single_source_shortest_path_length(
                self.graph.to_undirected(as_view=True),
                node_id,
                cutoff=max_hops,
            )
            distances.pop(node_id, None)
            return {neighbor: int(dist) for neighbor, dist in distances.items()}

    def get_subgraph(
        self,
        node_ids: Sequence[str],
        max_hops: int = 1,
    ) -> nx.MultiDiGraph:
        """Return a subgraph induced by nodes within N hops."""
        with self._lock:
            visited = set(node_ids)
            for node in list(node_ids):
                if node not in self.graph:
                    continue
                distances = nx.single_source_shortest_path_length(
                    self.graph.to_undirected(as_view=True),
                    node,
                    cutoff=max_hops,
                )
                visited.update(distances.keys())
            return self.graph.subgraph(visited).copy()

    # --------------------------------------------------------------------- #
    # Serialization helpers
    # --------------------------------------------------------------------- #
    def get_stats(self) -> dict[str, Any]:
        """Compute graph statistics."""
        with self._lock:
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
            density = nx.density(self.graph) if num_nodes > 1 else 0.0
            average_degree = (
                sum(dict(self.graph.degree()).values()) / num_nodes if num_nodes else 0.0
            )

            node_types: dict[str, int] = {}
            for _, attrs in self.graph.nodes(data=True):
                node_type = attrs.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

            relations: dict[str, int] = {}
            for _, _, attrs in self.graph.edges(data=True):
                rel = attrs.get("relation", "unknown")
                relations[rel] = relations.get(rel, 0) + 1

            stats = GraphStoreStats(
                num_nodes=num_nodes,
                num_edges=num_edges,
                density=float(density),
                average_degree=float(average_degree),
                node_types=node_types,
                relations=relations,
            )
            return stats.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        with self._lock:
            nodes = []
            for node_id, attrs in self.graph.nodes(data=True):
                node_record = {"id": node_id, **attrs}
                nodes.append(node_record)

            edges = []
            for source, target, key, attrs in self.graph.edges(keys=True, data=True):
                edge_record = {
                    "source": source,
                    "target": target,
                    "relation": key,
                    **attrs,
                }
                edges.append(edge_record)

            return {
                "nodes": nodes,
                "edges": edges,
                "stats": self.get_stats(),
            }

    export_to_dict = to_dict  # Backwards compatibility alias.

    def export_to_json(self, filepath: str) -> None:
        """Persist graph to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    def import_from_dict(self, data: Mapping[str, Any]) -> None:
        """Load graph from a dictionary produced by `to_dict`."""
        with self._lock:
            self.graph.clear()

            for node in data.get("nodes", []):
                node_id = str(node.pop("id"))
                metadata = node.pop("metadata", None)
                self.add_node(
                    node_id,
                    label=node.pop("label", node_id),
                    node_type=node.pop("node_type", "entity"),
                    metadata=metadata,
                )
                # Merge any remaining attributes
                if remaining := {
                    k: v for k, v in node.items() if k not in {"created_at", "updated_at"}
                }:
                    self.graph.nodes[node_id].update(remaining)

            for edge in data.get("edges", []):
                source = edge.pop("source")
                target = edge.pop("target")
                relation = edge.pop("relation")
                metadata = edge.pop("metadata", None)
                weight = edge.pop("weight", None)
                self.add_edge(
                    source,
                    target,
                    relation,
                    metadata=metadata,
                    weight=weight,
                )
                if remaining := edge:
                    edge_attrs = self.graph[source][target][relation]
                    edge_attrs.update(remaining)

    def import_from_json(self, filepath: str) -> None:
        """Load graph from a JSON file."""
        with open(filepath, encoding="utf-8") as handle:
            data = json.load(handle)
        self.import_from_dict(data)

    # ------------------------------------------------------------------ #
    # RDF helpers (optional rdflib dependency)
    # ------------------------------------------------------------------ #
    def to_rdflib_graph(self) -> RDFGraph:
        """Serialize the knowledge graph into an RDFLib graph."""
        if rdflib is None:  # pragma: no cover - optional dependency
            raise ImportError(
                "rdflib is required for RDF serialization. Install via `pip install rdflib`."
            )

        kg_ns = Namespace("kg://relation/")
        graph = RDFGraph()
        node_refs: dict[str, Any] = {}

        with self._lock:
            for node_id, attrs in self.graph.nodes(data=True):
                node_ref = BNode(node_id)
                node_refs[node_id] = node_ref
                label = attrs.get("label")
                node_type = attrs.get("node_type")
                if label:
                    graph.add((node_ref, RDFS.label, Literal(label)))
                if node_type:
                    graph.add((node_ref, RDF.type, Literal(node_type)))
                if metadata := attrs.get("metadata"):
                    graph.add((node_ref, kg_ns.metadata, Literal(json.dumps(metadata))))

            for source, target, key, attrs in self.graph.edges(keys=True, data=True):
                predicate = kg_ns[key]
                graph.add((node_refs[source], predicate, node_refs[target]))
                if metadata := attrs.get("metadata"):
                    graph.add(
                        (
                            node_refs[source],
                            kg_ns[f"{key}_metadata"],
                            Literal(json.dumps(metadata)),
                        )
                    )
                if weight := attrs.get("weight"):
                    graph.add((node_refs[source], kg_ns[f"{key}_weight"], Literal(weight)))

        return graph

    def import_from_rdflib(self, graph: RDFGraph) -> None:
        """Populate the store from an RDFLib graph produced by `to_rdflib_graph`."""
        if rdflib is None:  # pragma: no cover - optional dependency
            raise ImportError(
                "rdflib is required for RDF import. Install via `pip install rdflib`."
            )

        with self._lock:
            self.graph.clear()

        node_map: dict[Any, str] = {}
        for subject in set(graph.subjects()):
            node_id = str(subject)
            node_map[subject] = node_id
            label = None
            node_type = None
            metadata = None
            for _, predicate, obj in graph.triples((subject, None, None)):
                pred_str = str(predicate)
                if pred_str == str(RDFS.label):
                    label = str(obj)
                elif pred_str == str(RDF.type):
                    node_type = str(obj)
                elif pred_str.endswith("metadata"):
                    metadata = json.loads(str(obj))
            self.add_node(
                node_id,
                label=label or node_id,
                node_type=node_type or "entity",
                metadata=metadata,
            )

        for subject, predicate, obj in graph.triples((None, None, None)):
            pred_str = str(predicate)
            if pred_str.endswith(("metadata", "weight")):
                continue  # handled above
            source_id = node_map.get(subject)
            target_id = node_map.get(obj)
            if not source_id or not target_id:
                continue
            relation = pred_str.split("/")[-1]
            self.add_edge(source_id, target_id, relation)

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    def clear(self) -> None:
        """Remove all nodes and edges."""
        with self._lock:
            self.graph.clear()

    def copy(self) -> GraphStore:
        """Create a shallow copy of the graph store."""
        new_store = GraphStore()
        with self._lock:
            new_store.graph = self.graph.copy()
        return new_store


# --------------------------------------------------------------------------- #
# Optional Neo4j integration
# --------------------------------------------------------------------------- #


class Neo4jGraphStore:
    """Thin wrapper around the official Neo4j Python driver for KG persistence."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        database: str | None = None,
        encrypted: bool = True,
    ) -> None:
        try:
            from neo4j import GraphDatabase  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "neo4j driver is required for Neo4jGraphStore. Install via `pip install neo4j`."
            ) from exc

        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=encrypted)
        self._database = database

    def close(self) -> None:
        """Close the underlying driver."""
        self._driver.close()

    def __enter__(self) -> Neo4jGraphStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -- Write operations ------------------------------------------------ #
    def upsert_triple(self, triple: KnowledgeTriple) -> None:
        """Merge nodes and relation representing a knowledge triple."""

        def _tx(tx) -> None:
            tx.run(
                """
                MERGE (s:Entity {id: $subject})
                  ON CREATE SET s.label = $subject
                MERGE (o:Entity {id: $object})
                  ON CREATE SET o.label = $object
                MERGE (s)-[r:RELATION {type: $relation}]->(o)
                SET r.confidence = $confidence,
                    r.metadata = $metadata
                """,
                subject=triple.subject,
                object=triple.obj,
                relation=triple.relation,
                confidence=triple.confidence,
                metadata=json.dumps(triple.metadata),
            )

        with self._driver.session(database=self._database) as session:
            session.execute_write(_tx)

    # -- Read operations ------------------------------------------------- #
    def fetch_neighbors(self, node_id: str, max_hops: int = 1) -> list[dict[str, Any]]:
        """Fetch neighbors using the GDS BFS procedure."""

        def _tx(tx):
            result = tx.run(
                """
                MATCH (start {id: $node_id})
                CALL apoc.path.expandConfig(start, {
                    maxLevel: $max_hops,
                    bfs: true
                }) YIELD path
                RETURN nodes(path) AS nodes, relationships(path) AS rels
                """,
                node_id=node_id,
                max_hops=max_hops,
            )
            for record in result:
                yield {
                    "nodes": [n.get("id") for n in record["nodes"]],
                    "relations": [r.get("type") for r in record["rels"]],
                }

        with self._driver.session(database=self._database) as session:
            return list(session.execute_read(_tx))
