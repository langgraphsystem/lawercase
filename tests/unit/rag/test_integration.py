"""Integration tests for RAG Pipeline with Memory System.

Tests the integration between RAG pipeline components and
the existing memory management system.
"""

from __future__ import annotations

import pytest

from core.memory.memory_manager import MemoryManager
from core.memory.models import MemoryRecord
from core.memory.stores.semantic_store import SemanticStore
from core.rag import (
    BM25Retriever,
    Document,
    HybridRetriever,
    MemoryManagerAdapter,
    RAGPipeline,
    SemanticStoreAdapter,
    create_memory_adapter,
)


class TestSemanticStoreAdapter:
    """Tests for SemanticStoreAdapter."""

    @pytest.fixture
    def semantic_store(self) -> SemanticStore:
        """Create semantic store with test data."""
        store = SemanticStore(max_items=100, ttl_seconds=3600)
        return store

    @pytest.fixture
    def sample_records(self) -> list[MemoryRecord]:
        """Create sample memory records."""
        return [
            MemoryRecord(
                text="EB-1A visa requires extraordinary ability in sciences, arts, education, business, or athletics.",
                user_id="test_user",
                type="semantic",
                tags=["immigration", "visa", "eb1a"],
                source="uscis",
            ),
            MemoryRecord(
                text="H-1B visa is for specialty occupations requiring a bachelor's degree.",
                user_id="test_user",
                type="semantic",
                tags=["immigration", "visa", "h1b"],
                source="uscis",
            ),
            MemoryRecord(
                text="Contract law governs agreements between parties with offer, acceptance, and consideration.",
                user_id="test_user",
                type="semantic",
                tags=["contract", "law"],
                source="legal_encyclopedia",
            ),
        ]

    @pytest.mark.asyncio
    async def test_adapter_creation(self, semantic_store: SemanticStore) -> None:
        """Test creating adapter."""
        adapter = SemanticStoreAdapter(semantic_store)
        assert adapter.store is semantic_store
        assert adapter.default_user_id is None

    @pytest.mark.asyncio
    async def test_adapter_with_default_user(self, semantic_store: SemanticStore) -> None:
        """Test adapter with default user ID."""
        adapter = SemanticStoreAdapter(
            semantic_store,
            default_user_id="default_user",
        )
        assert adapter.default_user_id == "default_user"

    @pytest.mark.asyncio
    async def test_search_empty_store(self, semantic_store: SemanticStore) -> None:
        """Test searching empty store."""
        adapter = SemanticStoreAdapter(semantic_store)
        results = await adapter.asearch("EB-1A visa", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_data(
        self,
        semantic_store: SemanticStore,
        sample_records: list[MemoryRecord],
    ) -> None:
        """Test searching store with data."""
        await semantic_store.ainsert(sample_records)
        adapter = SemanticStoreAdapter(semantic_store)

        results = await adapter.asearch("EB-1A visa extraordinary", top_k=5)
        assert len(results) > 0

        # Results should be (text, score) tuples
        text, score = results[0]
        assert isinstance(text, str)
        assert isinstance(score, float)
        assert "EB-1A" in text or "extraordinary" in text

    @pytest.mark.asyncio
    async def test_search_respects_top_k(
        self,
        semantic_store: SemanticStore,
        sample_records: list[MemoryRecord],
    ) -> None:
        """Test that search respects top_k limit."""
        await semantic_store.ainsert(sample_records)
        adapter = SemanticStoreAdapter(semantic_store)

        results = await adapter.asearch("visa immigration", top_k=1)
        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_search_scores_sorted(
        self,
        semantic_store: SemanticStore,
        sample_records: list[MemoryRecord],
    ) -> None:
        """Test that results are sorted by score."""
        await semantic_store.ainsert(sample_records)
        adapter = SemanticStoreAdapter(semantic_store)

        results = await adapter.asearch("visa immigration law", top_k=10)
        if len(results) > 1:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)


class TestMemoryManagerAdapter:
    """Tests for MemoryManagerAdapter."""

    @pytest.fixture
    def memory_manager(self) -> MemoryManager:
        """Create memory manager."""
        return MemoryManager()

    @pytest.fixture
    def sample_records(self) -> list[MemoryRecord]:
        """Sample records for testing."""
        return [
            MemoryRecord(
                text="Green card application process takes 12-18 months.",
                user_id="user1",
                type="semantic",
                tags=["green_card"],
                source="test",
            ),
            MemoryRecord(
                text="Priority date is when USCIS receives the petition.",
                user_id="user1",
                type="semantic",
                tags=["priority_date"],
                source="test",
            ),
        ]

    @pytest.mark.asyncio
    async def test_adapter_creation(self, memory_manager: MemoryManager) -> None:
        """Test creating adapter."""
        adapter = MemoryManagerAdapter(memory_manager)
        assert adapter.manager is memory_manager

    @pytest.mark.asyncio
    async def test_search_with_data(
        self,
        memory_manager: MemoryManager,
        sample_records: list[MemoryRecord],
    ) -> None:
        """Test searching with data."""
        await memory_manager.awrite(sample_records)
        adapter = MemoryManagerAdapter(memory_manager)

        results = await adapter.asearch("green card application", top_k=5)
        assert len(results) > 0
        text, _score = results[0]
        assert "green card" in text.lower() or "application" in text.lower()


class TestCreateMemoryAdapter:
    """Tests for create_memory_adapter factory."""

    @pytest.mark.asyncio
    async def test_creates_semantic_adapter(self) -> None:
        """Test factory creates SemanticStoreAdapter."""
        store = SemanticStore()
        adapter = create_memory_adapter(store)
        assert isinstance(adapter, SemanticStoreAdapter)

    @pytest.mark.asyncio
    async def test_creates_memory_adapter(self) -> None:
        """Test factory creates MemoryManagerAdapter."""
        manager = MemoryManager()
        adapter = create_memory_adapter(manager)
        assert isinstance(adapter, MemoryManagerAdapter)

    @pytest.mark.asyncio
    async def test_invalid_source_raises_error(self) -> None:
        """Test factory raises error for invalid source."""
        with pytest.raises(TypeError):
            create_memory_adapter("invalid")  # type: ignore[arg-type]


class TestHybridRAGWithMemory:
    """Integration tests for hybrid RAG with memory adapters."""

    @pytest.fixture
    def semantic_store_with_data(self) -> SemanticStore:
        """Create semantic store with test data."""
        store = SemanticStore()
        return store

    @pytest.fixture
    def sample_records(self) -> list[MemoryRecord]:
        """Sample records."""
        return [
            MemoryRecord(
                text="EB-1A visa category is for individuals with extraordinary ability.",
                user_id="user",
                type="semantic",
                tags=["immigration"],
                source="test",
            ),
            MemoryRecord(
                text="Extraordinary ability means sustained national or international acclaim.",
                user_id="user",
                type="semantic",
                tags=["immigration"],
                source="test",
            ),
        ]

    @pytest.mark.asyncio
    async def test_hybrid_with_memory_adapter(
        self,
        semantic_store_with_data: SemanticStore,
        sample_records: list[MemoryRecord],
    ) -> None:
        """Test hybrid retriever with memory adapter as dense retriever."""
        await semantic_store_with_data.ainsert(sample_records)

        # Create BM25 retriever with same documents
        documents = [r.text for r in sample_records]
        bm25 = BM25Retriever(documents=documents)

        # Create adapter
        adapter = SemanticStoreAdapter(semantic_store_with_data)

        # Create hybrid retriever
        hybrid = HybridRetriever(
            sparse_retriever=bm25,
            dense_retriever=adapter,
            sparse_weight=0.5,
            dense_weight=0.5,
        )

        # Search
        results = await hybrid.search("extraordinary ability EB-1A", top_k=3)
        assert len(results) > 0


class TestRAGPipelineWithMemory:
    """Integration tests for full RAG pipeline with memory."""

    @pytest.fixture
    def pipeline(self) -> RAGPipeline:
        """Create RAG pipeline."""
        return RAGPipeline(chunk_size=200, use_hybrid=False)

    @pytest.fixture
    def memory_manager(self) -> MemoryManager:
        """Create memory manager."""
        return MemoryManager()

    @pytest.mark.asyncio
    async def test_pipeline_with_dense_adapter(
        self,
        pipeline: RAGPipeline,
        memory_manager: MemoryManager,
    ) -> None:
        """Test setting memory adapter as dense retriever."""
        # Add some data to memory
        records = [
            MemoryRecord(
                text="Immigration law includes various visa categories.",
                user_id="test",
                type="semantic",
                tags=["immigration"],
                source="test",
            ),
        ]
        await memory_manager.awrite(records)

        # Create adapter and set as dense retriever
        adapter = MemoryManagerAdapter(memory_manager)
        pipeline.set_dense_retriever(adapter)

        # Add documents to pipeline
        docs = [
            Document(text="EB-1A visa is for extraordinary ability."),
            Document(text="H-1B visa requires specialty occupation."),
        ]
        await pipeline.ingest(docs)

        # Query should work
        result = await pipeline.query("visa requirements", top_k=3)
        assert "results" in result

    @pytest.mark.asyncio
    async def test_end_to_end_rag_memory_integration(self) -> None:
        """Test end-to-end RAG with memory integration."""
        # Setup memory
        memory = MemoryManager()
        memory_records = [
            MemoryRecord(
                text="Previous case: AI researcher approved for EB-1A with 100+ citations.",
                user_id="case_db",
                type="semantic",
                tags=["eb1a", "approved", "ai"],
                source="case_database",
            ),
            MemoryRecord(
                text="Legal precedent: Matter of Dhanasar defines extraordinary ability.",
                user_id="case_db",
                type="semantic",
                tags=["precedent", "eb1a"],
                source="case_law",
            ),
        ]
        await memory.awrite(memory_records)

        # Setup RAG pipeline
        pipeline = RAGPipeline(chunk_size=300, use_hybrid=True)

        # Set memory adapter
        adapter = MemoryManagerAdapter(memory)
        pipeline.set_dense_retriever(adapter)

        # Ingest additional documents
        docs = [
            Document(
                text="EB-1A visa requirements include: sustained national acclaim, "
                "extraordinary ability evidence, and intent to work in the field.",
                metadata={"source": "uscis"},
            ),
            Document(
                text="Evidence categories for EB-1A include: awards, memberships, "
                "published work, judging others' work, and scholarly articles.",
                metadata={"source": "uscis"},
            ),
        ]
        await pipeline.ingest(docs)

        # Query
        result = await pipeline.query(
            "What evidence is needed for EB-1A visa?",
            top_k=5,
        )

        # Verify results
        assert len(result["results"]) > 0
        assert result["context"]["text"] != ""

        # Check stats
        stats = pipeline.get_stats()
        assert stats["queries_processed"] >= 1
        assert stats["documents_ingested"] >= 2
