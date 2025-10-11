"""Legal Citation Extractor.

Extracts and normalizes legal citations from text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CitationType(str, Enum):
    """Types of legal citations."""

    CASE = "case"
    STATUTE = "statute"
    REGULATION = "regulation"
    CONSTITUTION = "constitution"
    TREATY = "treaty"
    OTHER = "other"


@dataclass
class LegalCitation:
    """Legal citation."""

    citation_text: str
    citation_type: CitationType
    reporter: str | None = None
    volume: str | None = None
    page: str | None = None
    year: str | None = None
    court: str | None = None
    jurisdiction: str | None = None
    normalized: str | None = None


class CitationExtractor:
    """Extract and parse legal citations."""

    def __init__(self):
        """Initialize citation extractor."""
        # US Case law patterns
        self.case_patterns = [
            # 123 U.S. 456
            re.compile(r"(\d+)\s+([A-Z]\.?\s?[A-Z]\.?[A-Z]?\.?)\s+(\d+)"),
            # Smith v. Jones, 123 F.3d 456
            re.compile(
                r"([A-Z][a-z]+)\s+v\.?\s+([A-Z][a-z]+),\s+(\d+)\s+([A-Z][A-Z.]\.?[A-Z]?\.?)\s+(\d+)",
            ),
        ]

        # Statute patterns
        self.statute_patterns = [
            # 42 U.S.C. § 1983
            re.compile(r"(\d+)\s+U\.S\.C\.?\s+§\s*(\d+)"),
            # 15 USC 78
            re.compile(r"(\d+)\s+USC\s+(\d+)"),
        ]

    def extract(self, text: str) -> list[LegalCitation]:
        """Extract all citations from text."""
        citations = []

        # Extract case citations
        for pattern in self.case_patterns:
            for match in pattern.finditer(text):
                citation = self._parse_case_citation(match)
                if citation:
                    citations.append(citation)

        # Extract statute citations
        for pattern in self.statute_patterns:
            for match in pattern.finditer(text):
                citation = self._parse_statute_citation(match)
                if citation:
                    citations.append(citation)

        return citations

    def _parse_case_citation(self, match: re.Match) -> LegalCitation | None:
        """Parse case law citation."""
        groups = match.groups()
        if len(groups) >= 3:
            return LegalCitation(
                citation_text=match.group(0),
                citation_type=CitationType.CASE,
                volume=groups[0],
                reporter=groups[1],
                page=groups[2],
            )
        return None

    def _parse_statute_citation(self, match: re.Match) -> LegalCitation | None:
        """Parse statute citation."""
        return LegalCitation(
            citation_text=match.group(0),
            citation_type=CitationType.STATUTE,
            volume=match.group(1),
            page=match.group(2),
        )
