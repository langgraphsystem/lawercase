from __future__ import annotations


def renumber(items: list[str]) -> list[str]:  # scaffold
    return [f"{i+1}. {x}" for i, x in enumerate(items)]
