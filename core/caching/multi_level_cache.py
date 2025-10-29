from __future__ import annotations

"""Multi-level cache facade combining local, Redis, and semantic layers.

The Phase 2 roadmap calls for an explicit multi-level caching component.
This module layers an in-process L0 cache on top of the existing Redis +
semantic cache infrastructure exposed through `LLMCache`.
"""

from collections import OrderedDict
import json
import time
from typing import Any

from .llm_cache import LLMCache, get_llm_cache


class MultiLevelCache:
    """Three-level cache tuned for LLM prompts."""

    def __init__(
        self,
        *,
        namespace: str = "multi_level_cache",
        local_ttl: float = 30.0,
        local_max_entries: int = 256,
        llm_cache: LLMCache | None = None,
    ) -> None:
        self.namespace = namespace
        self.local_ttl = local_ttl
        self.local_max_entries = local_max_entries
        self.llm_cache = llm_cache or get_llm_cache(namespace=namespace)

        # Ordered dict to maintain insertion order for simple LRU behaviour.
        self._local: OrderedDict[str, tuple[float, Any]] = OrderedDict()

        # Metrics
        self._stats = {
            "l0_hits": 0,
            "l1_hits": 0,
            "misses": 0,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _local_key(self, prompt: str, model: str, temperature: float, extra: dict[str, Any]) -> str:
        payload = {
            "prompt": prompt,
            "model": model,
            "temperature": round(temperature, 2),
            "metadata": extra or {},
        }
        return f"{self.namespace}:{json.dumps(payload, sort_keys=True)}"

    def _local_remember(self, cache_key: str, value: Any) -> None:
        expiry = time.monotonic() + self.local_ttl
        self._local[cache_key] = (expiry, value)
        self._local.move_to_end(cache_key)

        # Evict stale entries first
        self._purge_expired()
        while len(self._local) > self.local_max_entries:
            self._local.popitem(last=False)

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, (expiry, _) in self._local.items() if expiry <= now]
        for key in expired:
            self._local.pop(key, None)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def get(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float = 0.0,
        metadata: dict[str, Any] | None = None,
        use_semantic: bool = True,
    ) -> dict[str, Any] | None:
        """Retrieve cached response across all layers."""

        metadata = metadata or {}
        cache_key = self._local_key(prompt, model, temperature, metadata)

        # L0: in-process cache
        self._purge_expired()
        local_entry = self._local.get(cache_key)
        if local_entry:
            self._stats["l0_hits"] += 1
            _, value = local_entry
            self._local.move_to_end(cache_key)
            return value

        # L1/L2 handled by LLMCache (redis exact + semantic fallback)
        cached = await self.llm_cache.get(
            prompt=prompt,
            model=model,
            temperature=temperature,
            use_semantic=use_semantic,
            **metadata,
        )
        if cached is not None:
            self._stats["l1_hits"] += 1
            self._local_remember(cache_key, cached)
            return cached

        self._stats["misses"] += 1
        return None

    async def set(
        self,
        prompt: str,
        response: dict[str, Any],
        *,
        model: str,
        temperature: float = 0.0,
        metadata: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> None:
        """Store response across layers."""

        metadata = metadata or {}
        cache_key = self._local_key(prompt, model, temperature, metadata)
        self._local_remember(cache_key, response)

        await self.llm_cache.set(
            prompt=prompt,
            response=response,
            model=model,
            temperature=temperature,
            ttl=ttl,
            **metadata,
        )

    async def delete(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Invalidate cached entry across all layers."""

        metadata = metadata or {}
        cache_key = self._local_key(prompt, model, temperature, metadata)
        self._local.pop(cache_key, None)
        return await self.llm_cache.delete(
            prompt=prompt,
            model=model,
            temperature=temperature,
            **metadata,
        )

    async def warm_start(self, items: list[tuple[str, dict[str, Any], dict[str, Any]]]) -> None:
        """Pre-populate cache with known items.

        Each item is a tuple of (prompt, response, options) where options
        may include model/temperature/metadata.
        """

        for prompt, response, options in items:
            await self.set(
                prompt,
                response,
                model=options.get("model", response.get("model", "default")),
                temperature=options.get("temperature", 0.0),
                metadata=options.get("metadata"),
                ttl=options.get("ttl"),
            )

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""

        hits = self._stats["l0_hits"] + self._stats["l1_hits"]
        total = hits + self._stats["misses"]
        hit_rate = hits / total if total else 0.0
        result = dict(self._stats)
        result["total"] = total
        result["hit_rate"] = hit_rate
        return result

    async def clear(self) -> None:
        """Clear all cached values."""

        self._local.clear()
        await self.llm_cache.clear()
        for key in self._stats:
            self._stats[key] = 0
