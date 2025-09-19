# -*- coding: utf-8 -*-
"""Tests for the RAG Retriever."""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Adjust the import path as necessary
from core.rag.retrieve import RAGRetriever, SimpleEmbedder, PineconeIndex

@pytest.fixture
def mock_embedder():
    """Fixture for a mocked SimpleEmbedder."""
    embedder = MagicMock(spec=SimpleEmbedder)
    embedder.embedding_dim = 384
    embedder.aembed = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    return embedder

@pytest.fixture
def mock_pinecone_index():
    """Fixture for a mocked PineconeIndex."""
    index = MagicMock(spec=PineconeIndex)
    index.dimension = 384
    index.upsert = MagicMock()
    return index

def test_retriever_init_correct_dimension(mock_embedder, mock_pinecone_index):
    """
    Tests that RAGRetriever initializes correctly when embedder and index dimensions match.
    This implicitly tests that the retriever correctly uses `embedding_dim` from the embedder
    and `dimension` from the index for comparison.
    """
    # Arrange & Act
    try:
        retriever = RAGRetriever(embedder=mock_embedder, index=mock_pinecone_index)
        # Assert
        assert retriever.embedder == mock_embedder
        assert retriever.index == mock_pinecone_index
    except ValueError:
        pytest.fail("RAGRetriever raised ValueError unexpectedly on matching dimensions.")

def test_retriever_init_dimension_mismatch():
    """
    Tests that RAGRetriever raises a ValueError on dimension mismatch.
    """
    # Arrange
    embedder_low_dim = SimpleEmbedder(embedding_dim=128)
    index_high_dim = PineconeIndex(index_name="test-index", dimension=384)

    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        RAGRetriever(embedder=embedder_low_dim, index=index_high_dim)
    
    assert "Dimension mismatch" in str(excinfo.value)
    assert "128" in str(excinfo.value)
    assert "384" in str(excinfo.value)

@pytest.mark.asyncio
async def test_retriever_batch_embedding_call(mock_embedder, mock_pinecone_index):
    """
    Tests that `aembed` is called only once for a list of documents, not per chunk.
    """
    # Arrange
    retriever = RAGRetriever(embedder=mock_embedder, index=mock_pinecone_index)
    documents = ["This is the first document.", "This is the second one."]

    # Act
    await retriever.add_documents(documents)

    # Assert
    # Verify that aembed was called exactly once with the list of documents
    mock_embedder.aembed.assert_called_once_with(documents)
    
    # Verify that the upsert call was made with the correct number of vectors
    mock_pinecone_index.upsert.assert_called_once()
    upsert_args = mock_pinecone_index.upsert.call_args[1]
    assert len(upsert_args["vectors"]) == len(documents)

@pytest.mark.asyncio
async def test_pinecone_index_upsert_dimension_check():
    """
    Simulates a Pinecone index initialization and checks that no mismatch occurs
    when the vector dimension is correct.
    """
    # Arrange
    embedder = SimpleEmbedder(embedding_dim=384)
    index = PineconeIndex(index_name="test-index", dimension=384)
    retriever = RAGRetriever(embedder=embedder, index=index)
    documents = ["A test document."]

    # Act & Assert
    try:
        # This call will fail if the vector dimension passed to upsert is incorrect
        await retriever.add_documents(documents)
    except ValueError as e:
        pytest.fail(f"Upsert failed with dimension mismatch unexpectedly: {e}")
