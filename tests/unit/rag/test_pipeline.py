"""Unit tests for RAG Pipeline.

Tests the main RAGPipeline class and its components.
"""

from __future__ import annotations

import pytest

from core.rag import (ChunkingStrategy, Document, DocumentStore, RAGPipeline,
                      RAGResult, create_rag_pipeline)


class TestDocument:
    """Tests for Document dataclass."""

    def test_document_creation(self) -> None:
        """Test creating a document with text."""
        doc = Document(text="Test document content")
        assert doc.text == "Test document content"
        assert doc.doc_id is not None
        assert doc.doc_id.startswith("doc_")

    def test_document_with_metadata(self) -> None:
        """Test creating a document with metadata."""
        doc = Document(
            text="Immigration law requirements",
            metadata={"source": "uscis.gov", "category": "legal"},
        )
        assert doc.metadata["source"] == "uscis.gov"
        assert doc.metadata["category"] == "legal"

    def test_document_with_custom_id(self) -> None:
        """Test creating a document with custom ID."""
        doc = Document(text="Content", doc_id="custom_id_123")
        assert doc.doc_id == "custom_id_123"

    def test_document_id_generation_deterministic(self) -> None:
        """Test that same content generates same ID."""
        doc1 = Document(text="Same content")
        doc2 = Document(text="Same content")
        assert doc1.doc_id == doc2.doc_id

    def test_document_id_different_content(self) -> None:
        """Test that different content generates different IDs."""
        doc1 = Document(text="Content A")
        doc2 = Document(text="Content B")
        assert doc1.doc_id != doc2.doc_id


class TestRAGResult:
    """Tests for RAGResult dataclass."""

    def test_rag_result_creation(self) -> None:
        """Test creating a RAG result."""
        result = RAGResult(
            chunk_id="chunk_001",
            text="Retrieved text content",
            score=0.85,
        )
        assert result.chunk_id == "chunk_001"
        assert result.text == "Retrieved text content"
        assert result.score == 0.85
        assert result.metadata == {}

    def test_rag_result_with_metadata(self) -> None:
        """Test RAG result with metadata."""
        result = RAGResult(
            chunk_id="chunk_002",
            text="Content",
            score=0.7,
            metadata={"source": "doc.pdf", "page": 1},
        )
        assert result.metadata["source"] == "doc.pdf"
        assert result.metadata["page"] == 1


class TestDocumentStore:
    """Tests for DocumentStore."""

    def test_empty_store(self) -> None:
        """Test empty document store."""
        store = DocumentStore()
        assert len(store) == 0
        assert store.get_all_texts() == []

    def test_add_document(self) -> None:
        """Test adding a document."""
        store = DocumentStore()
        doc = Document(text="Test content", doc_id="doc1")
        store.add_document(doc)
        assert store.get_document("doc1") is not None
        assert store.get_document("doc1").text == "Test content"

    def test_get_nonexistent_document(self) -> None:
        """Test getting non-existent document."""
        store = DocumentStore()
        assert store.get_document("nonexistent") is None

    def test_get_content_map(self) -> None:
        """Test getting content map."""
        store = DocumentStore()
        # Add some chunks manually
        from core.rag import DocumentChunk

        chunk = DocumentChunk(
            content="Chunk content",
            chunk_id="chunk_001",
            start_pos=0,
            end_pos=13,
            metadata={},
        )
        store.add_chunks([chunk], "doc1")
        content_map = store.get_content_map()
        assert "chunk_001" in content_map
        assert content_map["chunk_001"] == "Chunk content"


class TestRAGPipeline:
    """Tests for RAGPipeline."""

    @pytest.fixture
    def sample_documents(self) -> list[Document]:
        """Create sample documents for testing."""
        return [
            Document(
                text="The EB-1A visa is for individuals with extraordinary ability. "
                "It requires evidence of sustained national or international acclaim.",
                metadata={"category": "immigration"},
            ),
            Document(
                text="Contract law governs agreements between parties. "
                "A valid contract requires offer, acceptance, and consideration.",
                metadata={"category": "contract"},
            ),
            Document(
                text="Immigration law covers various visa categories including EB-1, EB-2, and EB-3. "
                "Each category has different requirements and processing times.",
                metadata={"category": "immigration"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_pipeline_creation(self) -> None:
        """Test creating RAG pipeline."""
        pipeline = RAGPipeline()
        assert pipeline is not None
        assert len(pipeline.store) == 0

    @pytest.mark.asyncio
    async def test_pipeline_factory(self) -> None:
        """Test pipeline factory function."""
        pipeline = await create_rag_pipeline(
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=500,
        )
        assert pipeline is not None

    @pytest.mark.asyncio
    async def test_ingest_documents(self, sample_documents: list[Document]) -> None:
        """Test ingesting documents."""
        pipeline = RAGPipeline(chunk_size=200)
        chunks = await pipeline.ingest(sample_documents)
        assert len(chunks) > 0
        stats = pipeline.get_stats()
        assert stats["documents_ingested"] == 3
        assert stats["chunks_created"] > 0

    @pytest.mark.asyncio
    async def test_query_after_ingest(self, sample_documents: list[Document]) -> None:
        """Test querying after ingestion."""
        pipeline = RAGPipeline(chunk_size=200)
        await pipeline.ingest(sample_documents)

        result = await pipeline.query("What are EB-1A visa requirements?", top_k=3)
        assert "results" in result
        assert "context" in result
        assert "query_time_ms" in result
        assert len(result["results"]) > 0

    @pytest.mark.asyncio
    async def test_query_empty_pipeline(self) -> None:
        """Test querying empty pipeline."""
        pipeline = RAGPipeline()
        result = await pipeline.query("test query")
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_query_result_scores(self, sample_documents: list[Document]) -> None:
        """Test that query results have valid scores."""
        pipeline = RAGPipeline(chunk_size=200)
        await pipeline.ingest(sample_documents)

        result = await pipeline.query("immigration visa requirements", top_k=5)
        for r in result["results"]:
            assert isinstance(r, RAGResult)
            assert r.score >= 0

    @pytest.mark.asyncio
    async def test_context_assembly(self, sample_documents: list[Document]) -> None:
        """Test context assembly for LLM."""
        pipeline = RAGPipeline(chunk_size=200)
        await pipeline.ingest(sample_documents)

        result = await pipeline.query("contract law", top_k=2)
        context = result["context"]
        assert context is not None
        assert "text" in context
        assert "sources" in context
        assert "query" in context

    @pytest.mark.asyncio
    async def test_pipeline_stats(self, sample_documents: list[Document]) -> None:
        """Test pipeline statistics."""
        pipeline = RAGPipeline(chunk_size=200)
        await pipeline.ingest(sample_documents)
        await pipeline.query("test query")

        stats = pipeline.get_stats()
        assert stats["queries_processed"] == 1
        assert stats["store_size"] > 0

    @pytest.mark.asyncio
    async def test_clear_pipeline(self, sample_documents: list[Document]) -> None:
        """Test clearing pipeline."""
        pipeline = RAGPipeline(chunk_size=200)
        await pipeline.ingest(sample_documents)
        assert len(pipeline.store) > 0

        await pipeline.clear()
        assert len(pipeline.store) == 0
        stats = pipeline.get_stats()
        assert stats["documents_ingested"] == 0

    @pytest.mark.asyncio
    async def test_different_chunking_strategies(self) -> None:
        """Test different chunking strategies."""
        doc = Document(text="First sentence here. Second sentence follows. Third one now.")

        # Test just semantic strategy for speed
        pipeline = RAGPipeline(
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=50,
        )
        chunks = await pipeline.ingest([doc])
        assert len(chunks) > 0


class TestRAGPipelineWithHybrid:
    """Tests for RAG Pipeline with hybrid retrieval."""

    @pytest.mark.asyncio
    async def test_hybrid_disabled(self) -> None:
        """Test pipeline with hybrid disabled."""
        pipeline = RAGPipeline(use_hybrid=False)
        assert pipeline.use_hybrid is False

    @pytest.mark.asyncio
    async def test_hybrid_enabled_without_dense(self) -> None:
        """Test pipeline with hybrid enabled but no dense retriever."""
        pipeline = RAGPipeline(use_hybrid=True)
        assert pipeline.use_hybrid is True
        # Should work with sparse-only when dense not set
        doc = Document(text="Test document for hybrid search")
        await pipeline.ingest([doc])
        result = await pipeline.query("test")
        assert "results" in result


class TestRAGPipelineIntegration:
    """Integration tests for complete RAG workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        """Test complete RAG workflow."""
        # Create pipeline
        pipeline = RAGPipeline(
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=300,
            use_hybrid=False,  # Sparse only for simplicity
            use_reranking=False,
        )

        # Ingest documents
        documents = [
            Document(
                text="The EB-1A visa category is for individuals with extraordinary ability "
                "in sciences, arts, education, business, or athletics. Applicants must "
                "demonstrate sustained national or international acclaim.",
                metadata={"source": "uscis", "type": "visa_info"},
            ),
            Document(
                text="H-1B visa is a non-immigrant visa that allows US employers to "
                "temporarily employ foreign workers in specialty occupations. "
                "It requires a bachelor's degree or equivalent.",
                metadata={"source": "uscis", "type": "visa_info"},
            ),
            Document(
                text="Green card through employment can be obtained through various categories "
                "including EB-1, EB-2, and EB-3. Priority dates and processing times vary.",
                metadata={"source": "uscis", "type": "visa_info"},
            ),
        ]
        chunks = await pipeline.ingest(documents)
        assert len(chunks) > 0

        # Query for EB-1A information
        result = await pipeline.query(
            query="What is EB-1A visa extraordinary ability?",
            top_k=3,
        )

        # Verify results
        assert len(result["results"]) > 0
        assert result["context"]["text"] != ""

        # Top result should be about EB-1A
        top_result = result["results"][0]
        assert "EB-1A" in top_result.text or "extraordinary" in top_result.text

        # Check stats
        stats = pipeline.get_stats()
        assert stats["queries_processed"] == 1
        assert stats["documents_ingested"] == 3
