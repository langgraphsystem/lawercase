"""Memory Consolidation Policy - Deduplicate, merge, and compress memories.

This module provides:
- Semantic deduplication using cosine similarity
- Importance decay over time
- Memory compression/summarization for LLM extraction
- Batch consolidation for efficient processing
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from ..models import ConsolidateStats, MemoryRecord


@dataclass
class ConsolidationConfig:
    """Configuration for memory consolidation."""

    # Semantic deduplication
    similarity_threshold: float = 0.92  # Cosine similarity threshold for deduplication
    use_semantic_dedup: bool = True

    # Importance decay
    enable_decay: bool = True
    decay_half_life_days: float = 30.0  # Time for importance to halve
    min_importance: float = 0.1  # Floor for decayed importance

    # Compression
    enable_compression: bool = False
    compression_threshold: int = 50  # Compress when more than N similar memories
    max_memories_per_user: int = 10000

    # Batch processing
    batch_size: int = 100


@dataclass
class ConsolidationResult:
    """Result of consolidation operation."""

    deduplicated: int = 0
    decayed: int = 0
    compressed: int = 0
    merged: int = 0
    total_before: int = 0
    total_after: int = 0
    clusters: list[list[str]] = field(default_factory=list)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score between 0.0 and 1.0
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    a = np.array(vec1)
    b = np.array(vec2)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def find_semantic_duplicates(
    records: list[MemoryRecord],
    threshold: float = 0.92,
) -> list[list[MemoryRecord]]:
    """Find groups of semantically similar records.

    Uses cosine similarity between embeddings to identify duplicates.

    Args:
        records: List of MemoryRecord objects with embeddings
        threshold: Minimum similarity to consider as duplicate

    Returns:
        List of duplicate groups (each group is a list of similar records)
    """
    if not records:
        return []

    # Filter records with embeddings
    with_embeddings = [r for r in records if r.embedding]
    if len(with_embeddings) < 2:
        return []

    # Build similarity matrix
    n = len(with_embeddings)
    visited = set()
    clusters: list[list[MemoryRecord]] = []

    for i in range(n):
        if i in visited:
            continue

        cluster = [with_embeddings[i]]
        visited.add(i)

        for j in range(i + 1, n):
            if j in visited:
                continue

            sim = cosine_similarity(
                with_embeddings[i].embedding or [],
                with_embeddings[j].embedding or [],
            )

            if sim >= threshold:
                cluster.append(with_embeddings[j])
                visited.add(j)

        if len(cluster) > 1:
            clusters.append(cluster)

    return clusters


def merge_duplicate_records(
    duplicates: list[MemoryRecord],
) -> MemoryRecord:
    """Merge a group of duplicate records into one.

    Keeps the record with highest salience and merges metadata.

    Args:
        duplicates: List of duplicate MemoryRecord objects

    Returns:
        Merged MemoryRecord
    """
    if not duplicates:
        raise ValueError("Cannot merge empty list")

    if len(duplicates) == 1:
        return duplicates[0]

    # Sort by salience (descending), then by created_at (most recent first)
    sorted_dups = sorted(
        duplicates,
        key=lambda r: (r.salience, r.created_at or datetime.min.replace(tzinfo=UTC)),
        reverse=True,
    )

    # Use highest salience record as base
    base = sorted_dups[0]

    # Merge tags from all records
    all_tags = set(base.tags or [])
    for r in sorted_dups[1:]:
        if r.tags:
            all_tags.update(r.tags)

    # Merge metadata
    merged_metadata = dict(base.metadata or {})
    merged_metadata["merged_from"] = [r.id for r in sorted_dups if r.id]
    merged_metadata["merge_count"] = len(sorted_dups)

    # Calculate average confidence (handle None values)
    confidences = [r.confidence for r in sorted_dups if r.confidence is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7

    # Create merged record
    merged_id = f"merged_{hashlib.md5(base.text.encode(), usedforsecurity=False).hexdigest()[:12]}"

    return MemoryRecord(
        id=merged_id,
        user_id=base.user_id,
        type=base.type,
        text=base.text,
        embedding=base.embedding,
        salience=base.salience,
        confidence=avg_confidence,
        source=base.source,
        tags=list(all_tags),
        metadata=merged_metadata,
        created_at=base.created_at,
    )


def calculate_decay(
    created_at: datetime,
    half_life_days: float = 30.0,
    min_importance: float = 0.1,
    reference_time: datetime | None = None,
) -> float:
    """Calculate time-based importance decay factor.

    Uses exponential decay: factor = 0.5 ^ (days / half_life)

    Args:
        created_at: When the memory was created
        half_life_days: Days for importance to halve
        min_importance: Minimum decay factor (floor)
        reference_time: Reference time for decay (default: now)

    Returns:
        Decay factor between min_importance and 1.0
    """
    if reference_time is None:
        reference_time = datetime.now(UTC)

    # Ensure timezone awareness
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=UTC)

    age_days = (reference_time - created_at).total_seconds() / 86400.0

    if age_days <= 0:
        return 1.0

    # Exponential decay
    decay = math.pow(0.5, age_days / half_life_days)

    return max(min_importance, decay)


def apply_importance_decay(
    records: list[MemoryRecord],
    half_life_days: float = 30.0,
    min_importance: float = 0.1,
) -> list[MemoryRecord]:
    """Apply time-based decay to record salience.

    Args:
        records: List of MemoryRecord objects
        half_life_days: Days for importance to halve
        min_importance: Minimum importance floor

    Returns:
        Records with updated salience values
    """
    now = datetime.now(UTC)
    decayed_records = []

    for r in records:
        if r.created_at:
            decay_factor = calculate_decay(
                r.created_at,
                half_life_days=half_life_days,
                min_importance=min_importance,
                reference_time=now,
            )
            # Apply decay to salience
            new_salience = r.salience * decay_factor
            r.salience = max(min_importance, new_salience)
        decayed_records.append(r)

    return decayed_records


class ConsolidationPolicy:
    """Configurable memory consolidation policy.

    Provides semantic deduplication, importance decay, and memory compression.
    """

    def __init__(
        self,
        config: ConsolidationConfig | None = None,
        llm_client: Any | None = None,
    ) -> None:
        """Initialize consolidation policy.

        Args:
            config: ConsolidationConfig (uses defaults if None)
            llm_client: LLM client for compression (optional)
        """
        self.config = config or ConsolidationConfig()
        self.llm_client = llm_client

    async def consolidate(
        self,
        records: list[MemoryRecord],
        user_id: str | None = None,
    ) -> tuple[list[MemoryRecord], ConsolidationResult]:
        """Consolidate memory records.

        Steps:
        1. Apply importance decay (if enabled)
        2. Find semantic duplicates (if enabled)
        3. Merge duplicate groups
        4. Compress if threshold exceeded (if enabled)

        Args:
            records: List of MemoryRecord objects
            user_id: Optional user filter

        Returns:
            Tuple of (consolidated records, ConsolidationResult)
        """
        result = ConsolidationResult(total_before=len(records))

        # Filter by user if specified
        if user_id:
            records = [r for r in records if r.user_id == user_id]

        if not records:
            return [], result

        # Step 1: Apply importance decay
        if self.config.enable_decay:
            records = apply_importance_decay(
                records,
                half_life_days=self.config.decay_half_life_days,
                min_importance=self.config.min_importance,
            )
            result.decayed = len(records)

        # Step 2: Find semantic duplicates
        consolidated = []
        if self.config.use_semantic_dedup:
            clusters = find_semantic_duplicates(
                records,
                threshold=self.config.similarity_threshold,
            )

            # Track which records are in clusters
            clustered_ids = set()
            for cluster in clusters:
                for r in cluster:
                    if r.id:
                        clustered_ids.add(r.id)

            # Add non-clustered records as-is
            for r in records:
                if r.id not in clustered_ids:
                    consolidated.append(r)

            # Merge each cluster
            for cluster in clusters:
                merged = merge_duplicate_records(cluster)
                consolidated.append(merged)
                result.merged += len(cluster) - 1

            result.deduplicated = result.merged
            result.clusters = [[r.id or "" for r in c] for c in clusters]
        else:
            # Exact text deduplication (fallback)
            seen_texts: set[tuple[str | None, str, str]] = set()
            for r in records:
                key = (r.user_id, r.type, r.text)
                if key in seen_texts:
                    result.deduplicated += 1
                    continue
                seen_texts.add(key)
                consolidated.append(r)

        # Step 3: Compress if too many similar memories
        if (
            self.config.enable_compression
            and len(consolidated) > self.config.compression_threshold
            and self.llm_client
        ):
            consolidated = await self._compress_memories(consolidated)
            result.compressed = result.total_before - len(consolidated)

        result.total_after = len(consolidated)
        return consolidated, result

    async def _compress_memories(
        self,
        records: list[MemoryRecord],
    ) -> list[MemoryRecord]:
        """Compress memories using LLM summarization.

        This is a placeholder for LLM-based compression.
        Implementation requires LLM client to be provided.

        Args:
            records: Records to compress

        Returns:
            Compressed records
        """
        # TODO: Implement LLM-based compression
        # For now, keep top N by salience
        sorted_records = sorted(records, key=lambda r: r.salience, reverse=True)
        return sorted_records[: self.config.max_memories_per_user]

    def to_stats(self, result: ConsolidationResult) -> ConsolidateStats:
        """Convert ConsolidationResult to ConsolidateStats for backward compatibility.

        Args:
            result: ConsolidationResult object

        Returns:
            ConsolidateStats object
        """
        return ConsolidateStats(
            deduplicated=result.deduplicated,
            total_after=result.total_after,
        )
