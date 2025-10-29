from __future__ import annotations

import pytest

from core.memory.embedders import DeterministicEmbedder


@pytest.mark.asyncio
async def test_deterministic_embedder_produces_consistent_vectors() -> None:
    embedder = DeterministicEmbedder(embedding_dim=16)
    text = "Consistency check for deterministic embedder."
    first = await embedder.aembed([text])
    second = await embedder.aembed([text])

    assert first == second
    assert len(first[0]) == 16
    assert all(0.0 <= value <= 1.0 for value in first[0])
