"""Cached LLM router with semantic cache integration.

This module extends the LLMRouter with caching capabilities to reduce
API calls and improve response times.
"""

from __future__ import annotations

from typing import Any

from ..caching.llm_cache import LLMCache, get_llm_cache
from .router import LLMProvider, LLMRouter


class CachedLLMRouter(LLMRouter):
    """
    LLM router with automatic response caching.

    Features:
    - Transparent caching layer
    - Semantic similarity matching for query variations
    - Budget savings from cache hits
    - Cache statistics tracking

    Example:
        >>> providers = [
        >>>     LLMProvider("gpt-4", cost_per_token=0.03),
        >>>     LLMProvider("claude-3", cost_per_token=0.015),
        >>> ]
        >>> router = CachedLLMRouter(providers, initial_budget=10.0)
        >>>
        >>> # First call - cache miss
        >>> result1 = await router.ainvoke("What is contract law?")
        >>> print(result1["cached"])  # False
        >>>
        >>> # Second call - cache hit
        >>> result2 = await router.ainvoke("Explain contract law")  # Similar query
        >>> print(result2["cached"])  # True
        >>> print(result2["cost"])  # 0.0 - no API call made
    """

    def __init__(
        self,
        providers: list[LLMProvider],
        initial_budget: float = 1.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        cache: LLMCache | None = None,
        use_cache: bool = True,
        use_semantic_cache: bool = True,
    ):
        """
        Initialize cached router.

        Args:
            providers: List of LLM providers
            initial_budget: Initial budget in dollars
            max_retries: Max retry attempts per provider
            backoff_factor: Exponential backoff factor
            cache: LLMCache instance (creates default if None)
            use_cache: Whether to enable caching
            use_semantic_cache: Whether to use semantic similarity matching
        """
        super().__init__(providers, initial_budget, max_retries, backoff_factor)
        self.cache = cache or get_llm_cache()
        self.use_cache = use_cache
        self.use_semantic_cache = use_semantic_cache

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._budget_saved = 0.0

    async def ainvoke(
        self,
        prompt: str,
        temperature: float = 0.0,
        bypass_cache: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Invoke LLM with automatic caching.

        Args:
            prompt: User prompt
            temperature: Generation temperature (0.0 = deterministic)
            bypass_cache: Skip cache lookup if True
            **kwargs: Additional parameters passed to providers

        Returns:
            Response dict with fields:
                - provider: Provider name (or "cache" if cached)
                - response: Response text
                - tokens_used: Token count (0 if cached)
                - cost: Cost in dollars (0 if cached)
                - cached: Whether response came from cache

        Process:
            1. Check cache (if enabled and temp=0)
            2. If cache hit, return cached response
            3. If cache miss, call LLM provider
            4. Cache response for future use
        """
        # Try cache first (only for deterministic queries)
        if self.use_cache and not bypass_cache and temperature < 0.1 and self.providers:
            # Use first provider's name as model identifier
            model = self.providers[0].name

            cached_result = await self.cache.get(
                prompt=prompt,
                model=model,
                temperature=temperature,
                use_semantic=self.use_semantic_cache,
                **kwargs,
            )

            if cached_result is not None:
                self._cache_hits += 1

                # Convert cached format to router format
                result = {
                    "provider": "cache",
                    "response": cached_result.get("content", cached_result.get("text", "")),
                    "tokens_used": 0,
                    "cost": 0.0,
                    "cached": True,
                }

                # Calculate savings
                if "tokens_used" in cached_result:
                    saved_tokens = cached_result["tokens_used"]
                    saved_cost = saved_tokens * self.providers[0].cost_per_token
                    self._budget_saved += saved_cost

                return result

        # Cache miss - call LLM
        self._cache_misses += 1

        try:
            result = await super().ainvoke(prompt)

            # Cache the result (only for deterministic queries)
            if self.use_cache and temperature < 0.1 and self.providers:
                model = result.get("provider", self.providers[0].name)

                cached_response = {
                    "content": result["response"],
                    "text": result["response"],
                    "model": model,
                    "tokens_used": result["tokens_used"],
                    "cached": False,
                }

                await self.cache.set(
                    prompt=prompt,
                    response=cached_response,
                    model=model,
                    temperature=temperature,
                    **kwargs,
                )

            result["cached"] = False
            return result

        except Exception as e:
            # Don't cache errors
            raise e

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache metrics:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - hit_rate: Cache hit rate (0-1)
                - budget_saved: Total budget saved from cache hits
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate": hit_rate,
            "budget_saved": self._budget_saved,
        }

    async def clear_cache(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of entries cleared
        """
        return await self.cache.clear()

    async def reset_cache_stats(self) -> None:
        """Reset cache statistics."""
        self._cache_hits = 0
        self._cache_misses = 0
        self._budget_saved = 0.0
        await self.cache.reset_stats()


def create_cached_router(
    providers: list[LLMProvider],
    initial_budget: float = 1.0,
    max_retries: int = 3,
    use_cache: bool = True,
) -> CachedLLMRouter:
    """
    Factory function to create a cached LLM router.

    Args:
        providers: List of LLM providers
        initial_budget: Initial budget in dollars
        max_retries: Max retry attempts per provider
        use_cache: Whether to enable caching

    Returns:
        CachedLLMRouter instance

    Example:
        >>> from core.llm.router import LLMProvider
        >>> from core.llm.cached_router import create_cached_router
        >>>
        >>> providers = [
        >>>     LLMProvider("gpt-4", cost_per_token=0.03),
        >>>     LLMProvider("claude-3", cost_per_token=0.015),
        >>> ]
        >>>
        >>> router = create_cached_router(providers, initial_budget=10.0)
        >>> result = await router.ainvoke("What is immigration law?")
    """
    return CachedLLMRouter(
        providers=providers,
        initial_budget=initial_budget,
        max_retries=max_retries,
        use_cache=use_cache,
    )
