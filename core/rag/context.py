"""Context building helpers for retrieved RAG chunks."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .utils import deduplicate_ordered, tokenize

if TYPE_CHECKING:
    from .hybrid import ScoredChunk

# Try to use accurate token counting from context module
try:
    from core.context import count_tokens

    _ACCURATE_TOKENS = True
except ImportError:
    _ACCURATE_TOKENS = False


@dataclass(slots=True)
class ContextFragment:
    """Serializable structure describing an individual context fragment."""

    chunk_id: str
    doc_id: str
    text: str
    score: float


class ContextBuilder:
    """Aggregate retrieved chunks into a bounded textual context.

    Uses accurate token counting from context module when available,
    falls back to approximate estimation otherwise.
    """

    def __init__(
        self,
        *,
        separator: str = "\n\n",
        approximate_token_size: int = 4,
        use_accurate_tokens: bool = True,
    ) -> None:
        self.separator = separator
        self.approximate_token_size = approximate_token_size
        self.use_accurate_tokens = use_accurate_tokens and _ACCURATE_TOKENS

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses tiktoken-based counting when available for accuracy.
        """
        if self.use_accurate_tokens:
            return count_tokens(text)
        return max(1, len(tokenize(text)) // max(1, self.approximate_token_size))

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
            fragment_tokens = self._estimate_tokens(scored.chunk.text)
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
