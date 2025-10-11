"""Knowledge Graph Construction from Text.

This module provides tools to extract entities and relations from text
and build a knowledge graph.
"""

from __future__ import annotations

import re
from typing import Any

from .entities import KnowledgeTriple
from .graph_store import GraphStore


class EntityExtractor:
    """
    Extract entities from text.

    Uses simple pattern matching for demo. In production,
    would use NER models like spaCy or transformer-based models.
    """

    def __init__(self):
        """Initialize entity extractor."""
        # Common entity patterns (simplified for demo)
        self.patterns = {
            "PERSON": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            "ORG": r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+ (?:Inc\.|LLC|Corp\.|Ltd\.)\b",
            "DATE": r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b",
            "MONEY": r"\$\d+(?:,\d{3})*(?:\.\d{2})?",
        }

    def extract(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities from text.

        Args:
            text: Input text

        Returns:
            List of entities with type and span
        """
        entities = []

        for entity_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                entities.append(
                    {
                        "text": match.group(),
                        "type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        # Sort by position
        entities.sort(key=lambda x: x["start"])

        return entities


class RelationExtractor:
    """
    Extract relations between entities.

    Uses simple pattern matching. In production, would use
    relation extraction models.
    """

    def __init__(self):
        """Initialize relation extractor."""
        # Relation patterns (simplified)
        self.relation_patterns = [
            (r"(.+) works (?:at|for) (.+)", "works_at"),
            (r"(.+) is (?:a |an )?(.+) at (.+)", "is_role_at"),
            (r"(.+) founded (.+)", "founded"),
            (r"(.+) owns (.+)", "owns"),
            (r"(.+) located in (.+)", "located_in"),
            (r"(.+) born in (.+)", "born_in"),
            (r"(.+) graduated from (.+)", "graduated_from"),
            (r"(.+) subsidiary of (.+)", "subsidiary_of"),
        ]

    def extract(
        self,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[KnowledgeTriple]:
        """
        Extract relations from text given entities.

        Args:
            text: Input text
            entities: Extracted entities

        Returns:
            List of knowledge triples
        """
        triples = []

        # Try pattern matching
        text_lower = text.lower()
        for pattern, relation_type in self.relation_patterns:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                groups = match.groups()
                if len(groups) >= 2:
                    subject = groups[0].strip()
                    obj = groups[-1].strip()

                    # Create triple
                    triple = KnowledgeTriple(
                        subject=subject,
                        relation=relation_type,
                        obj=obj,
                        metadata={
                            "source": "pattern_matching",
                            "confidence": 0.7,
                        },
                    )
                    triples.append(triple)

        return triples


class GraphConstructor:
    """
    Constructs knowledge graph from text documents.

    Features:
    - Entity extraction
    - Relation extraction
    - Entity linking
    - Graph building

    Example:
        >>> constructor = GraphConstructor()
        >>> constructor.add_document("John Doe works at Acme Corp.")
        >>> graph = constructor.get_graph()
    """

    def __init__(self, graph_store: GraphStore | None = None):
        """
        Initialize graph constructor.

        Args:
            graph_store: Optional graph store instance
        """
        self.graph_store = graph_store or GraphStore()
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

        # Entity linking cache
        self.entity_cache: dict[str, str] = {}  # text -> node_id

    def add_document(
        self,
        text: str,
        doc_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a document and add to graph.

        Args:
            text: Document text
            doc_id: Optional document ID
            metadata: Optional document metadata

        Returns:
            Processing results (entities, relations, etc.)
        """
        # Extract entities
        entities = self.entity_extractor.extract(text)

        # Extract relations
        relations = self.relation_extractor.extract(text, entities)

        # Add to graph
        added_nodes = []
        added_edges = []

        # Add entities as nodes
        for entity in entities:
            node_id = self._get_or_create_entity_id(entity["text"], entity["type"])
            self.graph_store.add_node(
                node_id,
                entity["text"],
                node_type=entity["type"],
                **(metadata or {}),
            )
            added_nodes.append(node_id)

        # Add relations as edges
        for triple in relations:
            # Link entities
            subject_id = self._get_or_create_entity_id(triple.subject, "ENTITY")
            object_id = self._get_or_create_entity_id(triple.obj, "ENTITY")

            # Add edge
            self.graph_store.add_edge(
                subject_id,
                object_id,
                triple.relation,
                **triple.metadata,
            )
            added_edges.append((subject_id, object_id, triple.relation))

        return {
            "doc_id": doc_id,
            "entities_found": len(entities),
            "relations_found": len(relations),
            "nodes_added": len(added_nodes),
            "edges_added": len(added_edges),
            "entities": entities,
            "relations": [
                {
                    "subject": r.subject,
                    "relation": r.relation,
                    "object": r.obj,
                }
                for r in relations
            ],
        }

    def _get_or_create_entity_id(self, text: str, entity_type: str) -> str:
        """Get or create entity ID with linking."""
        # Normalize text
        normalized = text.strip().lower()

        # Check cache
        if normalized in self.entity_cache:
            return self.entity_cache[normalized]

        # Create new ID
        entity_id = f"{entity_type}_{len(self.entity_cache)}"
        self.entity_cache[normalized] = entity_id

        return entity_id

    def add_triple(
        self,
        subject: str,
        relation: str,
        obj: str,
        **metadata: Any,
    ) -> None:
        """
        Manually add a knowledge triple.

        Args:
            subject: Subject entity
            relation: Relation type
            obj: Object entity
            **metadata: Additional metadata
        """
        triple = KnowledgeTriple(
            subject=subject,
            relation=relation,
            obj=obj,
            metadata=metadata,
        )
        self.graph_store.add_triple(triple)

    def get_graph(self) -> GraphStore:
        """Get the constructed graph."""
        return self.graph_store

    def get_entity_context(
        self,
        entity: str,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        """
        Get context for an entity from the graph.

        Args:
            entity: Entity text
            max_hops: Maximum hops in graph

        Returns:
            Entity context with neighbors and relations
        """
        # Find entity in cache
        normalized = entity.strip().lower()
        entity_id = self.entity_cache.get(normalized)

        if not entity_id:
            return {"found": False, "entity": entity}

        # Get node info
        node_info = self.graph_store.get_node(entity_id)

        # Get neighbors
        neighbors = self.graph_store.get_neighbors(entity_id)

        # Get related entities
        related = self.graph_store.get_related_entities(entity_id, max_hops)

        return {
            "found": True,
            "entity": entity,
            "entity_id": entity_id,
            "node_info": node_info,
            "direct_neighbors": neighbors,
            "related_entities": related,
        }

    def merge_entities(self, entity1: str, entity2: str) -> bool:
        """
        Merge two entities (entity resolution).

        Args:
            entity1: First entity text
            entity2: Second entity text

        Returns:
            True if merged successfully
        """
        # Find both entities
        id1 = self.entity_cache.get(entity1.strip().lower())
        id2 = self.entity_cache.get(entity2.strip().lower())

        if not id1 or not id2 or id1 == id2:
            return False

        # Merge edges from id2 to id1
        for neighbor in self.graph_store.get_neighbors(id2):
            edges = self.graph_store.graph[id2][neighbor]
            for relation, attrs in edges.items():
                self.graph_store.add_edge(id1, neighbor, relation, **attrs)

        # Update cache
        self.entity_cache[entity2.strip().lower()] = id1

        # Note: In production, would also handle incoming edges and remove old node

        return True

    def get_statistics(self) -> dict[str, Any]:
        """Get graph construction statistics."""
        return {
            "graph_stats": self.graph_store.get_stats(),
            "cached_entities": len(self.entity_cache),
            "entity_types": self._count_entity_types(),
        }

    def _count_entity_types(self) -> dict[str, int]:
        """Count entities by type."""
        type_counts: dict[str, int] = {}
        for _node_id, attrs in self.graph_store.graph.nodes(data=True):
            node_type = attrs.get("node_type", "unknown")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        return type_counts


# Global singleton
_graph_constructor: GraphConstructor | None = None


def get_graph_constructor() -> GraphConstructor:
    """
    Get global graph constructor instance.

    Returns:
        GraphConstructor instance
    """
    global _graph_constructor

    if _graph_constructor is None:
        _graph_constructor = GraphConstructor()

    return _graph_constructor
