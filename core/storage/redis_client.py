"""Redis client initialization for production workflow persistence."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis | None:
    """Get or create Redis client.

    Returns:
        Redis client instance or None if not configured/available
    """
    global _redis_client

    # Check if Redis is enabled
    use_redis = os.getenv("USE_REDIS", "false").lower() == "true"
    if not use_redis:
        logger.debug("redis_disabled", message="USE_REDIS environment variable not set")
        return None

    # Return existing client if available
    if _redis_client is not None:
        return _redis_client

    try:
        # Import redis (optional dependency)
        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.warning(
                "redis_import_failed",
                message="redis package not installed. Install with: pip install redis[hiredis]",
            )
            return None

        # Get configuration from environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        password = os.getenv("REDIS_PASSWORD")
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

        # Create Redis client
        _redis_client = await aioredis.from_url(
            redis_url,
            password=password if password else None,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,  # Auto-decode bytes to strings
        )

        # Test connection
        await _redis_client.ping()

        logger.info(
            "redis_connected",
            url=(
                redis_url.split("@")[-1] if "@" in redis_url else redis_url
            ),  # Hide password in logs
            max_connections=max_connections,
        )

        return _redis_client

    except Exception as e:
        logger.error("redis_connection_failed", error=str(e), redis_url=redis_url)
        _redis_client = None
        return None


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("redis_disconnected")
        except Exception as e:
            logger.error("redis_close_error", error=str(e))
        finally:
            _redis_client = None


async def health_check() -> bool:
    """Check if Redis connection is healthy.

    Returns:
        True if Redis is connected and responding, False otherwise
    """
    try:
        client = await get_redis_client()
        if client is None:
            return False

        await client.ping()
        return True
    except Exception as e:
        logger.warning("redis_health_check_failed", error=str(e))
        return False


__all__ = ["close_redis_client", "get_redis_client", "health_check"]
