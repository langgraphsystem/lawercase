"""Enhanced logging utilities for production.

This module provides:
- Structured logging with context
- Error tracking and reporting
- Performance logging
- Audit logging
- Log aggregation utilities
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import contextvars
from datetime import datetime
from functools import wraps
import logging
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Optional, TypeVar

from pythonjsonlogger import jsonlogger
import structlog

from core.exceptions import MegaAgentError

# Context variables for request tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)

T = TypeVar("T")


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[Path] = None,
    service_name: str = "megaagent-pro",
) -> None:
    """Setup structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format (json or text)
        log_file: Optional file path for logging
        service_name: Service name for log context
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        console_handler.setFormatter(json_formatter)
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    handlers.append(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )

    # Add service context
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding context to logs.

    Example:
        with LogContext(user_id="user_123", request_id="req_456"):
            logger.info("Processing request")
    """

    def __init__(self, **kwargs: Any):
        """Initialize log context.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs

    def __enter__(self) -> LogContext:
        """Enter context."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit context."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())
        return False


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    include_traceback: bool = True,
) -> None:
    """Log error with full context.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context
        include_traceback: Include full traceback
    """
    error_data: dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # Add MegaAgentError specific fields
    if isinstance(error, MegaAgentError):
        error_data.update(
            {
                "error_code": error.code.value,
                "error_category": error.category.value,
                "recoverable": error.recoverable,
                "details": error.details,
            }
        )

    # Add traceback
    if include_traceback:
        error_data["traceback"] = traceback.format_exc()

    # Add additional context
    if context:
        error_data.update(context)

    logger.error("Error occurred", **error_data)


def log_performance(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Log performance metrics.

    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        metadata: Additional metadata
    """
    perf_data = {
        "operation": operation,
        "duration_ms": duration_ms,
        "duration_seconds": duration_ms / 1000,
    }

    if metadata:
        perf_data.update(metadata)

    logger.info("Performance metric", **perf_data)


class PerformanceLogger:
    """Context manager for performance logging.

    Example:
        with PerformanceLogger(logger, "database_query", user_id="user_123"):
            # Your operation
            result = await db.query()
    """

    def __init__(
        self,
        logger: structlog.BoundLogger,
        operation: str,
        **metadata: Any,
    ):
        """Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Operation name
            **metadata: Additional metadata
        """
        self.logger = logger
        self.operation = operation
        self.metadata = metadata
        self.start_time = 0.0

    def __enter__(self) -> PerformanceLogger:
        """Enter context."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit context and log performance."""
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is None:
            log_performance(self.logger, self.operation, duration_ms, self.metadata)
        else:
            self.logger.warning(
                "Operation failed",
                operation=self.operation,
                duration_ms=duration_ms,
                error=str(exc_val),
                **self.metadata,
            )

        return False


def log_function_call(
    logger: Optional[structlog.BoundLogger] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to log function calls with performance.

    Example:
        @log_function_call(include_args=True)
        async def my_function(arg1, arg2):
            return result
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = f"{func.__module__}.{func.__name__}"
            log_data: dict[str, Any] = {"function": func_name}

            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            logger.debug("Function called", **log_data)

            start_time = time.perf_counter()
            error_occurred = False

            try:
                result = await func(*args, **kwargs)

                if include_result:
                    log_data["result"] = str(result)

                return result

            except Exception as e:
                error_occurred = True
                log_error(logger, e, context={"function": func_name})
                raise

            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "Function completed" if not error_occurred else "Function failed",
                    function=func_name,
                    duration_ms=duration_ms,
                    error=error_occurred,
                )

        return wrapper

    return decorator


class AuditLogger:
    """Audit logger for tracking important actions.

    Example:
        audit = AuditLogger(logger)
        audit.log_action(
            action="user_login",
            user_id="user_123",
            details={"ip": "1.2.3.4"}
        )
    """

    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        """Initialize audit logger.

        Args:
            logger: Logger instance (creates new if None)
        """
        self.logger = logger or get_logger("audit")

    def log_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log audit event.

        Args:
            action: Action performed (e.g., "user_login", "document_created")
            user_id: User who performed action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            status: Action status (success, failure, error)
            details: Additional details
        """
        audit_data = {
            "event_type": "audit",
            "action": action,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            audit_data["user_id"] = user_id
        if resource_type:
            audit_data["resource_type"] = resource_type
        if resource_id:
            audit_data["resource_id"] = resource_id
        if details:
            audit_data["details"] = details

        self.logger.info("Audit event", **audit_data)


class ErrorTracker:
    """Track errors for monitoring and alerting.

    Example:
        tracker = ErrorTracker()
        tracker.track_error(error, context={"user_id": "user_123"})
        stats = tracker.get_error_stats()
    """

    def __init__(self):
        """Initialize error tracker."""
        self.errors: list[dict[str, Any]] = []
        self.error_counts: dict[str, int] = {}
        self.logger = get_logger("error_tracker")

    def track_error(
        self,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
        severity: str = "error",
    ) -> None:
        """Track error occurrence.

        Args:
            error: Exception to track
            context: Additional context
            severity: Error severity (warning, error, critical)
        """
        error_type = type(error).__name__
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": str(error),
            "severity": severity,
            "context": context or {},
        }

        if isinstance(error, MegaAgentError):
            error_record.update(
                {
                    "error_code": error.code.value,
                    "error_category": error.category.value,
                    "recoverable": error.recoverable,
                }
            )

        self.errors.append(error_record)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log error
        log_error(self.logger, error, context, include_traceback=True)

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics.

        Returns:
            Dictionary with error statistics
        """
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "recent_errors": self.errors[-10:],  # Last 10 errors
        }

    def clear_errors(self) -> None:
        """Clear tracked errors."""
        self.errors.clear()
        self.error_counts.clear()


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


# Request tracking utilities
def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)
    structlog.contextvars.bind_contextvars(request_id=request_id)


def get_request_id() -> Optional[str]:
    """Get request ID from context."""
    return request_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set user ID in context."""
    user_id_var.set(user_id)
    structlog.contextvars.bind_contextvars(user_id=user_id)


def get_user_id() -> Optional[str]:
    """Get user ID from context."""
    return user_id_var.get()


class RequestContext:
    """Context manager for request tracking.

    Example:
        with RequestContext(request_id="req_123", user_id="user_456"):
            await process_request()
    """

    def __init__(self, request_id: str, user_id: Optional[str] = None):
        """Initialize request context.

        Args:
            request_id: Unique request identifier
            user_id: User identifier
        """
        self.request_id = request_id
        self.user_id = user_id
        self._old_request_id: Optional[str] = None
        self._old_user_id: Optional[str] = None

    def __enter__(self) -> RequestContext:
        """Enter context."""
        self._old_request_id = get_request_id()
        self._old_user_id = get_user_id()

        set_request_id(self.request_id)
        if self.user_id:
            set_user_id(self.user_id)

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit context."""
        if self._old_request_id:
            set_request_id(self._old_request_id)
        if self._old_user_id:
            set_user_id(self._old_user_id)

        structlog.contextvars.unbind_contextvars("request_id", "user_id")
        return False
