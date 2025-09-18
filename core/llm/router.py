from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional

from config.settings import RouterSettings, Settings, get_settings
from core.dto.llm_response import LLMResponse
from core.dto.route_policy import RoutePolicy
from core.dto.task_request import TaskRequest
from core.telemetry import metrics
from .providers import (
    BaseLLMProvider,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderTransientError,
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
)


class RouterExhaustedError(RuntimeError):
    """Raised when the router cannot satisfy the request."""


class LLMRouter:
    """Budget-aware LLM router with retries, telemetry, and fallbacks."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._router_settings: RouterSettings = self._settings.router_settings()
        self._provider_budgets = self._settings.provider_budgets()
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._budget_tracker: Dict[str, Dict[str, float]] = defaultdict(lambda: {"cost": 0.0, "tokens": 0.0})
        self._default_policy = RoutePolicy(provider_priority=self._router_settings.provider_priority)
        self._register_builtin_providers()

    def _register_builtin_providers(self) -> None:
        self.register_provider(OpenAIProvider(self._settings.openai_api_key))
        self.register_provider(AnthropicProvider(self._settings.anthropic_api_key))
        self.register_provider(GeminiProvider(self._settings.gemini_api_key))

    def register_provider(self, provider: BaseLLMProvider) -> None:
        if provider.requires_api_key() and not provider._api_key:
            return
        self._providers[provider.name] = provider

    async def invoke(self, task: TaskRequest, policy: Optional[RoutePolicy] = None) -> LLMResponse:
        policy = policy or task.policy or self._default_policy
        provider_order = policy.provider_priority or self._default_policy.provider_priority
        last_error: Optional[Exception] = None

        for provider_name in provider_order:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            if self._is_budget_exhausted(provider_name, policy):
                continue
            try:
                start = time.perf_counter()
                response = await self._call_with_retry(provider, task, policy)
                elapsed = (time.perf_counter() - start)
                self._update_budget(provider_name, response)
                metrics.record_llm_call(
                    provider=provider_name,
                    policy_label=policy.label or "default",
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    cost_usd=response.cost_usd or 0.0,
                    duration_seconds=elapsed,
                )
                return response
            except ProviderError as exc:  # pragma: no cover - defensive
                last_error = exc
                continue
        raise RouterExhaustedError(str(last_error) if last_error else "No providers available")

    async def _call_with_retry(self, provider: BaseLLMProvider, task: TaskRequest, policy: RoutePolicy) -> LLMResponse:
        max_retries = policy.max_retries or self._router_settings.max_retries
        timeout = policy.timeout_seconds or self._router_settings.request_timeout_seconds
        backoff = self._router_settings.initial_backoff_seconds

        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(provider.acompletion(task), timeout=timeout)
            except ProviderRateLimitError:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(self._apply_jitter(backoff))
            except (ProviderTransientError, ProviderTimeoutError):
                if attempt == max_retries:
                    raise
                await asyncio.sleep(self._apply_jitter(backoff))
            finally:
                backoff *= self._router_settings.backoff_multiplier
        raise RouterExhaustedError(f"{provider.name} exhausted retries")

    def _apply_jitter(self, base: float) -> float:
        jitter = random.uniform(0, self._router_settings.jitter_seconds)
        return base + jitter

    def _is_budget_exhausted(self, provider: str, policy: RoutePolicy) -> bool:
        budget = self._provider_budgets.get(provider)
        if not budget:
            return False
        tracker = self._budget_tracker[provider]
        if budget.max_cost_usd is not None and tracker["cost"] >= budget.max_cost_usd:
            return True
        if budget.max_tokens is not None and tracker["tokens"] >= budget.max_tokens:
            return True
        if policy.max_cost_usd is not None and tracker["cost"] >= policy.max_cost_usd:
            return True
        return False

    def _update_budget(self, provider: str, response: LLMResponse) -> None:
        tracker = self._budget_tracker[provider]
        tracker["cost"] += response.cost_usd or 0.0
        tracker["tokens"] += response.tokens_in + response.tokens_out

    @property
    def providers(self) -> List[str]:
        return sorted(self._providers.keys())
