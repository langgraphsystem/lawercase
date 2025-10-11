"""Shared NLP utilities for legal-domain processing.

This module centralises construction of the spaCy pipeline used by the legal
tooling so that expensive model loading happens only once across the process.
The pipeline favours official spaCy components and augments them with
EntityRuler patterns tailored for legal terminology (courts, statutes, contract
types, etc.).
"""

from __future__ import annotations

import re
import threading
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache

try:  # pragma: no cover - dependency optional at runtime
    import spacy
    from spacy.language import Language
    from spacy.pipeline import EntityRuler
except ModuleNotFoundError:  # pragma: no cover - fallback implementation
    spacy = None  # type: ignore
    Language = object  # type: ignore
    EntityRuler = None  # type: ignore

_NLP_LOCK = threading.Lock()
_NLP_INSTANCE: Language | _FallbackNLP | None = None


@dataclass
class _FallbackSentence:
    text: str
    start_char: int
    end_char: int


@dataclass
class _FallbackSpan(_FallbackSentence):
    label_: str = ""


class _FallbackDoc:
    """Minimal stand-in for spaCy's Doc when spaCy is unavailable."""

    def __init__(self, text: str) -> None:
        self.text = text
        self._sentences = self._split_sentences(text)
        self.ents: list[_FallbackSpan] = []

    def _split_sentences(self, text: str) -> list[_FallbackSentence]:
        sentences: list[_FallbackSentence] = []
        offset = 0
        for part in re.split(r"(?<=[.!?])\s+", text.strip()):
            if not part:
                continue
            start = text.find(part, offset)
            end = start + len(part)
            sentences.append(_FallbackSentence(part, start, end))
            offset = end
        if not sentences:
            sentences.append(_FallbackSentence(text, 0, len(text)))
        return sentences

    @property
    def sents(self) -> Iterator[_FallbackSentence]:
        return iter(self._sentences)

    def __iter__(self) -> Iterator[_FallbackSentence]:
        return self.sents

    def __len__(self) -> int:
        return len(self.text)

    def char_span(self, start: int, end: int, label: str = "") -> _FallbackSpan | None:
        if 0 <= start < end <= len(self.text):
            return _FallbackSpan(self.text[start:end], start, end, label)
        return None


class _FallbackNLP:
    """Very small NLP pipeline used when spaCy is not installed."""

    pipe_names: tuple[str, ...] = ("sentencizer",)

    def __call__(self, text: str) -> _FallbackDoc:
        return _FallbackDoc(text)


@lru_cache(maxsize=1)
def _legal_patterns() -> list[dict[str, object]]:
    """Return EntityRuler patterns for legal terminology."""
    courts = [
        "Supreme Court",
        "District Court",
        "Court of Appeals",
        "Circuit Court",
        "Bankruptcy Court",
        "High Court",
    ]
    contract_types = [
        "Service Agreement",
        "Employment Agreement",
        "Master Services Agreement",
        "License Agreement",
        "Non-Disclosure Agreement",
        "Purchase Agreement",
        "Lease Agreement",
    ]
    statutes = [
        {
            "label": "STATUTE",
            "pattern": [
                {"TEXT": {"REGEX": r"^\d+$"}},
                {"LOWER": {"IN": ["u.s.c.", "usc"]}},
                {"TEXT": {"IN": ["§", "sec.", "section"]}},
                {"TEXT": {"REGEX": r"^[0-9A-Za-z\.-]+$"}},
            ],
        },
        {
            "label": "STATUTE",
            "pattern": [
                {"TEXT": {"REGEX": r"^\d+$"}},
                {"LOWER": "cfr"},
                {"TEXT": {"IN": ["§", "part", "section"]}},
                {"TEXT": {"REGEX": r"^[0-9A-Za-z\.-]+$"}},
            ],
        },
    ]

    patterns: list[dict[str, object]] = []
    patterns.extend({"label": "COURT", "pattern": court} for court in courts)
    patterns.extend({"label": "CONTRACT_TYPE", "pattern": contract} for contract in contract_types)
    patterns.extend(statutes)
    patterns.extend(
        {
            "label": "LEGAL_TERM",
            "pattern": phrase,
        }
        for phrase in [
            "force majeure",
            "indemnification",
            "limitation of liability",
            "governing law",
            "arbitration",
            "data processing agreement",
        ]
    )
    return patterns


def _configure_entity_ruler(nlp: Language, before: str | None = None) -> EntityRuler:
    """Create an entity ruler with legal patterns."""
    if EntityRuler is None:  # spaCy unavailable
        raise RuntimeError("EntityRuler requires spaCy to be installed.")
    ruler = nlp.add_pipe("entity_ruler", before=before)
    ruler.add_patterns(_legal_patterns())
    return ruler


def _build_pipeline() -> Language:
    """Create the spaCy language pipeline used across the legal modules."""
    if spacy is None:  # spaCy not installed, fall back to lightweight implementation
        return _FallbackNLP()  # type: ignore[return-value]

    try:
        # Prefer an official pretrained model if available.
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Fall back to a lightweight blank English pipeline.
        nlp = spacy.blank("en")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")

    # Ensure sentence boundaries exist even for pretrained models (some disable it).
    if "senter" not in nlp.pipe_names and "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")

    # Insert the entity ruler ahead of the statistical NER so that pattern-based
    # matches take precedence while still allowing the statistical model to run.
    before_component = "ner" if "ner" in nlp.pipe_names else None
    if "entity_ruler" not in nlp.pipe_names:
        _configure_entity_ruler(nlp, before_component)
    else:
        ruler = nlp.get_pipe("entity_ruler")
        if isinstance(ruler, EntityRuler):
            ruler.add_patterns(_legal_patterns())

    return nlp


def get_legal_nlp() -> Language:
    """Return a shared spaCy pipeline instance configured for legal text."""
    global _NLP_INSTANCE
    with _NLP_LOCK:
        if _NLP_INSTANCE is None:
            _NLP_INSTANCE = _build_pipeline()
    return _NLP_INSTANCE


def ensure_pipeline_components(components: Iterable[str]) -> None:
    """Ensure optional components are present in the shared pipeline."""
    nlp = get_legal_nlp()
    pipe_names = getattr(nlp, "pipe_names", ())
    missing = [component for component in components if component not in pipe_names]
    for component in missing:
        if spacy is None:
            continue
        if component == "lemmatizer":
            nlp.add_pipe("lemmatizer", name="lemmatizer", config={"mode": "rule"})
        elif component == "attribute_ruler":
            nlp.add_pipe("attribute_ruler")
