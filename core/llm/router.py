from __future__ import annotations

import asyncio
from typing import Any


class BudgetExhaustedError(Exception):
    """Custom exception for when the budget is exhausted."""


class LLMProvider:
    """A mockable class representing an LLM provider."""

    def __init__(self, name: str, cost_per_token: float = 0.001):
        self.name = name
        self.cost_per_token = cost_per_token

    async def ainvoke(self, prompt: str) -> dict[str, Any]:
        """Simulates an async call to the LLM provider."""
        # In a real scenario, this would make a network request.
        # For testing, we can simulate success or failure.
        if "fail" in prompt:
            raise ConnectionError(f"{self.name} API call failed")

        response_text = f"Response from {self.name} for: {prompt}"
        tokens_used = len(response_text.split())
        return {"text": response_text, "tokens_used": tokens_used}


class LLMRouter:
    """
    A router that manages calls to multiple LLM providers, with budget control,
    fallback, and retry mechanisms.
    """

    def __init__(
        self,
        providers: list[LLMProvider],
        initial_budget: float = 1.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.providers = providers
        self.budget = initial_budget
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _spend_budget(self, tokens: int, cost_per_token: float):
        """Deducts cost from the budget."""
        cost = tokens * cost_per_token
        if self.budget < cost:
            raise BudgetExhaustedError("Not enough budget for this request.")
        self.budget -= cost

    async def ainvoke(self, prompt: str) -> dict[str, Any]:
        """
        Invokes LLM providers with fallback and retry logic.
        """
        last_exception = None
        for provider in self.providers:
            for attempt in range(self.max_retries):
                try:
                    result = await provider.ainvoke(prompt)
                    tokens_used = result.get("tokens_used", 0)

                    self._spend_budget(tokens_used, provider.cost_per_token)

                    return {
                        "provider": provider.name,
                        "response": result["text"],
                        "tokens_used": tokens_used,
                        "cost": tokens_used * provider.cost_per_token,
                    }
                except ConnectionError as e:
                    last_exception = e
                    wait_time = self.backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue  # Retry with the same provider
                except BudgetExhaustedError as e:
                    # If budget is exhausted, no point in retrying or falling back.
                    raise e
                except Exception as e:
                    last_exception = e
                    break  # Break from retries and fallback to the next provider

        raise last_exception or Exception("All providers failed.")
