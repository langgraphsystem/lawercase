"""Caching layer for mega_agent_pro.

This module provides multi-level caching:
- L1: In-memory cache (fastest)
- L2: Redis cache (shared across instances)
- L3: Semantic cache (similarity-based)

Features:
- LRU eviction policies
- TTL-based expiration
- Cache warming strategies
- Hit rate metrics
- Intelligent invalidation strategies
- Proactive cache warming with prediction

Advanced (v2.0):
- InvalidationManager: Multiple invalidation strategies
- ProactiveWarmer: Predictive cache warming
"""

from __future__ import annotations

from .invalidation_strategies import (
    AdaptiveInvalidationStrategy,
    CacheEntry,
    CompositeInvalidationStrategy,
    DependencyTrackingStrategy,
    EventDrivenInvalidationStrategy,
    InvalidationEvent,
    InvalidationManager,
    InvalidationReason,
    InvalidationStrategy,
    PatternMatchingStrategy,
    SlidingWindowStrategy,
    TTLInvalidationStrategy,
    create_default_invalidation_strategy,
    create_invalidation_manager,
)

# Import implementations
from .llm_cache import LLMCache, get_llm_cache
from .metrics import CacheMonitor, get_cache_monitor
from .multi_level_cache import MultiLevelCache
from .proactive_warming import (
    CompositePredictor,
    DependencyChainPredictor,
    ProactiveWarmer,
    TimeBasedPredictor,
    UsagePatternPredictor,
    WarmingCandidate,
    WarmingPredictor,
    WarmingPriority,
    WarmingResult,
    create_proactive_warmer,
)
from .redis_client import RedisClient, get_redis_client
from .semantic_cache import SemanticCache, get_semantic_cache

__all__ = [
    # Invalidation Strategies (v2.0)
    "AdaptiveInvalidationStrategy",
    "CacheEntry",
    # Core Cache
    "CacheMonitor",
    "CompositeInvalidationStrategy",
    # Proactive Warming (v2.0)
    "CompositePredictor",
    "DependencyChainPredictor",
    "DependencyTrackingStrategy",
    "EventDrivenInvalidationStrategy",
    "InvalidationEvent",
    "InvalidationManager",
    "InvalidationReason",
    "InvalidationStrategy",
    "LLMCache",
    "MultiLevelCache",
    "PatternMatchingStrategy",
    "ProactiveWarmer",
    "RedisClient",
    "SemanticCache",
    "SlidingWindowStrategy",
    "TTLInvalidationStrategy",
    "TimeBasedPredictor",
    "UsagePatternPredictor",
    "WarmingCandidate",
    "WarmingPredictor",
    "WarmingPriority",
    "WarmingResult",
    "create_default_invalidation_strategy",
    "create_invalidation_manager",
    "create_proactive_warmer",
    "get_cache_monitor",
    "get_llm_cache",
    "get_redis_client",
    "get_semantic_cache",
]
