"""Distributed Tracing with OpenTelemetry.

This module provides distributed tracing capabilities using OpenTelemetry.
It supports multiple exporters (Jaeger, Zipkin, OTLP) and integrates with
the LangGraph workflows for end-to-end tracing.
"""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
        OTLPSpanExporter
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                                ConsoleSpanExporter)

    OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    OTEL_AVAILABLE = False
    trace = None  # type: ignore


@dataclass
class TracingConfig:
    """Configuration for distributed tracing."""

    service_name: str = "megaagent-pro"
    enabled: bool = True
    exporter_type: str = "console"  # console, jaeger, zipkin, otlp
    # Jaeger settings
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    # Zipkin settings
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    # OTLP settings
    otlp_endpoint: str = "localhost:4317"
    # Sampling
    sample_rate: float = 1.0  # 0.0 to 1.0

    @classmethod
    def from_env(cls) -> TracingConfig:
        """Create config from environment variables."""
        return cls(
            service_name=os.getenv("TRACING_SERVICE_NAME", "megaagent-pro"),
            enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            exporter_type=os.getenv("TRACING_EXPORTER", "console"),
            jaeger_host=os.getenv("JAEGER_HOST", "localhost"),
            jaeger_port=int(os.getenv("JAEGER_PORT", "6831")),
            zipkin_endpoint=os.getenv("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans"),
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"),
            sample_rate=float(os.getenv("TRACING_SAMPLE_RATE", "1.0")),
        )


# Global tracer instance
_tracer: Any | None = None
_tracer_provider: TracerProvider | None = None


class _NoopSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, *args, **kwargs):
        return None

    def record_exception(self, *args, **kwargs):
        return None


class _NoopTracer:
    def start_as_current_span(self, name: str):
        return _NoopSpan()


def init_tracing(config: TracingConfig | None = None):
    """
    Initialize distributed tracing.

    Args:
        config: Tracing configuration. If None, loads from environment.

    Returns:
        Configured tracer instance

    Example:
        >>> config = TracingConfig(exporter_type="jaeger")
        >>> tracer = init_tracing(config)
    """
    global _tracer, _tracer_provider

    if not OTEL_AVAILABLE:
        _tracer = _NoopTracer()
        return _tracer

    if config is None:
        config = TracingConfig.from_env()

    if not config.enabled:
        # Return no-op tracer
        _tracer = _NoopTracer()
        return _tracer

    # Create resource
    resource = Resource(attributes={SERVICE_NAME: config.service_name})

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Configure exporter
    if config.exporter_type == "jaeger":
        exporter = JaegerExporter(
            agent_host_name=config.jaeger_host,
            agent_port=config.jaeger_port,
        )
    elif config.exporter_type == "zipkin":
        exporter = ZipkinExporter(endpoint=config.zipkin_endpoint)
    elif config.exporter_type == "otlp":
        exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
    else:  # console
        exporter = ConsoleSpanExporter()

    # Add span processor
    _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Get tracer
    _tracer = trace.get_tracer(__name__)

    return _tracer


def get_tracer() -> Any:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance. Initializes with default config if not already initialized.

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_operation"):
        ...     # do work
        ...     pass
    """
    global _tracer

    if _tracer is None:
        _tracer = init_tracing()

    return _tracer


def trace_function(name: str | None = None, attributes: dict[str, Any] | None = None):
    """
    Decorator to trace a synchronous function.

    Args:
        name: Span name. If None, uses function name.
        attributes: Additional span attributes

    Example:
        >>> @trace_function(name="process_query")
        ... def my_function(query: str):
        ...     return query.upper()
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("result.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("result.status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def trace_async(name: str | None = None, attributes: dict[str, Any] | None = None):
    """
    Decorator to trace an async function.

    Args:
        name: Span name. If None, uses function name.
        attributes: Additional span attributes

    Example:
        >>> @trace_async(name="async_query")
        ... async def my_async_function(query: str):
        ...     return await process_query(query)
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("result.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("result.status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


class TracingContext:
    """
    Context manager for creating traced operations.

    Example:
        >>> with TracingContext("database_query") as span:
        ...     span.set_attribute("query", "SELECT * FROM users")
        ...     result = execute_query()
    """

    def __init__(self, name: str, attributes: dict[str, Any] | None = None):
        """
        Initialize tracing context.

        Args:
            name: Span name
            attributes: Span attributes
        """
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self):
        """Start span."""
        tracer = get_tracer()
        self.span = tracer.start_as_current_span(self.name).__enter__()

        # Set attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End span."""
        if exc_type is not None:
            self.span.set_attribute("error.type", exc_type.__name__)
            self.span.set_attribute("error.message", str(exc_val))
            self.span.record_exception(exc_val)

        self.span.__exit__(exc_type, exc_val, exc_tb)


def trace_workflow_node(node_name: str):
    """
    Decorator specifically for LangGraph workflow nodes.

    Args:
        node_name: Name of the workflow node

    Example:
        >>> @trace_workflow_node("process_query_node")
        ... async def process_query(state: WorkflowState):
        ...     return {"result": "processed"}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"workflow.node.{node_name}") as span:
                span.set_attribute("workflow.node", node_name)
                span.set_attribute("workflow.type", "langgraph")

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("workflow.status", "completed")
                    return result
                except Exception as e:
                    span.set_attribute("workflow.status", "failed")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def add_span_event(event_name: str, attributes: dict[str, Any] | None = None) -> None:
    """
    Add an event to the current span.

    Args:
        event_name: Event name
        attributes: Event attributes

    Example:
        >>> add_span_event("cache_hit", {"key": "user:123", "ttl": 3600})
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(event_name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any) -> None:
    """
    Set attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value

    Example:
        >>> set_span_attribute("user.id", "123")
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def get_trace_context() -> dict[str, str]:
    """
    Get current trace context for propagation.

    Returns:
        Dictionary with trace context (trace_id, span_id, etc.)

    Example:
        >>> context = get_trace_context()
        >>> print(context["trace_id"])
    """
    if not OTEL_AVAILABLE or trace is None:
        return {}

    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        if ctx:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
                "trace_flags": format(ctx.trace_flags, "02x"),
            }
    return {}
