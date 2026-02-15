"""Agentic Memory System (A-Mem).

Based on latest research (2025-2026):
- A-Mem: LLM-driven memory note construction with Zettelkasten principles
- Memory-R1: RL-based adaptive memory management
- Temporal Knowledge Graph: Versioned entity relationships

Features:
- Atomic memory notes with contextual understanding
- Flexible organization with dynamic linking
- Memory operations: add, update, delete, consolidate
- Episodic, Semantic, and Associative memory types
- Temporal reasoning with decay functions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
from typing import Any
import uuid

import structlog

logger = structlog.get_logger(__name__)


class MemoryType(str, Enum):
    """Types of memory in the A-Mem system."""

    EPISODIC = "episodic"  # Specific events and interactions
    SEMANTIC = "semantic"  # General knowledge (RAG-based)
    ASSOCIATIVE = "associative"  # Entity relationships (graph-based)
    PROCEDURAL = "procedural"  # How-to knowledge
    WORKING = "working"  # Short-term active context


class MemoryOperation(str, Enum):
    """Memory operations supported by the system."""

    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    CONSOLIDATE = "consolidate"
    RETRIEVE = "retrieve"
    FORGET = "forget"  # Selective decay


@dataclass
class MemoryNote:
    """
    Atomic memory note following Zettelkasten principles.

    Each note is self-contained with:
    - Unique ID and content
    - LLM-generated contextual understanding
    - Links to related notes
    - Temporal metadata with decay
    """

    note_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    summary: str = ""  # LLM-generated summary
    context: str = ""  # LLM-generated contextual understanding
    memory_type: MemoryType = MemoryType.SEMANTIC

    # Linking (Zettelkasten)
    links: list[str] = field(default_factory=list)  # IDs of related notes
    tags: list[str] = field(default_factory=list)
    source: str = ""

    # Metadata
    case_id: str | None = None
    user_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0

    # Importance and decay
    importance: float = 0.5  # 0-1, affects retention
    decay_rate: float = 0.1  # Higher = faster forgetting
    confidence: float = 1.0  # Reliability of the memory

    # Embedding for semantic search
    embedding: list[float] | None = None

    def calculate_relevance(self, current_time: datetime | None = None) -> float:
        """
        Calculate current relevance score with temporal decay.

        Based on Ebbinghaus forgetting curve:
        R = e^(-t/S) where S is memory strength
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        # Time since last access (in days)
        time_delta = (current_time - self.accessed_at).total_seconds() / 86400

        # Memory strength based on importance and access frequency
        strength = self.importance * (1 + 0.1 * min(self.access_count, 10))

        # Decay factor
        import math

        decay = math.exp(-self.decay_rate * time_delta / max(strength, 0.1))

        return self.confidence * decay

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "note_id": self.note_id,
            "content": self.content,
            "summary": self.summary,
            "context": self.context,
            "memory_type": self.memory_type.value,
            "links": self.links,
            "tags": self.tags,
            "source": self.source,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "importance": self.importance,
            "decay_rate": self.decay_rate,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryNote:
        """Create from dictionary."""
        return cls(
            note_id=data.get("note_id", str(uuid.uuid4())),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            context=data.get("context", ""),
            memory_type=MemoryType(data.get("memory_type", "semantic")),
            links=data.get("links", []),
            tags=data.get("tags", []),
            source=data.get("source", ""),
            case_id=data.get("case_id"),
            user_id=data.get("user_id"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(UTC)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now(UTC)
            ),
            accessed_at=(
                datetime.fromisoformat(data["accessed_at"])
                if "accessed_at" in data
                else datetime.now(UTC)
            ),
            access_count=data.get("access_count", 0),
            importance=data.get("importance", 0.5),
            decay_rate=data.get("decay_rate", 0.1),
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class EntityNode:
    """
    Entity in the knowledge graph (Associative Memory).

    Represents people, organizations, documents, concepts, etc.
    """

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: str = ""  # person, organization, document, concept, criterion
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass
class EntityRelation:
    """
    Relationship between entities in the knowledge graph.

    Supports temporal versioning for tracking changes.
    """

    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: str = ""  # worked_at, authored, awarded, supports_criterion
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None  # None = still valid
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AgenticMemory:
    """
    Advanced memory system for AI agents.

    Implements:
    - A-Mem: Atomic notes with LLM-generated context
    - Memory-R1: Operations (add, update, delete, consolidate)
    - Temporal Knowledge Graph: Versioned entity relationships
    - Multi-tier storage: Working → Episodic → Semantic → Associative
    """

    def __init__(
        self,
        llm_client: Any | None = None,
        embedding_client: Any | None = None,
        max_working_memory: int = 10,
        consolidation_threshold: int = 100,
    ):
        """
        Initialize Agentic Memory.

        Args:
            llm_client: LLM for generating summaries and context
            embedding_client: Embedding model for semantic search
            max_working_memory: Maximum items in working memory
            consolidation_threshold: Trigger consolidation at this count
        """
        self.llm_client = llm_client
        self.embedding_client = embedding_client
        self.max_working_memory = max_working_memory
        self.consolidation_threshold = consolidation_threshold

        # Memory stores
        self._working_memory: list[MemoryNote] = []
        self._episodic_memory: dict[str, MemoryNote] = {}
        self._semantic_memory: dict[str, MemoryNote] = {}
        self._associative_memory: dict[str, EntityNode] = {}
        self._relations: dict[str, EntityRelation] = {}

        # Index for fast lookup
        self._tag_index: dict[str, set[str]] = {}
        self._case_index: dict[str, set[str]] = {}
        self._type_index: dict[MemoryType, set[str]] = {t: set() for t in MemoryType}

        # Statistics
        self._stats = {
            "total_adds": 0,
            "total_updates": 0,
            "total_deletes": 0,
            "total_consolidations": 0,
            "total_retrievals": 0,
        }

        logger.info("AgenticMemory initialized", max_working=max_working_memory)

    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        tags: list[str] | None = None,
        case_id: str | None = None,
        user_id: str | None = None,
        source: str = "",
        importance: float = 0.5,
        generate_context: bool = True,
    ) -> MemoryNote:
        """
        Add new memory note with LLM-generated context.

        Args:
            content: Raw content to remember
            memory_type: Type of memory
            tags: Tags for categorization
            case_id: Associated case
            user_id: Associated user
            source: Source of the information
            importance: Importance score (0-1)
            generate_context: Whether to generate LLM context

        Returns:
            Created MemoryNote
        """
        note = MemoryNote(
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            case_id=case_id,
            user_id=user_id,
            source=source,
            importance=importance,
        )

        # Generate LLM context if enabled and client available
        if generate_context and self.llm_client:
            note.summary, note.context = await self._generate_note_context(content)

        # Generate embedding if available
        if self.embedding_client:
            note.embedding = await self._generate_embedding(content)

        # Find and create links to related notes
        note.links = await self._find_related_notes(note)

        # Store in appropriate memory tier
        await self._store_note(note)

        # Update indices
        self._update_indices(note, "add")

        self._stats["total_adds"] += 1

        logger.info(
            "Memory added",
            note_id=note.note_id,
            memory_type=memory_type.value,
            tags=tags,
            links_count=len(note.links),
        )

        return note

    async def update(
        self,
        note_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        importance: float | None = None,
    ) -> MemoryNote | None:
        """
        Update existing memory note.

        Args:
            note_id: ID of note to update
            content: New content (optional)
            tags: New tags (optional)
            importance: New importance (optional)

        Returns:
            Updated note or None if not found
        """
        note = await self.get(note_id)
        if not note:
            return None

        if content is not None:
            note.content = content
            if self.llm_client:
                note.summary, note.context = await self._generate_note_context(content)
            if self.embedding_client:
                note.embedding = await self._generate_embedding(content)

        if tags is not None:
            # Update tag index
            for old_tag in note.tags:
                if old_tag in self._tag_index:
                    self._tag_index[old_tag].discard(note_id)
            note.tags = tags
            for new_tag in tags:
                if new_tag not in self._tag_index:
                    self._tag_index[new_tag] = set()
                self._tag_index[new_tag].add(note_id)

        if importance is not None:
            note.importance = importance

        note.updated_at = datetime.now(UTC)

        self._stats["total_updates"] += 1

        logger.info("Memory updated", note_id=note_id)

        return note

    async def delete(self, note_id: str) -> bool:
        """
        Delete memory note.

        Args:
            note_id: ID of note to delete

        Returns:
            True if deleted, False if not found
        """
        note = await self.get(note_id)
        if not note:
            return False

        # Remove from indices
        self._update_indices(note, "delete")

        # Remove from storage
        if note.memory_type == MemoryType.WORKING:
            self._working_memory = [n for n in self._working_memory if n.note_id != note_id]
        elif note.memory_type == MemoryType.EPISODIC:
            self._episodic_memory.pop(note_id, None)
        else:
            self._semantic_memory.pop(note_id, None)

        # Remove links to this note from other notes
        for other_note in self._semantic_memory.values():
            if note_id in other_note.links:
                other_note.links.remove(note_id)

        self._stats["total_deletes"] += 1

        logger.info("Memory deleted", note_id=note_id)

        return True

    async def get(self, note_id: str) -> MemoryNote | None:
        """
        Get memory note by ID and update access metadata.

        Args:
            note_id: Note ID

        Returns:
            MemoryNote or None
        """
        note = None

        # Check all memory tiers
        for wm_note in self._working_memory:
            if wm_note.note_id == note_id:
                note = wm_note
                break

        if not note:
            note = self._episodic_memory.get(note_id)

        if not note:
            note = self._semantic_memory.get(note_id)

        if note:
            # Update access metadata
            note.accessed_at = datetime.now(UTC)
            note.access_count += 1
            self._stats["total_retrievals"] += 1

        return note

    async def retrieve(
        self,
        query: str,
        memory_types: list[MemoryType] | None = None,
        tags: list[str] | None = None,
        case_id: str | None = None,
        top_k: int = 5,
        min_relevance: float = 0.1,
    ) -> list[MemoryNote]:
        """
        Retrieve relevant memories using semantic search.

        Args:
            query: Search query
            memory_types: Filter by memory types
            tags: Filter by tags
            case_id: Filter by case
            top_k: Maximum results
            min_relevance: Minimum relevance score

        Returns:
            List of relevant MemoryNotes
        """
        candidates: list[MemoryNote] = []

        # Collect candidates from appropriate tiers
        memory_types = memory_types or list(MemoryType)

        for note_id in self._type_index.get(MemoryType.SEMANTIC, set()):
            note = self._semantic_memory.get(note_id)
            if note:
                candidates.append(note)

        for note_id in self._type_index.get(MemoryType.EPISODIC, set()):
            note = self._episodic_memory.get(note_id)
            if note:
                candidates.append(note)

        # Working memory always included
        candidates.extend(self._working_memory)

        # Filter by tags
        if tags:
            tag_set = set(tags)
            candidates = [n for n in candidates if tag_set.intersection(n.tags)]

        # Filter by case_id
        if case_id:
            candidates = [n for n in candidates if n.case_id == case_id]

        # Score candidates
        scored: list[tuple[MemoryNote, float]] = []
        query_lower = query.lower()

        for note in candidates:
            # Calculate relevance score
            relevance = note.calculate_relevance()

            # Keyword matching boost
            keyword_score = 0.0
            content_lower = note.content.lower()
            for word in query_lower.split():
                if len(word) > 3 and word in content_lower:
                    keyword_score += 0.1

            # Embedding similarity if available
            embedding_score = 0.0
            if self.embedding_client and note.embedding:
                query_embedding = await self._generate_embedding(query)
                if query_embedding:
                    embedding_score = self._cosine_similarity(query_embedding, note.embedding)

            # Combined score
            final_score = relevance * 0.3 + keyword_score * 0.3 + embedding_score * 0.4

            if final_score >= min_relevance:
                scored.append((note, final_score))

        # Sort by score and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [note for note, _ in scored[:top_k]]

        # Update access metadata
        for note in results:
            note.accessed_at = datetime.now(UTC)
            note.access_count += 1

        self._stats["total_retrievals"] += len(results)

        logger.info(
            "Memory retrieved",
            query_length=len(query),
            candidates=len(candidates),
            results=len(results),
        )

        return results

    async def consolidate(self, case_id: str | None = None) -> int:
        """
        Consolidate memories: merge similar, remove obsolete.

        Based on Memory-R1 consolidation approach.

        Args:
            case_id: Consolidate only for specific case

        Returns:
            Number of notes consolidated
        """
        consolidated = 0

        # Get memories to consolidate
        memories = list(self._semantic_memory.values())
        if case_id:
            memories = [m for m in memories if m.case_id == case_id]

        # Group by tags
        tag_groups: dict[str, list[MemoryNote]] = {}
        for note in memories:
            key = "_".join(sorted(note.tags[:3])) if note.tags else "untagged"
            if key not in tag_groups:
                tag_groups[key] = []
            tag_groups[key].append(note)

        # Merge similar notes in each group
        for _, group in tag_groups.items():
            if len(group) < 2:
                continue

            # Find notes with high content similarity
            for i, note1 in enumerate(group):
                for note2 in group[i + 1 :]:
                    similarity = self._calculate_similarity(note1.content, note2.content)
                    if similarity > 0.8:
                        # Merge note2 into note1
                        await self._merge_notes(note1, note2)
                        await self.delete(note2.note_id)
                        consolidated += 1

        # Remove low-relevance notes
        current_time = datetime.now(UTC)
        for note in list(self._semantic_memory.values()):
            relevance = note.calculate_relevance(current_time)
            if relevance < 0.05 and note.access_count == 0:
                # Note has decayed and never accessed
                await self.delete(note.note_id)
                consolidated += 1

        self._stats["total_consolidations"] += consolidated

        logger.info("Memory consolidated", count=consolidated, case_id=case_id)

        return consolidated

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> EntityNode:
        """
        Add entity to knowledge graph.

        Args:
            name: Entity name
            entity_type: Type (person, organization, etc.)
            attributes: Entity attributes

        Returns:
            Created EntityNode
        """
        entity = EntityNode(
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
        )

        self._associative_memory[entity.entity_id] = entity

        logger.info(
            "Entity added",
            entity_id=entity.entity_id,
            name=name,
            entity_type=entity_type,
        )

        return entity

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        attributes: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> EntityRelation | None:
        """
        Add relation between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Type of relation
            attributes: Relation attributes
            confidence: Confidence score

        Returns:
            Created EntityRelation or None if entities not found
        """
        if source_id not in self._associative_memory:
            logger.warning("Source entity not found", source_id=source_id)
            return None
        if target_id not in self._associative_memory:
            logger.warning("Target entity not found", target_id=target_id)
            return None

        relation = EntityRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            attributes=attributes or {},
            confidence=confidence,
        )

        self._relations[relation.relation_id] = relation

        logger.info(
            "Relation added",
            relation_id=relation.relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
        )

        return relation

    async def get_entity_relations(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
    ) -> list[tuple[EntityRelation, EntityNode]]:
        """
        Get all relations for an entity.

        Args:
            entity_id: Entity ID
            relation_types: Filter by relation types

        Returns:
            List of (relation, connected_entity) tuples
        """
        results = []

        for relation in self._relations.values():
            if relation_types and relation.relation_type not in relation_types:
                continue

            if relation.source_id == entity_id:
                target = self._associative_memory.get(relation.target_id)
                if target:
                    results.append((relation, target))
            elif relation.target_id == entity_id:
                source = self._associative_memory.get(relation.source_id)
                if source:
                    results.append((relation, source))

        return results

    def get_working_memory(self) -> list[MemoryNote]:
        """Get current working memory contents."""
        return list(self._working_memory)

    def clear_working_memory(self) -> None:
        """Clear working memory."""
        self._working_memory.clear()
        logger.info("Working memory cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            **self._stats,
            "working_memory_size": len(self._working_memory),
            "episodic_memory_size": len(self._episodic_memory),
            "semantic_memory_size": len(self._semantic_memory),
            "entity_count": len(self._associative_memory),
            "relation_count": len(self._relations),
            "tag_count": len(self._tag_index),
        }

    # ========== PRIVATE METHODS ==========

    async def _store_note(self, note: MemoryNote) -> None:
        """Store note in appropriate memory tier."""
        if note.memory_type == MemoryType.WORKING:
            self._working_memory.append(note)
            # Manage working memory size
            if len(self._working_memory) > self.max_working_memory:
                # Move oldest to episodic
                oldest = self._working_memory.pop(0)
                oldest.memory_type = MemoryType.EPISODIC
                self._episodic_memory[oldest.note_id] = oldest
        elif note.memory_type == MemoryType.EPISODIC:
            self._episodic_memory[note.note_id] = note
        else:
            self._semantic_memory[note.note_id] = note

        # Check consolidation threshold
        total = len(self._semantic_memory) + len(self._episodic_memory)
        if total > self.consolidation_threshold:
            await self.consolidate()

    def _update_indices(self, note: MemoryNote, operation: str) -> None:
        """Update search indices."""
        if operation == "add":
            # Tag index
            for tag in note.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(note.note_id)

            # Case index
            if note.case_id:
                if note.case_id not in self._case_index:
                    self._case_index[note.case_id] = set()
                self._case_index[note.case_id].add(note.note_id)

            # Type index
            self._type_index[note.memory_type].add(note.note_id)

        elif operation == "delete":
            # Remove from all indices
            for tag in note.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(note.note_id)

            if note.case_id and note.case_id in self._case_index:
                self._case_index[note.case_id].discard(note.note_id)

            self._type_index[note.memory_type].discard(note.note_id)

    async def _generate_note_context(self, content: str) -> tuple[str, str]:
        """Generate summary and context using LLM."""
        if not self.llm_client:
            return "", ""

        try:
            prompt = f"""Analyze this memory content and provide:
1. A concise summary (1-2 sentences)
2. Contextual understanding (why this might be important, connections to other concepts)

Content:
{content[:2000]}

Respond in JSON format:
{{"summary": "...", "context": "..."}}
"""
            response = await self.llm_client.acomplete(prompt)
            data = json.loads(response)
            return data.get("summary", ""), data.get("context", "")
        except Exception as e:
            logger.warning("Failed to generate note context", error=str(e))
            return "", ""

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for text."""
        if not self.embedding_client:
            return None

        try:
            return await self.embedding_client.embed(text)
        except Exception as e:
            logger.warning("Failed to generate embedding", error=str(e))
            return None

    async def _find_related_notes(self, note: MemoryNote) -> list[str]:
        """Find notes related to this one."""
        related = []

        # Find by tags
        for tag in note.tags[:3]:
            if tag in self._tag_index:
                related.extend(list(self._tag_index[tag])[:5])

        # Remove duplicates and self
        related = list(set(related) - {note.note_id})

        return related[:10]

    async def _merge_notes(self, note1: MemoryNote, note2: MemoryNote) -> None:
        """Merge note2 into note1."""
        # Combine content
        if note2.content not in note1.content:
            note1.content = f"{note1.content}\n\n{note2.content}"

        # Merge tags
        note1.tags = list(set(note1.tags + note2.tags))

        # Merge links
        note1.links = list(set(note1.links + note2.links))

        # Update importance (weighted average)
        note1.importance = (
            note1.importance * note1.access_count + note2.importance * note2.access_count
        ) / max(note1.access_count + note2.access_count, 1)

        # Update metadata
        note1.updated_at = datetime.now(UTC)
        note1.access_count += note2.access_count

        # Regenerate context
        if self.llm_client:
            note1.summary, note1.context = await self._generate_note_context(note1.content)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / max(union, 1)

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        return dot_product / max(norm1 * norm2, 1e-10)


# Global instance
_agentic_memory: AgenticMemory | None = None


def get_agentic_memory(
    llm_client: Any | None = None,
    embedding_client: Any | None = None,
) -> AgenticMemory:
    """Get or create global AgenticMemory instance."""
    global _agentic_memory

    if _agentic_memory is None:
        _agentic_memory = AgenticMemory(
            llm_client=llm_client,
            embedding_client=embedding_client,
        )

    return _agentic_memory
