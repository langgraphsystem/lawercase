# Redis Configuration for Production

## Overview

Redis is used for workflow state persistence in production to support:
- **Horizontal scaling** - Multiple API instances can share workflow state
- **Persistence** - Workflow state survives application restarts
- **Performance** - Fast in-memory storage with sub-millisecond latency
- **TTL support** - Automatic cleanup of old workflows (24-hour TTL)

---

## Installation

### Option 1: Docker (Recommended)

```bash
# Pull official Redis image
docker pull redis:7-alpine

# Run Redis with persistence
docker run -d \
  --name mega-agent-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes
```

### Option 2: Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: mega-agent-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_URL=redis://redis:6379/0
      - USE_REDIS=true

volumes:
  redis-data:
```

### Option 3: Local Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
```bash
# Use WSL2 or download from:
# https://github.com/microsoftarchive/redis/releases
```

---

## Python Dependencies

Add to `requirements.txt`:

```txt
redis[hiredis]>=5.0.0,<6.0.0
```

Install:

```bash
pip install redis[hiredis]
```

---

## Configuration

### Environment Variables

Add to `.env` or `.env.production`:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
USE_REDIS=true
REDIS_PASSWORD=  # Optional, leave empty for no auth
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Document Workflow Settings
WORKFLOW_STATE_TTL=86400  # 24 hours
```

### Production Settings

Update `core/config/production_settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class RedisSettings(BaseSettings):
    """Redis configuration."""

    redis_url: str = Field(default="redis://localhost:6379/0")
    use_redis: bool = Field(default=True)
    redis_password: str | None = Field(default=None)
    redis_db: int = Field(default=0)
    redis_max_connections: int = Field(default=50)
    redis_socket_timeout: int = Field(default=5)
    redis_socket_connect_timeout: int = Field(default=5)

    class Config:
        env_prefix = ""
```

---

## Initialize Redis Client

Create `core/storage/redis_client.py`:

```python
"""Redis client initialization for production."""

from __future__ import annotations

import os
from typing import Any

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis | None:
    """Get or create Redis client.

    Returns:
        Redis client instance or None if not configured
    """
    global _redis_client

    if not os.getenv("USE_REDIS", "false").lower() == "true":
        logger.info("redis_disabled", message="USE_REDIS is not enabled")
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        password = os.getenv("REDIS_PASSWORD")
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

        _redis_client = await aioredis.from_url(
            redis_url,
            password=password,
            max_connections=max_connections,
            decode_responses=True,  # Auto-decode bytes to strings
        )

        # Test connection
        await _redis_client.ping()
        logger.info("redis_connected", url=redis_url)

        return _redis_client

    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        return None


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_disconnected")
```

---

## Update Document Workflow Store

Modify `core/storage/document_workflow_store.py`:

```python
from core.storage.redis_client import get_redis_client

# Global instance
_workflow_store: DocumentWorkflowStore | None = None

async def get_document_workflow_store() -> DocumentWorkflowStore:
    """Get or create workflow store instance.

    Automatically uses Redis if configured.
    """
    global _workflow_store

    if _workflow_store is not None:
        return _workflow_store

    # Try to get Redis client
    redis_client = await get_redis_client()

    if redis_client:
        logger.info("workflow_store_using_redis")
        _workflow_store = DocumentWorkflowStore(use_redis=True, redis_client=redis_client)
    else:
        logger.info("workflow_store_using_memory")
        _workflow_store = DocumentWorkflowStore(use_redis=False)

    return _workflow_store
```

---

## FastAPI Lifecycle Integration

Add to `api/main_production.py`:

```python
from contextlib import asynccontextmanager
from core.storage.redis_client import get_redis_client, close_redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with Redis initialization."""

    # Startup
    logger.info("Starting application...")

    # Initialize Redis
    redis_client = await get_redis_client()
    if redis_client:
        logger.info("Redis initialized successfully")
    else:
        logger.warning("Redis not available - using in-memory storage")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_redis_client()
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)
```

---

## Testing Redis Connection

### Test Script

```python
# test_redis.py
import asyncio
import redis.asyncio as aioredis

async def test_redis():
    client = await aioredis.from_url("redis://localhost:6379/0")

    # Test write
    await client.set("test_key", "test_value", ex=60)
    print("✅ Write successful")

    # Test read
    value = await client.get("test_key")
    print(f"✅ Read successful: {value}")

    # Test delete
    await client.delete("test_key")
    print("✅ Delete successful")

    await client.close()
    print("✅ Connection closed")

if __name__ == "__main__":
    asyncio.run(test_redis())
```

Run:

```bash
python test_redis.py
```

### Using Redis CLI

```bash
# Connect to Redis
redis-cli

# Check workflow keys
KEYS document_workflow:*

# View workflow state
GET document_workflow:abc-123-def-456

# Check TTL
TTL document_workflow:abc-123-def-456

# Monitor commands (for debugging)
MONITOR
```

---

## Monitoring

### Redis Info

```bash
redis-cli INFO

# Check specific section
redis-cli INFO stats
redis-cli INFO memory
redis-cli INFO replication
```

### Key Metrics

```bash
# Total keys
redis-cli DBSIZE

# Memory usage
redis-cli INFO memory | grep used_memory_human

# Connected clients
redis-cli INFO clients | grep connected_clients

# Ops per second
redis-cli INFO stats | grep instantaneous_ops_per_sec
```

---

## Production Considerations

### 1. Persistence

Enable AOF (Append-Only File) for durability:

```bash
# In redis.conf
appendonly yes
appendfsync everysec
```

Or via Docker:

```bash
docker run -d redis:7-alpine redis-server --appendonly yes --appendfsync everysec
```

### 2. Memory Limits

Set max memory and eviction policy:

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 3. Security

Enable authentication:

```bash
# redis.conf
requirepass your-strong-password
```

Update environment:

```bash
REDIS_URL=redis://:your-strong-password@localhost:6379/0
```

### 4. High Availability

For production, consider:

- **Redis Sentinel** - Automatic failover
- **Redis Cluster** - Horizontal scaling
- **Managed services** - AWS ElastiCache, Azure Redis Cache, Google Memorystore

---

## Troubleshooting

### Connection Refused

```bash
# Check Redis is running
redis-cli ping

# If not, start it
sudo systemctl start redis-server  # Linux
brew services start redis           # macOS
docker start mega-agent-redis       # Docker
```

### Authentication Error

```bash
# Verify password
redis-cli -a your-password ping

# Check REDIS_URL environment variable
echo $REDIS_URL
```

### Out of Memory

```bash
# Check memory usage
redis-cli INFO memory

# Clear old keys manually
redis-cli --scan --pattern "document_workflow:*" | xargs redis-cli DEL

# Or flush database (WARNING: deletes everything)
redis-cli FLUSHDB
```

### Slow Performance

```bash
# Check slow log
redis-cli SLOWLOG GET 10

# Monitor operations
redis-cli --latency

# Check connection pool
# Increase REDIS_MAX_CONNECTIONS if needed
```

---

## Migration from In-Memory to Redis

### Zero-Downtime Migration

1. **Enable Redis** without changing existing code
2. **New workflows** will use Redis automatically
3. **Old workflows** in memory will expire naturally
4. **No data migration needed** (workflows are ephemeral)

### Force Migration (Optional)

If you need to migrate active workflows:

```python
# migration_script.py
import asyncio
from core.storage.document_workflow_store import DocumentWorkflowStore
from core.storage.redis_client import get_redis_client

async def migrate_workflows():
    # Old in-memory store
    old_store = DocumentWorkflowStore(use_redis=False)

    # New Redis store
    redis_client = await get_redis_client()
    new_store = DocumentWorkflowStore(use_redis=True, redis_client=redis_client)

    # Migrate all workflows
    for thread_id, state in old_store._memory_store.items():
        await new_store.save_state(thread_id, state)
        print(f"Migrated: {thread_id}")

    print("Migration complete!")

asyncio.run(migrate_workflows())
```

---

## Summary

✅ **Redis installed and running**
✅ **Python dependencies added** (`redis[hiredis]`)
✅ **Environment variables configured**
✅ **Document workflow store supports Redis**
✅ **FastAPI lifecycle manages connections**
✅ **Monitoring and troubleshooting tools ready**

**Next steps:**
1. Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`
2. Set environment: `export USE_REDIS=true`
3. Start API: `python -m uvicorn api.main_production:app`
4. Verify logs: Look for "Redis initialized successfully"

**Status:** ✅ Production-ready
