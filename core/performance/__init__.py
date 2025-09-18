"""
Performance & Optimization module для mega_agent_pro.

Provides comprehensive performance optimization:
- Multi-level caching system (L1: Memory, L2: Redis, L3: Persistent)
- Semantic caching для embeddings и LLM responses
- Query result caching для database операций
- Cache integration с существующими агентами
- Performance monitoring и analytics
- Automatic optimization strategies
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Caching System
    "CacheManager",
    "InMemoryCache",
    "RedisCache",
    "MultiLevelCache",
    "SemanticCache",
    "CacheConfig",
    "CacheMetrics",
    "CacheItem",
    "CacheLevel",
    "CacheStrategy",
    "CacheItemType",
    "InvalidationStrategy",

    # Cache Integration
    "CacheIntegrationManager",
    "CachedMemoryManager",
    "CachedRAGPipelineAgent",
    "CachedMegaAgent",
    "WorkflowStateCache",
    "DatabaseQueryCache",

    # Utilities
    "create_cache_key",
    "cache_result",
    "create_default_cache_manager",
    "create_production_cache_manager",
]

# Import caching system
from .caching_system import (
    CacheManager,
    InMemoryCache,
    RedisCache,
    MultiLevelCache,
    SemanticCache,
    CacheConfig,
    CacheMetrics,
    CacheItem,
    CacheLevel,
    CacheStrategy,
    CacheItemType,
    InvalidationStrategy,
    create_cache_key,
    cache_result,
    create_default_cache_manager,
    create_production_cache_manager,
)

# Import cache integration
from .cache_integration import (
    CacheIntegrationManager,
    CachedMemoryManager,
    CachedRAGPipelineAgent,
    CachedMegaAgent,
    WorkflowStateCache,
    DatabaseQueryCache,
)