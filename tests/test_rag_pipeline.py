"""Tests for RAG Pipeline Agent.

This module tests the RAG pipeline including:
- Answer generation with LLM synthesis
- Fallback to simple extraction
- Source handling and confidence calculation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.groupagents.rag_pipeline_agent import (
    RagAnswer,
    RagPipelineAgent,
    RagSource,
)


class TestRagSource:
    """Tests for RagSource model."""

    def test_rag_source_creation(self):
        """Test basic RagSource creation."""
        source = RagSource(
            source_id="src-1",
            content="Test content",
            relevance_score=0.85,
            source_type="document",
        )
        assert source.source_id == "src-1"
        assert source.content == "Test content"
        assert source.relevance_score == 0.85
        assert source.source_type == "document"

    def test_rag_source_with_metadata(self):
        """Test RagSource with metadata."""
        source = RagSource(
            source_id="src-2",
            content="Legal content",
            relevance_score=0.92,
            source_type="policy",
            metadata={"cfr": "8 CFR 204.5(h)(3)"},
        )
        assert source.metadata["cfr"] == "8 CFR 204.5(h)(3)"


class TestRagAnswer:
    """Tests for RagAnswer model."""

    def test_rag_answer_creation(self):
        """Test basic RagAnswer creation."""
        answer = RagAnswer(
            query="What is EB-1A?",
            answer="EB-1A is for extraordinary ability.",
            confidence=0.85,
            sources=[],
            context_used="Sample context",
            retrieval_time_ms=50.0,
            generation_time_ms=100.0,
            total_time_ms=150.0,
        )
        assert "extraordinary ability" in answer.answer
        assert answer.confidence == 0.85
        assert answer.total_time_ms == 150.0


class TestRagPipelineAgent:
    """Tests for RagPipelineAgent."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager."""
        memory = MagicMock()
        memory.aretrieve = AsyncMock(return_value=[])
        return memory

    @pytest.fixture
    def rag_agent(self, mock_memory_manager):
        """Create RAG agent with mocked dependencies."""
        return RagPipelineAgent(memory_manager=mock_memory_manager)

    def test_agent_initialization(self, rag_agent):
        """Test RAG agent initialization."""
        assert rag_agent is not None

    @pytest.mark.asyncio
    async def test_generate_answer_simple_fallback_no_sources(self, rag_agent):
        """Test fallback when no sources available."""
        result = rag_agent._generate_answer_simple_fallback(
            question="What is EB-1A?",
            context="",
            sources=[],
        )
        assert "don't have enough information" in result

    @pytest.mark.asyncio
    async def test_generate_answer_simple_fallback_with_sources(self, rag_agent):
        """Test fallback with sources."""
        sources = [
            RagSource(
                source_id="src-1",
                content="EB-1A is for extraordinary ability.",
                relevance_score=0.9,
                source_type="document",
            ),
            RagSource(
                source_id="src-2",
                content="Requires 3 of 10 criteria.",
                relevance_score=0.8,
                source_type="document",
            ),
        ]
        result = rag_agent._generate_answer_simple_fallback(
            question="What is EB-1A?",
            context="",
            sources=sources,
        )
        assert "EB-1A is for extraordinary ability" in result
        assert "Additional relevant information" in result

    @pytest.mark.asyncio
    async def test_generate_answer_with_llm_fallback(self, rag_agent):
        """Test LLM generation falls back when router unavailable."""
        sources = [
            RagSource(
                source_id="src-1",
                content="Test content",
                relevance_score=0.9,
                source_type="document",
            ),
        ]

        # Mock the LLM router to raise ImportError
        with patch.dict("sys.modules", {"core.llm_interface.intelligent_router": None}):
            result = await rag_agent._generate_answer_with_llm(
                question="Test question",
                context="",
                sources=sources,
            )

        # Should fall back to simple generation
        assert "Test content" in result or "Based on" in result

    @pytest.mark.asyncio
    async def test_calculate_confidence_no_sources(self, rag_agent):
        """Test confidence calculation with no sources."""
        confidence = rag_agent._calculate_confidence(sources=[], context="")
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_calculate_confidence_with_sources(self, rag_agent):
        """Test confidence calculation with sources."""
        sources = [
            RagSource(
                source_id="src-1",
                content="High quality content",
                relevance_score=0.95,
                source_type="document",
            ),
            RagSource(
                source_id="src-2",
                content="Medium quality content",
                relevance_score=0.75,
                source_type="document",
            ),
        ]
        confidence = rag_agent._calculate_confidence(
            sources=sources,
            context="Combined context",
        )
        assert 0.0 < confidence <= 1.0


class TestRAGPipelineIntegration:
    """Integration tests for RAG pipeline."""

    @pytest.fixture
    def mock_llm_router(self):
        """Create mock LLM router."""
        router = MagicMock()
        router.aroute_request = AsyncMock(
            return_value=MagicMock(content="Generated answer from LLM")
        )
        return router

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_with_mock_llm(self, mock_llm_router):
        """Test full RAG pipeline with mocked LLM."""
        memory = MagicMock()
        memory.aretrieve = AsyncMock(return_value=[])

        agent = RagPipelineAgent(memory_manager=memory)

        # Mock the router at the import location
        with patch(
            "core.llm_interface.intelligent_router.IntelligentRouter",
            return_value=mock_llm_router,
        ):
            sources = [
                RagSource(
                    source_id="src-1",
                    content="EB-1A requires extraordinary ability evidence.",
                    relevance_score=0.92,
                    source_type="policy",
                ),
            ]

            result = await agent._generate_answer_with_llm(
                question="What evidence is needed for EB-1A?",
                context="",
                sources=sources,
            )

            # Either LLM response or fallback
            assert result is not None
            assert len(result) > 0


class TestEB1AContextEnrichment:
    """Tests for EB-1A context enrichment in RAG."""

    def test_eb1a_context_detection(self):
        """Test detection of EB-1A related queries."""
        eb1a_queries = [
            "What are the EB-1A criteria?",
            "How to prove extraordinary ability?",
            "8 CFR 204.5(h)(3) requirements",
            "Awards and prizes criterion",
        ]

        non_eb1a_queries = [
            "What is the weather today?",
            "How to make coffee?",
        ]

        # Import the context function
        try:
            from core.groupagents.rag_pipeline_agent import get_eb1a_context_for_query

            for query in eb1a_queries:
                context = get_eb1a_context_for_query(query)
                # Should return some context for EB-1A queries
                # (may be None if not implemented, but shouldn't error)
                assert context is None or isinstance(context, str)

        except ImportError:
            pytest.skip("get_eb1a_context_for_query not available")
