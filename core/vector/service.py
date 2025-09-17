"""Vector service abstraction with Pinecone implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .pinecone_client import PineconeClient, PineconeClientError
from config.settings import Settings

logger = logging.getLogger(__name__)


class VectorMetadata(BaseModel):
    """Metadata for vector storage."""
    document_id: str
    chunk_id: str
    lang: Optional[str] = "en"
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    text: Optional[str] = None  # Original text for reference


class VectorRecord(BaseModel):
    """Vector record with embedding and metadata."""
    id: str
    vector: List[float]
    metadata: VectorMetadata


class QueryResult(BaseModel):
    """Query result with score and metadata."""
    id: str
    score: float
    metadata: VectorMetadata


class VectorService(ABC):
    """Abstract vector service interface."""

    @abstractmethod
    async def initialize(self, dimension: int) -> bool:
        """Initialize vector store with given dimension."""
        pass

    @abstractmethod
    async def upsert_batch(self, records: List[VectorRecord]) -> bool:
        """Upsert a batch of vector records."""
        pass

    @abstractmethod
    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """Query similar vectors."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if vector service is healthy."""
        pass


class PineconeVectorService(VectorService):
    """Pinecone implementation of vector service."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.client = PineconeClient(self.settings)
        self._initialized = False

    async def initialize(self, dimension: int) -> bool:
        """Initialize Pinecone index with given dimension."""
        try:
            success = await self.client.ensure_index_exists(dimension)
            if success:
                self._initialized = True
                logger.info(f"Pinecone vector service initialized with dimension {dimension}")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone vector service: {e}")
            return False

    def _prepare_vectors_for_upsert(self, records: List[VectorRecord]) -> List[Dict[str, Any]]:
        """Convert VectorRecord objects to Pinecone format."""
        vectors = []
        for record in records:
            # Convert metadata to dict, ensuring all values are JSON serializable
            metadata_dict = {
                "document_id": record.metadata.document_id,
                "chunk_id": record.metadata.chunk_id,
                "lang": record.metadata.lang or "en",
                "source": record.metadata.source or "",
                "tags": ",".join(record.metadata.tags) if record.metadata.tags else "",
                "text": record.metadata.text or ""
            }

            vectors.append({
                "id": record.id,
                "values": record.vector,
                "metadata": metadata_dict
            })
        return vectors

    async def upsert_batch(self, records: List[VectorRecord]) -> bool:
        """Upsert a batch of vector records to Pinecone."""
        if not self._initialized:
            logger.error("Vector service not initialized")
            return False

        if not records:
            return True

        try:
            # Split into smaller batches for rate limiting
            batch_size = 100  # Pinecone recommended batch size

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                vectors = self._prepare_vectors_for_upsert(batch)

                success = await self.client.upsert(vectors)
                if not success:
                    logger.error(f"Failed to upsert batch {i//batch_size + 1}")
                    return False

                logger.debug(f"Upserted batch {i//batch_size + 1}/{(len(records)-1)//batch_size + 1} ({len(batch)} vectors)")

            logger.info(f"Successfully upserted {len(records)} vectors to Pinecone")
            return True

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False

    def _parse_query_results(self, pinecone_result: Dict[str, Any]) -> List[QueryResult]:
        """Parse Pinecone query results to QueryResult objects."""
        results = []

        if not pinecone_result or "matches" not in pinecone_result:
            return results

        for match in pinecone_result["matches"]:
            try:
                metadata_dict = match.get("metadata", {})

                # Parse tags back from comma-separated string
                tags_str = metadata_dict.get("tags", "")
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []

                metadata = VectorMetadata(
                    document_id=metadata_dict.get("document_id", ""),
                    chunk_id=metadata_dict.get("chunk_id", ""),
                    lang=metadata_dict.get("lang", "en"),
                    source=metadata_dict.get("source"),
                    tags=tags,
                    text=metadata_dict.get("text")
                )

                result = QueryResult(
                    id=match["id"],
                    score=match["score"],
                    metadata=metadata
                )
                results.append(result)

            except Exception as e:
                logger.warning(f"Failed to parse query result: {e}")
                continue

        return results

    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """Query similar vectors from Pinecone."""
        if not self._initialized:
            logger.error("Vector service not initialized")
            return []

        try:
            pinecone_result = await self.client.query(
                vector=vector,
                top_k=top_k,
                filter_dict=filters,
                include_metadata=True
            )

            results = self._parse_query_results(pinecone_result)
            logger.debug(f"Retrieved {len(results)} similar vectors from Pinecone")
            return results

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if Pinecone service is healthy."""
        try:
            indexes = await self.client.list_indexes()
            return len(indexes) >= 0  # Successfully got index list
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return False


# Global vector service instance
_vector_service: Optional[VectorService] = None


async def get_vector_service() -> VectorService:
    """Get global vector service instance."""
    global _vector_service
    if _vector_service is None:
        settings = Settings()
        _vector_service = PineconeVectorService(settings)
    return _vector_service


async def initialize_vector_service(dimension: int) -> bool:
    """Initialize global vector service."""
    service = await get_vector_service()
    return await service.initialize(dimension)