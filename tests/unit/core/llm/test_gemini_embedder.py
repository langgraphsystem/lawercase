from __future__ import annotations

import types

import pytest

from core.llm.gemini_embedder import GeminiEmbedder


class _StubGenAI:
    def __init__(self, response):
        self._response = response
        self.configured_api_key = None

    def configure(self, api_key=None):
        self.configured_api_key = api_key

    def embed_content(self, **kwargs):
        return self._response


@pytest.mark.asyncio
async def test_batch_embeddings_dict_values(monkeypatch):
    response = {
        "embeddings": [
            {"values": [0.1, 0.2, 0.3]},
            {"values": [0.4, 0.5, 0.6]},
        ]
    }
    stub = _StubGenAI(response)
    mod = types.SimpleNamespace(embed_content=stub.embed_content, configure=stub.configure)
    monkeypatch.setitem(__import__("sys").modules, "google.generativeai", mod)

    e = GeminiEmbedder(api_key="k", model="gemini-embedding-001")
    out = await e.aembed(["a", "b"])
    assert len(out) == 2
    assert out[0] == [0.1, 0.2, 0.3]
    assert e.embedding_dim in (0, 3072) or e.embedding_dim == 3


@pytest.mark.asyncio
async def test_single_text_fallback_list(monkeypatch):
    # Force batch to raise, so per-text fallback is used
    class _StubFailFirst(_StubGenAI):
        def embed_content(self, **kwargs):
            if isinstance(kwargs.get("content"), list):
                raise RuntimeError("batch not supported")
            return {"embedding": {"values": [1.0, 2.0]}}

    stub = _StubFailFirst(None)
    mod = types.SimpleNamespace(embed_content=stub.embed_content, configure=stub.configure)
    monkeypatch.setitem(__import__("sys").modules, "google.generativeai", mod)

    e = GeminiEmbedder(api_key="k", model="gemini-embedding-001")
    out = await e.aembed(["x"])
    assert out == [[1.0, 2.0]]


@pytest.mark.asyncio
async def test_missing_lib_returns_empty(monkeypatch):
    # Ensure import fails
    if "google.generativeai" in __import__("sys").modules:
        del __import__("sys").modules["google.generativeai"]
    e = GeminiEmbedder(api_key="k", model="gemini-embedding-001")
    out = await e.aembed(["a", "b"])
    assert out == [[], []]
