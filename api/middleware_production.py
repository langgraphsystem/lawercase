"""Production-ready middleware for FastAPI.

This module provides:
- Enhanced rate limiting
- Request ID tracking
- Performance monitoring
- Error handling
- Request validation
"""

from __future__ import annotations

from collections.abc import Callable
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.exceptions import MegaAgentError, RateLimitExceededError
from core.logging_utils import get_logger, set_request_id

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request.

    Generates or uses existing X-Request-ID header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with ID tracking."""
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set in context for logging
        set_request_id(request_id)

        # Add to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Track request performance metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance tracking."""
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Log performance
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=getattr(request.state, "request_id", None),
        )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Handle errors and convert to proper HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling."""
        try:
            response = await call_next(request)
            return response

        except MegaAgentError as e:
            # Handle our custom exceptions
            from fastapi.responses import JSONResponse

            logger.error(
                "MegaAgent error occurred",
                error_code=e.code.value,
                error_category=e.category.value,
                error_message=str(e),
                request_id=getattr(request.state, "request_id", None),
            )

            # Map to HTTP status codes
            status_code = 500  # Default
            if "AUTH" in e.code.value or "TOKEN" in e.code.value:
                status_code = 401
            elif "PERMISSION" in e.code.value:
                status_code = 403
            elif "NOT_FOUND" in e.code.value:
                status_code = 404
            elif "VALIDATION" in e.code.value:
                status_code = 422
            elif "RATE_LIMIT" in e.code.value:
                status_code = 429

            return JSONResponse(
                status_code=status_code,
                content=e.to_dict(),
                headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
            )

        except Exception as e:
            # Handle unexpected exceptions
            logger.exception(
                "Unexpected error occurred",
                error=str(e),
                request_id=getattr(request.state, "request_id", None),
            )

            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "message": "Internal server error",
                        "code": "ERR_1000",
                        "recoverable": False,
                    }
                },
                headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
            )


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation."""

    def __init__(self, rate: int, per: float = 60.0):
        """Initialize rate limiter.

        Args:
            rate: Number of requests per time period
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.buckets: dict[str, dict[str, float]] = {}

    def is_allowed(self, key: str) -> tuple[bool, float]:
        """Check if request is allowed.

        Args:
            key: Rate limit key (e.g., user ID, IP address)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current = time.time()

        if key not in self.buckets:
            self.buckets[key] = {
                "allowance": float(self.rate),
                "last_check": current,
            }

        bucket = self.buckets[key]
        time_passed = current - bucket["last_check"]
        bucket["last_check"] = current

        # Add new tokens based on time passed
        bucket["allowance"] += time_passed * (self.rate / self.per)
        if bucket["allowance"] > self.rate:
            bucket["allowance"] = float(self.rate)

        # Check if we have tokens available
        if bucket["allowance"] < 1.0:
            # Calculate retry after time
            retry_after = (1.0 - bucket["allowance"]) * (self.per / self.rate)
            return False, retry_after
        else:
            bucket["allowance"] -= 1.0
            return True, 0.0


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with per-user limits."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        """Initialize rate limiter.

        Args:
            app: ASGI application
            requests_per_minute: Requests allowed per minute
            requests_per_hour: Requests allowed per hour
        """
        super().__init__(app)
        self.minute_limiter = TokenBucketRateLimiter(requests_per_minute, per=60.0)
        self.hour_limiter = TokenBucketRateLimiter(requests_per_hour, per=3600.0)

    def get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key for request.

        Uses user ID if authenticated, otherwise IP address.

        Args:
            request: HTTP request

        Returns:
            Rate limit key
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            return f"user:{request.state.user.user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/readiness", "/liveness"]:
            return await call_next(request)

        key = self.get_rate_limit_key(request)

        # Check minute limit
        allowed, retry_after = self.minute_limiter.is_allowed(key)
        if not allowed:
            logger.warning(
                "Rate limit exceeded (per minute)",
                key=key,
                retry_after=retry_after,
                request_id=getattr(request.state, "request_id", None),
            )

            from fastapi.responses import JSONResponse

            error = RateLimitExceededError(
                message="Rate limit exceeded (per minute)",
                retry_after=int(retry_after) + 1,
                limit=self.minute_limiter.rate,
            )

            return JSONResponse(
                status_code=429,
                content=error.to_dict(),
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(self.minute_limiter.rate),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )

        # Check hour limit
        allowed, retry_after = self.hour_limiter.is_allowed(key)
        if not allowed:
            logger.warning(
                "Rate limit exceeded (per hour)",
                key=key,
                retry_after=retry_after,
                request_id=getattr(request.state, "request_id", None),
            )

            from fastapi.responses import JSONResponse

            error = RateLimitExceededError(
                message="Rate limit exceeded (per hour)",
                retry_after=int(retry_after) + 1,
                limit=self.hour_limiter.rate,
            )

            return JSONResponse(
                status_code=429,
                content=error.to_dict(),
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(self.hour_limiter.rate),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.minute_limiter.rate)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.hour_limiter.rate)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )

        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """Add compression hint headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enable compression."""
        response = await call_next(request)

        # Add vary header for proper caching
        response.headers["Vary"] = "Accept-Encoding"

        return response
