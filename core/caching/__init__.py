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
"""

from __future__ import annotations

__all__ = [
    "CacheMonitor",
    "LLMCache",
    "MultiLevelCache",
    "RedisClient",
    "SemanticCache",
    # Metrics
    "get_cache_monitor",
    # LLM cache
    "get_llm_cache",
    # Redis client
    "get_redis_client",
    # Semantic cache
    "get_semantic_cache",
]

# Import implementations
from .llm_cache import LLMCache, get_llm_cache
from .multi_level_cache import MultiLevelCache
from .metrics import CacheMonitor, get_cache_monitor
from .redis_client import RedisClient, get_redis_client
from .semantic_cache import SemanticCache, get_semantic_cache
