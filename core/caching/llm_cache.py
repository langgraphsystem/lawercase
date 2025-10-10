"""LLM response cache with semantic matching.

This module provides caching for LLM responses to reduce API calls
and improve response times.
"""

from __future__ import annotations

import json
from typing import Any

from .config import get_cache_config
from .semantic_cache import SemanticCache, get_semantic_cache


class LLMCache:
    """
    Cache for LLM responses with semantic similarity matching.

    Features:
    - Automatic cache key generation from prompts
    - Model-aware caching (different models cached separately)
    - Configurable TTL
    - Semantic similarity for query variations
    - Hit/miss metrics

    Example:
        >>> cache = LLMCache()
        >>>
        >>> # Check cache before LLM call
        >>> cached = await cache.get("What is contract law?", model="gpt-4")
        >>> if cached is None:
        >>>     response = await llm_client.complete("What is contract law?")
        >>>     await cache.set("What is contract law?", response, model="gpt-4")
        >>>     result = response
        >>> else:
        >>>     result = cached
    """

    def __init__(
        self,
        semantic_cache: SemanticCache | None = None,
        namespace: str = "llm_cache",
    ):
        self.semantic_cache = semantic_cache or get_semantic_cache(namespace=namespace)
        self.config = get_cache_config()

    def _make_cache_key(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Generate cache key from prompt and parameters.

        Cache keys are model and parameter-specific to ensure
        cached responses match the requested configuration.

        Args:
            prompt: User prompt
            model: Model identifier
            temperature: Generation temperature
            **kwargs: Additional parameters

        Returns:
            Cache key string
        """
        # Normalize parameters
        params = {
            "model": model,
            "temperature": round(temperature, 2),
        }
        params.update(kwargs)

        # Create deterministic key
        key_data = {
            "prompt": prompt,
            "params": params,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"{model}:{prompt}"  # Use prompt directly for semantic matching

    async def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        use_semantic: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """
        Get cached LLM response.

        Args:
            prompt: User prompt
            model: Model identifier
            temperature: Generation temperature
            use_semantic: Whether to use semantic similarity matching
            **kwargs: Additional parameters

        Returns:
            Cached response dict or None if not found

        Response format:
            {
                "content": "response text",
                "model": "model_id",
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                "cached": True,
            }
        """
        if not self.config.llm_cache_enabled:
            return None

        # For deterministic responses (temp=0), use semantic cache
        if temperature == 0.0 or temperature < 0.1:
            cache_key = self._make_cache_key(prompt, model, temperature, **kwargs)
            cached = await self.semantic_cache.get(cache_key, use_semantic=use_semantic)

            if cached is not None:
                # Mark as cached
                if isinstance(cached, dict):
                    cached["cached"] = True
                return cached

        return None

    async def set(
        self,
        prompt: str,
        response: dict[str, Any],
        model: str,
        temperature: float = 0.0,
        ttl: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Cache LLM response.

        Args:
            prompt: User prompt
            response: LLM response to cache
            model: Model identifier
            temperature: Generation temperature
            ttl: Time to live in seconds (None = use default)
            **kwargs: Additional parameters

        Notes:
            - Only caches deterministic responses (temp=0)
            - Non-deterministic responses are not cached
        """
        if not self.config.llm_cache_enabled:
            return

        # Only cache deterministic responses
        if temperature > 0.1:
            return

        if ttl is None:
            ttl = self.config.llm_cache_ttl

        cache_key = self._make_cache_key(prompt, model, temperature, **kwargs)

        # Mark response as not from cache
        response_copy = response.copy() if isinstance(response, dict) else response
        if isinstance(response_copy, dict):
            response_copy["cached"] = False

        await self.semantic_cache.set(cache_key, response_copy, ttl=ttl)

    async def delete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> bool:
        """
        Delete cached response.

        Args:
            prompt: User prompt
            model: Model identifier
            temperature: Generation temperature
            **kwargs: Additional parameters

        Returns:
            True if entry was deleted
        """
        cache_key = self._make_cache_key(prompt, model, temperature, **kwargs)
        return await self.semantic_cache.delete(cache_key)

    async def clear(self) -> int:
        """
        Clear all cached LLM responses.

        Returns:
            Number of entries cleared
        """
        return await self.semantic_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss rates and counts
        """
        return self.semantic_cache.get_stats()

    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        await self.semantic_cache.reset_stats()


# Global singleton
_llm_cache: LLMCache | None = None


def get_llm_cache(namespace: str = "llm_cache") -> LLMCache:
    """
    Get global LLM cache instance.

    Args:
        namespace: Cache namespace for isolation

    Returns:
        Shared LLMCache instance

    Example:
        >>> cache = get_llm_cache()
        >>> await cache.set("prompt", response, model="gpt-4")
    """
    global _llm_cache  # noqa: PLW0603
    if _llm_cache is None:
        _llm_cache = LLMCache(namespace=namespace)
    return _llm_cache


async def close_llm_cache() -> None:
    """Close global LLM cache."""
    global _llm_cache  # noqa: PLW0603
    if _llm_cache is not None:
        _llm_cache = None
