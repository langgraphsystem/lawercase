"""Legal-specific entity recognition built on top of the shared NLP pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import Any

try:  # pragma: no cover - spaCy optional
    from spacy.language import Language
    from spacy.tokens import Doc, Span
except ModuleNotFoundError:  # pragma: no cover
    Language = Any  # type: ignore
    Doc = Any  # type: ignore
    Span = Any  # type: ignore

from .nlp import get_legal_nlp


class LegalEntityType(str, Enum):
    """Supported entity categories for legal text."""

    PARTY = "party"
    JUDGE = "judge"
    ATTORNEY = "attorney"
    COURT = "court"
    LAW_FIRM = "law_firm"
    STATUTE = "statute"
    CASE_NAME = "case_name"
    CONTRACT_TYPE = "contract_type"
    LEGAL_TERM = "legal_term"


@dataclass(slots=True)
class LegalEntity:
    """A detected entity mention within legal text."""

    text: str
    entity_type: LegalEntityType
    start: int
    end: int
    confidence: float = 1.0


class LegalEntityRecognizer:
    """Wrapper around spaCy that emits `LegalEntity` objects."""

    _LABEL_MAPPING = {
        "ORG": LegalEntityType.PARTY,
        "PERSON": LegalEntityType.PARTY,
        "LAW_FIRM": LegalEntityType.LAW_FIRM,
        "COURT": LegalEntityType.COURT,
        "CONTRACT_TYPE": LegalEntityType.CONTRACT_TYPE,
        "STATUTE": LegalEntityType.STATUTE,
        "GPE": LegalEntityType.PARTY,
        "LEGAL_TERM": LegalEntityType.LEGAL_TERM,
        "JUDGE": LegalEntityType.JUDGE,
        "ATTORNEY": LegalEntityType.ATTORNEY,
    }

    _FALLBACK_PATTERNS = {
        LegalEntityType.COURT: [
            r"Supreme\s+Court",
            r"Court\s+of\s+Appeals",
            r"District\s+Court",
            r"Circuit\s+Court",
        ],
        LegalEntityType.STATUTE: [
            r"\d+\s+U\.S\.C\.",
            r"\d+\s+USC",
            r"Title\s+\d+",
        ],
        LegalEntityType.CONTRACT_TYPE: [
            r"Employment\s+Agreement",
            r"Purchase\s+Agreement",
            r"License\s+Agreement",
            r"Non-Disclosure\s+Agreement",
        ],
    }

    def __init__(self, nlp: Language | None = None) -> None:
        self._nlp = nlp or get_legal_nlp()

    def recognize(self, text: str) -> list[LegalEntity]:
        """Run entity recognition over the provided text."""
        if not text.strip():
            return []

        doc = self._nlp(text)
        entities: list[LegalEntity] = []
        seen_offsets: set[tuple[int, int]] = set()

        def _add_entity(span: Span, entity_type: LegalEntityType, confidence: float) -> None:
            start, end = span.start_char, span.end_char
            if (start, end) not in seen_offsets:
                seen_offsets.add((start, end))
                entities.append(
                    LegalEntity(
                        text=span.text,
                        entity_type=entity_type,
                        start=start,
                        end=end,
                        confidence=confidence,
                    )
                )

        for span in doc.ents:
            label = span.label_
            if label == "LAW_FIRM" and "Law" not in span.text and "LLP" not in span.text:
                continue
            entity_type = self._LABEL_MAPPING.get(label)
            if entity_type:
                confidence = (
                    0.95 if label in {"COURT", "STATUTE", "CONTRACT_TYPE", "LEGAL_TERM"} else 0.85
                )
                _add_entity(span, entity_type, confidence)

        if not getattr(doc, "ents", []):
            for entity_type, patterns in self._FALLBACK_PATTERNS.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        span = getattr(doc, "char_span", lambda *_, **__: None)(
                            match.start(), match.end()
                        )
                        if span is None:
                            span = SimpleNamespace(
                                text=match.group(0),
                                start_char=match.start(),
                                end_char=match.end(),
                            )
                        _add_entity(span, entity_type, 0.9)

        case_pattern = re.compile(r"[A-Z][\w&.\s]+ v\. [A-Z][\w&.\s]+")
        for match in case_pattern.finditer(text):
            span = doc.char_span(match.start(), match.end())
            if span:
                _add_entity(span, LegalEntityType.CASE_NAME, 0.9)

        return entities
