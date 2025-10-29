"""Context building helpers for retrieved RAG chunks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .utils import deduplicate_ordered, tokenize


@dataclass(slots=True)
class ContextFragment:
    """Serializable structure describing an individual context fragment."""

    chunk_id: str
    doc_id: str
    text: str
    score: float


class ContextBuilder:
    """Aggregate retrieved chunks into a bounded textual context."""

    def __init__(self, *, separator: str = "\n\n", approximate_token_size: int = 4) -> None:
        self.separator = separator
        self.approximate_token_size = approximate_token_size

    @staticmethod
    def _estimate_tokens(text: str, *, approximate_token_size: int) -> int:
        return max(1, len(tokenize(text)) // max(1, approximate_token_size))

    def build(
        self,
        chunks: Iterable[ScoredChunk],
        *,
        max_tokens: int = 600,
    ) -> dict[str, list[ContextFragment] | str]:
        """Produce normalized context text and fragment metadata."""

        fragments: list[ContextFragment] = []
        included_chunk_ids: list[str] = []
        budget = max_tokens

        for scored in chunks:
            fragment_tokens = self._estimate_tokens(
                scored.chunk.text, approximate_token_size=self.approximate_token_size
            )
            if fragment_tokens > budget:
                break
            budget -= fragment_tokens
            fragments.append(
                ContextFragment(
                    chunk_id=scored.chunk.chunk_id,
                    doc_id=scored.chunk.doc_id,
                    text=scored.chunk.text,
                    score=scored.combined_score,
                )
            )
            included_chunk_ids.append(scored.chunk.chunk_id)

        joined = self.separator.join(fragment.text for fragment in fragments)
        unique_ids = deduplicate_ordered(included_chunk_ids)
        return {
            "text": joined,
            "fragments": fragments,
            "chunk_ids": unique_ids,
        }


__all__ = ["ContextBuilder", "ContextFragment"]
