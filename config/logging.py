"""Structlog logging configuration helpers."""

from __future__ import annotations

import logging

import structlog

_IS_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """Configure structlog with JSON output and standard processors."""

    global _IS_CONFIGURED
    if _IS_CONFIGURED:
        return

    level_name = (level or "INFO").upper()
    try:
        log_level = getattr(logging, level_name)
    except AttributeError:  # pragma: no cover - defensive
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    _IS_CONFIGURED = True
