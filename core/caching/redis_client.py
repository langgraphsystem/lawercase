"""Redis client manager with connection pooling and async support."""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from redis.asyncio import ConnectionPool, Redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .config import get_cache_config


class RedisClient:
    """
    Async Redis client with connection pooling.

    Features:
    - Automatic connection pooling
    - JSON serialization/deserialization
    - TTL support
    - Health checks
    - Graceful degradation

    Example:
        >>> client = RedisClient()
        >>> await client.set("key", {"data": "value"}, ttl=3600)
        >>> data = await client.get("key")
        >>> print(data)
        {'data': 'value'}
    """

    def __init__(self):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package required. Install with: pip install redis[hiredis]")

        self.config = get_cache_config()
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._fake_mode: bool = False  # when True, use in-memory FakeRedis

    def _get_pool(self) -> ConnectionPool:
        """Get or create Redis connection pool."""
        if self._pool is None:
            redis_url = str(self.config.redis_url)

            # Build connection kwargs
            pool_kwargs = {
                "max_connections": self.config.redis_max_connections,
                "socket_timeout": self.config.redis_socket_timeout,
                "socket_connect_timeout": self.config.redis_socket_connect_timeout,
                "decode_responses": True,  # Auto-decode bytes to strings
            }

            # Add password if configured
            if self.config.redis_password:
                pool_kwargs["password"] = self.config.redis_password.get_secret_value()

            # Add SSL if enabled
            if self.config.redis_ssl:
                pool_kwargs["ssl"] = True
                pool_kwargs["ssl_cert_reqs"] = "required"

            self._pool = ConnectionPool.from_url(redis_url, **pool_kwargs)

        return self._pool

    def get_client(self) -> Redis:
        """Get or create Redis client.

        Falls back to an in-memory FakeRedis if real Redis is unavailable
        or when explicitly requested via env var CACHE_USE_FAKEREDIS=true.
        """
        # Explicit opt-in to fakeredis via env var
        use_fake_env = os.getenv("CACHE_USE_FAKEREDIS", "false").lower() == "true"
        if use_fake_env and not self._fake_mode:
            self._client = self._init_fakeredis()
            self._fake_mode = True
            return self._client

        if self._client is None:
            try:
                pool = self._get_pool()
                self._client = Redis(connection_pool=pool)
            except Exception:
                # If client creation fails (e.g., invalid URL), fallback
                self._client = self._init_fakeredis()
                self._fake_mode = True
        return self._client

    def _init_fakeredis(self):  # type: ignore[no-untyped-def]
        """Initialize and return an async FakeRedis client.

        Requires 'fakeredis' package. If missing, re-raise the original error.
        """
        try:
            from fakeredis import aioredis as fake  # type: ignore
        except Exception as e:  # pragma: no cover - environment dependent
            raise ImportError("fakeredis is required for in-memory cache fallback.") from e
        # decode_responses=True to mirror real client behavior
        return fake.FakeRedis(decode_responses=True)

    async def _ensure_or_fallback(self) -> None:
        """Ensure client is usable; on failure, switch to FakeRedis."""
        if self._fake_mode:
            return
        try:
            client = self.get_client()
            # Quick ping to validate connection
            await client.ping()
        except Exception:
            # Switch to FakeRedis
            self._client = self._init_fakeredis()
            self._fake_mode = True

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        serialize: bool = True,
    ) -> bool:
        """
        Set a key-value pair in Redis.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized if serialize=True)
            ttl: Time to live in seconds (None = no expiration)
            serialize: Whether to JSON-serialize the value

        Returns:
            True if successful

        Example:
            >>> await client.set("user:123", {"name": "John"}, ttl=3600)
            True
        """
        await self._ensure_or_fallback()
        client = self.get_client()

        # Serialize value if needed
        if serialize:
            value = json.dumps(value)

        # Set with TTL
        if ttl:
            return await client.setex(key, ttl, value)
        return await client.set(key, value)

    async def get(
        self,
        key: str,
        deserialize: bool = True,
    ) -> Any:
        """
        Get a value from Redis.

        Args:
            key: Cache key
            deserialize: Whether to JSON-deserialize the value

        Returns:
            Cached value or None if not found

        Example:
            >>> data = await client.get("user:123")
            >>> print(data["name"])
            John
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        value = await client.get(key)

        if value is None:
            return None

        # Deserialize if needed
        if deserialize:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return value

    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted

        Example:
            >>> await client.delete("user:123")
            True
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        result = await client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.

        Args:
            key: Cache key to check

        Returns:
            True if key exists

        Example:
            >>> await client.exists("user:123")
            True
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.exists(key) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful

        Example:
            >>> await client.expire("user:123", 3600)
            True
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist

        Example:
            >>> await client.ttl("user:123")
            3456
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.ttl(key)

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment by

        Returns:
            New value after increment

        Example:
            >>> await client.incr("api:calls:user123")
            42
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a counter.

        Args:
            key: Counter key
            amount: Amount to decrement by

        Returns:
            New value after decrement
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.decrby(key, amount)

    async def keys(self, pattern: str) -> list[str]:
        """
        Find keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            List of matching keys

        Warning:
            Expensive operation in production. Use SCAN instead for large datasets.

        Example:
            >>> await client.keys("cache:llm:*")
            ['cache:llm:query1', 'cache:llm:query2']
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.keys(pattern)

    async def flush(self, pattern: str | None = None) -> int:
        """
        Delete keys matching a pattern.

        Args:
            pattern: Pattern to match (None = delete all)

        Returns:
            Number of keys deleted

        Example:
            >>> await client.flush("cache:temp:*")
            15
        """
        await self._ensure_or_fallback()
        client = self.get_client()

        if pattern:
            keys = await self.keys(pattern)
            if keys:
                return await client.delete(*keys)
            return 0
        # Flush entire database
        await client.flushdb()
        return -1

    async def ping(self) -> bool:
        """
        Check Redis connection.

        Returns:
            True if Redis is reachable

        Example:
            >>> await client.ping()
            True
        """
        try:
            await self._ensure_or_fallback()
            client = self.get_client()
            return await client.ping()
        except Exception:
            return False

    async def info(self) -> dict[str, Any]:
        """
        Get Redis server information.

        Returns:
            Dictionary with Redis stats

        Example:
            >>> info = await client.info()
            >>> print(info["used_memory_human"])
            '2.5M'
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.info()

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """
        Add members to sorted set.

        Args:
            key: Sorted set key
            mapping: Dict of {member: score}

        Returns:
            Number of members added

        Example:
            >>> await client.zadd("leaderboard", {"player1": 100, "player2": 200})
            2
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.zadd(key, mapping)

    async def zrevrange(
        self, key: str, start: int, end: int, withscores: bool = False
    ) -> list[str] | list[tuple[str, float]]:
        """
        Get members from sorted set in reverse order (highest to lowest score).

        Args:
            key: Sorted set key
            start: Start index
            end: End index
            withscores: Include scores in result

        Returns:
            List of members or (member, score) tuples

        Example:
            >>> await client.zrevrange("leaderboard", 0, 9)
            ['player2', 'player1']
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.zrevrange(key, start, end, withscores=withscores)

    async def zremrangebyrank(self, key: str, start: int, end: int) -> int:
        """
        Remove members by rank range.

        Args:
            key: Sorted set key
            start: Start rank
            end: End rank

        Returns:
            Number of members removed

        Example:
            >>> await client.zremrangebyrank("leaderboard", 0, -11)  # Keep top 10
            5
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.zremrangebyrank(key, start, end)

    async def zrem(self, key: str, *members: str) -> int:
        """
        Remove members from sorted set.

        Args:
            key: Sorted set key
            members: Members to remove

        Returns:
            Number of members removed

        Example:
            >>> await client.zrem("leaderboard", "player1", "player2")
            2
        """
        await self._ensure_or_fallback()
        client = self.get_client()
        return await client.zrem(key, *members)

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            try:
                await self._client.close()
            except Exception:  # nosec B110
                pass  # Safe: cleanup, exceptions during close are expected
            self._client = None
        if self._pool and not self._fake_mode:
            try:
                await self._pool.disconnect()
            except Exception:  # nosec B110
                pass  # Safe: cleanup, exceptions during disconnect are expected
            self._pool = None


# Global singleton
_redis_clients_by_loop: dict[int, RedisClient] = {}


def get_redis_client() -> RedisClient:
    """
    Get global Redis client instance.

    Returns:
        Shared RedisClient instance

    Example:
        >>> client = get_redis_client()
        >>> await client.set("key", "value")
    """
    # Bind client to current asyncio event loop to avoid cross-loop issues
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        key = id(loop)
    except RuntimeError:
        # No running loop; fall back to a single instance
        key = -1

    global _redis_clients_by_loop
    client = _redis_clients_by_loop.get(key)
    if client is None:
        client = RedisClient()
        _redis_clients_by_loop[key] = client
    return client


async def close_redis_client() -> None:
    """Close global Redis client connection."""
    # Close all loop-bound clients
    global _redis_clients_by_loop
    for client in list(_redis_clients_by_loop.values()):
        try:
            await client.close()
        except Exception:  # nosec B110
            pass  # Safe: cleanup, exceptions during close are expected
    _redis_clients_by_loop.clear()
