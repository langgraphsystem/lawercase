"""Pinecone vector store for semantic memory with Voyage embeddings.

Official Documentation:
https://docs.pinecone.io/docs/python-client
https://docs.pinecone.io/docs/manage-indexes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from pydantic import SecretStr

    from ..memory.models import MemoryRecord

try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False


class PineconeSemanticStore:
    """
    Pinecone-backed semantic memory store for vector search.

    Features:
    - Serverless Pinecone index with cosine similarity
    - 2048-dimensional vectors (voyage-3-large)
    - Metadata filtering for multi-tenant isolation
    - Automatic index creation

    Docs: https://docs.pinecone.io/docs/python-client
    """

    def __init__(
        self,
        api_key: SecretStr | None = None,
        index_name: str | None = None,
        namespace: str | None = None,
    ):
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "pinecone package is required. Install with: pip install pinecone-client"
            )

        # Import config here to avoid circular imports
        from .config import get_storage_config

        config = get_storage_config()

        self.api_key = api_key or config.pinecone_api_key
        self.index_name = index_name or config.pinecone_index_name
        self.namespace = namespace or config.pinecone_namespace
        self.environment = config.pinecone_environment
        self.dimension = config.voyage_dimension  # 2048

        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.api_key.get_secret_value())

        # Ensure index exists
        self._ensure_index()

        # Get index connection
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self) -> None:
        """Create Pinecone index if it doesn't exist."""
        existing_indexes = self.pc.list_indexes()
        index_names = [idx.name for idx in existing_indexes]

        if self.index_name not in index_names:
            # Create serverless index
            # https://docs.pinecone.io/docs/manage-indexes#create-a-serverless-index
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",  # Cosine similarity for Voyage embeddings
                spec=ServerlessSpec(cloud="aws", region=self.environment),
            )

    async def upsert(
        self,
        records: list[MemoryRecord],
        embeddings: list[list[float]],
    ) -> int:
        """
        Insert or update records with embeddings in Pinecone.

        Args:
            records: Memory records with text and metadata
            embeddings: Corresponding Voyage embeddings (2048-dim each)

        Returns:
            Number of vectors upserted

        Raises:
            ValueError: If records and embeddings length mismatch

        Example:
            >>> store = PineconeSemanticStore()
            >>> records = [MemoryRecord(user_id="u1", text="fact")]
            >>> embeddings = [[0.1] * 2048]
            >>> count = await store.upsert(records, embeddings)
        """
        if not records or not embeddings:
            return 0

        if len(records) != len(embeddings):
            raise ValueError(f"Mismatch: {len(records)} records but {len(embeddings)} embeddings")

        # Prepare vectors for Pinecone
        vectors = []
        for record, embedding in zip(records, embeddings, strict=False):
            # Generate or retrieve Pinecone ID
            pinecone_id = (
                record.metadata.get("pinecone_id")
                if hasattr(record, "metadata") and record.metadata
                else str(uuid4())
            )
            if not pinecone_id:
                pinecone_id = str(uuid4())

            # Prepare metadata (stored alongside vector in Pinecone)
            metadata = {
                "record_id": str(getattr(record, "record_id", uuid4())),
                "user_id": record.user_id,
                "text": record.text[:1000],  # Limit for metadata size
                "type": record.type,
                "source": record.source or "",
                "tags": record.tags if record.tags else [],
            }

            # Add timestamp if available
            if hasattr(record, "created_at") and record.created_at:
                metadata["created_at"] = record.created_at.isoformat()

            # Merge custom metadata (only primitive types)
            if hasattr(record, "metadata") and record.metadata:
                for k, v in record.metadata.items():
                    if isinstance(v, str | int | float | bool):
                        metadata[k] = v

            vectors.append({"id": pinecone_id, "values": embedding, "metadata": metadata})

        # Batch upsert to Pinecone
        # https://docs.pinecone.io/docs/upsert-data
        self.index.upsert(vectors=vectors, namespace=self.namespace)

        return len(vectors)

    async def search(
        self,
        query_embedding: list[float],
        user_id: str | None = None,
        topk: int = 10,
        filters: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Vector similarity search in Pinecone.

        Args:
            query_embedding: Query vector (2048-dim)
            user_id: Filter results by user_id
            topk: Number of results to return
            filters: Additional metadata filters
            min_score: Minimum similarity score (0-1)

        Returns:
            List of matches with scores and metadata

        Example:
            >>> store = PineconeSemanticStore()
            >>> query_vec = [0.1] * 2048
            >>> results = await store.search(query_vec, user_id="u1", topk=5)
        """
        # Build Pinecone metadata filter
        # https://docs.pinecone.io/docs/metadata-filtering
        pinecone_filter: dict[str, Any] = {}

        if user_id:
            pinecone_filter["user_id"] = {"$eq": user_id}

        if filters:
            # Type filter
            if record_type := filters.get("type"):
                pinecone_filter["type"] = {"$eq": record_type}

            # Tags filter (match any)
            if tags := filters.get("tags"):
                if isinstance(tags, list):
                    pinecone_filter["tags"] = {"$in": tags}

            # Source filter
            if source := filters.get("source"):
                pinecone_filter["source"] = {"$eq": source}

        # Query Pinecone index
        results = self.index.query(
            vector=query_embedding,
            top_k=topk,
            namespace=self.namespace,
            filter=pinecone_filter if pinecone_filter else None,
            include_metadata=True,
        )

        # Format results
        matches = []
        for match in results.matches:
            if match.score >= min_score:
                matches.append(
                    {
                        "pinecone_id": match.id,
                        "score": match.score,
                        "metadata": match.metadata,
                    }
                )

        return matches

    async def delete(self, pinecone_ids: list[str]) -> None:
        """
        Delete vectors from Pinecone by IDs.

        Args:
            pinecone_ids: List of Pinecone vector IDs to delete

        Example:
            >>> store = PineconeSemanticStore()
            >>> await store.delete(["id1", "id2"])
        """
        if not pinecone_ids:
            return

        self.index.delete(ids=pinecone_ids, namespace=self.namespace)

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        """
        Delete vectors matching metadata filters.

        Args:
            filters: Metadata filters for deletion

        Example:
            >>> store = PineconeSemanticStore()
            >>> await store.delete_by_filter({"user_id": {"$eq": "u1"}})
        """
        self.index.delete(filter=filters, namespace=self.namespace)

    async def delete_all(self) -> None:
        """Delete all vectors in the current namespace."""
        self.index.delete(delete_all=True, namespace=self.namespace)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get Pinecone index statistics.

        Returns:
            Dict with total vectors, dimension, and namespace info

        Example:
            >>> store = PineconeSemanticStore()
            >>> stats = await store.get_stats()
            >>> print(stats["total_vectors"])
        """
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "namespaces": stats.namespaces,
            "index_fullness": getattr(stats, "index_fullness", None),
        }

    async def health_check(self) -> bool:
        """
        Check Pinecone connectivity.

        Returns:
            True if connected, False otherwise
        """
        try:
            await self.get_stats()
            return True
        except Exception:
            return False


def create_pinecone_store(namespace: str | None = None) -> PineconeSemanticStore:
    """
    Factory function to create Pinecone store with config from environment.

    Args:
        namespace: Optional namespace override for multi-tenancy

    Returns:
        Configured PineconeSemanticStore instance

    Example:
        >>> store = create_pinecone_store(namespace="production")
        >>> store.dimension
        2048
    """
    return PineconeSemanticStore(namespace=namespace)
