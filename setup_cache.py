"""Quick setup and health check for caching layer.

Run this script to verify that the caching layer is properly configured
and all dependencies are working.
"""

from __future__ import annotations

import asyncio
import sys


async def check_redis():
    """Check Redis connection."""
    print("🔍 Checking Redis connection...")

    try:
        from core.caching import get_redis_client

        client = get_redis_client()
        is_healthy = await client.ping()

        if is_healthy:
            print("✅ Redis: Connected")

            # Get Redis info
            info = await client.info("server")
            redis_version = info.get("redis_version", "unknown")
            print(f"   Version: {redis_version}")

            return True
        print("❌ Redis: Ping failed")
        return False

    except ImportError as e:
        print(f"❌ Redis: Missing dependency - {e}")
        print("   Install with: pip install redis[hiredis]")
        return False
    except Exception as e:
        print(f"❌ Redis: Connection error - {e}")
        print("   Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
        return False


async def check_voyage():
    """Check Voyage AI embeddings."""
    print("\n🔍 Checking Voyage AI embeddings...")

    try:
        from core.llm.voyage_embedder import create_voyage_embedder

        embedder = create_voyage_embedder()

        # Test embedding
        test_texts = ["Hello world"]
        embeddings = await embedder.aembed(test_texts)

        if embeddings and len(embeddings[0]) == 2048:
            print("✅ Voyage AI: Working")
            print(f"   Model: {embedder.model}")
            print(f"   Dimension: {embedder.dimension}")
            return True
        print("❌ Voyage AI: Unexpected embedding dimension")
        return False

    except ImportError as e:
        print(f"❌ Voyage AI: Missing dependency - {e}")
        print("   Install with: pip install voyageai")
        return False
    except Exception as e:
        print(f"❌ Voyage AI: API error - {e}")
        print("   Check VOYAGE_API_KEY in .env")
        return False


async def check_semantic_cache():
    """Check semantic cache."""
    print("\n🔍 Checking semantic cache...")

    try:
        from core.caching import get_semantic_cache

        cache = get_semantic_cache(namespace="health_check")

        # Test set/get
        test_key = "test_query"
        test_value = {"content": "test response", "model": "test"}

        await cache.set(test_key, test_value, ttl=60)
        retrieved = await cache.get(test_key)

        # Cleanup
        await cache.delete(test_key)

        if retrieved is not None:
            print("✅ Semantic Cache: Working")
            print(f"   Namespace: {cache.namespace}")
            print(f"   Threshold: {cache.config.semantic_cache_threshold}")
            return True
        print("❌ Semantic Cache: Failed to retrieve test data")
        return False

    except Exception as e:
        print(f"❌ Semantic Cache: Error - {e}")
        return False


async def check_llm_cache():
    """Check LLM cache."""
    print("\n🔍 Checking LLM cache...")

    try:
        from core.caching import get_llm_cache

        cache = get_llm_cache(namespace="health_check")

        # Test set/get
        test_prompt = "test prompt"
        test_response = {"content": "test response"}

        await cache.set(test_prompt, test_response, model="test", temperature=0.0)
        retrieved = await cache.get(test_prompt, model="test", temperature=0.0)

        # Cleanup
        await cache.delete(test_prompt, model="test", temperature=0.0)

        if retrieved is not None:
            print("✅ LLM Cache: Working")
            stats = cache.get_stats()
            print(f"   Hits: {stats['hits']}")
            return True
        print("❌ LLM Cache: Failed to retrieve test data")
        return False

    except Exception as e:
        print(f"❌ LLM Cache: Error - {e}")
        return False


async def check_metrics():
    """Check metrics and monitoring."""
    print("\n🔍 Checking metrics system...")

    try:
        from core.caching.metrics import get_cache_monitor

        monitor = get_cache_monitor()

        # Record test metrics
        monitor.record_hit(latency_ms=5.0)
        monitor.record_miss(latency_ms=100.0)

        # Get stats
        stats = monitor.get_stats()

        if stats["total_operations"] >= 2:
            print("✅ Metrics: Working")
            print(f"   Hit rate: {stats['hit_rate']:.1%}")
            print(f"   Avg hit latency: {stats['avg_hit_latency_ms']:.1f}ms")

            # Reset for cleanup
            monitor.reset()
            return True
        print("❌ Metrics: Failed to record operations")
        return False

    except Exception as e:
        print(f"❌ Metrics: Error - {e}")
        return False


async def check_cached_router():
    """Check cached LLM router."""
    print("\n🔍 Checking cached router...")

    try:
        from core.llm.cached_router import create_cached_router
        from core.llm.router import LLMProvider

        # Create test router
        providers = [LLMProvider("test-model", cost_per_token=0.01)]
        router = create_cached_router(providers=providers, initial_budget=1.0, use_cache=True)

        # Test call
        result = await router.ainvoke("test query", temperature=0.0)

        if result and "response" in result:
            print("✅ Cached Router: Working")
            print(f"   Provider: {result['provider']}")
            print(f"   Cached: {result['cached']}")

            # Cleanup
            await router.clear_cache()
            return True
        print("❌ Cached Router: Unexpected response format")
        return False

    except Exception as e:
        print(f"❌ Cached Router: Error - {e}")
        return False


async def run_health_check():
    """Run complete health check."""
    print("=" * 60)
    print("Caching Layer Health Check")
    print("=" * 60)

    results = []

    # Run all checks
    results.append(await check_redis())
    results.append(await check_voyage())
    results.append(await check_semantic_cache())
    results.append(await check_llm_cache())
    results.append(await check_metrics())
    results.append(await check_cached_router())

    # Summary
    print("\n" + "=" * 60)
    print("Health Check Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✅ All checks passed! Caching layer is ready.")
        return 0
    print(f"\n⚠️  {total - passed} check(s) failed. See errors above.")
    print("\nCommon fixes:")
    print("1. Install dependencies: pip install -r requirements_caching.txt")
    print("2. Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
    print("3. Configure .env with VOYAGE_API_KEY and CACHE_REDIS_URL")
    return 1


async def setup_env_file():
    """Create .env file template if it doesn't exist."""

    from pathlib import Path

    env_file = Path(".env")

    if env_file.exists():
        print(f"\n✓ {env_file} already exists")
        return

    print(f"\n📝 Creating {env_file} template...")

    template = """# Phase 2: Caching Layer Configuration

# Redis Configuration
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_REDIS_PASSWORD=
CACHE_REDIS_SSL=false
CACHE_REDIS_MAX_CONNECTIONS=50

# Cache Settings
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600

# Semantic Cache
CACHE_SEMANTIC_CACHE_ENABLED=true
CACHE_SEMANTIC_CACHE_THRESHOLD=0.95
CACHE_SEMANTIC_CACHE_MAX_CANDIDATES=5

# LLM Cache
CACHE_LLM_CACHE_ENABLED=true
CACHE_LLM_CACHE_TTL=86400

# Metrics
CACHE_METRICS_ENABLED=true
CACHE_METRICS_WINDOW=300

# Voyage AI (from Phase 1 - required for semantic cache)
VOYAGE_API_KEY=your_voyage_api_key_here
VOYAGE_MODEL=voyage-3-large
"""

    with open(env_file, "w") as f:
        f.write(template)

    print(f"✅ Created {env_file}")
    print("   Update VOYAGE_API_KEY and other settings as needed")


def print_next_steps():
    """Print next steps for setup."""
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print("\n1. Review and update .env configuration")
    print("2. Start Redis if not running:")
    print("   docker run -d -p 6379:6379 redis:7-alpine")
    print("\n3. Run examples:")
    print("   python examples/caching_usage_example.py")
    print("\n4. Run tests:")
    print("   pytest tests/integration/caching/ -v")
    print("\n5. See documentation:")
    print("   cat CACHING_LAYER_README.md")


async def main():
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup and check caching layer")
    parser.add_argument("--setup-env", action="store_true", help="Create .env template file")
    parser.add_argument("--health-check", action="store_true", help="Run health check")

    args = parser.parse_args()

    # Default to health check if no args
    if not args.setup_env and not args.health_check:
        args.health_check = True

    if args.setup_env:
        await setup_env_file()

    if args.health_check:
        exit_code = await run_health_check()

        if exit_code == 0:
            print_next_steps()

        return exit_code

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
