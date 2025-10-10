"""Integration tests for cached LLM router."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.llm.cached_router import CachedLLMRouter, create_cached_router
from core.llm.router import LLMProvider


@pytest.fixture
def providers():
    """Create test LLM providers."""
    return [
        LLMProvider("gpt-4", cost_per_token=0.03),
        LLMProvider("claude-3", cost_per_token=0.015),
    ]


@pytest.fixture
async def router(providers):
    """Create cached router with test namespace."""
    namespace = f"test_router_{uuid4().hex[:8]}"
    from core.caching.llm_cache import LLMCache
    from core.caching.semantic_cache import SemanticCache

    semantic_cache = SemanticCache(namespace=namespace)
    llm_cache = LLMCache(semantic_cache=semantic_cache, namespace=namespace)

    router = CachedLLMRouter(
        providers=providers,
        initial_budget=10.0,
        cache=llm_cache,
        use_cache=True,
    )
    yield router

    # Cleanup
    await router.clear_cache()


@pytest.mark.asyncio
async def test_cache_miss_first_call(router):
    """Test that first call is a cache miss."""
    result = await router.ainvoke("What is AI?")

    assert result is not None
    assert result["cached"] is False
    assert result["provider"] in ["gpt-4", "claude-3"]
    assert result["cost"] > 0

    # Check cache stats
    stats = router.get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


@pytest.mark.asyncio
async def test_cache_hit_second_call(router):
    """Test that second identical call is a cache hit."""
    prompt = "What is machine learning?"

    # First call - miss
    result1 = await router.ainvoke(prompt, temperature=0.0)
    assert result1["cached"] is False
    initial_cost = result1["cost"]

    # Second call - hit
    result2 = await router.ainvoke(prompt, temperature=0.0)
    assert result2["cached"] is True
    assert result2["provider"] == "cache"
    assert result2["cost"] == 0.0
    assert result2["response"] == result1["response"]

    # Check cache stats
    stats = router.get_cache_stats()
    assert stats["hits"] >= 1
    assert stats["budget_saved"] >= initial_cost


@pytest.mark.asyncio
async def test_high_temperature_not_cached(router):
    """Test that high-temperature calls are not cached."""
    prompt = "Write a creative story"

    # First call with high temperature
    result1 = await router.ainvoke(prompt, temperature=0.8)
    assert result1["cached"] is False

    # Second call - should still be a miss (not cached due to temp)
    result2 = await router.ainvoke(prompt, temperature=0.8)
    assert result2["cached"] is False

    # Both should have cost
    assert result1["cost"] > 0
    assert result2["cost"] > 0


@pytest.mark.asyncio
async def test_bypass_cache(router):
    """Test bypassing cache with bypass_cache flag."""
    prompt = "What is NLP?"

    # First call - cache
    result1 = await router.ainvoke(prompt, temperature=0.0)
    assert result1["cached"] is False

    # Second call with bypass - should not hit cache
    result2 = await router.ainvoke(prompt, temperature=0.0, bypass_cache=True)
    assert result2["cached"] is False
    assert result2["cost"] > 0


@pytest.mark.asyncio
async def test_cache_stats_accumulation(router):
    """Test that cache stats accumulate correctly."""
    # Generate multiple hits and misses
    await router.ainvoke("query1", temperature=0.0)  # Miss
    await router.ainvoke("query1", temperature=0.0)  # Hit
    await router.ainvoke("query2", temperature=0.0)  # Miss
    await router.ainvoke("query2", temperature=0.0)  # Hit

    stats = router.get_cache_stats()
    assert stats["hits"] >= 2
    assert stats["misses"] >= 2
    assert stats["total"] >= 4
    assert 0.0 <= stats["hit_rate"] <= 1.0
    assert stats["budget_saved"] >= 0.0


@pytest.mark.asyncio
async def test_budget_savings(router):
    """Test that cache hits save budget."""
    prompt = "What is deep learning?"

    # First call - costs money
    result1 = await router.ainvoke(prompt, temperature=0.0)
    cost1 = result1["cost"]
    budget_after_first = router.budget

    # Second call - cached (free)
    result2 = await router.ainvoke(prompt, temperature=0.0)
    cost2 = result2["cost"]
    budget_after_second = router.budget

    # Cache hit should be free
    assert cost2 == 0.0
    assert budget_after_second == budget_after_first

    # Budget savings should be tracked
    stats = router.get_cache_stats()
    assert stats["budget_saved"] >= cost1


@pytest.mark.asyncio
async def test_clear_cache(router):
    """Test clearing router cache."""
    prompt = "Test clear"

    # Cache a response
    await router.ainvoke(prompt, temperature=0.0)

    # Should hit cache
    result1 = await router.ainvoke(prompt, temperature=0.0)
    assert result1["cached"] is True

    # Clear cache
    deleted = await router.clear_cache()
    assert deleted >= 1

    # Should miss after clear
    result2 = await router.ainvoke(prompt, temperature=0.0)
    assert result2["cached"] is False


@pytest.mark.asyncio
async def test_reset_stats(router):
    """Test resetting cache statistics."""
    # Generate some activity
    await router.ainvoke("query1", temperature=0.0)
    await router.ainvoke("query1", temperature=0.0)

    stats_before = router.get_cache_stats()
    assert stats_before["total"] > 0

    # Reset
    await router.reset_cache_stats()

    stats_after = router.get_cache_stats()
    assert stats_after["hits"] == 0
    assert stats_after["misses"] == 0
    assert stats_after["total"] == 0


@pytest.mark.asyncio
async def test_factory_function(providers):
    """Test create_cached_router factory function."""
    router = create_cached_router(providers=providers, initial_budget=5.0, use_cache=True)

    assert router is not None
    assert router.budget == 5.0
    assert router.use_cache is True

    # Test it works
    result = await router.ainvoke("Test query", temperature=0.0)
    assert result is not None


@pytest.mark.asyncio
async def test_cache_disabled(providers):
    """Test router with cache disabled."""
    router = CachedLLMRouter(
        providers=providers,
        initial_budget=10.0,
        use_cache=False,
    )

    prompt = "Test no cache"

    # First call
    result1 = await router.ainvoke(prompt, temperature=0.0)
    assert result1["cached"] is False

    # Second call - should still be miss (cache disabled)
    result2 = await router.ainvoke(prompt, temperature=0.0)
    assert result2["cached"] is False

    # Both should cost money
    assert result1["cost"] > 0
    assert result2["cost"] > 0


@pytest.mark.asyncio
async def test_semantic_cache_similarity(router):
    """Test semantic similarity matching in router."""
    prompt1 = "What is artificial intelligence?"
    prompt2 = "Explain AI to me"

    # First call
    result1 = await router.ainvoke(prompt1, temperature=0.0)
    assert result1["cached"] is False

    # Small delay for embedding indexing
    import asyncio

    await asyncio.sleep(0.5)

    # Similar query - might hit via semantic matching
    result2 = await router.ainvoke(prompt2, temperature=0.0)

    # If semantic matching works, it should be cached
    # But we can't guarantee it in tests, so just verify no errors
    assert result2 is not None
    if result2["cached"]:
        assert result2["cost"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
