"""Log Aggregation and Structured Logging.

This module provides structured logging with support for multiple outputs:
- Console (for development)
- JSON files (for log aggregation systems like ELK, Loki)
- Syslog (for centralized logging)

Integrates with distributed tracing to include trace IDs in logs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .distributed_tracing import get_trace_context


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        trace_ctx = get_trace_context()
        if trace_ctx:
            log_data["trace_id"] = trace_ctx.get("trace_id")
            log_data["span_id"] = trace_ctx.get("span_id")

        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class LogAggregator:
    """
    Central log aggregation manager.

    Features:
    - Structured JSON logging
    - Multiple output handlers (console, file, syslog)
    - Trace context integration
    - Custom fields and metadata
    - Log rotation

    Example:
        >>> aggregator = LogAggregator()
        >>> logger = aggregator.get_logger("my_module")
        >>> logger.info("User logged in", extra={"user_id": "123"})
    """

    def __init__(
        self,
        service_name: str = "megaagent-pro",
        log_level: str = "INFO",
        console_output: bool = True,
        file_output: bool = True,
        json_format: bool = True,
        log_dir: str | Path = "logs",
    ):
        """
        Initialize log aggregator.

        Args:
            service_name: Service name for log tagging
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Enable console output
            file_output: Enable file output
            json_format: Use JSON formatting (vs plain text)
            log_dir: Directory for log files
        """
        self.service_name = service_name
        self.log_level = getattr(logging, log_level.upper())
        self.console_output = console_output
        self.file_output = file_output
        self.json_format = json_format
        self.log_dir = Path(log_dir)

        # Create log directory
        if self.file_output:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        self._configure_root_logger()

    def _configure_root_logger(self) -> None:
        """Configure the root logger with handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Remove existing handlers
        root_logger.handlers.clear()

        # Add handlers
        if self.console_output:
            self._add_console_handler(root_logger)

        if self.file_output:
            self._add_file_handler(root_logger)

    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Add console handler to logger."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.log_level)

        if self.json_format:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def _add_file_handler(self, logger: logging.Logger) -> None:
        """Add file handler to logger with rotation."""
        from logging.handlers import RotatingFileHandler

        # Main log file
        log_file = self.log_dir / f"{self.service_name}.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            delay=True,
        )
        handler.setLevel(self.log_level)

        if self.json_format:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Error log file (separate file for errors)
        error_log_file = self.log_dir / f"{self.service_name}.error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            delay=True,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    def _close_file_handlers(self) -> None:
        """Close and detach file handlers (helps on Windows temp dirs)."""
        from logging.handlers import RotatingFileHandler

        root_logger = logging.getLogger()
        to_remove = []
        for h in root_logger.handlers:
            if isinstance(h, RotatingFileHandler):
                try:
                    h.flush()
                except Exception:
                    pass
                try:
                    h.close()
                except Exception:
                    pass
                to_remove.append(h)
        for h in to_remove:
            try:
                root_logger.removeHandler(h)
            except Exception:
                pass

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (typically module name)

        Returns:
            Configured logger instance

        Example:
            >>> aggregator = LogAggregator()
            >>> logger = aggregator.get_logger(__name__)
            >>> logger.info("Processing request")
        """
        return logging.getLogger(name)

    def log_with_context(
        self,
        logger: logging.Logger,
        level: str,
        message: str,
        **extra_fields: Any,
    ) -> None:
        """
        Log with additional context fields.

        Args:
            logger: Logger instance
            level: Log level (info, warning, error, etc.)
            message: Log message
            **extra_fields: Additional structured fields

        Example:
            >>> logger = aggregator.get_logger(__name__)
            >>> aggregator.log_with_context(
            ...     logger, "info", "User action",
            ...     user_id="123", action="login", ip="192.168.1.1"
            ... )
        """
        log_func = getattr(logger, level.lower())
        extra_fields["service"] = self.service_name

        # Create LogRecord with extra fields
        log_func(message, extra={"extra_fields": extra_fields})
        # Proactively close file handlers to release temp files (Windows)
        if self.file_output:
            self._close_file_handlers()

    def log_workflow_event(
        self,
        logger: logging.Logger,
        workflow_name: str,
        event_type: str,
        **details: Any,
    ) -> None:
        """
        Log a workflow event with standard structure.

        Args:
            logger: Logger instance
            workflow_name: Name of the workflow
            event_type: Event type (start, complete, error, etc.)
            **details: Additional event details

        Example:
            >>> logger = aggregator.get_logger(__name__)
            >>> aggregator.log_workflow_event(
            ...     logger, "research_workflow", "start",
            ...     query="What is AI?", user_id="123"
            ... )
        """
        self.log_with_context(
            logger,
            "info",
            f"Workflow event: {workflow_name} - {event_type}",
            workflow_name=workflow_name,
            event_type=event_type,
            **details,
        )
        if self.file_output:
            self._close_file_handlers()

    def log_llm_request(
        self,
        logger: logging.Logger,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        **metadata: Any,
    ) -> None:
        """
        Log an LLM request with metrics.

        Args:
            logger: Logger instance
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            latency_ms: Request latency in milliseconds
            **metadata: Additional metadata

        Example:
            >>> logger = aggregator.get_logger(__name__)
            >>> aggregator.log_llm_request(
            ...     logger, "claude-3-opus", 150, 300, 1200.5,
            ...     temperature=0.7, cached=False
            ... )
        """
        self.log_with_context(
            logger,
            "info",
            f"LLM request to {model}",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            **metadata,
        )
        if self.file_output:
            self._close_file_handlers()

    def log_cache_operation(
        self,
        logger: logging.Logger,
        operation: str,
        hit: bool,
        latency_ms: float,
        **metadata: Any,
    ) -> None:
        """
        Log a cache operation.

        Args:
            logger: Logger instance
            operation: Operation type (get, set, delete)
            hit: Whether operation was a cache hit
            latency_ms: Operation latency
            **metadata: Additional metadata

        Example:
            >>> logger = aggregator.get_logger(__name__)
            >>> aggregator.log_cache_operation(
            ...     logger, "get", True, 2.5,
            ...     key="user:123", semantic=False
            ... )
        """
        self.log_with_context(
            logger,
            "debug",
            f"Cache {operation}: {'hit' if hit else 'miss'}",
            operation=operation,
            hit=hit,
            latency_ms=latency_ms,
            **metadata,
        )


# Global singleton
_log_aggregator: LogAggregator | None = None


def init_logging(
    service_name: str = "megaagent-pro",
    log_level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
    json_format: bool = True,
    log_dir: str | Path = "logs",
) -> LogAggregator:
    """
    Initialize global log aggregator.

    Args:
        service_name: Service name
        log_level: Minimum log level
        console_output: Enable console output
        file_output: Enable file output
        json_format: Use JSON formatting
        log_dir: Log directory

    Returns:
        Configured LogAggregator instance

    Example:
        >>> init_logging(log_level="DEBUG", console_output=True)
    """
    global _log_aggregator

    _log_aggregator = LogAggregator(
        service_name=service_name,
        log_level=log_level,
        console_output=console_output,
        file_output=file_output,
        json_format=json_format,
        log_dir=log_dir,
    )

    return _log_aggregator


def init_logging_from_env() -> LogAggregator:
    """Initialize logging using environment variables."""

    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.lower() in {"1", "true", "yes", "on"}

    return init_logging(
        service_name=os.getenv("LOG_SERVICE_NAME", "megaagent-pro"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        console_output=_env_bool("LOG_CONSOLE_OUTPUT", True),
        file_output=_env_bool("LOG_FILE_OUTPUT", True),
        json_format=_env_bool("LOG_JSON_FORMAT", True),
        log_dir=os.getenv("LOG_DIR", "logs"),
    )


def get_log_aggregator() -> LogAggregator:
    """
    Get global log aggregator instance.

    Returns:
        LogAggregator instance. Initializes with defaults if not already initialized.

    Example:
        >>> aggregator = get_log_aggregator()
        >>> logger = aggregator.get_logger(__name__)
    """
    global _log_aggregator

    if _log_aggregator is None:
        _log_aggregator = init_logging()

    return _log_aggregator


def structured_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for a module.

    Args:
        name: Module name (use __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = structured_logger(__name__)
        >>> logger.info("Processing request", extra={"user_id": "123"})
    """
    aggregator = get_log_aggregator()
    return aggregator.get_logger(name)
