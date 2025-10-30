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
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, app, limit: int | None = None, window: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit if limit is not None else int(os.getenv("API_RATE_LIMIT", "60"))
        self.window = window if window is not None else int(os.getenv("API_RATE_WINDOW", "60"))
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.limit <= 0:
            return await call_next(request)

        now = time.time()
        client = request.client.host if request.client else "anonymous"
        bucket = self._buckets[client]

        while bucket and now - bucket[0] > self.window:
            bucket.popleft()

        if len(bucket) >= self.limit:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        bucket.append(now)
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
    "get_rate_limit_settings",
]
