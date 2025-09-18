"""Pinecone client wrapper with retry logic and error handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None
    ServerlessSpec = None

from config.settings import Settings

logger = logging.getLogger(__name__)


class PineconeClientError(Exception):
    """Base exception for Pinecone client errors."""
    pass


class PineconeClient:
    """Async wrapper for Pinecone with retry logic and error handling."""

    def __init__(self, settings: Optional[Settings] = None):
        if not PINECONE_AVAILABLE:
            raise ImportError("pinecone-client package is required but not installed")

        self.settings = settings or Settings()
        self._client: Optional[Pinecone] = None
        self._index = None

        if not self.settings.pinecone_api_key:
            logger.warning("PINECONE_API_KEY not set, Pinecone client will not be functional")

    async def _get_client(self) -> Pinecone:
        """Get or create Pinecone client."""
        if self._client is None:
            if not self.settings.pinecone_api_key:
                raise PineconeClientError("Pinecone API key not configured")

            self._client = Pinecone(api_key=self.settings.pinecone_api_key)
        return self._client

    async def _get_index(self):
        """Get or create index reference."""
        if self._index is None:
            client = await self._get_client()
            self._index = client.Index(self.settings.pinecone_index)
        return self._index

    async def _retry_with_backoff(self, func, *args, max_retries: int = 3, **kwargs):
        """Execute function with exponential backoff on rate limits and server errors."""
        for attempt in range(max_retries):
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, lambda: func(*args, **kwargs)
                )
            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limiting (429) or server errors (5xx)
                if "429" in error_msg or "rate limit" in error_msg or any(code in error_msg for code in ["500", "502", "503", "504"]):
                    if attempt < max_retries - 1:
                        backoff_time = (2 ** attempt) + (attempt * 0.1)  # Exponential backoff with jitter
                        logger.warning(f"Pinecone rate limit/server error (attempt {attempt + 1}/{max_retries}), retrying in {backoff_time:.1f}s: {e}")
                        await asyncio.sleep(backoff_time)
                        continue

                # Re-raise non-retryable errors or after max retries
                raise PineconeClientError(f"Pinecone operation failed after {attempt + 1} attempts: {e}")

        raise PineconeClientError(f"Pinecone operation failed after {max_retries} attempts")

    async def ensure_index_exists(self, dimension: int) -> bool:
        """Ensure index exists with correct dimension. Create if absent."""
        try:
            client = await self._get_client()

            # List existing indexes
            indexes = await self._retry_with_backoff(client.list_indexes)
            index_names = [idx.name for idx in indexes.indexes] if hasattr(indexes, 'indexes') else []

            if self.settings.pinecone_index in index_names:
                logger.info(f"Pinecone index '{self.settings.pinecone_index}' already exists")
                return True

            # Create index with serverless spec
            logger.info(f"Creating Pinecone index '{self.settings.pinecone_index}' with dimension {dimension}")
            spec = ServerlessSpec(cloud="aws", region=self.settings.pinecone_env or "us-east-1")

            await self._retry_with_backoff(
                client.create_index,
                name=self.settings.pinecone_index,
                dimension=dimension,
                metric="cosine",
                spec=spec
            )

            # Wait for index to be ready
            await asyncio.sleep(2)
            logger.info(f"Pinecone index '{self.settings.pinecone_index}' created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure Pinecone index exists: {e}")
            return False

    async def list_indexes(self) -> List[str]:
        """List available indexes for health check."""
        try:
            client = await self._get_client()
            indexes = await self._retry_with_backoff(client.list_indexes)
            return [idx.name for idx in indexes.indexes] if hasattr(indexes, 'indexes') else []
        except Exception as e:
            logger.error(f"Failed to list Pinecone indexes: {e}")
            raise PineconeClientError(f"Failed to list indexes: {e}")

    async def upsert(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None) -> bool:
        """Upsert vectors with metadata."""
        try:
            index = await self._get_index()
            ns = namespace or self.settings.vector_namespace

            await self._retry_with_backoff(
                index.upsert,
                vectors=vectors,
                namespace=ns
            )
            return True

        except Exception as e:
            logger.error(f"Failed to upsert vectors to Pinecone: {e}")
            raise PineconeClientError(f"Upsert failed: {e}")

    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Query vectors with optional filtering."""
        try:
            index = await self._get_index()
            ns = namespace or self.settings.vector_namespace

            result = await self._retry_with_backoff(
                index.query,
                vector=vector,
                top_k=top_k,
                filter=filter_dict,
                namespace=ns,
                include_metadata=include_metadata
            )
            return result

        except Exception as e:
            logger.error(f"Failed to query Pinecone: {e}")
            raise PineconeClientError(f"Query failed: {e}")