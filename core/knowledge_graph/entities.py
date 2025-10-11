"""Knowledge Graph Entity Models.

This module defines data models for knowledge graph entities and relations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KGNode:
    """Knowledge graph node."""

    node_id: str
    label: str
    node_type: str = "entity"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KGEdge:
    """Knowledge graph edge."""

    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeTriple:
    """Knowledge triple (subject-relation-object)."""

    subject: str
    relation: str
    obj: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.obj,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


@dataclass
class EntityMention:
    """Mention of an entity in text."""

    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationMention:
    """Mention of a relation in text."""

    subject: EntityMention
    relation: str
    obj: EntityMention
    confidence: float = 1.0
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
