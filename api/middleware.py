from __future__ import annotations

from collections import defaultdict, deque
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def get_rate_limit_settings() -> tuple[int, int]:
    """Read rate limit configuration from environment."""
    limit = int(os.getenv("API_RATE_LIMIT", "60"))
    window = int(os.getenv("API_RATE_WINDOW", "60"))
    return limit, window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window rate limiter.

    Automatically evicts stale client buckets to prevent unbounded memory growth.
    """

    _MAX_CLIENTS = 10_000  # Hard cap on tracked clients
    _CLEANUP_INTERVAL = 300  # Seconds between full cleanup sweeps

    def __init__(self, app, limit: int | None = None, window: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit if limit is not None else int(os.getenv("API_RATE_LIMIT", "60"))
        self.window = window if window is not None else int(os.getenv("API_RATE_WINDOW", "60"))
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.time()

    def _cleanup_stale_buckets(self, now: float) -> None:
        """Remove buckets with no recent requests to bound memory usage."""
        if now - self._last_cleanup < self._CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        stale_keys = [k for k, v in self._buckets.items() if not v or now - v[-1] > self.window]
        for k in stale_keys:
            del self._buckets[k]
        # Hard cap: if still too many, drop oldest
        if len(self._buckets) > self._MAX_CLIENTS:
            excess = len(self._buckets) - self._MAX_CLIENTS
            for k in list(self._buckets.keys())[:excess]:
                del self._buckets[k]

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.limit <= 0:
            return await call_next(request)

        now = time.time()
        self._cleanup_stale_buckets(now)

        client = request.client.host if request.client else "anonymous"
        bucket = self._buckets[client]

        while bucket and now - bucket[0] > self.window:
            bucket.popleft()

        if len(bucket) >= self.limit:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        bucket.append(now)
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding a configurable body size limit."""

    def __init__(self, app, max_mb: int = 10) -> None:
        super().__init__(app)
        self.max_bytes = max_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": f"Request body too large (max {self.max_bytes // (1024 * 1024)} MB)"},
                status_code=413,
            )
        return await call_next(request)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Records request processing time for observability."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration = time.perf_counter() - start
            request.scope["metrics.total_time"] = duration
        return response


__all__ = [
    "RateLimitMiddleware",
    "RequestMetricsMiddleware",
    "RequestSizeLimitMiddleware",
    "get_rate_limit_settings",
]
