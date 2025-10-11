"""Legal Entity Recognition.

Recognizes legal-specific entities in text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class LegalEntityType(str, Enum):
    """Types of legal entities."""

    PARTY = "party"
    JUDGE = "judge"
    ATTORNEY = "attorney"
    COURT = "court"
    LAW_FIRM = "law_firm"
    STATUTE = "statute"
    CASE_NAME = "case_name"
    CONTRACT_TYPE = "contract_type"
    LEGAL_TERM = "legal_term"


@dataclass
class LegalEntity:
    """Legal entity mention."""

    text: str
    entity_type: LegalEntityType
    start: int
    end: int
    confidence: float = 1.0


class LegalEntityRecognizer:
    """Recognize legal-specific entities."""

    def __init__(self):
        """Initialize entity recognizer."""
        self.patterns = {
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

    def recognize(self, text: str) -> list[LegalEntity]:
        """Recognize legal entities in text."""
        entities = []

        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        LegalEntity(
                            text=match.group(0),
                            entity_type=entity_type,
                            start=match.start(),
                            end=match.end(),
                        ),
                    )

        return entities
