"""Enhanced health check endpoints for production.

This module provides:
- Liveness probe (is service running)
- Readiness probe (is service ready to accept requests)
- Detailed health status
- Dependency health checks
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import Enum
import time
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from core.agui.middleware import require_role, verify_jwt
from core.config.production_settings import AppSettings, get_settings
from core.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Models
# ============================================================================


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status of a dependency."""

    name: str
    status: HealthStatus
    response_time_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Comprehensive health response."""

    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    version: str
    environment: str
    dependencies: list[DependencyHealth]
    details: dict[str, Any] = {}


# ============================================================================
# Health Check Functions
# ============================================================================


# Track service start time
SERVICE_START_TIME = time.time()


async def check_database_health() -> DependencyHealth:
    """Check database connectivity and health.

    Uses DatabaseManager.health_check() to verify PostgreSQL connection.

    Returns:
        Database health status
    """
    start_time = time.perf_counter()

    try:
        from core.storage.connection import get_db_manager

        db = get_db_manager()
        is_healthy = await db.health_check()

        response_time = (time.perf_counter() - start_time) * 1000

        if is_healthy:
            return DependencyHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message="Database connection successful",
            )
        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message="Database health check returned False",
        )

    except ImportError as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.warning("Database module not available", error=str(e))

        return DependencyHealth(
            name="database",
            status=HealthStatus.DEGRADED,
            response_time_ms=response_time,
            message="Database module not configured",
        )

    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error("Database health check failed", error=str(e))

        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message=f"Database check failed: {e!s}",
        )


async def check_redis_health() -> DependencyHealth:
    """Check Redis connectivity and health.

    Uses RedisClient.ping() to verify Redis connection.

    Returns:
        Redis health status
    """
    start_time = time.perf_counter()

    try:
        from core.caching.redis_client import get_redis_client

        redis_client = get_redis_client()
        is_healthy = await redis_client.ping()

        response_time = (time.perf_counter() - start_time) * 1000

        # Check if using FakeRedis (degraded mode)
        is_fake = getattr(redis_client, "_fake_mode", False)

        if is_healthy and not is_fake:
            return DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message="Redis connection successful",
            )
        if is_healthy and is_fake:
            return DependencyHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                message="Using in-memory FakeRedis (real Redis unavailable)",
            )
        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message="Redis ping returned False",
        )

    except ImportError as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.warning("Redis module not available", error=str(e))

        return DependencyHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            response_time_ms=response_time,
            message="Redis module not configured",
        )

    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error("Redis health check failed", error=str(e))

        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message=f"Redis check failed: {e!s}",
        )


async def check_llm_health(settings: AppSettings) -> DependencyHealth:
    """Check LLM provider availability.

    Verifies API keys are configured and attempts a lightweight API call
    to confirm connectivity. Uses a short timeout to avoid blocking the
    health endpoint.

    Args:
        settings: Application settings

    Returns:
        LLM health status
    """
    start_time = time.perf_counter()
    _health_timeout = 5.0

    try:
        # 1. Check if any API key is configured
        openai_key = getattr(settings.llm, "openai_api_key", None)
        anthropic_key = getattr(settings.llm, "anthropic_api_key", None)
        gemini_key = getattr(settings.llm, "gemini_api_key", None)

        has_api_key = any(k is not None for k in (openai_key, anthropic_key, gemini_key))

        if not has_api_key:
            response_time = (time.perf_counter() - start_time) * 1000
            return DependencyHealth(
                name="llm_provider",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                message="No LLM API keys configured",
            )

        # 2. Attempt a lightweight connectivity check with the first available provider
        provider_name = "unknown"
        try:
            if openai_key:
                provider_name = "openai"
                import httpx

                key = (
                    openai_key.get_secret_value()
                    if hasattr(openai_key, "get_secret_value")
                    else str(openai_key)
                )
                async with httpx.AsyncClient(timeout=_health_timeout) as client:
                    resp = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    resp.raise_for_status()

            elif anthropic_key:
                provider_name = "anthropic"
                import httpx

                key = (
                    anthropic_key.get_secret_value()
                    if hasattr(anthropic_key, "get_secret_value")
                    else str(anthropic_key)
                )
                async with httpx.AsyncClient(timeout=_health_timeout) as client:
                    resp = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers={
                            "x-api-key": key,
                            "anthropic-version": "2023-06-01",
                        },
                    )
                    resp.raise_for_status()

            elif gemini_key:
                provider_name = "google"
                import httpx

                key = (
                    gemini_key.get_secret_value()
                    if hasattr(gemini_key, "get_secret_value")
                    else str(gemini_key)
                )
                async with httpx.AsyncClient(timeout=_health_timeout) as client:
                    resp = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                    )
                    resp.raise_for_status()

        except TimeoutError:
            response_time = (time.perf_counter() - start_time) * 1000
            return DependencyHealth(
                name="llm_provider",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                message=f"LLM provider ({provider_name}) reachable but slow (timeout {_health_timeout}s)",
            )
        except Exception as ping_err:
            response_time = (time.perf_counter() - start_time) * 1000
            logger.warning("llm_health_ping_failed", provider=provider_name, error=str(ping_err))
            return DependencyHealth(
                name="llm_provider",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                message=f"LLM key configured but connectivity check failed ({provider_name}): {ping_err!s}",
            )

        response_time = (time.perf_counter() - start_time) * 1000
        return DependencyHealth(
            name="llm_provider",
            status=HealthStatus.HEALTHY,
            response_time_ms=response_time,
            message=f"LLM provider ({provider_name}) reachable",
        )

    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error("LLM health check failed", error=str(e))

        return DependencyHealth(
            name="llm_provider",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message=f"LLM check failed: {e!s}",
        )


async def check_memory_health() -> DependencyHealth:
    """Check memory manager health.

    Verifies MemoryManager can be instantiated and is operational.

    Returns:
        Memory health status
    """
    start_time = time.perf_counter()

    try:
        from core.memory.memory_manager import MemoryManager

        # Try to instantiate memory manager (validates configuration)
        memory = MemoryManager()

        response_time = (time.perf_counter() - start_time) * 1000

        return DependencyHealth(
            name="memory_manager",
            status=HealthStatus.HEALTHY,
            response_time_ms=response_time,
            message="Memory manager operational",
            details={"type": type(memory).__name__},
        )

    except ImportError as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.warning("Memory module not available", error=str(e))

        return DependencyHealth(
            name="memory_manager",
            status=HealthStatus.DEGRADED,
            response_time_ms=response_time,
            message="Memory module not configured",
        )

    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error("Memory health check failed", error=str(e))

        return DependencyHealth(
            name="memory_manager",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time,
            message=f"Memory check failed: {e!s}",
        )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    settings: AppSettings = Depends(get_settings),
) -> HealthResponse:
    """Comprehensive health check endpoint.

    Checks all dependencies and returns detailed status.

    Returns:
        Detailed health status
    """
    # Run all health checks in parallel
    checks = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_llm_health(settings),
        check_memory_health(),
        return_exceptions=True,
    )

    # Filter out exceptions and collect results
    dependencies: list[DependencyHealth] = []
    for check in checks:
        if isinstance(check, DependencyHealth):
            dependencies.append(check)
        elif isinstance(check, Exception):
            logger.error("Health check failed", error=str(check))

    # Determine overall status
    if all(d.status == HealthStatus.HEALTHY for d in dependencies):
        overall_status = HealthStatus.HEALTHY
    elif any(d.status == HealthStatus.UNHEALTHY for d in dependencies):
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.DEGRADED

    uptime = time.time() - SERVICE_START_TIME

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        uptime_seconds=uptime,
        version=settings.app_version,
        environment=settings.env.value,
        dependencies=dependencies,
        details={
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        },
    )


@router.get("/liveness", tags=["Health"])
async def liveness_probe() -> dict[str, Any]:
    """Kubernetes liveness probe.

    Returns 200 if service is running.

    Returns:
        Simple liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/readiness", tags=["Health"])
async def readiness_probe(
    settings: AppSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Kubernetes readiness probe.

    Returns 200 if service is ready to accept requests.
    Checks critical dependencies.

    Returns:
        Readiness status

    Raises:
        HTTPException: If service is not ready (status 503)
    """
    from fastapi import HTTPException

    # Check critical dependencies
    critical_checks = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        return_exceptions=True,
    )

    # Check if any critical dependency is unhealthy
    for check in critical_checks:
        if isinstance(check, DependencyHealth):
            if check.status == HealthStatus.UNHEALTHY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service not ready: {check.name} is unhealthy",
                )

    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/startup", tags=["Health"])
async def startup_probe() -> dict[str, Any]:
    """Kubernetes startup probe.

    Returns 200 when service has completed startup.

    Returns:
        Startup status
    """
    uptime = time.time() - SERVICE_START_TIME

    # Consider service started after 5 seconds
    if uptime < 5:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service still starting up",
        )

    return {
        "status": "started",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": uptime,
    }


@router.get("/metrics", tags=["Health"])
async def metrics(
    _: dict[str, Any] = Depends(verify_jwt),
    __: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Basic metrics endpoint.

    Returns:
        Service metrics
    """
    uptime = time.time() - SERVICE_START_TIME

    return {
        "uptime_seconds": uptime,
        "timestamp": datetime.now(UTC).isoformat(),
        # TODO: Add more metrics
        # - Request count
        # - Error rate
        # - Response time percentiles
        # - Resource usage
    }
