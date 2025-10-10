"""Cache configuration for Redis and other caching backends."""

from __future__ import annotations

from pydantic import Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings


class CacheConfig(BaseSettings):
    """Configuration for caching layer."""

    # Redis connection
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_password: SecretStr | None = Field(
        default=None, description="Redis password (if required)"
    )
    redis_ssl: bool = Field(default=False, description="Use SSL for Redis connection")
    redis_max_connections: int = Field(default=50, description="Max connections in Redis pool")
    redis_socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    redis_socket_connect_timeout: int = Field(
        default=5, description="Socket connect timeout in seconds"
    )

    # Cache settings
    cache_enabled: bool = Field(default=True, description="Enable caching globally")
    cache_default_ttl: int = Field(
        default=3600, description="Default TTL for cached items (seconds)"
    )
    cache_max_size: int = Field(
        default=10000, description="Maximum number of items in memory cache"
    )

    # Semantic cache settings
    semantic_cache_enabled: bool = Field(
        default=True, description="Enable semantic similarity caching"
    )
    semantic_cache_threshold: float = Field(
        default=0.95, description="Similarity threshold for semantic cache hits (0-1)"
    )
    semantic_cache_max_candidates: int = Field(
        default=5, description="Max candidates to check for semantic similarity"
    )

    # LLM cache settings
    llm_cache_enabled: bool = Field(default=True, description="Cache LLM responses")
    llm_cache_ttl: int = Field(
        default=86400, description="TTL for LLM responses (24 hours default)"
    )

    # Cache warming
    cache_warming_enabled: bool = Field(
        default=False, description="Pre-populate cache with popular queries"
    )
    cache_warming_interval: int = Field(
        default=3600, description="Cache warming interval in seconds"
    )

    # Metrics
    cache_metrics_enabled: bool = Field(default=True, description="Collect cache hit/miss metrics")
    cache_metrics_window: int = Field(
        default=300, description="Metrics aggregation window in seconds"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "CACHE_",
    }


# Global singleton
_cache_config: CacheConfig | None = None


def get_cache_config() -> CacheConfig:
    """Get global cache configuration instance."""
    global _cache_config  # noqa: PLW0603
    if _cache_config is None:
        _cache_config = CacheConfig()
    return _cache_config
