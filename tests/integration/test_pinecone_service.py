"""Integration tests for Pinecone vector service with mocked client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.vector.service import PineconeVectorService, VectorRecord, VectorMetadata, QueryResult
from core.vector.pinecone_client import PineconeClient, PineconeClientError
from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings()
    settings.pinecone_api_key = "test-api-key"
    settings.pinecone_env = "us-east-1"
    settings.pinecone_index = "test-index"
    settings.vector_dim = 1536
    settings.vector_namespace = "test-namespace"
    return settings


@pytest.fixture
def sample_vector_records():
    """Sample vector records for testing."""
    return [
        VectorRecord(
            id="chunk_1",
            vector=[0.1] * 1536,
            metadata=VectorMetadata(
                document_id="doc_1",
                chunk_id="chunk_1",
                lang="en",
                source="test_document.pdf",
                tags=["legal", "contract"],
                text="This is a test chunk about legal contracts."
            )
        ),
        VectorRecord(
            id="chunk_2",
            vector=[0.2] * 1536,
            metadata=VectorMetadata(
                document_id="doc_1",
                chunk_id="chunk_2",
                lang="en",
                source="test_document.pdf",
                tags=["legal", "terms"],
                text="This chunk discusses legal terms and conditions."
            )
        )
    ]


class TestPineconeClient:
    """Test PineconeClient with mocked Pinecone API."""

    @patch('core.vector.pinecone_client.PINECONE_AVAILABLE', True)
    @patch('core.vector.pinecone_client.Pinecone')
    @patch('core.vector.pinecone_client.ServerlessSpec')
    async def test_ensure_index_exists_creates_new_index(self, mock_serverless_spec, mock_pinecone_class, mock_settings):
        """Test index creation when index doesn't exist."""
        # Mock Pinecone client
        mock_client = MagicMock()
        mock_pinecone_class.return_value = mock_client

        # Mock list_indexes response (empty)
        mock_indexes_response = MagicMock()
        mock_indexes_response.indexes = []
        mock_client.list_indexes.return_value = mock_indexes_response

        # Mock ServerlessSpec
        mock_spec = MagicMock()
        mock_serverless_spec.return_value = mock_spec

        client = PineconeClient(mock_settings)
        result = await client.ensure_index_exists(1536)

        assert result is True
        mock_client.create_index.assert_called_once_with(
            name="test-index",
            dimension=1536,
            metric="cosine",
            spec=mock_spec
        )

    @patch('core.vector.pinecone_client.PINECONE_AVAILABLE', True)
    @patch('core.vector.pinecone_client.Pinecone')
    async def test_ensure_index_exists_index_already_exists(self, mock_pinecone_class, mock_settings):
        """Test when index already exists."""
        # Mock Pinecone client
        mock_client = MagicMock()
        mock_pinecone_class.return_value = mock_client

        # Mock list_indexes response (with existing index)
        mock_index = MagicMock()
        mock_index.name = "test-index"
        mock_indexes_response = MagicMock()
        mock_indexes_response.indexes = [mock_index]
        mock_client.list_indexes.return_value = mock_indexes_response

        client = PineconeClient(mock_settings)
        result = await client.ensure_index_exists(1536)

        assert result is True
        mock_client.create_index.assert_not_called()

    @patch('core.vector.pinecone_client.PINECONE_AVAILABLE', True)
    @patch('core.vector.pinecone_client.Pinecone')
    async def test_upsert_vectors(self, mock_pinecone_class, mock_settings):
        """Test upserting vectors."""
        # Mock Pinecone client and index
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_pinecone_class.return_value = mock_client
        mock_client.Index.return_value = mock_index

        client = PineconeClient(mock_settings)

        vectors = [
            {"id": "test_1", "values": [0.1] * 1536, "metadata": {"text": "test"}}
        ]

        result = await client.upsert(vectors)

        assert result is True
        mock_index.upsert.assert_called_once_with(
            vectors=vectors,
            namespace="test-namespace"
        )

    @patch('core.vector.pinecone_client.PINECONE_AVAILABLE', True)
    @patch('core.vector.pinecone_client.Pinecone')
    async def test_query_vectors(self, mock_pinecone_class, mock_settings):
        """Test querying vectors."""
        # Mock Pinecone client and index
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_pinecone_class.return_value = mock_client
        mock_client.Index.return_value = mock_index

        # Mock query response
        mock_response = {
            "matches": [
                {"id": "chunk_1", "score": 0.95, "metadata": {"text": "test chunk"}}
            ]
        }
        mock_index.query.return_value = mock_response

        client = PineconeClient(mock_settings)

        query_vector = [0.1] * 1536
        result = await client.query(query_vector, top_k=5)

        assert result == mock_response
        mock_index.query.assert_called_once_with(
            vector=query_vector,
            top_k=5,
            filter=None,
            namespace="test-namespace",
            include_metadata=True
        )


class TestPineconeVectorService:
    """Test PineconeVectorService with mocked client."""

    @patch('core.vector.service.PineconeClient')
    async def test_initialize_success(self, mock_client_class, mock_settings):
        """Test successful initialization."""
        mock_client = AsyncMock()
        mock_client.ensure_index_exists.return_value = True
        mock_client_class.return_value = mock_client

        service = PineconeVectorService(mock_settings)
        result = await service.initialize(1536)

        assert result is True
        assert service._initialized is True
        mock_client.ensure_index_exists.assert_called_once_with(1536)

    @patch('core.vector.service.PineconeClient')
    async def test_upsert_batch(self, mock_client_class, mock_settings, sample_vector_records):
        """Test batch upsert operation."""
        mock_client = AsyncMock()
        mock_client.upsert.return_value = True
        mock_client_class.return_value = mock_client

        service = PineconeVectorService(mock_settings)
        service._initialized = True

        result = await service.upsert_batch(sample_vector_records)

        assert result is True
        mock_client.upsert.assert_called_once()

        # Verify vectors were properly formatted
        call_args = mock_client.upsert.call_args[0]  # Get positional arguments
        vectors = call_args[0]

        assert len(vectors) == 2
        assert vectors[0]["id"] == "chunk_1"
        assert vectors[0]["metadata"]["document_id"] == "doc_1"
        assert vectors[0]["metadata"]["tags"] == "legal,contract"

    @patch('core.vector.service.PineconeClient')
    async def test_query(self, mock_client_class, mock_settings):
        """Test vector query operation."""
        mock_client = AsyncMock()
        mock_query_result = {
            "matches": [
                {
                    "id": "chunk_1",
                    "score": 0.95,
                    "metadata": {
                        "document_id": "doc_1",
                        "chunk_id": "chunk_1",
                        "lang": "en",
                        "source": "test.pdf",
                        "tags": "legal,contract",
                        "text": "Test text"
                    }
                }
            ]
        }
        mock_client.query.return_value = mock_query_result
        mock_client_class.return_value = mock_client

        service = PineconeVectorService(mock_settings)
        service._initialized = True

        query_vector = [0.1] * 1536
        results = await service.query(query_vector, top_k=5)

        assert len(results) == 1
        assert isinstance(results[0], QueryResult)
        assert results[0].id == "chunk_1"
        assert results[0].score == 0.95
        assert results[0].metadata.document_id == "doc_1"
        assert results[0].metadata.tags == ["legal", "contract"]

    @patch('core.vector.service.PineconeClient')
    async def test_health_check(self, mock_client_class, mock_settings):
        """Test health check operation."""
        mock_client = AsyncMock()
        mock_client.list_indexes.return_value = ["index1", "index2"]
        mock_client_class.return_value = mock_client

        service = PineconeVectorService(mock_settings)
        result = await service.health_check()

        assert result is True
        mock_client.list_indexes.assert_called_once()

    @patch('core.vector.service.PineconeClient')
    async def test_health_check_failure(self, mock_client_class, mock_settings):
        """Test health check when Pinecone is unavailable."""
        mock_client = AsyncMock()
        mock_client.list_indexes.side_effect = PineconeClientError("Connection failed")
        mock_client_class.return_value = mock_client

        service = PineconeVectorService(mock_settings)
        result = await service.health_check()

        assert result is False

    async def test_upsert_batch_not_initialized(self, mock_settings, sample_vector_records):
        """Test upsert when service is not initialized."""
        service = PineconeVectorService(mock_settings)
        # Don't initialize

        result = await service.upsert_batch(sample_vector_records)

        assert result is False

    async def test_query_not_initialized(self, mock_settings):
        """Test query when service is not initialized."""
        service = PineconeVectorService(mock_settings)
        # Don't initialize

        query_vector = [0.1] * 1536
        results = await service.query(query_vector)

        assert results == []