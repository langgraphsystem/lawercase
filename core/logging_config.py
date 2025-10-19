"""Logging configuration for mega_agent_pro.

This module provides a simple, user-friendly interface to the comprehensive
logging infrastructure in core/logging_utils.py.

Usage:
    from core.logging_config import setup_logging, StructuredLogger

    # Setup logging at application start
    setup_logging(log_level="INFO")

    # Use structured logger in your classes
    logger = StructuredLogger("my_module")
    logger.info("Operation completed", user_id="123", duration_ms=45)
"""

from __future__ import annotations

import logging
from typing import Any

# Import comprehensive logging utilities (optional)
try:
    from core.logging_utils import (
        AuditLogger,
        ErrorTracker,
        LogContext,
        PerformanceLogger,
        RequestContext,
        get_error_tracker,
        get_logger as get_structlog_logger,
        get_request_id,
        get_user_id,
        log_error,
        log_function_call,
        log_performance,
        set_request_id,
        set_user_id,
        setup_logging as setup_comprehensive_logging,
    )

    COMPREHENSIVE_LOGGING_AVAILABLE = True
except ImportError:
    # Fallback if structlog/pythonjsonlogger not available
    COMPREHENSIVE_LOGGING_AVAILABLE = False

    # Provide minimal fallback implementations
    def setup_comprehensive_logging(*args, **kwargs):
        pass

    def get_structlog_logger(name):
        return logging.getLogger(name)

    # Export None for optional features
    AuditLogger = None
    ErrorTracker = None
    LogContext = None
    PerformanceLogger = None
    RequestContext = None
    get_error_tracker = None
    get_request_id = None
    get_user_id = None
    log_error = None
    log_function_call = None
    log_performance = None
    set_request_id = None
    set_user_id = None

__all__ = [
    # Simple API
    "setup_logging",
    "StructuredLogger",
    # Advanced API from logging_utils
    "get_structlog_logger",
    "LogContext",
    "log_error",
    "log_performance",
    "log_function_call",
    "PerformanceLogger",
    "AuditLogger",
    "ErrorTracker",
    "get_error_tracker",
    "RequestContext",
    "set_request_id",
    "get_request_id",
    "set_user_id",
    "get_user_id",
]


def setup_logging(log_level: str | None = None, log_format: str = "text") -> None:
    """Configure logging for the application.

    This is a simplified wrapper around core.logging_utils.setup_logging()
    that provides sensible defaults.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, uses "INFO" for production and "DEBUG" for development.
        log_format: Format (json or text). Default: text for readability.

    Example:
        >>> from core.logging_config import setup_logging
        >>> setup_logging(log_level="INFO")
        >>> # Now all loggers are configured
    """
    # Try to get settings for environment-aware defaults
    try:
        from core.config import get_settings

        settings = get_settings()
        if log_level is None:
            # Use environment-specific defaults
            if hasattr(settings, "env") and settings.env.value == "production":
                log_level = "WARNING"
            elif hasattr(settings, "env") and settings.env.value == "development":
                log_level = "DEBUG"
            else:
                log_level = "INFO"

        # Get observability log level if available
        if hasattr(settings, "observability") and hasattr(settings.observability, "log_level"):
            log_level = settings.observability.log_level.value
    except Exception:
        # Fallback if settings not available
        log_level = log_level or "INFO"

    # Setup comprehensive logging
    setup_comprehensive_logging(
        level=log_level,
        log_format=log_format,
        log_file=None,  # Can be configured via logging_utils directly if needed
        service_name="megaagent-pro",
    )

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langsmith").setLevel(logging.WARNING)

    # Agent-specific loggers - set to DEBUG in development, INFO in production
    agent_log_level = logging.DEBUG if log_level == "DEBUG" else logging.INFO
    for agent_name in ["mega_agent", "case_agent", "writer_agent", "supervisor_agent"]:
        logger = logging.getLogger(f"core.groupagents.{agent_name}")
        logger.setLevel(agent_log_level)


class StructuredLogger:
    """Helper for structured logging with context.

    This provides a simple interface to structlog while maintaining
    compatibility with the standard logging module.

    Example:
        >>> logger = StructuredLogger("core.groupagents.case_agent")
        >>> logger.info("Case created", user_id="123", case_id="456")
        >>> logger.error("Case creation failed", user_id="123", error="Invalid data")
    """

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (typically module path like "core.groupagents.case_agent")
        """
        self.name = name
        self.stdlib_logger = logging.getLogger(name)

        # Get structlog logger if available
        if COMPREHENSIVE_LOGGING_AVAILABLE:
            self.structlog_logger = get_structlog_logger(name)
        else:
            self.structlog_logger = self.stdlib_logger

    def log(self, level: str, message: str, **context: Any) -> None:
        """Log with structured context.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.log("info", "Operation completed", duration_ms=45, user_id="123")
        """
        # Format context as key=value pairs
        if context:
            context_str = " | " + " | ".join(f"{k}={v}" for k, v in context.items())
            full_message = message + context_str
        else:
            full_message = message

        # Use structlog if available, otherwise stdlib
        log_func = getattr(self.structlog_logger, level.lower())
        if COMPREHENSIVE_LOGGING_AVAILABLE:
            log_func(message, **context)
        else:
            log_func(full_message)

    def info(self, message: str, **context: Any) -> None:
        """Log info message with context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        self.log("info", message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message with context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        self.log("warning", message, **context)

    def error(self, message: str, **context: Any) -> None:
        """Log error message with context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        self.log("error", message, **context)

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message with context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        self.log("debug", message, **context)

    def critical(self, message: str, **context: Any) -> None:
        """Log critical message with context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        self.log("critical", message, **context)

    def exception(self, message: str, **context: Any) -> None:
        """Log exception with traceback and context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        # Format context as key=value pairs
        if context:
            context_str = " | " + " | ".join(f"{k}={v}" for k, v in context.items())
            full_message = message + context_str
        else:
            full_message = message

        # Use structlog if available, otherwise stdlib
        if COMPREHENSIVE_LOGGING_AVAILABLE:
            self.structlog_logger.exception(message, **context)
        else:
            self.stdlib_logger.exception(full_message)
