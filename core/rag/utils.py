"""Utility helpers for the RAG subsystem."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np


def tokenize(text: str) -> list[str]:
    """Lower-case whitespace tokenization with simple punctuation stripping."""
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower())
    return [token for token in cleaned.split() if token]


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two dense vectors."""
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    if not a.size or not b.size:
        return 0.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def deduplicate_ordered(items: Iterable[str]) -> list[str]:
    """Return the input items with duplicates removed, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp value to the inclusive [minimum, maximum] range."""
    return max(minimum, min(maximum, value))


__all__ = ["clamp", "cosine_similarity", "deduplicate_ordered", "tokenize"]
