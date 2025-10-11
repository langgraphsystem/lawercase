from __future__ import annotations

import pytest

from core.llm.router import LLMProvider
from core.llm_interface.intelligent_router import IntelligentRouter, LLMRequest
from core.optimization.cost_optimizer import CostOptimizer, CostTracker


class FakeMultiLevelCache:
    def __init__(self) -> None:
        self.storage: dict[tuple, dict[str, str]] = {}
        self.l0_hits = 0
        self.misses = 0

    def _key(self, prompt: str, model: str, temperature: float, metadata: dict[str, str]) -> tuple:
        return (prompt, model, round(temperature, 2), tuple(sorted(metadata.items())))

    async def get(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float = 0.0,
        metadata: dict[str, str] | None = None,
        use_semantic: bool = True,
    ):
        metadata = metadata or {}
        key = self._key(prompt, model, temperature, metadata)
        if key in self.storage:
            self.l0_hits += 1
            return self.storage[key]
        self.misses += 1
        return None

    async def set(
        self,
        prompt: str,
        response: dict[str, str],
        *,
        model: str,
        temperature: float = 0.0,
        metadata: dict[str, str] | None = None,
        ttl: int | None = None,
    ):
        metadata = metadata or {}
        self.storage[self._key(prompt, model, temperature, metadata)] = response

    def get_stats(self) -> dict[str, float]:
        total = self.l0_hits + self.misses
        return {
            "l0_hits": self.l0_hits,
            "l1_hits": 0,
            "misses": self.misses - self.l0_hits,
            "total": total,
            "hit_rate": self.l0_hits / total if total else 0.0,
        }


@pytest.mark.asyncio
async def test_intelligent_router_caching_and_cost_tracking():
    providers = [
        LLMProvider("claude-3-haiku", cost_per_token=0.00025),
        LLMProvider("claude-3-sonnet", cost_per_token=0.003),
    ]
    cache = FakeMultiLevelCache()
    tracker = CostTracker()
    optimizer = CostOptimizer(tracker, enable_auto_optimization=False)

    router = IntelligentRouter(
        providers,
        multi_level_cache=cache,  # type: ignore[arg-type]
        cost_tracker=tracker,
        cost_optimizer=optimizer,
        initial_budget=50.0,
    )

    request = LLMRequest(prompt="Explain contract law basics", task_complexity="medium")

    first_response = await router.acomplete(request)
    assert first_response["cached"] is False
    assert first_response["selected_model"] in {"claude-3-haiku", "claude-3-sonnet"}
    assert len(tracker.records) == 1

    second_response = await router.acomplete(request)
    assert second_response["cached"] is True
    assert second_response["cache_layer"] == "multi-level"
    assert len(tracker.records) == 2
    assert second_response["response"].startswith("Response from")
