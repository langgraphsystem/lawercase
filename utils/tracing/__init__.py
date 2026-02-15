"""Tracing Package.

Provides distributed tracing capabilities:
- Tracer: Main tracing interface
- LLMTracer: LLM-specific instrumentation
- SpanExporter: Export to various backends

Usage:
    from utils.tracing import get_tracer, trace

    # Use decorator
    @trace("my_operation")
    async def my_function():
        pass

    # Use context manager
    tracer = get_tracer()
    async with tracer.async_span("operation") as span:
        span.set_attribute("key", "value")
"""

from __future__ import annotations

from .distributed_tracing import (
    ConsoleExporter,
    JaegerExporter,
    LLMTracer,
    OTLPExporter,
    Span,
    SpanContext,
    SpanExporter,
    SpanKind,
    SpanStatus,
    Tracer,
    get_tracer,
    set_tracer,
    trace,
)

__all__ = [
    "ConsoleExporter",
    "JaegerExporter",
    "LLMTracer",
    "OTLPExporter",
    "Span",
    "SpanContext",
    "SpanExporter",
    "SpanKind",
    "SpanStatus",
    "Tracer",
    "get_tracer",
    "set_tracer",
    "trace",
]
