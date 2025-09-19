"""A simplified RAG retriever implementation for testing purposes."""

from __future__ import annotations

from typing import Any

import numpy as np


class SimpleEmbedder:
    """A mock embedding model that produces fixed-dimension vectors."""

    def __init__(self, embedding_dim: int = 384):
        # This parameter is named correctly as embedding_dim
        self.embedding_dim = embedding_dim

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        """Simulates batch embedding of texts."""
        # In a real scenario, this would be a single call to an embedding service.
        return [list(np.random.rand(self.embedding_dim)) for _ in texts]


class PineconeIndex:
    """A mock Pinecone index."""

    def __init__(self, index_name: str, dimension: int):
        """
        Initializes the mock index, checking for dimension mismatch.
        Note: Pinecone's client uses 'dimension', so we check against that.
        """
        self.index_name = index_name
        self.dimension = dimension
        self.vectors = {}

    def upsert(self, vectors: list[dict[str, Any]]):
        """Simulates upserting vectors to the index."""
        for vec in vectors:
            if len(vec["values"]) != self.dimension:
                raise ValueError(
                    f"Vector dimension {len(vec['values'])} does not match index dimension {self.dimension}"
                )
            self.vectors[vec["id"]] = vec["values"]
        return {"upserted_count": len(vectors)}


class RAGRetriever:
    """
    A retriever that uses an embedder and a vector index to store and retrieve
    information.
    """

    def __init__(self, embedder: SimpleEmbedder, index: PineconeIndex):
        # Verify that the embedder's output dimension matches the index's required dimension.
        if embedder.embedding_dim != index.dimension:
            raise ValueError(
                "Dimension mismatch: Embedder dimension is "
                f"{embedder.embedding_dim} but index dimension is {index.dimension}."
            )
        self.embedder = embedder
        self.index = index

    async def add_documents(self, documents: list[str]):
        """
        Embeds a batch of documents and upserts them into the index.
        """
        # This should call aembed ONCE for the entire batch.
        embeddings = await self.embedder.aembed(documents)

        vectors_to_upsert = [{"id": f"doc_{i}", "values": emb} for i, emb in enumerate(embeddings)]

        self.index.upsert(vectors=vectors_to_upsert)
