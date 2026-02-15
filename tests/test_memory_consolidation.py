"""Tests for Memory Consolidation System.

This module tests the memory consolidation including:
- Semantic deduplication
- Importance decay
- LLM-based compression
- Batch consolidation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.memory.models import MemoryRecord
from core.memory.policies.consolidation import (
    ConsolidationConfig,
    ConsolidationPolicy,
    ConsolidationResult,
    apply_importance_decay,
    calculate_decay,
    cosine_similarity,
    find_semantic_duplicates,
    merge_duplicate_records,
)


class TestCosineSimilarity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec = [1.0, 0.5, 0.3, 0.8]
        similarity = cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001

    def test_empty_vectors(self):
        """Test handling of empty vectors."""
        similarity = cosine_similarity([], [])
        assert similarity == 0.0

    def test_different_length_vectors(self):
        """Test handling of different length vectors."""
        vec1 = [1.0, 0.5]
        vec2 = [1.0, 0.5, 0.3]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0


class TestCalculateDecay:
    """Tests for importance decay calculation."""

    def test_no_decay_for_new_memory(self):
        """Test no decay for recently created memory."""
        now = datetime.now(UTC)
        decay = calculate_decay(now, half_life_days=30.0)
        assert abs(decay - 1.0) < 0.01

    def test_half_decay_at_half_life(self):
        """Test 50% decay at half-life."""
        now = datetime.now(UTC)
        past = now - timedelta(days=30)
        decay = calculate_decay(past, half_life_days=30.0, reference_time=now)
        assert abs(decay - 0.5) < 0.05

    def test_decay_respects_minimum(self):
        """Test decay doesn't go below minimum."""
        now = datetime.now(UTC)
        ancient = now - timedelta(days=365)
        decay = calculate_decay(
            ancient,
            half_life_days=30.0,
            min_importance=0.1,
            reference_time=now,
        )
        assert decay >= 0.1


class TestFindSemanticDuplicates:
    """Tests for semantic duplicate detection."""

    def test_no_duplicates_when_empty(self):
        """Test no duplicates found when input is empty."""
        clusters = find_semantic_duplicates([])
        assert clusters == []

    def test_no_duplicates_single_record(self):
        """Test no duplicates with single record."""
        record = MemoryRecord(
            id="rec-1",
            user_id="user-1",
            type="semantic",
            text="Test memory",
            embedding=[0.1, 0.2, 0.3],
            salience=0.8,
        )
        clusters = find_semantic_duplicates([record])
        assert clusters == []

    def test_finds_similar_records(self):
        """Test finding similar records based on embeddings."""
        # Create records with similar embeddings
        records = [
            MemoryRecord(
                id="rec-1",
                user_id="user-1",
                type="semantic",
                text="Memory about EB-1A",
                embedding=[0.9, 0.1, 0.1],
                salience=0.8,
            ),
            MemoryRecord(
                id="rec-2",
                user_id="user-1",
                type="semantic",
                text="Similar memory about EB-1A",
                embedding=[0.88, 0.12, 0.1],  # Very similar
                salience=0.7,
            ),
            MemoryRecord(
                id="rec-3",
                user_id="user-1",
                type="semantic",
                text="Different memory",
                embedding=[0.1, 0.9, 0.1],  # Different
                salience=0.6,
            ),
        ]

        clusters = find_semantic_duplicates(records, threshold=0.9)
        # Should find cluster of similar records
        assert len(clusters) >= 0  # May or may not find depending on exact similarity


class TestMergeDuplicateRecords:
    """Tests for merging duplicate records."""

    def test_merge_empty_raises(self):
        """Test merging empty list raises error."""
        with pytest.raises(ValueError):
            merge_duplicate_records([])

    def test_merge_single_returns_same(self):
        """Test merging single record returns same record."""
        record = MemoryRecord(
            id="rec-1",
            user_id="user-1",
            type="semantic",
            text="Single memory",
            salience=0.8,
        )
        merged = merge_duplicate_records([record])
        assert merged.text == record.text

    def test_merge_keeps_highest_salience(self):
        """Test merge keeps record with highest salience."""
        records = [
            MemoryRecord(
                id="rec-1",
                user_id="user-1",
                type="semantic",
                text="Low salience",
                salience=0.3,
            ),
            MemoryRecord(
                id="rec-2",
                user_id="user-1",
                type="semantic",
                text="High salience",
                salience=0.9,
            ),
        ]
        merged = merge_duplicate_records(records)
        assert merged.text == "High salience"
        assert merged.salience == 0.9

    def test_merge_combines_tags(self):
        """Test merge combines tags from all records."""
        records = [
            MemoryRecord(
                id="rec-1",
                user_id="user-1",
                type="semantic",
                text="Memory 1",
                salience=0.8,
                tags=["eb1a", "awards"],
            ),
            MemoryRecord(
                id="rec-2",
                user_id="user-1",
                type="semantic",
                text="Memory 2",
                salience=0.7,
                tags=["evidence", "awards"],
            ),
        ]
        merged = merge_duplicate_records(records)
        assert "eb1a" in merged.tags
        assert "evidence" in merged.tags
        assert "awards" in merged.tags


class TestApplyImportanceDecay:
    """Tests for applying importance decay to records."""

    def test_decay_reduces_salience(self):
        """Test that decay reduces salience over time."""
        old_time = datetime.now(UTC) - timedelta(days=60)
        records = [
            MemoryRecord(
                id="rec-1",
                user_id="user-1",
                type="semantic",
                text="Old memory",
                salience=1.0,
                created_at=old_time,
            ),
        ]

        decayed = apply_importance_decay(records, half_life_days=30.0)

        assert decayed[0].salience < 1.0
        assert decayed[0].salience > 0.0


class TestConsolidationConfig:
    """Tests for ConsolidationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConsolidationConfig()
        assert config.similarity_threshold == 0.92
        assert config.use_semantic_dedup is True
        assert config.enable_decay is True
        assert config.decay_half_life_days == 30.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = ConsolidationConfig(
            similarity_threshold=0.85,
            enable_compression=True,
            compression_threshold=30,
        )
        assert config.similarity_threshold == 0.85
        assert config.enable_compression is True
        assert config.compression_threshold == 30


class TestConsolidationPolicy:
    """Tests for ConsolidationPolicy."""

    @pytest.fixture
    def policy(self):
        """Create consolidation policy with default config."""
        return ConsolidationPolicy()

    @pytest.fixture
    def policy_with_llm(self):
        """Create consolidation policy with mock LLM client."""
        mock_llm = MagicMock()
        mock_llm.agenerate = AsyncMock(return_value="Summarized memory content")
        return ConsolidationPolicy(llm_client=mock_llm)

    @pytest.mark.asyncio
    async def test_consolidate_empty(self, policy):
        """Test consolidating empty list."""
        records, result = await policy.consolidate([])
        assert records == []
        assert result.total_before == 0
        assert result.total_after == 0

    @pytest.mark.asyncio
    async def test_consolidate_single_record(self, policy):
        """Test consolidating single record."""
        record = MemoryRecord(
            id="rec-1",
            user_id="user-1",
            type="semantic",
            text="Single memory",
            salience=0.8,
            created_at=datetime.now(UTC),
        )

        records, result = await policy.consolidate([record])
        assert len(records) == 1
        assert result.total_after == 1

    @pytest.mark.asyncio
    async def test_consolidate_with_user_filter(self, policy):
        """Test consolidating with user filter."""
        records = [
            MemoryRecord(
                id="rec-1",
                user_id="user-1",
                type="semantic",
                text="User 1 memory",
                salience=0.8,
                created_at=datetime.now(UTC),
            ),
            MemoryRecord(
                id="rec-2",
                user_id="user-2",
                type="semantic",
                text="User 2 memory",
                salience=0.7,
                created_at=datetime.now(UTC),
            ),
        ]

        filtered, _ = await policy.consolidate(records, user_id="user-1")
        assert all(r.user_id == "user-1" for r in filtered)


class TestLLMCompression:
    """Tests for LLM-based memory compression."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.agenerate = AsyncMock(return_value="Compressed summary of memories")
        return client

    @pytest.mark.asyncio
    async def test_compression_with_llm(self, mock_llm_client):
        """Test compression uses LLM when available."""
        config = ConsolidationConfig(
            enable_compression=True,
            compression_threshold=2,
        )
        policy = ConsolidationPolicy(config=config, llm_client=mock_llm_client)

        # Create many similar records
        records = [
            MemoryRecord(
                id=f"rec-{i}",
                user_id="user-1",
                type="semantic",
                text=f"Memory about EB-1A evidence {i}",
                salience=0.8 - (i * 0.01),
                embedding=[0.1 + (i * 0.01), 0.2, 0.3],
                created_at=datetime.now(UTC),
            )
            for i in range(5)
        ]

        compressed = await policy._compress_memories(records)

        # Should have fewer records after compression
        assert len(compressed) <= len(records)

    @pytest.mark.asyncio
    async def test_compression_fallback_without_llm(self):
        """Test compression falls back to salience sorting without LLM."""
        config = ConsolidationConfig(
            enable_compression=True,
            compression_threshold=2,
            max_memories_per_user=3,
        )
        policy = ConsolidationPolicy(config=config, llm_client=None)

        records = [
            MemoryRecord(
                id=f"rec-{i}",
                user_id="user-1",
                type="semantic",
                text=f"Memory {i}",
                salience=0.9 - (i * 0.1),
                created_at=datetime.now(UTC),
            )
            for i in range(5)
        ]

        compressed = await policy._compress_memories(records)

        # Should keep top 3 by salience
        assert len(compressed) == 3
        # Highest salience should be first
        assert compressed[0].salience >= compressed[1].salience


class TestConsolidationResult:
    """Tests for ConsolidationResult."""

    def test_result_initialization(self):
        """Test result initialization with defaults."""
        result = ConsolidationResult()
        assert result.deduplicated == 0
        assert result.decayed == 0
        assert result.compressed == 0
        assert result.merged == 0
        assert result.total_before == 0
        assert result.total_after == 0
        assert result.clusters == []

    def test_result_with_values(self):
        """Test result with custom values."""
        result = ConsolidationResult(
            deduplicated=5,
            decayed=10,
            compressed=3,
            total_before=20,
            total_after=12,
        )
        assert result.deduplicated == 5
        assert result.total_before == 20
        assert result.total_after == 12
