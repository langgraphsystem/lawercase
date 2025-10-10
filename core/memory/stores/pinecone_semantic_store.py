"""Pinecone-backed SemanticStore that implements the same interface as in-memory version.

This adapter allows seamless replacement of in-memory SemanticStore with Pinecone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ...llm.voyage_embedder import VoyageEmbedder
    from ..models import MemoryRecord

# Import storage modules
from ...storage.pinecone_store import PineconeSemanticStore


class PineconeSemanticStoreAdapter:
    """
    Adapter that wraps PineconeSemanticStore to match SemanticStore interface.

    This allows drop-in replacement in MemoryManager while using Pinecone + Voyage.
    """

    def __init__(
        self,
        pinecone_store: PineconeSemanticStore | None = None,
        embedder: VoyageEmbedder | None = None,
        namespace: str | None = None,
    ):
        """
        Initialize Pinecone semantic store adapter.

        Args:
            pinecone_store: PineconeSemanticStore instance (created if None)
            embedder: VoyageEmbedder instance (created if None)
            namespace: Pinecone namespace for multi-tenancy
        """
        # Lazy imports to avoid circular dependencies
        from ...llm.voyage_embedder import create_voyage_embedder
        from ...storage.pinecone_store import create_pinecone_store

        self.pinecone = pinecone_store or create_pinecone_store(namespace=namespace)
        self.embedder = embedder or create_voyage_embedder()

        # Cache for mapping MemoryRecord to Pinecone IDs
        self._record_to_pinecone_id: dict[str, str] = {}

    async def ainsert(self, records: Iterable[MemoryRecord]) -> int:
        """
        Insert memory records into Pinecone.

        Args:
            records: Iterable of MemoryRecord objects

        Returns:
            Number of records inserted

        Note:
            Embeddings are generated automatically using Voyage AI
        """
        records_list = list(records)
        if not records_list:
            return 0

        # Generate embeddings for all records
        texts = [r.text for r in records_list]
        embeddings = await self.embedder.aembed_documents(texts)

        # Generate Pinecone IDs for records
        for record in records_list:
            if not hasattr(record, "id") or not record.id:
                record.id = str(uuid4())

            # Store mapping
            pinecone_id = f"mem_{record.id}"
            self._record_to_pinecone_id[record.id] = pinecone_id

            # Add pinecone_id to metadata
            if not hasattr(record, "metadata"):
                record.metadata = {}  # type: ignore[attr-defined]
            record.metadata["pinecone_id"] = pinecone_id  # type: ignore[attr-defined]

        # Upsert to Pinecone
        count = await self.pinecone.upsert(records_list, embeddings)

        return count

    async def aretrieve(
        self,
        query: str,
        user_id: str | None = None,
        topk: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """
        Retrieve memory records using vector similarity search.

        Args:
            query: Search query text
            user_id: Filter by user_id
            topk: Number of results to return
            filters: Additional metadata filters

        Returns:
            List of MemoryRecord objects sorted by similarity
        """
        # Generate query embedding
        query_embedding = await self.embedder.aembed_query(query)

        # Search in Pinecone
        results = await self.pinecone.search(
            query_embedding=query_embedding,
            user_id=user_id,
            topk=topk,
            filters=filters,
        )

        # Convert Pinecone results back to MemoryRecord objects
        from ..models import MemoryRecord

        memory_records = []
        for result in results:
            metadata = result["metadata"]

            # Reconstruct MemoryRecord
            record = MemoryRecord(
                id=metadata.get("record_id"),
                user_id=metadata.get("user_id"),
                text=metadata.get("text", ""),
                type=metadata.get("type", "semantic"),
                source=metadata.get("source"),
                tags=metadata.get("tags", []),
                # Add similarity score as confidence
                confidence=result["score"],
            )

            memory_records.append(record)

        return memory_records

    async def aall(self, user_id: str | None = None) -> list[MemoryRecord]:
        """
        Get all memory records (or filtered by user_id).

        Warning: This can be expensive for large datasets. Use with caution.

        Args:
            user_id: Optional user_id filter

        Returns:
            List of all MemoryRecord objects
        """
        # For Pinecone, we need to use a dummy query and large topk
        # This is not ideal for production - consider pagination
        dummy_query = [0.0] * self.embedder.get_dimension()

        results = await self.pinecone.search(
            query_embedding=dummy_query,
            user_id=user_id,
            topk=10000,  # Large number to get all
            min_score=0.0,  # No score filtering
        )

        from ..models import MemoryRecord

        memory_records = []
        for result in results:
            metadata = result["metadata"]
            record = MemoryRecord(
                id=metadata.get("record_id"),
                user_id=metadata.get("user_id"),
                text=metadata.get("text", ""),
                type=metadata.get("type", "semantic"),
                source=metadata.get("source"),
                tags=metadata.get("tags", []),
            )
            memory_records.append(record)

        return memory_records

    async def acount(self) -> int:
        """
        Get total count of vectors in Pinecone.

        Returns:
            Total number of memory records
        """
        stats = await self.pinecone.get_stats()
        return stats.get("total_vectors", 0)

    async def adelete_by_user(self, user_id: str) -> None:
        """
        Delete all records for a specific user.

        Args:
            user_id: User ID to delete records for
        """
        await self.pinecone.delete_by_filter({"user_id": {"$eq": user_id}})

    async def health_check(self) -> bool:
        """
        Check if Pinecone connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        return await self.pinecone.health_check()


# Alias for backwards compatibility
PineconeSemanticStore = PineconeSemanticStoreAdapter
