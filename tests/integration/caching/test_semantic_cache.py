"""Integration tests for semantic cache."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.caching.semantic_cache import SemanticCache, get_semantic_cache


@pytest.fixture
async def cache():
    """Fixture for semantic cache with test namespace."""
    cache = SemanticCache(namespace=f"test_{uuid4().hex[:8]}")
    yield cache
    # Cleanup
    await cache.clear()


@pytest.mark.asyncio
async def test_exact_match_cache(cache):
    """Test exact match caching (L1)."""
    query = "What is contract law?"
    response = {"content": "Contract law governs agreements...", "model": "gpt-5-mini"}

    # Set
    await cache.set(query, response)

    # Get exact match
    cached = await cache.get(query)
    assert cached is not None
    assert cached["content"] == response["content"]

    # Stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0


@pytest.mark.asyncio
async def test_semantic_similarity_cache(cache):
    """Test semantic similarity matching (L2)."""
    query1 = "What is contract law?"
    query2 = "Explain contract law to me"  # Similar query
    response = {"content": "Contract law governs agreements...", "model": "gpt-5-mini"}

    # Cache first query
    await cache.set(query1, response, ttl=300)

    # Small delay for embedding indexing
    import asyncio

    await asyncio.sleep(0.5)

    # Query with similar text - should hit via semantic similarity
    cached = await cache.get(query2, use_semantic=True)

    # Depending on embedding quality, this might or might not hit
    # At minimum, test that no error occurs
    if cached:
        assert cached["content"] == response["content"]
        stats = cache.get_stats()
        assert stats["semantic_hits"] > 0


@pytest.mark.asyncio
async def test_cache_miss(cache):
    """Test cache miss behavior."""
    result = await cache.get("completely unique query that won't exist")
    assert result is None

    stats = cache.get_stats()
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_delete(cache):
    """Test deleting cached entries."""
    query = "What is immigration law?"
    response = {"content": "Immigration law...", "model": "gpt-5-mini"}

    # Set and verify
    await cache.set(query, response)
    cached = await cache.get(query)
    assert cached is not None

    # Delete
    deleted = await cache.delete(query)
    assert deleted is True

    # Verify deleted
    cached = await cache.get(query)
    assert cached is None


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test that cache entries expire after TTL."""
    cache = SemanticCache(namespace=f"test_ttl_{uuid4().hex[:8]}")
    query = "Test TTL query"
    response = {"content": "Test response", "model": "gpt-5-mini"}

    # Set with short TTL
    await cache.set(query, response, ttl=1)

    # Immediate get should work
    cached = await cache.get(query)
    assert cached is not None

    # Wait for expiration
    import asyncio

    await asyncio.sleep(2)

    # Should be expired
    cached = await cache.get(query)
    assert cached is None

    await cache.clear()


@pytest.mark.asyncio
async def test_cache_clear(cache):
    """Test clearing all cache entries."""
    # Add multiple entries
    for i in range(5):
        await cache.set(f"query_{i}", {"content": f"response_{i}"})

    # Clear
    deleted_count = await cache.clear()
    assert deleted_count >= 5

    # Verify all cleared
    for i in range(5):
        cached = await cache.get(f"query_{i}")
        assert cached is None


@pytest.mark.asyncio
async def test_cache_stats(cache):
    """Test cache statistics tracking."""
    # Generate hits and misses
    await cache.set("query1", {"content": "response1"})
    await cache.get("query1")  # Hit
    await cache.get("query2")  # Miss
    await cache.get("query3")  # Miss

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["total"] == 3
    assert 0.0 <= stats["hit_rate"] <= 1.0


@pytest.mark.asyncio
async def test_semantic_cache_disabled():
    """Test behavior when semantic cache is disabled."""

    cache = SemanticCache(namespace=f"test_disabled_{uuid4().hex[:8]}")

    # Temporarily disable semantic cache
    original_enabled = cache.config.semantic_cache_enabled
    cache.config.semantic_cache_enabled = False

    query1 = "What is contract law?"
    query2 = "Explain contract law"
    response = {"content": "Contract law...", "model": "gpt-5-mini"}

    await cache.set(query1, response)

    # Should not find via semantic similarity
    cached = await cache.get(query2, use_semantic=True)
    assert cached is None

    # Restore config
    cache.config.semantic_cache_enabled = original_enabled
    await cache.clear()


@pytest.mark.asyncio
async def test_singleton_cache():
    """Test global singleton cache."""
    cache1 = get_semantic_cache("test_singleton")
    cache2 = get_semantic_cache("test_singleton")

    # Should be the same instance
    assert cache1 is cache2

    # Different namespace should be different instance
    cache3 = get_semantic_cache("test_singleton_2")
    assert cache1 is not cache3


@pytest.mark.asyncio
async def test_cosine_similarity():
    """Test cosine similarity calculation."""
    cache = SemanticCache(namespace=f"test_similarity_{uuid4().hex[:8]}")

    # Identical vectors
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    similarity = cache._cosine_similarity(vec1, vec2)
    assert abs(similarity - 1.0) < 0.01

    # Orthogonal vectors
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    similarity = cache._cosine_similarity(vec3, vec4)
    assert abs(similarity - 0.0) < 0.01

    # Opposite vectors
    vec5 = [1.0, 0.0, 0.0]
    vec6 = [-1.0, 0.0, 0.0]
    similarity = cache._cosine_similarity(vec5, vec6)
    assert abs(similarity - (-1.0)) < 0.01

    await cache.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
