"""Semantic cache with vector similarity matching.

This cache uses embeddings to find semantically similar queries,
reducing redundant LLM calls for similar questions.

Architecture:
- L1: Exact match cache (Redis string keys)
- L2: Semantic similarity cache (Redis + embeddings)
- Hit detection based on cosine similarity threshold
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..llm.voyage_embedder import VoyageEmbedder, create_voyage_embedder
from .config import get_cache_config
from .redis_client import RedisClient, get_redis_client


class _LocalEmbedder:
    """Deterministic local embedder for testing environments.

    Produces fixed-size vectors using SHA256-based hashing; no external services.
    """

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    async def aembed(self, texts: list[str], input_type: str | None = None) -> list[list[float]]:
        return [self._hash_to_vec(t) for t in texts]

    async def aembed_query(self, query: str) -> list[float]:
        return self._hash_to_vec(query)

    def _hash_to_vec(self, text: str) -> list[float]:
        # Build a deterministic vector by chaining hashes with index salt
        out: list[float] = []
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        block = seed
        i = 0
        while len(out) < self.dim:
            # Mix with index to create new block every 32 bytes
            h = hashlib.sha256(block + i.to_bytes(4, "little", signed=False)).digest()
            for b in h:
                # Map byte 0..255 to [0,1]
                out.append(b / 255.0)
                if len(out) >= self.dim:
                    break
            block = h
            i += 1
        return out


class SemanticCache:
    """
    Semantic cache for LLM responses.

    Features:
    - Exact match detection (fast path)
    - Semantic similarity matching (fallback)
    - Configurable similarity threshold
    - TTL-based expiration
    - Hit/miss metrics

    Example:
        >>> cache = SemanticCache()
        >>>
        >>> # Cache miss - compute and store
        >>> result = await cache.get("What is contract law?")
        >>> if result is None:
        >>>     result = await call_llm("What is contract law?")
        >>>     await cache.set("What is contract law?", result)
        >>>
        >>> # Cache hit - similar question
        >>> result = await cache.get("Explain contract law basics")
        >>> # Returns cached result due to semantic similarity
    """

    def __init__(
        self,
        redis_client: RedisClient | None = None,
        embedder: VoyageEmbedder | None = None,
        namespace: str = "semantic_cache",
    ):
        self.redis = redis_client or get_redis_client()
        # Prefer provided embedder; otherwise try Voyage, and gracefully fallback
        if embedder is not None:
            self.embedder = embedder
        else:
            try:
                self.embedder = create_voyage_embedder()
            except Exception:  # pragma: no cover - environment dependent
                # Fallback to lightweight local embedder (no external deps)
                self.embedder = _LocalEmbedder()
        self.config = get_cache_config()
        self.namespace = namespace

        # Cache metrics
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0

    def _exact_key(self, query: str) -> str:
        """Generate key for exact match cache."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return f"{self.namespace}:exact:{query_hash}"

    def _embedding_key(self, query: str) -> str:
        """Generate key for storing query embedding."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return f"{self.namespace}:embedding:{query_hash}"

    def _candidates_key(self) -> str:
        """Key for sorted set of candidate queries."""
        return f"{self.namespace}:candidates"

    async def get(
        self,
        query: str,
        *,
        use_semantic: bool = True,
    ) -> Any | None:
        """
        Get cached response for query.

        Args:
            query: Query string to look up
            use_semantic: Whether to use semantic similarity matching

        Returns:
            Cached response or None if not found

        Process:
            1. Check exact match cache (fast path)
            2. If enabled and miss, check semantic similarity
            3. Update metrics
        """
        if not self.config.cache_enabled:
            return None

        # L1: Exact match
        exact_key = self._exact_key(query)
        result = await self.redis.get(exact_key)

        if result is not None:
            self._hits += 1
            return result

        # L2: Semantic similarity
        if use_semantic and self.config.semantic_cache_enabled:
            semantic_result = await self._semantic_lookup(query)
            if semantic_result is not None:
                self._hits += 1
                self._semantic_hits += 1
                return semantic_result

        self._misses += 1
        return None

    async def set(
        self,
        query: str,
        response: Any,
        *,
        ttl: int | None = None,
    ) -> None:
        """
        Cache a query-response pair.

        Args:
            query: Query string
            response: Response to cache
            ttl: Time to live in seconds (None = use default)

        Process:
            1. Store exact match
            2. Generate and store embedding
            3. Add to candidates list
        """
        if not self.config.cache_enabled:
            return

        if ttl is None:
            ttl = self.config.llm_cache_ttl

        # Store exact match
        exact_key = self._exact_key(query)
        await self.redis.set(exact_key, response, ttl=ttl)

        # Store for semantic matching if enabled
        if self.config.semantic_cache_enabled:
            await self._store_semantic(query, ttl)

    async def _store_semantic(self, query: str, ttl: int) -> None:
        """Store query embedding and metadata for semantic matching."""
        # Generate embedding
        embedding = await self.embedder.aembed_query(query)

        # Store embedding
        embedding_key = self._embedding_key(query)
        await self.redis.set(
            embedding_key,
            {"query": query, "embedding": embedding},
            ttl=ttl,
        )

        # Add to candidates sorted set (score = timestamp)
        import time

        candidates_key = self._candidates_key()
        await self.redis.zadd(candidates_key, {embedding_key: time.time()})

        # Trim candidates list to max size
        max_candidates = self.config.semantic_cache_max_candidates * 10
        await self.redis.zremrangebyrank(candidates_key, 0, -(max_candidates + 1))

    async def _semantic_lookup(self, query: str) -> Any | None:
        """
        Find semantically similar cached query.

        Args:
            query: Query to match

        Returns:
            Cached response if similar query found, else None

        Process:
            1. Generate query embedding
            2. Get recent candidates
            3. Compute similarity scores
            4. Return cached response if above threshold
        """
        # Generate query embedding
        query_embedding = await self.embedder.aembed_query(query)

        # Get recent candidates
        candidates_key = self._candidates_key()
        max_candidates = self.config.semantic_cache_max_candidates

        candidate_keys = await self.redis.zrevrange(candidates_key, 0, max_candidates - 1)

        if not candidate_keys:
            return None

        # Check each candidate
        best_match = None
        best_score = 0.0

        for candidate_key in candidate_keys:
            # Get candidate embedding and query
            candidate_data = await self.redis.get(candidate_key)
            if candidate_data is None:
                continue

            candidate_query = candidate_data["query"]
            candidate_embedding = candidate_data["embedding"]

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, candidate_embedding)

            # Check if above threshold and better than current best
            if similarity > best_score:
                best_score = similarity
                best_match = candidate_query

        # If best match exceeds threshold, return cached response
        threshold = self.config.semantic_cache_threshold
        if best_match and best_score >= threshold:
            exact_key = self._exact_key(best_match)
            cached_response = await self.redis.get(exact_key)
            return cached_response

        return None

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))

        # Magnitudes
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    async def delete(self, query: str) -> bool:
        """
        Delete cached entry for query.

        Args:
            query: Query to delete

        Returns:
            True if entry was deleted
        """
        exact_key = self._exact_key(query)
        deleted = await self.redis.delete(exact_key)

        # Also remove from semantic cache
        if self.config.semantic_cache_enabled:
            embedding_key = self._embedding_key(query)
            await self.redis.delete(embedding_key)

            candidates_key = self._candidates_key()
            await self.redis.zrem(candidates_key, embedding_key)

        return deleted

    async def clear(self) -> int:
        """
        Clear all cached entries in this namespace.

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.namespace}:*"
        return await self.redis.flush(pattern)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss rates and counts
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "semantic_hits": self._semantic_hits,
            "total": total,
            "hit_rate": hit_rate,
            "semantic_hit_rate": (self._semantic_hits / self._hits if self._hits > 0 else 0.0),
        }

    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0


# Note: RedisClient already has zadd, zrevrange, zremrangebyrank, zrem methods
# imported from redis_client.py


# Global singletons keyed by event loop and namespace
_semantic_caches: dict[tuple[int, str], SemanticCache] = {}


def get_semantic_cache(namespace: str = "semantic_cache") -> SemanticCache:
    """
    Get global semantic cache instance.

    Args:
        namespace: Cache namespace for isolation

    Returns:
        Shared SemanticCache instance
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop_key = id(loop)
    except RuntimeError:
        loop_key = -1

    global _semantic_caches
    key = (loop_key, namespace)
    cache = _semantic_caches.get(key)
    if cache is None:
        cache = SemanticCache(namespace=namespace)
        _semantic_caches[key] = cache
    return cache


async def close_semantic_cache() -> None:
    """Close global semantic cache."""
    global _semantic_caches
    _semantic_caches.clear()
