"""Memory Consolidation Engine for Advanced Memory Hierarchy.

Implements intelligent memory consolidation with importance scoring,
tiered storage management, and cross-session persistence.

Based on A-Mem (Agentic Memory) research patterns for LLM agents.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryTier(str, Enum):
    """Memory storage tiers based on access patterns and importance."""

    HOT = "hot"  # Frequently accessed, kept in-memory
    WARM = "warm"  # Moderately accessed, Redis/fast storage
    COLD = "cold"  # Rarely accessed, persistent storage
    ARCHIVE = "archive"  # Long-term archive, compressed


class ConsolidationStrategy(str, Enum):
    """Strategy for consolidating memories."""

    SUMMARIZE = "summarize"  # Summarize related memories
    MERGE = "merge"  # Merge duplicate/similar memories
    COMPRESS = "compress"  # Compress verbose memories
    DISTILL = "distill"  # Extract key insights
    CLUSTER = "cluster"  # Group by semantic similarity


@dataclass
class ImportanceScore:
    """Multi-factor importance score for a memory."""

    recency: float = 0.0  # How recent (0-1)
    frequency: float = 0.0  # Access frequency (0-1)
    relevance: float = 0.0  # Query relevance (0-1)
    emotional_salience: float = 0.0  # Emotional importance (0-1)
    causal_strength: float = 0.0  # Causal connections (0-1)
    uniqueness: float = 0.0  # Information uniqueness (0-1)

    @property
    def composite(self) -> float:
        """Weighted composite score."""
        weights = {
            "recency": 0.20,
            "frequency": 0.25,
            "relevance": 0.25,
            "emotional_salience": 0.10,
            "causal_strength": 0.10,
            "uniqueness": 0.10,
        }
        return sum(getattr(self, k) * v for k, v in weights.items())

    def to_dict(self) -> dict[str, float]:
        return {
            "recency": self.recency,
            "frequency": self.frequency,
            "relevance": self.relevance,
            "emotional_salience": self.emotional_salience,
            "causal_strength": self.causal_strength,
            "uniqueness": self.uniqueness,
            "composite": self.composite,
        }


@dataclass
class MemoryEntry:
    """A memory entry with metadata for consolidation."""

    id: str
    content: str
    embedding: list[float] | None = None
    tier: MemoryTier = MemoryTier.WARM
    importance: ImportanceScore = field(default_factory=ImportanceScore)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    tags: set[str] = field(default_factory=set)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "tier": self.tier.value,
            "importance": self.importance.to_dict(),
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "tags": list(self.tags),
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class ConsolidationResult:
    """Result of a consolidation operation."""

    strategy: ConsolidationStrategy
    original_count: int
    consolidated_count: int
    bytes_saved: int
    entries_promoted: int
    entries_demoted: int
    entries_archived: int
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "original_count": self.original_count,
            "consolidated_count": self.consolidated_count,
            "bytes_saved": self.bytes_saved,
            "entries_promoted": self.entries_promoted,
            "entries_demoted": self.entries_demoted,
            "entries_archived": self.entries_archived,
            "duration_ms": self.duration_ms,
        }


class ImportanceScorer:
    """Calculates importance scores for memories."""

    def __init__(
        self,
        recency_half_life_hours: float = 24.0,
        frequency_decay: float = 0.1,
        relevance_threshold: float = 0.5,
    ):
        self.recency_half_life = timedelta(hours=recency_half_life_hours)
        self.frequency_decay = frequency_decay
        self.relevance_threshold = relevance_threshold
        self._keyword_weights: dict[str, float] = {}

    def score_recency(self, created_at: datetime, now: datetime | None = None) -> float:
        """Score based on age with exponential decay."""
        now = now or datetime.now(UTC)
        age = now - created_at
        half_lives = age.total_seconds() / self.recency_half_life.total_seconds()
        return 2 ** (-half_lives)

    def score_frequency(self, access_count: int, max_count: int = 100) -> float:
        """Score based on access frequency with saturation."""
        normalized = min(access_count / max_count, 1.0)
        return 1 - (1 - normalized) ** 2  # Quadratic saturation

    async def score_relevance(
        self,
        memory: MemoryEntry,
        query_embedding: list[float] | None = None,
    ) -> float:
        """Score based on relevance to current context."""
        if memory.embedding is None or query_embedding is None:
            return 0.5  # Default neutral score

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(memory.embedding, query_embedding, strict=False))
        mag_a = sum(a * a for a in memory.embedding) ** 0.5
        mag_b = sum(b * b for b in query_embedding) ** 0.5

        if mag_a == 0 or mag_b == 0:
            return 0.0

        similarity = dot_product / (mag_a * mag_b)
        return max(0.0, min(1.0, (similarity + 1) / 2))  # Normalize to [0,1]

    def score_emotional_salience(self, content: str) -> float:
        """Score based on emotional content indicators."""
        emotional_markers = [
            "important",
            "critical",
            "urgent",
            "must",
            "need",
            "success",
            "failure",
            "error",
            "warning",
            "breakthrough",
            "decision",
            "agree",
            "disagree",
            "concern",
            "priority",
        ]
        content_lower = content.lower()
        matches = sum(1 for marker in emotional_markers if marker in content_lower)
        return min(matches / 5, 1.0)

    def score_uniqueness(
        self,
        content: str,
        content_hashes: set[str],
    ) -> float:
        """Score based on information uniqueness."""
        content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:16]
        if content_hash in content_hashes:
            return 0.3
        return 0.8 + 0.2 * (1 - len(content_hashes) / 1000)

    async def compute_score(
        self,
        memory: MemoryEntry,
        query_embedding: list[float] | None = None,
        content_hashes: set[str] | None = None,
    ) -> ImportanceScore:
        """Compute full importance score."""
        content_hashes = content_hashes or set()

        return ImportanceScore(
            recency=self.score_recency(memory.created_at),
            frequency=self.score_frequency(memory.access_count),
            relevance=await self.score_relevance(memory, query_embedding),
            emotional_salience=self.score_emotional_salience(memory.content),
            causal_strength=0.5,  # Would require causal graph analysis
            uniqueness=self.score_uniqueness(memory.content, content_hashes),
        )


class TieredStorageManager:
    """Manages memory across storage tiers."""

    def __init__(
        self,
        hot_max_entries: int = 100,
        warm_max_entries: int = 1000,
        cold_max_entries: int = 10000,
        promotion_threshold: float = 0.8,
        demotion_threshold: float = 0.3,
    ):
        self.hot_max = hot_max_entries
        self.warm_max = warm_max_entries
        self.cold_max = cold_max_entries
        self.promotion_threshold = promotion_threshold
        self.demotion_threshold = demotion_threshold

        # In-memory hot tier
        self._hot: dict[str, MemoryEntry] = {}
        # Warm tier (would be Redis in production)
        self._warm: dict[str, MemoryEntry] = {}
        # Cold tier (would be persistent storage)
        self._cold: dict[str, MemoryEntry] = {}
        # Archive tier (compressed)
        self._archive: dict[str, MemoryEntry] = {}

        self._tier_maps = {
            MemoryTier.HOT: self._hot,
            MemoryTier.WARM: self._warm,
            MemoryTier.COLD: self._cold,
            MemoryTier.ARCHIVE: self._archive,
        }

    async def store(self, memory: MemoryEntry, tier: MemoryTier | None = None) -> None:
        """Store memory in appropriate tier."""
        target_tier = tier or self._determine_tier(memory)
        memory.tier = target_tier

        tier_map = self._tier_maps[target_tier]
        tier_map[memory.id] = memory

        # Enforce tier limits
        await self._enforce_limits(target_tier)

    async def retrieve(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve memory from any tier."""
        for tier in MemoryTier:
            tier_map = self._tier_maps[tier]
            if memory_id in tier_map:
                memory = tier_map[memory_id]
                memory.access_count += 1
                memory.last_accessed = datetime.now(UTC)
                return memory
        return None

    def _determine_tier(self, memory: MemoryEntry) -> MemoryTier:
        """Determine appropriate tier based on importance."""
        score = memory.importance.composite
        if score >= self.promotion_threshold:
            return MemoryTier.HOT
        if score >= self.demotion_threshold:
            return MemoryTier.WARM
        return MemoryTier.COLD

    async def _enforce_limits(self, tier: MemoryTier) -> None:
        """Enforce entry limits for tier by demoting excess entries."""
        tier_map = self._tier_maps[tier]
        limits = {
            MemoryTier.HOT: self.hot_max,
            MemoryTier.WARM: self.warm_max,
            MemoryTier.COLD: self.cold_max,
            MemoryTier.ARCHIVE: None,  # No limit
        }

        limit = limits[tier]
        if limit is None or len(tier_map) <= limit:
            return

        # Sort by importance and demote lowest
        sorted_entries = sorted(
            tier_map.values(),
            key=lambda m: m.importance.composite,
        )

        excess = len(tier_map) - limit
        for entry in sorted_entries[:excess]:
            await self._demote(entry)

    async def _demote(self, memory: MemoryEntry) -> None:
        """Demote memory to next lower tier."""
        current_tier = memory.tier
        tier_order = [MemoryTier.HOT, MemoryTier.WARM, MemoryTier.COLD, MemoryTier.ARCHIVE]

        current_idx = tier_order.index(current_tier)
        if current_idx >= len(tier_order) - 1:
            return  # Already at lowest tier

        new_tier = tier_order[current_idx + 1]

        # Remove from current tier
        self._tier_maps[current_tier].pop(memory.id, None)

        # Add to new tier
        memory.tier = new_tier
        self._tier_maps[new_tier][memory.id] = memory

    async def promote(self, memory: MemoryEntry) -> None:
        """Promote memory to next higher tier."""
        current_tier = memory.tier
        tier_order = [MemoryTier.HOT, MemoryTier.WARM, MemoryTier.COLD, MemoryTier.ARCHIVE]

        current_idx = tier_order.index(current_tier)
        if current_idx <= 0:
            return  # Already at highest tier

        new_tier = tier_order[current_idx - 1]

        # Remove from current tier
        self._tier_maps[current_tier].pop(memory.id, None)

        # Add to new tier
        memory.tier = new_tier
        self._tier_maps[new_tier][memory.id] = memory

        # Enforce limits on new tier
        await self._enforce_limits(new_tier)

    def get_tier_stats(self) -> dict[str, dict[str, int]]:
        """Get statistics for each tier."""
        return {
            tier.value: {
                "count": len(self._tier_maps[tier]),
                "total_bytes": sum(len(m.content.encode()) for m in self._tier_maps[tier].values()),
            }
            for tier in MemoryTier
        }


class ConsolidationEngine:
    """Engine for memory consolidation operations."""

    def __init__(
        self,
        scorer: ImportanceScorer | None = None,
        storage: TieredStorageManager | None = None,
        summarizer: Callable[[list[str]], str] | None = None,
    ):
        self.scorer = scorer or ImportanceScorer()
        self.storage = storage or TieredStorageManager()
        self._summarizer = summarizer or self._default_summarizer
        self._consolidation_history: list[ConsolidationResult] = []

    @staticmethod
    def _default_summarizer(texts: list[str]) -> str:
        """Default summarization by truncation and concatenation."""
        combined = " ".join(t[:200] for t in texts[:5])
        return combined[:500] + "..." if len(combined) > 500 else combined

    async def consolidate(
        self,
        memories: list[MemoryEntry],
        strategy: ConsolidationStrategy = ConsolidationStrategy.SUMMARIZE,
    ) -> tuple[list[MemoryEntry], ConsolidationResult]:
        """Consolidate memories using specified strategy."""
        import time

        start_time = time.monotonic()
        original_count = len(memories)
        original_bytes = sum(len(m.content.encode()) for m in memories)

        if strategy == ConsolidationStrategy.SUMMARIZE:
            consolidated = await self._consolidate_summarize(memories)
        elif strategy == ConsolidationStrategy.MERGE:
            consolidated = await self._consolidate_merge(memories)
        elif strategy == ConsolidationStrategy.COMPRESS:
            consolidated = await self._consolidate_compress(memories)
        elif strategy == ConsolidationStrategy.DISTILL:
            consolidated = await self._consolidate_distill(memories)
        elif strategy == ConsolidationStrategy.CLUSTER:
            consolidated = await self._consolidate_cluster(memories)
        else:
            consolidated = memories

        # Calculate tier movements
        promoted = demoted = archived = 0
        for memory in consolidated:
            await self.scorer.compute_score(memory)
            new_tier = self._determine_optimal_tier(memory)

            if new_tier.value < memory.tier.value:
                promoted += 1
            elif new_tier.value > memory.tier.value:
                if new_tier == MemoryTier.ARCHIVE:
                    archived += 1
                else:
                    demoted += 1

        consolidated_bytes = sum(len(m.content.encode()) for m in consolidated)
        duration_ms = (time.monotonic() - start_time) * 1000

        result = ConsolidationResult(
            strategy=strategy,
            original_count=original_count,
            consolidated_count=len(consolidated),
            bytes_saved=original_bytes - consolidated_bytes,
            entries_promoted=promoted,
            entries_demoted=demoted,
            entries_archived=archived,
            duration_ms=duration_ms,
        )

        self._consolidation_history.append(result)
        return consolidated, result

    def _determine_optimal_tier(self, memory: MemoryEntry) -> MemoryTier:
        """Determine optimal tier for memory."""
        score = memory.importance.composite
        if score >= 0.8:
            return MemoryTier.HOT
        if score >= 0.5:
            return MemoryTier.WARM
        if score >= 0.2:
            return MemoryTier.COLD
        return MemoryTier.ARCHIVE

    async def _consolidate_summarize(
        self,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Summarize related memories into fewer entries."""
        if len(memories) <= 3:
            return memories

        # Group by tags or source
        groups: dict[str, list[MemoryEntry]] = defaultdict(list)
        for memory in memories:
            key = memory.source or "default"
            groups[key].append(memory)

        consolidated = []
        for group_key, group_memories in groups.items():
            if len(group_memories) <= 2:
                consolidated.extend(group_memories)
            else:
                # Summarize the group
                contents = [m.content for m in group_memories]
                summary = self._summarizer(contents)

                summary_entry = MemoryEntry(
                    id=f"consolidated_{hashlib.md5(summary.encode(), usedforsecurity=False).hexdigest()[:8]}",
                    content=summary,
                    tier=MemoryTier.WARM,
                    created_at=max(m.created_at for m in group_memories),
                    access_count=sum(m.access_count for m in group_memories),
                    tags=set().union(*(m.tags for m in group_memories)),
                    source=group_key,
                    metadata={"consolidated_from": [m.id for m in group_memories]},
                )
                consolidated.append(summary_entry)

        return consolidated

    async def _consolidate_merge(
        self,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Merge duplicate or near-duplicate memories."""
        if len(memories) <= 1:
            return memories

        # Simple content-based deduplication
        seen_hashes: dict[str, MemoryEntry] = {}

        for memory in memories:
            content_hash = hashlib.md5(
                memory.content.lower().encode(), usedforsecurity=False
            ).hexdigest()[:16]

            if content_hash in seen_hashes:
                # Merge into existing
                existing = seen_hashes[content_hash]
                existing.access_count += memory.access_count
                existing.tags.update(memory.tags)
            else:
                seen_hashes[content_hash] = memory

        return list(seen_hashes.values())

    async def _consolidate_compress(
        self,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Compress verbose memories."""
        compressed = []
        for memory in memories:
            if len(memory.content) > 500:
                # Truncate while preserving key information
                content = memory.content
                compressed_content = content[:200] + " [...] " + content[-200:]
                memory.content = compressed_content
                memory.metadata["compressed"] = True
            compressed.append(memory)

        return compressed

    async def _consolidate_distill(
        self,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Extract key insights from memories."""
        # Group by importance score
        high_importance = [m for m in memories if m.importance.composite >= 0.7]
        medium_importance = [m for m in memories if 0.3 <= m.importance.composite < 0.7]
        low_importance = [m for m in memories if m.importance.composite < 0.3]

        # Keep high importance as-is
        distilled = list(high_importance)

        # Summarize medium importance
        if medium_importance:
            contents = [m.content for m in medium_importance]
            summary = self._summarizer(contents)
            distilled.append(
                MemoryEntry(
                    id=f"distilled_medium_{datetime.now(UTC).timestamp():.0f}",
                    content=summary,
                    tier=MemoryTier.WARM,
                    metadata={"distilled_from": len(medium_importance)},
                )
            )

        # Archive low importance (keep only count)
        if low_importance:
            distilled.append(
                MemoryEntry(
                    id=f"distilled_low_{datetime.now(UTC).timestamp():.0f}",
                    content=f"[Archived {len(low_importance)} low-importance memories]",
                    tier=MemoryTier.ARCHIVE,
                    metadata={"archived_count": len(low_importance)},
                )
            )

        return distilled

    async def _consolidate_cluster(
        self,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Group memories by semantic similarity."""
        # Without embeddings, fall back to tag-based clustering
        clusters: dict[str, list[MemoryEntry]] = defaultdict(list)

        for memory in memories:
            cluster_key = sorted(memory.tags)[0] if memory.tags else "uncategorized"
            clusters[cluster_key].append(memory)

        consolidated = []
        for _cluster_key, cluster_memories in clusters.items():
            sorted_memories = sorted(
                cluster_memories,
                key=lambda m: m.importance.composite,
                reverse=True,
            )
            consolidated.extend(sorted_memories[:3])

        return consolidated

    async def run_maintenance(self) -> dict[str, Any]:
        """Run periodic maintenance on memory tiers."""
        stats = {
            "tier_stats": self.storage.get_tier_stats(),
            "consolidation_runs": len(self._consolidation_history),
            "last_run": datetime.now(UTC).isoformat(),
        }

        all_memories = []
        for tier in MemoryTier:
            tier_map = self.storage._tier_maps[tier]
            all_memories.extend(tier_map.values())

        content_hashes = {
            hashlib.md5(m.content.encode(), usedforsecurity=False).hexdigest()[:16]
            for m in all_memories
        }

        for memory in all_memories:
            memory.importance = await self.scorer.compute_score(
                memory,
                content_hashes=content_hashes,
            )

        stats["memories_rescored"] = len(all_memories)
        return stats

    def get_history(self) -> list[dict[str, Any]]:
        """Get consolidation history."""
        return [r.to_dict() for r in self._consolidation_history]


# Factory functions
def create_consolidation_engine(
    hot_max: int = 100,
    warm_max: int = 1000,
    cold_max: int = 10000,
) -> ConsolidationEngine:
    """Create a consolidation engine with default configuration."""
    storage = TieredStorageManager(
        hot_max_entries=hot_max,
        warm_max_entries=warm_max,
        cold_max_entries=cold_max,
    )
    scorer = ImportanceScorer()
    return ConsolidationEngine(scorer=scorer, storage=storage)


__all__ = [
    "ConsolidationEngine",
    "ConsolidationResult",
    "ConsolidationStrategy",
    "ImportanceScore",
    "ImportanceScorer",
    "MemoryEntry",
    "MemoryTier",
    "TieredStorageManager",
    "create_consolidation_engine",
]
