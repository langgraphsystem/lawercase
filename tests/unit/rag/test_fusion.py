"""Tests for Reciprocal Rank Fusion and Hybrid Retrieval.

Verifies RRF algorithm correctness and hybrid retriever functionality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.rag.fusion import (
    HybridRetriever,
    ReciprocalRankFusion,
    create_hybrid_retriever,
)


class TestReciprocalRankFusion:
    """Test RRF algorithm implementation."""

    @pytest.mark.asyncio
    async def test_rrf_basic_fusion(self):
        """RRF should correctly fuse two rankings."""
        fusion = ReciprocalRankFusion(k=60)

        # Two rankings with overlapping documents
        ranking1 = [("doc1", 0.9), ("doc2", 0.7), ("doc3", 0.5)]
        ranking2 = [("doc2", 0.95), ("doc1", 0.6), ("doc4", 0.4)]

        fused = await fusion.fuse([ranking1, ranking2], top_k=None)

        # doc1 and doc2 should rank higher (appear in both)
        assert len(fused) == 4
        assert fused[0][0] in ["doc1", "doc2"]  # Top result is one of overlapping docs
        assert fused[1][0] in ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_rrf_score_calculation(self):
        """RRF scores should follow formula: 1/(k+rank)."""
        fusion = ReciprocalRankFusion(k=60)

        # Single ranking
        ranking = [("doc1", 1.0), ("doc2", 0.5)]

        fused = await fusion.fuse([ranking])

        # Expected scores: doc1=1/(60+1)=0.0164, doc2=1/(60+2)=0.0161
        assert fused[0][0] == "doc1"
        assert fused[1][0] == "doc2"
        assert fused[0][1] > fused[1][1]  # doc1 score > doc2 score

    @pytest.mark.asyncio
    async def test_rrf_with_weights(self):
        """RRF should apply weights to different retrieval methods."""
        # Prefer second ranking (weight=0.8 vs 0.2)
        fusion = ReciprocalRankFusion(k=60, weights=[0.2, 0.8])

        ranking1 = [("doc1", 1.0), ("doc2", 0.5)]
        ranking2 = [("doc3", 1.0), ("doc4", 0.5)]

        fused = await fusion.fuse([ranking1, ranking2])

        # doc3 from ranking2 should score highest (weighted 0.8)
        assert fused[0][0] == "doc3"

    @pytest.mark.asyncio
    async def test_rrf_top_k_limit(self):
        """RRF should respect top_k parameter."""
        fusion = ReciprocalRankFusion()

        ranking1 = [("doc1", 1.0), ("doc2", 0.9), ("doc3", 0.8)]
        ranking2 = [("doc4", 1.0), ("doc5", 0.9), ("doc6", 0.8)]

        fused = await fusion.fuse([ranking1, ranking2], top_k=3)

        assert len(fused) == 3

    @pytest.mark.asyncio
    async def test_rrf_handles_empty_ranking(self):
        """RRF should handle empty rankings gracefully."""
        fusion = ReciprocalRankFusion()

        ranking1 = [("doc1", 1.0), ("doc2", 0.5)]
        ranking2 = []  # Empty ranking

        fused = await fusion.fuse([ranking1, ranking2])

        # Should return documents from ranking1 only
        assert len(fused) == 2
        assert fused[0][0] == "doc1"

    @pytest.mark.asyncio
    async def test_rrf_weight_mismatch_raises_error(self):
        """RRF should raise error if weights don't match rankings."""
        fusion = ReciprocalRankFusion(weights=[0.5, 0.5])  # 2 weights

        ranking1 = [("doc1", 1.0)]
        ranking2 = [("doc2", 1.0)]
        ranking3 = [("doc3", 1.0)]  # 3 rankings!

        with pytest.raises(ValueError, match="Number of weights"):
            await fusion.fuse([ranking1, ranking2, ranking3])

    @pytest.mark.asyncio
    async def test_rrf_fuse_with_metadata(self):
        """RRF should preserve metadata from first occurrence."""
        fusion = ReciprocalRankFusion()

        ranking1 = [
            ("doc1", 0.9, {"source": "sparse", "chunk_id": 1}),
            ("doc2", 0.7, {"source": "sparse", "chunk_id": 2}),
        ]
        ranking2 = [
            ("doc1", 0.95, {"source": "dense", "chunk_id": 10}),
            ("doc3", 0.8, {"source": "dense", "chunk_id": 11}),
        ]

        fused = await fusion.fuse_with_metadata([ranking1, ranking2])

        # doc1 metadata should come from ranking1 (first occurrence)
        doc1_result = next(r for r in fused if r[0] == "doc1")
        assert doc1_result[2]["source"] == "sparse"
        assert doc1_result[2]["chunk_id"] == 1

    @pytest.mark.asyncio
    async def test_rrf_deduplication(self):
        """RRF should deduplicate documents across rankings."""
        fusion = ReciprocalRankFusion()

        # Same document in both rankings
        ranking1 = [("doc1", 0.9)]
        ranking2 = [("doc1", 0.95)]

        fused = await fusion.fuse([ranking1, ranking2])

        # Should have exactly 1 result (deduplicated)
        assert len(fused) == 1
        assert fused[0][0] == "doc1"


class TestHybridRetriever:
    """Test hybrid retriever combining sparse and dense search."""

    @pytest.mark.asyncio
    async def test_hybrid_search_calls_both_retrievers(self):
        """Hybrid search should call both sparse and dense retrievers."""
        # Mock retrievers
        sparse_mock = AsyncMock()
        sparse_mock.asearch = AsyncMock(return_value=[("doc1", 0.9), ("doc2", 0.7)])

        dense_mock = AsyncMock()
        dense_mock.asearch = AsyncMock(return_value=[("doc2", 0.95), ("doc3", 0.8)])

        # Create hybrid retriever
        hybrid = HybridRetriever(
            sparse_retriever=sparse_mock,
            dense_retriever=dense_mock,
        )

        # Execute search
        results = await hybrid.search("test query", top_k=5)

        # Verify both retrievers were called
        sparse_mock.asearch.assert_called_once()
        dense_mock.asearch.assert_called_once()

        # Should return fused results
        assert len(results) > 0
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_hybrid_search_over_retrieval(self):
        """Hybrid search should over-retrieve before fusion."""
        sparse_mock = AsyncMock()
        sparse_mock.asearch = AsyncMock(return_value=[])

        dense_mock = AsyncMock()
        dense_mock.asearch = AsyncMock(return_value=[])

        hybrid = HybridRetriever(sparse_mock, dense_mock)

        await hybrid.search("test query", top_k=5)

        # Should retrieve top_k * 2 = 10 from each
        sparse_mock.asearch.assert_called_once_with("test query", top_k=10)
        dense_mock.asearch.assert_called_once_with("test query", top_k=10)

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_weights(self):
        """Hybrid retriever should apply configured weights."""
        sparse_mock = AsyncMock()
        sparse_mock.asearch = AsyncMock(return_value=[("doc1", 1.0)])

        dense_mock = AsyncMock()
        dense_mock.asearch = AsyncMock(return_value=[("doc2", 1.0)])

        # Prefer dense (70% weight)
        hybrid = HybridRetriever(
            sparse_mock,
            dense_mock,
            sparse_weight=0.3,
            dense_weight=0.7,
        )

        # Verify weights normalized
        weights = hybrid.get_weights()
        assert weights["sparse"] == 0.3
        assert weights["dense"] == 0.7

    @pytest.mark.asyncio
    async def test_hybrid_search_batch(self):
        """Hybrid search should support batch queries."""
        sparse_mock = AsyncMock()
        sparse_mock.asearch = AsyncMock(return_value=[("doc1", 0.9)])

        dense_mock = AsyncMock()
        dense_mock.asearch = AsyncMock(return_value=[("doc2", 0.95)])

        hybrid = HybridRetriever(sparse_mock, dense_mock)

        queries = ["query1", "query2", "query3"]
        results = await hybrid.search_batch(queries, top_k=5)

        # Should return one result list per query
        assert len(results) == 3

        # Each retriever should be called 3 times (once per query)
        assert sparse_mock.asearch.call_count == 3
        assert dense_mock.asearch.call_count == 3

    @pytest.mark.asyncio
    async def test_hybrid_search_custom_top_k(self):
        """Hybrid search should allow custom retrieval limits."""
        sparse_mock = AsyncMock()
        sparse_mock.asearch = AsyncMock(return_value=[])

        dense_mock = AsyncMock()
        dense_mock.asearch = AsyncMock(return_value=[])

        hybrid = HybridRetriever(sparse_mock, dense_mock)

        await hybrid.search(
            "test query",
            top_k=10,
            sparse_top_k=20,
            dense_top_k=30,
        )

        # Should use custom limits
        sparse_mock.asearch.assert_called_once_with("test query", top_k=20)
        dense_mock.asearch.assert_called_once_with("test query", top_k=30)

    @pytest.mark.asyncio
    async def test_create_hybrid_retriever_factory(self):
        """Factory function should create hybrid retriever correctly."""
        sparse_mock = MagicMock()
        dense_mock = MagicMock()

        hybrid = await create_hybrid_retriever(
            sparse_mock,
            dense_mock,
            sparse_weight=0.4,
            dense_weight=0.6,
        )

        assert isinstance(hybrid, HybridRetriever)
        assert hybrid.sparse_retriever is sparse_mock
        assert hybrid.dense_retriever is dense_mock

        weights = hybrid.get_weights()
        assert weights["sparse"] == 0.4
        assert weights["dense"] == 0.6


class TestRRFIntegration:
    """Integration tests for RRF algorithm."""

    @pytest.mark.asyncio
    async def test_rrf_real_world_scenario(self):
        """Test RRF with realistic search scenario."""
        fusion = ReciprocalRankFusion(k=60)

        # Sparse (BM25): Good at exact keyword matches
        sparse_results = [
            ("immigration_law_doc", 0.92),
            ("visa_requirements_doc", 0.85),
            ("eb1a_criteria_doc", 0.78),
            ("general_immigration", 0.65),
        ]

        # Dense (vector): Good at semantic similarity
        dense_results = [
            ("eb1a_criteria_doc", 0.95),  # Highly relevant semantically
            ("immigration_law_doc", 0.88),
            ("extraordinary_ability", 0.82),
            ("visa_requirements_doc", 0.76),
        ]

        fused = await fusion.fuse([sparse_results, dense_results], top_k=5)

        # Documents appearing in both should rank highest
        top_2_docs = {fused[0][0], fused[1][0]}
        assert "immigration_law_doc" in top_2_docs  # Appears in both
        assert "eb1a_criteria_doc" in top_2_docs  # Appears in both, high scores

    @pytest.mark.asyncio
    async def test_rrf_handles_single_ranking(self):
        """RRF should work with single ranking (fallback mode)."""
        fusion = ReciprocalRankFusion()

        ranking = [("doc1", 0.9), ("doc2", 0.7), ("doc3", 0.5)]

        fused = await fusion.fuse([ranking], top_k=2)

        # Should preserve order from single ranking
        assert fused[0][0] == "doc1"
        assert fused[1][0] == "doc2"

    @pytest.mark.asyncio
    async def test_rrf_three_way_fusion(self):
        """RRF should handle fusion from 3+ retrieval methods."""
        fusion = ReciprocalRankFusion(k=60)

        ranking1 = [("doc1", 1.0), ("doc2", 0.8)]
        ranking2 = [("doc1", 1.0), ("doc3", 0.7)]
        ranking3 = [("doc1", 1.0), ("doc4", 0.6)]

        fused = await fusion.fuse([ranking1, ranking2, ranking3])

        # doc1 appears in all three -> should rank first
        assert fused[0][0] == "doc1"

        # doc1 score should be highest (3 contributions)
        doc1_score = fused[0][1]
        other_scores = [score for _doc, score in fused[1:]]
        assert all(doc1_score > score for score in other_scores)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
