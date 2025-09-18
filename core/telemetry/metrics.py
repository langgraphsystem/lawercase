from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram  # type: ignore
except ImportError:  # pragma: no cover - fallback for local dev without prometheus_client
    class _NoOpMetric:
        def labels(self, **_kwargs):
            return self

        def observe(self, *_args, **_kwargs) -> None:
            return None

        def inc(self, *_args, **_kwargs) -> None:
            return None

    def Counter(*_args, **_kwargs):  # type: ignore
        return _NoOpMetric()

    def Histogram(*_args, **_kwargs):  # type: ignore
        return _NoOpMetric()

LLM_ROUTE_LATENCY_SECONDS = Histogram(
    "llm_route_latency_seconds",
    "LLM call latency",
    labelnames=("provider", "policy"),
)

LLM_TOKENS_IN = Counter(
    "llm_tokens_in_total",
    "Total input tokens routed",
    labelnames=("provider",),
)

LLM_TOKENS_OUT = Counter(
    "llm_tokens_out_total",
    "Total output tokens routed",
    labelnames=("provider",),
)

LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Accumulated USD cost per provider",
    labelnames=("provider",),
)

RAG_RETRIEVE_LATENCY_SECONDS = Histogram(
    "rag_retrieve_latency_seconds",
    "Hybrid retrieval latency",
    labelnames=("namespace",),
)


def record_llm_call(
    *,
    provider: str,
    policy_label: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    duration_seconds: float,
) -> None:
    LLM_ROUTE_LATENCY_SECONDS.labels(provider=provider, policy=policy_label).observe(duration_seconds)
    LLM_TOKENS_IN.labels(provider=provider).inc(tokens_in)
    LLM_TOKENS_OUT.labels(provider=provider).inc(tokens_out)
    if cost_usd:
        LLM_COST_USD.labels(provider=provider).inc(cost_usd)


def record_rag_latency(*, namespace: str, duration_seconds: float) -> None:
    RAG_RETRIEVE_LATENCY_SECONDS.labels(namespace=namespace).observe(duration_seconds)
