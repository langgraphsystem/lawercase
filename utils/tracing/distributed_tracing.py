"""Distributed Tracing for LLM Agent Systems.

Provides comprehensive tracing capabilities:
- OpenTelemetry integration
- LLM-specific spans
- Agent workflow tracing
- Performance monitoring
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
import functools
import time
from typing import Any, TypeVar
import uuid

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class SpanKind(str, Enum):
    """Types of spans."""

    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Status of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    baggage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "baggage": self.baggage,
        }


@dataclass
class Span:
    """Single tracing span."""

    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": time.perf_counter(),
                "attributes": attributes or {},
            }
        )

    def set_status(self, status: SpanStatus, description: str | None = None) -> None:
        self.status = status
        if description:
            self.attributes["status.description"] = description

    def end(self) -> None:
        self.end_time = time.perf_counter()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "context": self.context.to_dict(),
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
        }


class SpanExporter:
    """Base class for span exporters."""

    async def export(self, spans: list[Span]) -> bool:
        """Export spans to backend."""
        raise NotImplementedError


class ConsoleExporter(SpanExporter):
    """Export spans to console for development."""

    async def export(self, spans: list[Span]) -> bool:
        for span in spans:
            logger.info(
                "trace.span",
                name=span.name,
                duration_ms=span.duration_ms,
                status=span.status.value,
                attributes=span.attributes,
            )
        return True


class JaegerExporter(SpanExporter):
    """Export spans to Jaeger."""

    def __init__(self, endpoint: str = "http://localhost:14268/api/traces") -> None:
        self.endpoint = endpoint

    async def export(self, spans: list[Span]) -> bool:
        try:
            import httpx

            # Convert to Jaeger format
            jaeger_spans = [self._to_jaeger_format(span) for span in spans]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json={"spans": jaeger_spans},
                    headers={"Content-Type": "application/json"},
                )
                return response.status_code == 202

        except Exception as e:
            logger.warning("jaeger_export.failed", error=str(e))
            return False

    def _to_jaeger_format(self, span: Span) -> dict[str, Any]:
        return {
            "traceId": span.context.trace_id,
            "spanId": span.context.span_id,
            "parentSpanId": span.context.parent_span_id,
            "operationName": span.name,
            "startTime": int(span.start_time * 1_000_000),
            "duration": int((span.duration_ms or 0) * 1000),
            "tags": [
                {"key": k, "type": "string", "value": str(v)} for k, v in span.attributes.items()
            ],
            "logs": [
                {
                    "timestamp": int(e["timestamp"] * 1_000_000),
                    "fields": [
                        {"key": "event", "value": e["name"]},
                        *[{"key": k, "value": str(v)} for k, v in e["attributes"].items()],
                    ],
                }
                for e in span.events
            ],
        }


class OTLPExporter(SpanExporter):
    """Export spans using OpenTelemetry Protocol."""

    def __init__(self, endpoint: str = "http://localhost:4318/v1/traces") -> None:
        self.endpoint = endpoint

    async def export(self, spans: list[Span]) -> bool:
        try:
            import httpx

            # Convert to OTLP format
            otlp_data = self._to_otlp_format(spans)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json=otlp_data,
                    headers={"Content-Type": "application/json"},
                )
                return response.status_code in (200, 202)

        except Exception as e:
            logger.warning("otlp_export.failed", error=str(e))
            return False

    def _to_otlp_format(self, spans: list[Span]) -> dict[str, Any]:
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "mega_agent"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "mega_agent.tracer"},
                            "spans": [self._span_to_otlp(s) for s in spans],
                        }
                    ],
                }
            ]
        }

    def _span_to_otlp(self, span: Span) -> dict[str, Any]:
        return {
            "traceId": span.context.trace_id,
            "spanId": span.context.span_id,
            "parentSpanId": span.context.parent_span_id or "",
            "name": span.name,
            "kind": self._kind_to_otlp(span.kind),
            "startTimeUnixNano": int(span.start_time * 1_000_000_000),
            "endTimeUnixNano": int((span.end_time or span.start_time) * 1_000_000_000),
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}} for k, v in span.attributes.items()
            ],
            "status": {
                "code": (
                    1
                    if span.status == SpanStatus.OK
                    else 2
                    if span.status == SpanStatus.ERROR
                    else 0
                ),
            },
        }

    def _kind_to_otlp(self, kind: SpanKind) -> int:
        mapping = {
            SpanKind.INTERNAL: 1,
            SpanKind.SERVER: 2,
            SpanKind.CLIENT: 3,
            SpanKind.PRODUCER: 4,
            SpanKind.CONSUMER: 5,
        }
        return mapping.get(kind, 1)


class Tracer:
    """Distributed tracer for agent systems.

    Features:
    - Hierarchical span management
    - Automatic context propagation
    - Multiple export backends
    - LLM-specific instrumentation

    Usage:
        tracer = Tracer()

        # Context manager
        with tracer.span("my_operation") as span:
            span.set_attribute("key", "value")
            # Do work

        # Decorator
        @tracer.trace("my_function")
        async def my_function():
            pass

        # Manual spans
        span = tracer.start_span("operation")
        try:
            # Do work
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
        finally:
            span.end()
    """

    def __init__(
        self,
        service_name: str = "mega_agent",
        exporters: list[SpanExporter] | None = None,
        sample_rate: float = 1.0,
    ) -> None:
        self.service_name = service_name
        self.exporters = exporters or [ConsoleExporter()]
        self.sample_rate = sample_rate

        self._spans: list[Span] = []
        self._current_context: SpanContext | None = None
        self._context_stack: list[SpanContext] = []
        self._lock = asyncio.Lock()

        # Batch export
        self._export_interval = 10.0
        self._export_task: asyncio.Task | None = None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a new span."""
        # Create context
        trace_id = self._current_context.trace_id if self._current_context else self._new_trace_id()
        span_id = self._new_span_id()
        parent_span_id = self._current_context.span_id if self._current_context else None

        context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {},
        )

        # Set service name
        span.set_attribute("service.name", self.service_name)

        return span

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ):
        """Context manager for creating spans."""
        span = self.start_span(name, kind, attributes)

        # Push context
        old_context = self._current_context
        self._current_context = span.context

        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
        finally:
            span.end()
            self._spans.append(span)
            self._current_context = old_context

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ):
        """Async context manager for creating spans."""
        span = self.start_span(name, kind, attributes)

        old_context = self._current_context
        self._current_context = span.context

        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
        finally:
            span.end()
            self._spans.append(span)
            self._current_context = old_context

    def trace(
        self,
        name: str | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> Callable[[F], F]:
        """Decorator for tracing functions."""

        def decorator(func: F) -> F:
            span_name = name or func.__name__

            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    async with self.async_span(span_name, kind) as span:
                        span.set_attribute("function.name", func.__name__)
                        return await func(*args, **kwargs)

                return async_wrapper  # type: ignore

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.span(span_name, kind) as span:
                    span.set_attribute("function.name", func.__name__)
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

        return decorator

    async def flush(self) -> None:
        """Flush pending spans to exporters."""
        async with self._lock:
            if not self._spans:
                return

            spans_to_export = self._spans.copy()
            self._spans.clear()

        for exporter in self.exporters:
            try:
                await exporter.export(spans_to_export)
            except Exception as e:
                logger.warning("span_export.failed", exporter=type(exporter).__name__, error=str(e))

    def start_export_loop(self) -> None:
        """Start background export loop."""
        if self._export_task is not None:
            return

        async def export_loop():
            while True:
                await asyncio.sleep(self._export_interval)
                await self.flush()

        self._export_task = asyncio.create_task(export_loop())

    def stop_export_loop(self) -> None:
        """Stop background export loop."""
        if self._export_task:
            self._export_task.cancel()
            self._export_task = None

    def get_current_context(self) -> SpanContext | None:
        """Get current span context."""
        return self._current_context

    def inject_context(self, carrier: dict[str, str]) -> None:
        """Inject context into carrier for propagation."""
        if self._current_context:
            carrier["traceparent"] = (
                f"00-{self._current_context.trace_id}-" f"{self._current_context.span_id}-01"
            )
            if self._current_context.baggage:
                carrier["baggage"] = ",".join(
                    f"{k}={v}" for k, v in self._current_context.baggage.items()
                )

    def extract_context(self, carrier: dict[str, str]) -> SpanContext | None:
        """Extract context from carrier."""
        traceparent = carrier.get("traceparent")
        if not traceparent:
            return None

        parts = traceparent.split("-")
        if len(parts) != 4:
            return None

        return SpanContext(
            trace_id=parts[1],
            span_id=parts[2],
        )

    def _new_trace_id(self) -> str:
        return uuid.uuid4().hex

    def _new_span_id(self) -> str:
        return uuid.uuid4().hex[:16]


# LLM-specific tracing
class LLMTracer(Tracer):
    """Tracer with LLM-specific instrumentation."""

    @asynccontextmanager
    async def llm_span(
        self,
        operation: str,
        model: str,
        provider: str,
    ):
        """Create span for LLM operation."""
        async with self.async_span(f"llm.{operation}", SpanKind.CLIENT) as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.operation", operation)
            yield span

    def record_llm_request(
        self,
        span: Span,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> None:
        """Record LLM request details."""
        span.set_attribute("llm.prompt_length", len(prompt))
        span.set_attribute("llm.temperature", temperature)
        if max_tokens:
            span.set_attribute("llm.max_tokens", max_tokens)
        span.add_event("llm.request_sent")

    def record_llm_response(
        self,
        span: Span,
        response: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = 0.0,
    ) -> None:
        """Record LLM response details."""
        span.set_attribute("llm.response_length", len(response))
        span.set_attribute("llm.input_tokens", input_tokens)
        span.set_attribute("llm.output_tokens", output_tokens)
        span.set_attribute("llm.total_tokens", input_tokens + output_tokens)
        span.set_attribute("llm.cost_usd", cost_usd)
        span.add_event("llm.response_received")


# Global tracer instance
_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Get global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = LLMTracer()
    return _tracer


def set_tracer(tracer: Tracer) -> None:
    """Set global tracer instance."""
    global _tracer
    _tracer = tracer


# Convenience functions
def trace(name: str | None = None, kind: SpanKind = SpanKind.INTERNAL):
    """Decorator using global tracer."""
    return get_tracer().trace(name, kind)
