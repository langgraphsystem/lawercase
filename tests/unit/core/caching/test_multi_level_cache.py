from __future__ import annotations

import pytest

from core.caching.multi_level_cache import MultiLevelCache


class StubLLMCache:
    def __init__(self) -> None:
        self._store: dict[tuple, dict[str, str]] = {}

    def _key(self, prompt: str, model: str, temperature: float, metadata: dict[str, str]) -> tuple:
        return (prompt, model, round(temperature, 2), tuple(sorted(metadata.items())))

    async def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        use_semantic: bool = True,
        **metadata: str,
    ) -> dict[str, str] | None:
        return self._store.get(self._key(prompt, model, temperature, metadata))

    async def set(
        self,
        prompt: str,
        response: dict[str, str],
        model: str,
        temperature: float = 0.0,
        ttl: int | None = None,
        **metadata: str,
    ) -> None:
        self._store[self._key(prompt, model, temperature, metadata)] = response

    async def delete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        **metadata: str,
    ) -> bool:
        return self._store.pop(self._key(prompt, model, temperature, metadata), None) is not None

    async def clear(self) -> None:
        self._store.clear()


@pytest.mark.asyncio
async def test_multi_level_cache_local_hits():
    cache = MultiLevelCache(llm_cache=StubLLMCache(), local_ttl=2.0, local_max_entries=16)

    prompt = "What is contract law?"
    response = {"content": "Contract law governs agreements.", "model": "claude-3-haiku"}

    await cache.set(prompt, response, model="claude-3-haiku")

    # First access -> underlying LLM cache
    result1 = await cache.get(prompt, model="claude-3-haiku")
    assert result1["content"].startswith("Contract law")

    # Second access -> local hit
    result2 = await cache.get(prompt, model="claude-3-haiku")
    assert result2 is result1

    stats = cache.get_stats()
    assert stats["l0_hits"] == 1
    assert stats["l1_hits"] == 1
    assert stats["misses"] == 0

    deleted = await cache.delete(prompt, model="claude-3-haiku")
    assert deleted

