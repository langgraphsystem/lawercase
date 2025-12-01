"""Tests for memory consolidation policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.memory.models import MemoryRecord
from core.memory.policies.consolidation import (ConsolidationConfig,
                                                ConsolidationPolicy,
                                                apply_importance_decay,
                                                calculate_decay,
                                                cosine_similarity,
                                                find_semantic_duplicates,
                                                merge_duplicate_records)


class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0."""
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        assert cosine_similarity([], []) == 0.0
        assert cosine_similarity([1.0], []) == 0.0

    def test_different_length_vectors(self):
        """Different length vectors should return 0.0."""
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


class TestSemanticDuplicates:
    """Tests for semantic duplicate detection."""

    def test_find_exact_duplicates(self):
        """Should find records with identical embeddings."""
        records = [
            MemoryRecord(
                id="r1",
                user_id="u1",
                text="Test 1",
                embedding=[1.0, 0.0, 0.0],
            ),
            MemoryRecord(
                id="r2",
                user_id="u1",
                text="Test 2",
                embedding=[1.0, 0.0, 0.0],  # Same embedding
            ),
            MemoryRecord(
                id="r3",
                user_id="u1",
                text="Test 3",
                embedding=[0.0, 1.0, 0.0],  # Different
            ),
        ]

        clusters = find_semantic_duplicates(records, threshold=0.95)
        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_no_duplicates(self):
        """Should return empty list when no duplicates."""
        records = [
            MemoryRecord(
                id="r1",
                user_id="u1",
                text="Test 1",
                embedding=[1.0, 0.0, 0.0],
            ),
            MemoryRecord(
                id="r2",
                user_id="u1",
                text="Test 2",
                embedding=[0.0, 1.0, 0.0],
            ),
        ]

        clusters = find_semantic_duplicates(records, threshold=0.95)
        assert len(clusters) == 0

    def test_records_without_embeddings(self):
        """Should skip records without embeddings."""
        records = [
            MemoryRecord(id="r1", user_id="u1", text="Test 1"),
            MemoryRecord(id="r2", user_id="u1", text="Test 2"),
        ]

        clusters = find_semantic_duplicates(records, threshold=0.95)
        assert len(clusters) == 0


class TestMergeDuplicates:
    """Tests for duplicate record merging."""

    def test_merge_keeps_highest_salience(self):
        """Merged record should have highest salience from group."""
        now = datetime.now(UTC)
        records = [
            MemoryRecord(
                id="r1",
                user_id="u1",
                text="Important fact",
                salience=0.8,
                confidence=0.7,
                tags=["tag1"],
                created_at=now,
            ),
            MemoryRecord(
                id="r2",
                user_id="u1",
                text="Important fact variant",
                salience=0.9,
                confidence=0.8,
                tags=["tag2"],
                created_at=now,
            ),
        ]

        merged = merge_duplicate_records(records)
        assert merged.salience == 0.9
        assert "tag1" in merged.tags
        assert "tag2" in merged.tags
        assert merged.metadata.get("merge_count") == 2

    def test_merge_single_record(self):
        """Single record should return unchanged."""
        record = MemoryRecord(id="r1", user_id="u1", text="Test")
        merged = merge_duplicate_records([record])
        assert merged.id == "r1"

    def test_merge_empty_raises(self):
        """Merging empty list should raise."""
        with pytest.raises(ValueError):
            merge_duplicate_records([])


class TestImportanceDecay:
    """Tests for importance decay over time."""

    def test_no_decay_for_new_record(self):
        """Recent records should have decay factor ~1.0."""
        now = datetime.now(UTC)
        decay = calculate_decay(now, half_life_days=30.0)
        assert decay == pytest.approx(1.0, abs=0.01)

    def test_half_decay_at_half_life(self):
        """Record at half-life should have decay ~0.5."""
        now = datetime.now(UTC)
        created = now - timedelta(days=30)
        decay = calculate_decay(created, half_life_days=30.0, reference_time=now)
        assert decay == pytest.approx(0.5, abs=0.01)

    def test_decay_respects_minimum(self):
        """Very old records should not go below minimum."""
        now = datetime.now(UTC)
        very_old = now - timedelta(days=365)
        decay = calculate_decay(
            very_old,
            half_life_days=30.0,
            min_importance=0.1,
            reference_time=now,
        )
        assert decay >= 0.1

    def test_apply_decay_to_records(self):
        """Should update salience based on age."""
        now = datetime.now(UTC)
        records = [
            MemoryRecord(
                id="r1",
                user_id="u1",
                text="Recent",
                salience=1.0,
                created_at=now,
            ),
            MemoryRecord(
                id="r2",
                user_id="u1",
                text="Old",
                salience=1.0,
                created_at=now - timedelta(days=60),
            ),
        ]

        decayed = apply_importance_decay(records, half_life_days=30.0)
        # Recent should be ~1.0, old should be ~0.25
        assert decayed[0].salience > decayed[1].salience


class TestConsolidationPolicy:
    """Tests for ConsolidationPolicy class."""

    @pytest.mark.asyncio
    async def test_exact_text_dedup(self):
        """Should deduplicate exact text matches."""
        config = ConsolidationConfig(
            use_semantic_dedup=False,
            enable_decay=False,
        )
        policy = ConsolidationPolicy(config=config)

        records = [
            MemoryRecord(id="r1", user_id="u1", type="semantic", text="Hello"),
            MemoryRecord(id="r2", user_id="u1", type="semantic", text="Hello"),
            MemoryRecord(id="r3", user_id="u1", type="semantic", text="World"),
        ]

        consolidated, result = await policy.consolidate(records)
        assert len(consolidated) == 2
        assert result.deduplicated == 1

    @pytest.mark.asyncio
    async def test_semantic_dedup_with_embeddings(self):
        """Should deduplicate based on embedding similarity."""
        config = ConsolidationConfig(
            use_semantic_dedup=True,
            similarity_threshold=0.95,
            enable_decay=False,
        )
        policy = ConsolidationPolicy(config=config)

        records = [
            MemoryRecord(
                id="r1",
                user_id="u1",
                text="Hello world",
                embedding=[1.0, 0.0, 0.0],
                salience=0.8,
            ),
            MemoryRecord(
                id="r2",
                user_id="u1",
                text="Hello world variant",
                embedding=[0.99, 0.1, 0.0],  # Very similar
                salience=0.9,
            ),
            MemoryRecord(
                id="r3",
                user_id="u1",
                text="Different",
                embedding=[0.0, 1.0, 0.0],  # Different
                salience=0.7,
            ),
        ]

        consolidated, result = await policy.consolidate(records)
        # First two should merge, third stays separate
        assert len(consolidated) == 2
        assert result.merged >= 1

    @pytest.mark.asyncio
    async def test_consolidate_with_user_filter(self):
        """Should only consolidate records for specified user."""
        config = ConsolidationConfig(
            use_semantic_dedup=False,
            enable_decay=False,
        )
        policy = ConsolidationPolicy(config=config)

        records = [
            MemoryRecord(id="r1", user_id="u1", type="semantic", text="Hello"),
            MemoryRecord(id="r2", user_id="u2", type="semantic", text="Hello"),
        ]

        consolidated, result = await policy.consolidate(records, user_id="u1")
        assert len(consolidated) == 1
        assert consolidated[0].user_id == "u1"
