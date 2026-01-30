"""Tests for unified knowledge search across all 3 database sources.

Covers:
- public.knowledge_base (571 USCIS policy chunks via Supabase REST)
- mega_agent.semantic_memory (384 records via pgvector)
- mega_agent.rfe_knowledge (5626 RFE case records via pgvector)
- Unified aretrieve_all_sources() combining all 3
- MemoryManager delegation
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.memory.memory_manager import MemoryManager
from core.memory.models import MemoryRecord
from core.memory.stores.supabase_semantic_store import SupabaseSemanticStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns fixed-size vectors."""
    embedder = MagicMock()
    embedder.model = "text-embedding-3-large"
    embedder.dimension = 2000
    embedder.aembed_query = AsyncMock(return_value=[0.1] * 2000)
    embedder.aembed_documents = AsyncMock(return_value=[[0.1] * 2000])
    return embedder


@pytest.fixture
def mock_db_manager():
    """Mock database manager for session context."""
    db = MagicMock()
    session = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    db.session.return_value = ctx
    return db, session


@pytest.fixture
def store(mock_embedder, mock_db_manager):
    """Create SupabaseSemanticStore with mocked dependencies."""
    db, _ = mock_db_manager
    with patch(
        "core.memory.stores.supabase_semantic_store.get_storage_config"
    ) as mock_config, patch(
        "core.memory.stores.supabase_semantic_store.get_db_manager",
        return_value=db,
    ):
        mock_config.return_value.vector_namespace = "default"
        mock_config.return_value.embedding_dimension = 2000
        s = SupabaseSemanticStore(embedder=mock_embedder)
        s.db = db
        return s


def _make_record(
    text: str,
    source: str = "test",
    tags: list[str] | None = None,
    confidence: float = 0.8,
) -> MemoryRecord:
    return MemoryRecord(
        id="test-id",
        text=text,
        source=source,
        tags=tags or [],
        confidence=confidence,
        created_at=datetime.utcnow(),
    )


# ===========================================================================
# Test public.knowledge_base (aretrieve_public_kb)
# ===========================================================================


class TestPublicKnowledgeBase:
    """Tests for public.knowledge_base search via Supabase REST."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self, store):
        """Empty query should return no results."""
        results = await store.aretrieve_public_kb("", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_short_keywords_filtered(self, store):
        """Keywords shorter than 3 chars should be ignored."""
        results = await store.aretrieve_public_kb("ab cd", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_successful_search(self, store):
        """Successful search returns MemoryRecord list with correct source."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "abc123",
                "content": "Awards criterion requires nationally recognized prizes",
                "metadata": {"source": "uscis", "collection": "eb1a"},
                "namespace": "eb1a",
                "created_at": "2026-01-22T00:00:00Z",
            },
            {
                "id": "def456",
                "content": "Evidence of receipt of lesser nationally recognized prizes",
                "metadata": {"source": "uscis"},
                "namespace": "eb1a",
                "created_at": "2026-01-22T00:00:00Z",
            },
        ]

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = mock_response

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch(
            "supabase.create_client",
            return_value=mock_client,
        ), patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"},
        ):
            results = await store.aretrieve_public_kb(
                "awards nationally recognized", topk=5
            )

        assert len(results) == 2
        assert all(r.source == "public_knowledge_base" for r in results)
        assert all("knowledge_base" in r.tags for r in results)
        assert all("uscis_policy" in r.tags for r in results)

    @pytest.mark.asyncio
    async def test_keyword_scoring(self, store):
        """Records matching more keywords should have higher confidence."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "content": "awards nationally recognized prizes excellence",
                "metadata": {},
                "namespace": "eb1a",
                "created_at": None,
            },
            {
                "id": "2",
                "content": "awards only mentioned here",
                "metadata": {},
                "namespace": "eb1a",
                "created_at": None,
            },
        ]

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = mock_response

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch(
            "supabase.create_client",
            return_value=mock_client,
        ), patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"},
        ):
            results = await store.aretrieve_public_kb(
                "awards nationally recognized prizes excellence", topk=5
            )

        assert len(results) == 2
        # First result should have higher confidence (more keyword matches)
        assert results[0].confidence >= results[1].confidence

    @pytest.mark.asyncio
    async def test_text_truncation(self, store):
        """Long content should be truncated to 2000 chars."""
        long_content = "A" * 5000
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "content": long_content,
                "metadata": {},
                "namespace": "eb1a",
                "created_at": None,
            },
        ]

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = mock_response

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch(
            "supabase.create_client",
            return_value=mock_client,
        ), patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"},
        ):
            results = await store.aretrieve_public_kb("AAA content", topk=1)

        assert len(results) == 1
        assert len(results[0].text) == 2000

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_empty(self, store):
        """Missing Supabase credentials should return empty list."""
        with patch.dict(
            "os.environ", {"SUPABASE_URL": "", "SUPABASE_KEY": ""}, clear=False
        ):
            results = await store.aretrieve_public_kb("test query", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_supabase_error_returns_empty(self, store):
        """Supabase REST errors should be caught and return empty list."""
        with patch(
            "supabase.create_client",
            side_effect=Exception("Connection refused"),
        ), patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"},
        ):
            results = await store.aretrieve_public_kb("test query", topk=5)
        assert results == []


# ===========================================================================
# Test mega_agent.rfe_knowledge (aretrieve_rfe_knowledge)
# ===========================================================================


class TestRFEKnowledge:
    """Tests for mega_agent.rfe_knowledge search via pgvector."""

    @pytest.mark.asyncio
    async def test_rfe_search_returns_records(self, store, mock_db_manager):
        """RFE search should return formatted MemoryRecords."""
        _, session = mock_db_manager

        # Mock SQL result rows
        mock_row = MagicMock()
        mock_row.id = "rfe-001"
        mock_row.criterion = "awards"
        mock_row.issue_type = "awards_not_nationally_recognized"
        mock_row.uscis_quote = "The evidence does not establish..."
        mock_row.problem_description = "University award not nationally recognized"
        mock_row.success_response = "Provided evidence of 500+ applicants"
        mock_row.similarity = 0.85

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        session.execute = AsyncMock(return_value=mock_result)

        results = await store.aretrieve_rfe_knowledge("awards not recognized", topk=5)

        assert len(results) == 1
        r = results[0]
        assert r.source == "rfe_knowledge"
        assert "rfe" in r.tags
        assert "awards" in r.tags
        assert "Criterion: awards" in r.text
        assert "Problem: University award" in r.text
        assert "Response: Provided evidence" in r.text
        assert r.confidence == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_rfe_search_empty_results(self, store, mock_db_manager):
        """Empty RFE results should return empty list."""
        _, session = mock_db_manager
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        results = await store.aretrieve_rfe_knowledge("nonexistent query", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_rfe_search_handles_null_fields(self, store, mock_db_manager):
        """RFE records with null fields should not break formatting."""
        _, session = mock_db_manager

        mock_row = MagicMock()
        mock_row.id = "rfe-002"
        mock_row.criterion = "membership"
        mock_row.issue_type = None
        mock_row.uscis_quote = None
        mock_row.problem_description = "Membership issue"
        mock_row.success_response = None
        mock_row.similarity = 0.6

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        session.execute = AsyncMock(return_value=mock_result)

        results = await store.aretrieve_rfe_knowledge("membership", topk=5)

        assert len(results) == 1
        assert "Criterion: membership" in results[0].text
        assert "Problem: Membership issue" in results[0].text
        # Null fields should be omitted
        assert "USCIS:" not in results[0].text
        assert "Response:" not in results[0].text


# ===========================================================================
# Test mega_agent.semantic_memory (aretrieve, aretrieve_knowledge_base)
# ===========================================================================


class TestSemanticMemory:
    """Tests for mega_agent.semantic_memory search via pgvector."""

    @pytest.mark.asyncio
    async def test_retrieve_knowledge_base_filters_by_tags(self, store):
        """Knowledge base retrieval should filter by tags and exclude case docs."""
        with patch.object(store, "aretrieve", new_callable=AsyncMock) as mock:
            mock.return_value = [
                _make_record("USCIS policy content", source="knowledge_base")
            ]

            results = await store.aretrieve_knowledge_base("awards", topk=5)

            mock.assert_called_once_with(
                query="awards",
                user_id=None,
                topk=5,
                filters={
                    "tags": ["knowledge_base"],
                    "exclude_tags": ["case_document"],
                },
            )
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_retrieve_case_documents_filters_by_case_id(self, store):
        """Case document retrieval should filter by case_id and exclude KB."""
        with patch.object(store, "aretrieve", new_callable=AsyncMock) as mock:
            mock.return_value = [
                _make_record("Client resume", source="case_document")
            ]

            results = await store.aretrieve_case_documents(
                "resume", case_id="case-123", topk=5
            )

            mock.assert_called_once_with(
                query="resume",
                user_id=None,
                topk=5,
                filters={
                    "case_id": "case-123",
                    "exclude_tags": ["knowledge_base"],
                },
            )
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_retrieve_hybrid_combines_sources(self, store):
        """Hybrid retrieval should combine KB and case documents."""
        kb_record = _make_record(
            "Policy content", source="knowledge_base", confidence=0.9
        )
        case_record = _make_record(
            "Case evidence", source="case_document", confidence=0.7
        )

        with patch.object(
            store,
            "aretrieve_knowledge_base",
            new_callable=AsyncMock,
            return_value=[kb_record],
        ), patch.object(
            store,
            "aretrieve_case_documents",
            new_callable=AsyncMock,
            return_value=[case_record],
        ):
            results = await store.aretrieve_hybrid(
                "awards",
                case_id="case-123",
                topk=5,
                knowledge_weight=0.5,
            )

        assert len(results) == 2
        # Sorted by confidence: KB first (0.9), then case (0.7)
        assert results[0].confidence >= results[1].confidence


# ===========================================================================
# Test aretrieve_all_sources (unified search)
# ===========================================================================


class TestUnifiedSearch:
    """Tests for aretrieve_all_sources combining all 3 database sources."""

    @pytest.mark.asyncio
    async def test_combines_all_three_sources(self, store):
        """Unified search should combine semantic, RFE, and public KB results."""
        semantic_record = _make_record(
            "Semantic memory content", source="semantic", confidence=0.9
        )
        rfe_record = _make_record(
            "RFE pattern response", source="rfe_knowledge", confidence=0.85
        )
        public_kb_record = _make_record(
            "USCIS policy chunk", source="public_knowledge_base", confidence=0.7
        )

        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            return_value=[semantic_record],
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            return_value=[rfe_record],
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            return_value=[public_kb_record],
        ):
            results = await store.aretrieve_all_sources("awards", topk=10)

        assert len(results) == 3
        sources = {r.source for r in results}
        assert sources == {"semantic", "rfe_knowledge", "public_knowledge_base"}
        # Should be sorted by confidence descending
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_handles_semantic_failure(self, store):
        """If semantic search fails, other sources should still return."""
        rfe_record = _make_record("RFE data", source="rfe_knowledge", confidence=0.8)
        public_record = _make_record(
            "Public KB", source="public_knowledge_base", confidence=0.6
        )

        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            side_effect=Exception("OpenAI API error"),
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            return_value=[rfe_record],
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            return_value=[public_record],
        ):
            results = await store.aretrieve_all_sources("awards", topk=10)

        assert len(results) == 2
        sources = {r.source for r in results}
        assert "semantic" not in sources
        assert "rfe_knowledge" in sources
        assert "public_knowledge_base" in sources

    @pytest.mark.asyncio
    async def test_handles_rfe_failure(self, store):
        """If RFE search fails, other sources should still return."""
        semantic_record = _make_record(
            "Semantic data", source="semantic", confidence=0.9
        )
        public_record = _make_record(
            "Public KB", source="public_knowledge_base", confidence=0.6
        )

        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            return_value=[semantic_record],
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            side_effect=Exception("RFE table error"),
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            return_value=[public_record],
        ):
            results = await store.aretrieve_all_sources("awards", topk=10)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_handles_public_kb_failure(self, store):
        """If public KB fails, other sources should still return."""
        semantic_record = _make_record(
            "Semantic data", source="semantic", confidence=0.9
        )
        rfe_record = _make_record("RFE data", source="rfe_knowledge", confidence=0.8)

        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            return_value=[semantic_record],
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            return_value=[rfe_record],
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            side_effect=Exception("Supabase REST error"),
        ):
            results = await store.aretrieve_all_sources("awards", topk=10)

        assert len(results) == 2
        sources = {r.source for r in results}
        assert "public_knowledge_base" not in sources

    @pytest.mark.asyncio
    async def test_all_sources_fail_returns_empty(self, store):
        """If all sources fail, should return empty list."""
        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ):
            results = await store.aretrieve_all_sources("awards", topk=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_respects_topk_limit(self, store):
        """Results should be truncated to topk."""
        records = [
            _make_record(f"Record {i}", confidence=0.9 - i * 0.05)
            for i in range(10)
        ]

        with patch.object(
            store,
            "aretrieve",
            new_callable=AsyncMock,
            return_value=records[:4],
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            return_value=records[4:8],
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            return_value=records[8:],
        ):
            results = await store.aretrieve_all_sources("test", topk=5)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_results_sorted_by_confidence(self, store):
        """Results from all sources should be sorted by confidence descending."""
        r1 = _make_record("Low", source="semantic", confidence=0.3)
        r2 = _make_record("High", source="rfe_knowledge", confidence=0.95)
        r3 = _make_record("Medium", source="public_knowledge_base", confidence=0.6)

        with patch.object(
            store, "aretrieve", new_callable=AsyncMock, return_value=[r1]
        ), patch.object(
            store,
            "_aretrieve_rfe_with_timeout",
            new_callable=AsyncMock,
            return_value=[r2],
        ), patch.object(
            store,
            "_aretrieve_public_kb_with_timeout",
            new_callable=AsyncMock,
            return_value=[r3],
        ):
            results = await store.aretrieve_all_sources("test", topk=10)

        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)
        assert results[0].source == "rfe_knowledge"
        assert results[1].source == "public_knowledge_base"
        assert results[2].source == "semantic"


# ===========================================================================
# Test timeout wrappers
# ===========================================================================


class TestTimeoutWrappers:
    """Tests for timeout wrapper methods."""

    @pytest.mark.asyncio
    async def test_rfe_timeout_returns_empty(self, store):
        """RFE timeout should return empty list, not raise."""
        with patch.object(
            store,
            "aretrieve_rfe_knowledge",
            new_callable=AsyncMock,
            side_effect=TimeoutError(),
        ):
            results = await store._aretrieve_rfe_with_timeout("test", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_rfe_error_returns_empty(self, store):
        """RFE errors should return empty list, not raise."""
        with patch.object(
            store,
            "aretrieve_rfe_knowledge",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB error"),
        ):
            results = await store._aretrieve_rfe_with_timeout("test", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_public_kb_timeout_returns_empty(self, store):
        """Public KB timeout should return empty list, not raise."""
        with patch.object(
            store,
            "aretrieve_public_kb",
            new_callable=AsyncMock,
            side_effect=TimeoutError(),
        ):
            results = await store._aretrieve_public_kb_with_timeout("test", topk=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_public_kb_error_returns_empty(self, store):
        """Public KB errors should return empty list, not raise."""
        with patch.object(
            store,
            "aretrieve_public_kb",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Network error"),
        ):
            results = await store._aretrieve_public_kb_with_timeout("test", topk=5)
        assert results == []


# ===========================================================================
# Test RFE knowledge counts
# ===========================================================================


class TestRFEKnowledgeCounts:
    """Tests for RFE record counting methods."""

    @pytest.mark.asyncio
    async def test_count_rfe_knowledge(self, store, mock_db_manager):
        """Should return total RFE record count."""
        _, session = mock_db_manager
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5626
        session.execute = AsyncMock(return_value=mock_result)

        count = await store.acount_rfe_knowledge()
        assert count == 5626

    @pytest.mark.asyncio
    async def test_count_rfe_by_criterion(self, store, mock_db_manager):
        """Should return breakdown by criterion."""
        _, session = mock_db_manager

        mock_row1 = MagicMock()
        mock_row1.criterion = "awards"
        mock_row1.count = 354

        mock_row2 = MagicMock()
        mock_row2.criterion = "membership"
        mock_row2.count = 350

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        session.execute = AsyncMock(return_value=mock_result)

        breakdown = await store.acount_rfe_by_criterion()

        assert len(breakdown) == 2
        assert breakdown[0] == {"criterion": "awards", "count": 354}
        assert breakdown[1] == {"criterion": "membership", "count": 350}


# ===========================================================================
# Test MemoryManager delegation
# ===========================================================================


class TestMemoryManagerDelegation:
    """Tests for MemoryManager delegating to unified search."""

    @pytest.mark.asyncio
    async def test_aretrieve_all_sources_delegates(self):
        """MemoryManager should delegate to store's aretrieve_all_sources."""
        mock_store = MagicMock()
        mock_store.aretrieve_all_sources = AsyncMock(
            return_value=[
                _make_record("Result 1", source="semantic"),
                _make_record("Result 2", source="rfe_knowledge"),
                _make_record("Result 3", source="public_knowledge_base"),
            ]
        )

        mm = MemoryManager(
            semantic=mock_store,
            episodic=MagicMock(),
            working=MagicMock(),
        )

        results = await mm.aretrieve_all_sources("test query", topk=10)

        mock_store.aretrieve_all_sources.assert_called_once_with(
            query="test query", topk=10
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_aretrieve_knowledge_base_delegates(self):
        """MemoryManager should delegate KB search to store."""
        mock_store = MagicMock()
        mock_store.aretrieve_knowledge_base = AsyncMock(
            return_value=[_make_record("KB result")]
        )

        mm = MemoryManager(
            semantic=mock_store,
            episodic=MagicMock(),
            working=MagicMock(),
        )

        results = await mm.aretrieve_knowledge_base("awards", topk=5)

        mock_store.aretrieve_knowledge_base.assert_called_once_with(
            query="awards", topk=5
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_aretrieve_case_documents_delegates(self):
        """MemoryManager should delegate case doc search to store."""
        mock_store = MagicMock()
        mock_store.aretrieve_case_documents = AsyncMock(
            return_value=[_make_record("Case doc")]
        )

        mm = MemoryManager(
            semantic=mock_store,
            episodic=MagicMock(),
            working=MagicMock(),
        )

        results = await mm.aretrieve_case_documents(
            "resume", case_id="case-123", topk=5
        )

        mock_store.aretrieve_case_documents.assert_called_once_with(
            query="resume", case_id="case-123", user_id=None, topk=5
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_aretrieve_hybrid_delegates(self):
        """MemoryManager should delegate hybrid search to store."""
        mock_store = MagicMock()
        mock_store.aretrieve_hybrid = AsyncMock(
            return_value=[_make_record("Hybrid result")]
        )

        mm = MemoryManager(
            semantic=mock_store,
            episodic=MagicMock(),
            working=MagicMock(),
        )

        results = await mm.aretrieve_hybrid(
            "awards", case_id="case-123", topk=8, knowledge_weight=0.4
        )

        mock_store.aretrieve_hybrid.assert_called_once_with(
            query="awards",
            case_id="case-123",
            user_id=None,
            topk=8,
            knowledge_weight=0.4,
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fallback_when_store_lacks_method(self):
        """MemoryManager should fallback if store lacks specialized methods."""
        mock_store = MagicMock(spec=[])  # No methods at all
        mock_store.aretrieve = AsyncMock(return_value=[_make_record("Fallback")])

        mm = MemoryManager(
            semantic=mock_store,
            episodic=MagicMock(),
            working=MagicMock(),
        )

        # aretrieve_all_sources fallback
        results = await mm.aretrieve_all_sources("test", topk=5)
        assert len(results) == 1
        mock_store.aretrieve.assert_called_with(query="test", user_id=None, topk=5)
