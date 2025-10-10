"""Complete usage examples for the caching layer.

This example demonstrates:
1. Basic semantic caching
2. LLM response caching
3. Cached router usage
4. Metrics and monitoring
5. Integration with storage layer
"""

from __future__ import annotations

import asyncio

from core.caching import get_llm_cache, get_semantic_cache
from core.caching.metrics import get_cache_monitor
from core.llm.cached_router import create_cached_router
from core.llm.router import LLMProvider


async def example_1_semantic_cache():
    """Example 1: Basic semantic cache usage."""
    print("\n" + "=" * 60)
    print("Example 1: Semantic Cache")
    print("=" * 60)

    cache = get_semantic_cache(namespace="example1")

    # Set a cache entry
    query = "What is contract law?"
    response = {
        "content": "Contract law governs agreements between parties...",
        "model": "gpt-4",
        "tokens_used": 150,
    }

    await cache.set(query, response, ttl=3600)
    print(f"✓ Cached query: '{query}'")

    # Get exact match
    cached = await cache.get(query)
    print(f"✓ Retrieved (exact match): {cached is not None}")

    # Get semantic match (similar query)
    similar_query = "Explain contract law basics"
    cached_similar = await cache.get(similar_query, use_semantic=True)
    print(f"✓ Retrieved (semantic match): {cached_similar is not None}")

    # Stats
    stats = cache.get_stats()
    print("\nCache Stats:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
    print(f"  Semantic hits: {stats['semantic_hits']}")

    # Cleanup
    await cache.clear()


async def example_2_llm_cache():
    """Example 2: LLM cache with model-specific caching."""
    print("\n" + "=" * 60)
    print("Example 2: LLM Cache")
    print("=" * 60)

    cache = get_llm_cache(namespace="example2")

    # Cache responses for different models
    prompt = "What is artificial intelligence?"

    # GPT-4 response
    gpt4_response = {
        "content": "AI is the simulation of human intelligence by machines (GPT-4)",
        "usage": {"prompt_tokens": 6, "completion_tokens": 12},
    }
    await cache.set(prompt, gpt4_response, model="gpt-4", temperature=0.0)
    print("✓ Cached GPT-4 response")

    # Claude response
    claude_response = {
        "content": "AI is the simulation of human intelligence by machines (Claude)",
        "usage": {"prompt_tokens": 6, "completion_tokens": 12},
    }
    await cache.set(prompt, claude_response, model="claude-3", temperature=0.0)
    print("✓ Cached Claude response")

    # Retrieve model-specific
    gpt4_cached = await cache.get(prompt, model="gpt-4", temperature=0.0)
    claude_cached = await cache.get(prompt, model="claude-3", temperature=0.0)

    print("\nModel-Specific Retrieval:")
    print(f"  GPT-4: {gpt4_cached['content'][:50]}...")
    print(f"  Claude: {claude_cached['content'][:50]}...")

    # Cleanup
    await cache.clear()


async def example_3_cached_router():
    """Example 3: Cached LLM router with budget tracking."""
    print("\n" + "=" * 60)
    print("Example 3: Cached LLM Router")
    print("=" * 60)

    # Create providers
    providers = [
        LLMProvider("gpt-4", cost_per_token=0.03),
        LLMProvider("claude-3", cost_per_token=0.015),
    ]

    # Create cached router
    router = create_cached_router(providers=providers, initial_budget=10.0, use_cache=True)

    print(f"Initial budget: ${router.budget:.2f}")

    # Simulate queries
    queries = [
        "What is contract law?",
        "What is contract law?",  # Duplicate - should hit cache
        "Explain contract law",  # Similar - might hit cache
        "What is immigration law?",  # Different - cache miss
    ]

    for i, query in enumerate(queries, 1):
        result = await router.ainvoke(query, temperature=0.0)

        print(f"\nQuery {i}: '{query}'")
        print(f"  Provider: {result['provider']}")
        print(f"  Cached: {result['cached']}")
        print(f"  Cost: ${result['cost']:.4f}")
        print(f"  Budget remaining: ${router.budget:.2f}")

    # Cache statistics
    stats = router.get_cache_stats()
    print("\nCache Performance:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
    print(f"  Budget saved: ${stats['budget_saved']:.4f}")

    # Cleanup
    await router.clear_cache()


async def example_4_metrics_monitoring():
    """Example 4: Metrics and monitoring."""
    print("\n" + "=" * 60)
    print("Example 4: Metrics and Monitoring")
    print("=" * 60)

    monitor = get_cache_monitor()

    # Simulate cache operations
    monitor.record_hit(latency_ms=2.5, is_semantic=False)
    monitor.record_hit(latency_ms=8.3, is_semantic=True)
    monitor.record_miss(latency_ms=150.0)
    monitor.record_set(latency_ms=5.0, size_bytes=1024)

    # Get stats
    stats = monitor.get_stats()
    print("\nMetrics:")
    print(f"  Total operations: {stats['total_operations']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
    print(f"  Semantic hit rate: {stats['semantic_hit_rate']:.1%}")
    print(f"  Avg hit latency: {stats['avg_hit_latency_ms']:.1f}ms")
    print(f"  Avg miss latency: {stats['avg_miss_latency_ms']:.1f}ms")

    # Health check
    health = monitor.get_health()
    print("\nHealth Status:")
    print(f"  Healthy: {health['healthy']}")
    if health["issues"]:
        print(f"  Issues: {health['issues']}")
    if health["recommendations"]:
        print(f"  Recommendations: {health['recommendations']}")

    # Prometheus export (first 5 lines)
    prometheus = monitor.export_prometheus()
    print("\nPrometheus Metrics (sample):")
    for line in prometheus.split("\n")[:10]:
        print(f"  {line}")


async def example_5_full_integration():
    """Example 5: Full integration with storage layer."""
    print("\n" + "=" * 60)
    print("Example 5: Full Integration (Storage + Cache)")
    print("=" * 60)

    # This example requires Phase 1 storage to be configured
    try:
        from core.memory.memory_manager_v2 import create_production_memory_manager
        from core.memory.models import MemoryRecord

        # Create components
        memory = create_production_memory_manager(namespace="example")

        providers = [
            LLMProvider("gpt-4", cost_per_token=0.03),
        ]
        router = create_cached_router(providers, initial_budget=5.0)

        print("✓ Initialized memory and cache layers")

        # Process a query
        user_query = "What are the requirements for I-485?"
        user_id = "example_user"

        # 1. Check LLM cache first
        llm_result = await router.ainvoke(user_query, temperature=0.0)
        print("\nLLM Response:")
        print(f"  Cached: {llm_result['cached']}")
        print(f"  Cost: ${llm_result['cost']:.4f}")

        # 2. Store in long-term memory if new
        if not llm_result["cached"]:
            record = MemoryRecord(
                user_id=user_id,
                text=f"Q: {user_query}\nA: {llm_result['response']}",
                type="semantic",
                source="llm_interaction",
                tags=["immigration", "i-485"],
            )
            await memory.awrite([record])
            print("  Stored in long-term memory")

        # 3. Retrieve relevant memories
        memories = await memory.aretrieve(user_query, user_id=user_id, topk=3)
        print(f"\nRetrieved {len(memories)} relevant memories")

        # Cleanup
        await router.clear_cache()

        print("\n✓ Full integration example complete")

    except ImportError:
        print("\n⚠ Storage layer not configured - skipping integration example")
        print("  Configure Phase 1 storage to run this example")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Caching Layer Usage Examples")
    print("=" * 60)

    # Check Redis connection
    from core.caching import get_redis_client

    redis = get_redis_client()
    if not await redis.ping():
        print("\n❌ Error: Cannot connect to Redis")
        print("   Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
        return

    print("\n✓ Redis connection successful")

    # Run examples
    await example_1_semantic_cache()
    await example_2_llm_cache()
    await example_3_cached_router()
    await example_4_metrics_monitoring()
    await example_5_full_integration()

    print("\n" + "=" * 60)
    print("All examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
