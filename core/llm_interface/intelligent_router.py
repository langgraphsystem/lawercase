from __future__ import annotations

"""Intelligent LLM router that combines caching and cost-aware selection."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..caching.llm_cache import LLMCache, get_llm_cache
from ..caching.multi_level_cache import MultiLevelCache
from ..llm.cached_router import CachedLLMRouter
from ..llm.router import LLMProvider
from ..optimization.cost_optimizer import (CostOptimizer, CostTracker,
                                           get_cost_optimizer,
                                           get_cost_tracker)


@dataclass(slots=True)
class LLMRequest:
    """Container describing an LLM generation request."""

    prompt: str
    temperature: float = 0.0
    task_complexity: str = "medium"
    required_quality: float = 0.85
    max_cost_usd: float | None = None
    max_latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IntelligentRouter:
    """Glue together caching, routing, and cost optimisation."""

    def __init__(
        self,
        providers: Sequence[LLMProvider],
        *,
        multi_level_cache: MultiLevelCache | None = None,
        llm_cache: LLMCache | None = None,
        cost_tracker: CostTracker | None = None,
        cost_optimizer: CostOptimizer | None = None,
        initial_budget: float = 20.0,
    ) -> None:
        if not providers:
            raise ValueError("IntelligentRouter requires at least one provider")

        self.providers: list[LLMProvider] = list(providers)
        self.provider_index = {provider.name: provider for provider in self.providers}

        self.multi_level_cache = multi_level_cache or MultiLevelCache(
            namespace="intelligent_router"
        )

        cache_candidate: LLMCache | None = llm_cache
        if cache_candidate is None and isinstance(self.multi_level_cache, MultiLevelCache):
            cache_candidate = self.multi_level_cache.llm_cache
        if cache_candidate is None:
            cache_candidate = getattr(self.multi_level_cache, "llm_cache", None)
        if cache_candidate is None:
            cache_candidate = get_llm_cache(namespace="intelligent_router")
        self.llm_cache = cache_candidate
        self.cost_tracker = cost_tracker or get_cost_tracker()
        self.cost_optimizer = cost_optimizer or get_cost_optimizer()

        # Use a dedicated cached router internally. We keep caching enabled so
        # the deeper layers stay in sync, while the multi-level cache adds a
        # short-lived in-process layer.
        self.router = CachedLLMRouter(
            list(self.providers),
            initial_budget=initial_budget,
            cache=self.llm_cache,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def acomplete(self, request: LLMRequest) -> dict[str, Any]:
        """Generate an LLM response honouring cache and cost constraints."""

        preferred_model = self._select_model(request)

        cached = await self.multi_level_cache.get(
            request.prompt,
            model=preferred_model,
            temperature=request.temperature,
            metadata=request.metadata,
            use_semantic=True,
        )
        if cached is not None:
            response_text = cached.get("content") or cached.get("text") or ""
            output_tokens = len(response_text.split())
            input_tokens = len(request.prompt.split())
            self.cost_tracker.record_operation(
                model=preferred_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=0.0,
                cached=True,
                request_temperature=request.temperature,
                from_cache_layer="multi-level",
            )
            return {
                "provider": "cache",
                "model": preferred_model,
                "response": response_text,
                "tokens_used": output_tokens,
                "cost": 0.0,
                "cached": True,
                "cache_layer": "multi-level",
                "cache_stats": self.multi_level_cache.get_stats(),
            }

        # Ensure preferred provider is first for router fallback ordering.
        self._prioritise_provider(preferred_model)

        result = await self.router.ainvoke(
            request.prompt,
            temperature=request.temperature,
            **request.metadata,
        )

        # Persist in multi-level cache
        cached_payload = {
            "content": result["response"],
            "model": result.get("provider", preferred_model),
            "tokens_used": result.get("tokens_used", 0),
        }
        await self.multi_level_cache.set(
            request.prompt,
            cached_payload,
            model=preferred_model,
            temperature=request.temperature,
            metadata=request.metadata,
        )

        # Track cost metrics
        input_tokens = len(request.prompt.split())
        output_tokens = result.get("tokens_used", 0)
        cost = self.cost_tracker.record_operation(
            model=result.get("provider", preferred_model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=request.metadata.get("latency_ms", 0.0),
            cached=False,
            request_temperature=request.temperature,
        )
        result.update(
            {
                "model": result.get("provider", preferred_model),
                "cached": False,
                "cache_layer": None,
                "cost": cost,
                "selected_model": preferred_model,
            }
        )
        return result

    async def abatch(self, requests: Iterable[LLMRequest]) -> list[dict[str, Any]]:
        """Execute a batch of requests sequentially."""

        responses = []
        for request in requests:
            responses.append(await self.acomplete(request))
        return responses

    def get_cache_stats(self) -> dict[str, Any]:
        """Expose cache statistics."""

        return self.multi_level_cache.get_stats()

    def get_cost_recommendations(self) -> list[dict[str, Any]]:
        """Expose cost optimisation recommendations."""

        return self.cost_optimizer.get_recommendations()

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    def _select_model(self, request: LLMRequest) -> str:
        return self.cost_optimizer.select_model(
            task_complexity=request.task_complexity,
            required_quality=request.required_quality,
            max_cost_usd=request.max_cost_usd,
            max_latency_ms=request.max_latency_ms,
        )

    def _prioritise_provider(self, preferred: str) -> None:
        if preferred not in self.provider_index:
            return

        self.providers.sort(key=lambda provider: 0 if provider.name == preferred else 1)
        self.router.providers = list(self.providers)
