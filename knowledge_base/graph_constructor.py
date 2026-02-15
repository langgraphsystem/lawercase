"""Knowledge Graph Constructor for Graph-Enhanced RAG.

Builds and maintains knowledge graphs from documents:
- Entity extraction (NER)
- Relation extraction
- Graph construction and updates
- Community detection for hierarchical structure
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    LAW = "law"
    REGULATION = "regulation"
    CASE = "case"
    CONCEPT = "concept"
    DOCUMENT = "document"
    CRITERION = "criterion"  # EB-1A specific
    EVIDENCE = "evidence"
    UNKNOWN = "unknown"


class RelationType(str, Enum):
    """Types of relations between entities."""

    CITES = "cites"
    REFERENCES = "references"
    MENTIONS = "mentions"
    PART_OF = "part_of"
    HAS_REQUIREMENT = "has_requirement"
    SATISFIES = "satisfies"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    AUTHORED_BY = "authored_by"
    OCCURRED_AT = "occurred_at"
    APPLIES_TO = "applies_to"
    EXAMPLE_OF = "example_of"
    RELATED_TO = "related_to"


@dataclass
class Entity:
    """An entity in the knowledge graph."""

    id: str
    name: str
    entity_type: EntityType
    aliases: set[str] = field(default_factory=set)
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    source_docs: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "aliases": list(self.aliases),
            "properties": self.properties,
            "source_docs": list(self.source_docs),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Relation:
    """A relation between two entities."""

    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    source_docs: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "properties": self.properties,
            "source_docs": list(self.source_docs),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Community:
    """A community (cluster) of related entities."""

    id: str
    name: str
    entity_ids: set[str] = field(default_factory=set)
    summary: str = ""
    level: int = 0  # Hierarchy level
    parent_id: str | None = None
    child_ids: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_ids": list(self.entity_ids),
            "summary": self.summary,
            "level": self.level,
            "parent_id": self.parent_id,
            "child_ids": list(self.child_ids),
        }


class EntityExtractor:
    """Extract entities from text using pattern matching and NER."""

    def __init__(self):
        # Legal/EB-1A specific patterns
        self._patterns = {
            EntityType.CRITERION: [
                r"criterion\s+(\d+)",
                r"extraordinary ability",
                r"outstanding professor",
                r"multinational manager",
            ],
            EntityType.LAW: [
                r"8\s*U\.?S\.?C\.?\s*§?\s*\d+",
                r"INA\s*§?\s*\d+",
                r"8\s*C\.?F\.?R\.?\s*§?\s*[\d\.]+",
            ],
            EntityType.CASE: [
                r"Matter of [A-Z][a-z]+",
                r"[A-Z][a-z]+ v\. [A-Z][a-z]+",
                r"AAO [A-Z]{3}\d+-\d+",
            ],
        }

        # Simple keyword-based extraction for demo
        self._keywords = {
            EntityType.CRITERION: [
                "awards",
                "membership",
                "published material",
                "judging",
                "original contributions",
                "scholarly articles",
                "exhibitions",
                "leading role",
                "high salary",
                "commercial success",
            ],
            EntityType.EVIDENCE: [
                "recommendation letter",
                "citation",
                "publication",
                "patent",
                "award",
                "membership certificate",
            ],
        }

    async def extract(
        self,
        text: str,
        doc_id: str,
    ) -> list[Entity]:
        """Extract entities from text."""
        import re

        entities = []
        seen_names: set[str] = set()

        # Pattern-based extraction
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match if isinstance(match, str) else match[0]
                    if name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        entity_id = self._make_id(name, entity_type)
                        entities.append(
                            Entity(
                                id=entity_id,
                                name=name,
                                entity_type=entity_type,
                                source_docs={doc_id},
                            )
                        )

        # Keyword-based extraction
        text_lower = text.lower()
        for entity_type, keywords in self._keywords.items():
            for keyword in keywords:
                if keyword in text_lower and keyword not in seen_names:
                    seen_names.add(keyword)
                    entity_id = self._make_id(keyword, entity_type)
                    entities.append(
                        Entity(
                            id=entity_id,
                            name=keyword.title(),
                            entity_type=entity_type,
                            source_docs={doc_id},
                        )
                    )

        return entities

    def _make_id(self, name: str, entity_type: EntityType) -> str:
        """Generate unique entity ID."""
        content = f"{entity_type.value}:{name.lower()}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]


class RelationExtractor:
    """Extract relations between entities."""

    def __init__(self):
        # Relation patterns (simplified)
        self._relation_patterns = [
            (r"(\w+)\s+cites?\s+(\w+)", RelationType.CITES),
            (r"(\w+)\s+references?\s+(\w+)", RelationType.REFERENCES),
            (r"(\w+)\s+supports?\s+(\w+)", RelationType.SUPPORTS),
            (r"(\w+)\s+requires?\s+(\w+)", RelationType.HAS_REQUIREMENT),
            (r"(\w+)\s+satisfies?\s+(\w+)", RelationType.SATISFIES),
        ]

    async def extract(
        self,
        text: str,
        entities: list[Entity],
        doc_id: str,
    ) -> list[Relation]:
        """Extract relations between entities."""
        relations = []
        entity_names = {e.name.lower(): e for e in entities}

        # Co-occurrence based relations
        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                # Check if entities appear close together
                if self._are_related(text, e1.name, e2.name):
                    relation_id = self._make_id(e1.id, e2.id, RelationType.RELATED_TO)
                    relations.append(
                        Relation(
                            id=relation_id,
                            source_id=e1.id,
                            target_id=e2.id,
                            relation_type=RelationType.RELATED_TO,
                            source_docs={doc_id},
                        )
                    )

        return relations

    def _are_related(
        self,
        text: str,
        name1: str,
        name2: str,
        window: int = 200,
    ) -> bool:
        """Check if two entities appear close together in text."""
        text_lower = text.lower()
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        pos1 = text_lower.find(name1_lower)
        pos2 = text_lower.find(name2_lower)

        if pos1 == -1 or pos2 == -1:
            return False

        return abs(pos1 - pos2) < window

    def _make_id(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
    ) -> str:
        """Generate unique relation ID."""
        content = f"{source_id}:{target_id}:{relation_type.value}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]


class KnowledgeGraph:
    """Main knowledge graph data structure."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._communities: dict[str, Community] = {}

        # Indexes for fast lookup
        self._entity_by_name: dict[str, str] = {}  # name -> entity_id
        self._entity_by_type: dict[EntityType, set[str]] = defaultdict(set)
        self._relations_by_source: dict[str, set[str]] = defaultdict(set)
        self._relations_by_target: dict[str, set[str]] = defaultdict(set)
        self._relations_by_type: dict[RelationType, set[str]] = defaultdict(set)

    def add_entity(self, entity: Entity) -> None:
        """Add or update an entity."""
        if entity.id in self._entities:
            # Merge with existing
            existing = self._entities[entity.id]
            existing.aliases.update(entity.aliases)
            existing.source_docs.update(entity.source_docs)
            existing.properties.update(entity.properties)
            existing.updated_at = datetime.now(UTC)
        else:
            self._entities[entity.id] = entity
            self._entity_by_name[entity.name.lower()] = entity.id
            self._entity_by_type[entity.entity_type].add(entity.id)

    def add_relation(self, relation: Relation) -> None:
        """Add or update a relation."""
        if relation.id in self._relations:
            # Update weight
            existing = self._relations[relation.id]
            existing.weight += relation.weight
            existing.source_docs.update(relation.source_docs)
        else:
            self._relations[relation.id] = relation
            self._relations_by_source[relation.source_id].add(relation.id)
            self._relations_by_target[relation.target_id].add(relation.id)
            self._relations_by_type[relation.relation_type].add(relation.id)

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Get entity by name."""
        entity_id = self._entity_by_name.get(name.lower())
        return self._entities.get(entity_id) if entity_id else None

    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a given type."""
        entity_ids = self._entity_by_type.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[RelationType] | None = None,
        max_hops: int = 1,
    ) -> list[Entity]:
        """Get neighboring entities."""
        visited: set[str] = {entity_id}
        current_level = {entity_id}
        neighbors: list[Entity] = []

        for _ in range(max_hops):
            next_level: set[str] = set()

            for eid in current_level:
                # Outgoing relations
                for rel_id in self._relations_by_source.get(eid, set()):
                    rel = self._relations[rel_id]
                    if relation_types is None or rel.relation_type in relation_types:
                        if rel.target_id not in visited:
                            visited.add(rel.target_id)
                            next_level.add(rel.target_id)
                            if rel.target_id in self._entities:
                                neighbors.append(self._entities[rel.target_id])

                # Incoming relations
                for rel_id in self._relations_by_target.get(eid, set()):
                    rel = self._relations[rel_id]
                    if relation_types is None or rel.relation_type in relation_types:
                        if rel.source_id not in visited:
                            visited.add(rel.source_id)
                            next_level.add(rel.source_id)
                            if rel.source_id in self._entities:
                                neighbors.append(self._entities[rel.source_id])

            current_level = next_level

        return neighbors

    def get_relations_for_entity(self, entity_id: str) -> list[Relation]:
        """Get all relations involving an entity."""
        relation_ids = self._relations_by_source.get(
            entity_id, set()
        ) | self._relations_by_target.get(entity_id, set())
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    def get_subgraph(
        self,
        entity_ids: list[str],
        max_hops: int = 1,
    ) -> tuple[list[Entity], list[Relation]]:
        """Extract a subgraph around given entities."""
        all_entity_ids: set[str] = set(entity_ids)
        relations: list[Relation] = []

        # Expand to neighbors
        for eid in entity_ids:
            neighbors = self.get_neighbors(eid, max_hops=max_hops)
            all_entity_ids.update(n.id for n in neighbors)

        # Get all relations between these entities
        for eid in all_entity_ids:
            for rel in self.get_relations_for_entity(eid):
                if rel.source_id in all_entity_ids and rel.target_id in all_entity_ids:
                    relations.append(rel)

        entities = [self._entities[eid] for eid in all_entity_ids if eid in self._entities]
        return entities, relations

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        return {
            "entity_count": len(self._entities),
            "relation_count": len(self._relations),
            "community_count": len(self._communities),
            "entities_by_type": {t.value: len(ids) for t, ids in self._entity_by_type.items()},
            "relations_by_type": {t.value: len(ids) for t, ids in self._relations_by_type.items()},
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relations": [r.to_dict() for r in self._relations.values()],
            "communities": [c.to_dict() for c in self._communities.values()],
            "stats": self.get_stats(),
        }


class GraphConstructor:
    """Main class for building knowledge graphs from documents."""

    def __init__(
        self,
        entity_extractor: EntityExtractor | None = None,
        relation_extractor: RelationExtractor | None = None,
        embedder: Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]] | None = None,
    ):
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relation_extractor = relation_extractor or RelationExtractor()
        self.embedder = embedder
        self.graph = KnowledgeGraph()

        self._stats = {
            "documents_processed": 0,
            "entities_extracted": 0,
            "relations_extracted": 0,
        }

    async def process_document(
        self,
        text: str,
        doc_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[list[Entity], list[Relation]]:
        """Process a document and add to graph."""
        # Extract entities
        entities = await self.entity_extractor.extract(text, doc_id)

        # Generate embeddings if embedder available
        if self.embedder and entities:
            entity_texts = [e.name for e in entities]
            embeddings = await self.embedder(entity_texts)
            for entity, embedding in zip(entities, embeddings, strict=False):
                entity.embedding = embedding

        # Add entities to graph
        for entity in entities:
            self.graph.add_entity(entity)

        # Extract relations
        relations = await self.relation_extractor.extract(text, entities, doc_id)

        # Add relations to graph
        for relation in relations:
            self.graph.add_relation(relation)

        # Update stats
        self._stats["documents_processed"] += 1
        self._stats["entities_extracted"] += len(entities)
        self._stats["relations_extracted"] += len(relations)

        return entities, relations

    async def process_documents(
        self,
        documents: list[tuple[str, str, dict[str, Any] | None]],
        concurrency: int = 5,
    ) -> dict[str, Any]:
        """Process multiple documents in parallel."""
        semaphore = asyncio.Semaphore(concurrency)

        async def process_one(doc: tuple[str, str, dict[str, Any] | None]) -> None:
            async with semaphore:
                text, doc_id, metadata = doc
                await self.process_document(text, doc_id, metadata)

        await asyncio.gather(*[process_one(doc) for doc in documents])

        return self.get_stats()

    def get_stats(self) -> dict[str, Any]:
        """Get construction statistics."""
        return {
            **self._stats,
            "graph": self.graph.get_stats(),
        }


# Factory functions
def create_graph_constructor(
    embedder: Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]] | None = None,
) -> GraphConstructor:
    """Create a graph constructor with default extractors."""
    return GraphConstructor(embedder=embedder)


__all__ = [
    "Community",
    "Entity",
    "EntityExtractor",
    "EntityType",
    "GraphConstructor",
    "KnowledgeGraph",
    "Relation",
    "RelationExtractor",
    "RelationType",
    "create_graph_constructor",
]
