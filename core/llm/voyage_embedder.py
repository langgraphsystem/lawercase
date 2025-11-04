"""Voyage AI embeddings client for voyage-3-large (2048 dimensions).

Official Documentation:
https://docs.voyageai.com/docs/embeddings
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import SecretStr

try:
    import voyageai

    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False


class VoyageEmbedder:
    """
    Voyage AI embeddings client using voyage-3-large model.

    Features:
    - 2048-dimensional embeddings
    - Optimized for semantic search
    - Input type optimization (document vs query)
    - Automatic truncation for long texts

    Docs: https://docs.voyageai.com/docs/embeddings
    """

    def __init__(self, api_key: SecretStr | None = None):
        if not VOYAGE_AVAILABLE:
            raise ImportError("voyageai package is required. Install with: pip install voyageai")

        # Import config here to avoid circular imports
        from ..storage.config import get_storage_config

        config = get_storage_config()

        self.api_key = api_key or config.voyage_api_key
        self.model = config.voyage_model  # "voyage-3-large"
        self.dimension = config.voyage_dimension  # 2048
        self.default_input_type = config.voyage_input_type_default

        # Initialize Voyage client
        self.client = voyageai.Client(api_key=self.api_key.get_secret_value())

    async def aembed(self, texts: list[str], input_type: str | None = None) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            input_type: "document" (for indexing) or "query" (for search).
                       If None, uses default from config.

        Returns:
            List of embedding vectors, each with 2048 dimensions

        Example:
            >>> embedder = VoyageEmbedder()
            >>> docs = ["Legal document text...", "Case summary..."]
            >>> embeddings = await embedder.aembed(docs, input_type="document")
            >>> len(embeddings[0])
            2048
        """
        if not texts:
            return []

        input_type = input_type or self.default_input_type

        # Call Voyage API
        # https://docs.voyageai.com/docs/embeddings#parameters
        result = self.client.embed(
            texts=texts,
            model=self.model,
            input_type=input_type,  # Optimizes embeddings for use case
            truncation=True,  # Auto-truncate texts exceeding token limit
        )

        return result.embeddings

    async def aembed_query(self, query: str) -> list[float]:
        """
        Generate embedding optimized for search queries.

        Args:
            query: Search query text

        Returns:
            Single embedding vector (2048-dim)

        Example:
            >>> embedder = VoyageEmbedder()
            >>> query_vec = await embedder.aembed_query("find similar cases")
            >>> len(query_vec)
            2048
        """
        embeddings = await self.aembed([query], input_type="query")
        return embeddings[0]

    async def aembed_documents(self, documents: list[str]) -> list[list[float]]:
        """
        Generate embeddings optimized for document indexing.

        Args:
            documents: List of document texts

        Returns:
            List of embedding vectors (each 2048-dim)

        Example:
            >>> embedder = VoyageEmbedder()
            >>> docs = ["Document 1", "Document 2"]
            >>> doc_vecs = await embedder.aembed_documents(docs)
            >>> all(len(vec) == 2048 for vec in doc_vecs)
            True
        """
        return await self.aembed(documents, input_type="document")

    def get_dimension(self) -> int:
        """Get embedding dimension (2048 for voyage-3-large)."""
        return self.dimension

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model


def create_voyage_embedder(api_key: SecretStr | None = None) -> VoyageEmbedder:
    """
    Factory function to create Voyage embedder with config from environment.

    Args:
        api_key: Optional API key override

    Returns:
        Configured VoyageEmbedder instance

    Example:
        >>> embedder = create_voyage_embedder()
        >>> embedder.get_dimension()
        2048
    """
    return VoyageEmbedder(api_key=api_key)
