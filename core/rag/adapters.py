"""RAG Adapters - Bridge between RAG pipeline and existing memory stores.

Provides adapters to integrate existing memory stores with the RAG pipeline
hybrid retrieval system.

Phase 3: Hybrid RAG Pipeline Integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..memory.memory_manager import MemoryManager
    from ..memory.stores.semantic_store import SemanticStore

logger = structlog.get_logger(__name__)


class SemanticStoreAdapter:
    """Adapter to use SemanticStore as a dense retriever in HybridRetriever.

    Wraps the existing SemanticStore to provide the `asearch()` interface
    expected by HybridRetriever for dense (vector) retrieval.

    Attributes:
        store: Underlying semantic store
        default_user_id: Default user ID for filtering
        default_filters: Default filters to apply

    Example:
        >>> from core.memory.stores import SemanticStore
        >>> from core.rag import HybridRetriever, BM25Retriever
        >>>
        >>> semantic = SemanticStore()
        >>> adapter = SemanticStoreAdapter(semantic)
        >>>
        >>> # Use in hybrid retriever
        >>> hybrid = HybridRetriever(
        ...     sparse_retriever=bm25,
        ...     dense_retriever=adapter
        ... )
    """

    def __init__(
        self,
        store: SemanticStore,
        default_user_id: str | None = None,
        default_filters: dict[str, Any] | None = None,
    ) -> None:
        """Initialize adapter.

        Args:
            store: SemanticStore instance to wrap
            default_user_id: Default user ID for filtering queries
            default_filters: Default filters to apply to all queries
        """
        self.store = store
        self.default_user_id = default_user_id
        self.default_filters = default_filters or {}
        self.logger = logger.bind(component="semantic_store_adapter")

    async def asearch(
        self,
        query: str,
        top_k: int = 10,
        user_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Search semantic store and return results in HybridRetriever format.

        Args:
            query: Search query string
            top_k: Number of results to return
            user_id: User ID for filtering (overrides default)
            filters: Additional filters (merged with defaults)

        Returns:
            List of (text, score) tuples sorted by score descending

        Example:
            >>> results = await adapter.asearch("EB-1A requirements", top_k=5)
            >>> for text, score in results:
            ...     print(f"{score:.2f}: {text[:50]}...")
        """
        # Merge filters with defaults
        merged_filters = {**self.default_filters, **(filters or {})}
        effective_user_id = user_id or self.default_user_id

        self.logger.debug(
            "semantic_search",
            query=query[:100],
            top_k=top_k,
            user_id=effective_user_id,
        )

        # Query semantic store
        records = await self.store.aretrieve(
            query=query,
            user_id=effective_user_id,
            topk=top_k,
            filters=merged_filters,
        )

        # Convert to (text, score) format
        # SemanticStore uses keyword overlap for scoring
        # We normalize scores to 0-1 range
        results: list[tuple[str, float]] = []
        query_tokens = set(query.lower().split())

        for record in records:
            text = record.text
            text_tokens = set(text.lower().split())
            overlap = len(query_tokens & text_tokens)

            # Normalize score based on query length
            score = overlap / max(len(query_tokens), 1)
            results.append((text, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        self.logger.debug("semantic_search_complete", results_count=len(results))

        return results


class MemoryManagerAdapter:
    """Adapter to use MemoryManager as a dense retriever.

    Similar to SemanticStoreAdapter but works with the full MemoryManager
    facade, enabling retrieval from multiple memory stores.

    Example:
        >>> from core.memory.memory_manager import MemoryManager
        >>> from core.rag import HybridRetriever
        >>>
        >>> memory = MemoryManager()
        >>> adapter = MemoryManagerAdapter(memory)
        >>>
        >>> hybrid = HybridRetriever(
        ...     sparse_retriever=bm25,
        ...     dense_retriever=adapter
        ... )
    """

    def __init__(
        self,
        manager: MemoryManager,
        default_user_id: str | None = None,
        default_filters: dict[str, Any] | None = None,
    ) -> None:
        """Initialize adapter.

        Args:
            manager: MemoryManager instance to wrap
            default_user_id: Default user ID for filtering
            default_filters: Default filters for queries
        """
        self.manager = manager
        self.default_user_id = default_user_id
        self.default_filters = default_filters or {}
        self.logger = logger.bind(component="memory_manager_adapter")

    async def asearch(
        self,
        query: str,
        top_k: int = 10,
        user_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Search memory manager and return results in HybridRetriever format.

        Args:
            query: Search query string
            top_k: Number of results to return
            user_id: User ID for filtering
            filters: Additional filters

        Returns:
            List of (text, score) tuples
        """
        merged_filters = {**self.default_filters, **(filters or {})}
        effective_user_id = user_id or self.default_user_id

        self.logger.debug(
            "memory_search",
            query=query[:100],
            top_k=top_k,
        )

        # Query memory manager
        records = await self.manager.aretrieve(
            query=query,
            user_id=effective_user_id,
            topk=top_k,
            filters=merged_filters,
        )

        # Convert to (text, score) format with normalized scores
        results: list[tuple[str, float]] = []
        query_tokens = set(query.lower().split())

        for record in records:
            text = record.text
            text_tokens = set(text.lower().split())
            overlap = len(query_tokens & text_tokens)
            score = overlap / max(len(query_tokens), 1)
            results.append((text, score))

        results.sort(key=lambda x: x[1], reverse=True)

        self.logger.debug("memory_search_complete", results_count=len(results))

        return results


def create_memory_adapter(
    source: SemanticStore | MemoryManager,
    user_id: str | None = None,
    filters: dict[str, Any] | None = None,
) -> SemanticStoreAdapter | MemoryManagerAdapter:
    """Factory function to create appropriate adapter for memory source.

    Args:
        source: SemanticStore or MemoryManager instance
        user_id: Default user ID for filtering
        filters: Default filters

    Returns:
        Appropriate adapter instance

    Example:
        >>> adapter = create_memory_adapter(semantic_store)
        >>> # or
        >>> adapter = create_memory_adapter(memory_manager)
    """
    # Import here to avoid circular imports
    from ..memory.memory_manager import MemoryManager
    from ..memory.stores.semantic_store import SemanticStore

    if isinstance(source, MemoryManager):
        return MemoryManagerAdapter(
            manager=source,
            default_user_id=user_id,
            default_filters=filters,
        )
    if isinstance(source, SemanticStore):
        return SemanticStoreAdapter(
            store=source,
            default_user_id=user_id,
            default_filters=filters,
        )
    raise TypeError(f"Expected SemanticStore or MemoryManager, got {type(source).__name__}")


__all__ = [
    "MemoryManagerAdapter",
    "SemanticStoreAdapter",
    "create_memory_adapter",
]
