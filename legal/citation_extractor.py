"""Legal Citation Extractor for EB-1A Processing.

Provides citation extraction and cross-referencing:
- Citation parsing (case law, regulations, statutes)
- Cross-reference identification
- Citation validation
- Shepardizing support (citation history)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class CitationType(str, Enum):
    """Types of legal citations."""

    CASE_LAW = "case_law"  # Court cases
    STATUTE = "statute"  # Laws (USC)
    REGULATION = "regulation"  # CFR regulations
    USCIS_DECISION = "uscis_decision"  # Administrative decisions (I&N Dec)
    POLICY_MEMO = "policy_memo"  # USCIS policy memoranda
    MATTER_OF = "matter_of"  # Matter of X decisions
    FEDERAL_REGISTER = "federal_register"  # FR citations
    OTHER = "other"


class CitationStrength(str, Enum):
    """Strength/relevance of a citation."""

    PRIMARY = "primary"  # Directly applicable authority
    SECONDARY = "secondary"  # Supporting authority
    PERSUASIVE = "persuasive"  # Non-binding but relevant
    BACKGROUND = "background"  # Contextual reference


@dataclass
class Citation:
    """A legal citation extracted from text."""

    id: str
    text: str
    citation_type: CitationType
    normalized: str
    strength: CitationStrength = CitationStrength.SECONDARY
    start_pos: int = -1
    end_pos: int = -1
    confidence: float = 0.8
    # Parsed components
    case_name: str | None = None
    volume: str | None = None
    reporter: str | None = None
    page: str | None = None
    year: int | None = None
    court: str | None = None
    # Context
    context: str = ""
    relevance_score: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "citation_type": self.citation_type.value,
            "normalized": self.normalized,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "case_name": self.case_name,
            "year": self.year,
            "relevance_score": self.relevance_score,
        }


@dataclass
class CrossReference:
    """A cross-reference between citations."""

    source_citation_id: str
    target_citation_id: str
    relationship: str  # cites, overrules, distinguishes, follows, etc.
    context: str = ""
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_citation_id,
            "target": self.target_citation_id,
            "relationship": self.relationship,
            "confidence": self.confidence,
        }


# Citation patterns
CITATION_PATTERNS = {
    CitationType.MATTER_OF: [
        re.compile(
            r"Matter\s+of\s+([A-Z][a-zA-Z\-]+)(?:\s*,\s*(\d+)\s+I&N\s+Dec\.?\s+(\d+))?", re.I
        ),
    ],
    CitationType.USCIS_DECISION: [
        re.compile(r"(\d+)\s+I&N\s+Dec\.?\s+(\d+)(?:\s*\(([^)]+)\))?"),
    ],
    CitationType.STATUTE: [
        re.compile(r"(\d+)\s+U\.?S\.?C\.?\s*§?\s*(\d+)(?:\(([a-z])\))?", re.I),
        re.compile(r"INA\s*§?\s*(\d+)(?:\(([a-z])\))?", re.I),
    ],
    CitationType.REGULATION: [
        re.compile(r"(\d+)\s+C\.?F\.?R\.?\s*§?\s*([\d.]+)(?:\(([a-z])\))?", re.I),
    ],
    CitationType.CASE_LAW: [
        # Supreme Court
        re.compile(r"(\d+)\s+U\.?S\.?\s+(\d+)(?:\s*\((\d{4})\))?"),
        # Federal Reporter
        re.compile(r"(\d+)\s+F\.?\s*(?:2d|3d|4th)?\s+(\d+)(?:\s*\(([^)]+)\))?"),
        # Federal Supplement
        re.compile(r"(\d+)\s+F\.?\s*Supp\.?\s*(?:2d|3d)?\s+(\d+)"),
    ],
    CitationType.FEDERAL_REGISTER: [
        re.compile(r"(\d+)\s+Fed\.?\s*Reg\.?\s+(\d+)"),
        re.compile(r"(\d+)\s+FR\s+(\d+)"),
    ],
    CitationType.POLICY_MEMO: [
        re.compile(r"PM-602-(\d+(?:\.\d+)?)"),
        re.compile(r"USCIS\s+Policy\s+(?:Memo(?:randum)?|Manual).*?(\d{4})", re.I),
    ],
}

# Key EB-1A cases
EB1A_KEY_CASES = {
    "kazarian": {
        "full_citation": "Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)",
        "importance": "Established two-part framework for EB-1A evaluation",
        "keywords": ["two-step", "two-part", "final merits", "comparable evidence"],
    },
    "dhanasar": {
        "full_citation": "Matter of Dhanasar, 26 I&N Dec. 884 (AAO 2016)",
        "importance": "Updated national interest waiver standard",
        "keywords": ["national interest", "NIW", "merit", "importance"],
    },
    "o-k-industries": {
        "full_citation": "O-K-Industries, 23 I&N Dec. 413 (BIA 2002)",
        "importance": "Defined 'extraordinary ability' standard",
        "keywords": ["extraordinary ability", "sustained acclaim"],
    },
}


class CitationParser:
    """Parse and normalize legal citations."""

    def __init__(self):
        self.patterns = CITATION_PATTERNS
        self.key_cases = EB1A_KEY_CASES

    def parse(self, text: str) -> list[Citation]:
        """Parse all citations from text."""
        citations = []
        citation_id = 0

        for citation_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    citation_id += 1
                    citation = self._create_citation(match, citation_type, f"cit_{citation_id}")
                    if citation:
                        # Add context
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        citation.context = text[start:end]
                        citations.append(citation)

        # Check for key EB-1A cases
        for case_key, case_info in self.key_cases.items():
            if (
                case_key.replace("-", " ") in text.lower()
                or case_key.replace("-", "") in text.lower()
            ):
                # Check if already captured
                already_found = any(
                    case_key.replace("-", "") in c.text.lower().replace("-", "") for c in citations
                )
                if not already_found:
                    citation_id += 1
                    citations.append(
                        Citation(
                            id=f"cit_{citation_id}",
                            text=case_info["full_citation"],
                            citation_type=CitationType.CASE_LAW,
                            normalized=case_info["full_citation"],
                            strength=CitationStrength.PRIMARY,
                            confidence=0.95,
                            case_name=case_key.replace("-", " ").title(),
                            relevance_score=0.9,
                            metadata={"key_case": True, "importance": case_info["importance"]},
                        )
                    )

        return citations

    def _create_citation(
        self,
        match: re.Match,
        citation_type: CitationType,
        citation_id: str,
    ) -> Citation | None:
        """Create Citation from regex match."""
        text = match.group(0)
        groups = match.groups()

        citation = Citation(
            id=citation_id,
            text=text,
            citation_type=citation_type,
            normalized=self._normalize(text, citation_type),
            start_pos=match.start(),
            end_pos=match.end(),
            confidence=0.85,
        )

        # Parse components based on type
        if citation_type == CitationType.MATTER_OF:
            citation.case_name = groups[0] if groups else None
            if len(groups) > 1 and groups[1]:
                citation.volume = groups[1]
                citation.reporter = "I&N Dec."
                citation.page = groups[2] if len(groups) > 2 else None
            citation.strength = CitationStrength.PRIMARY

        elif citation_type == CitationType.USCIS_DECISION:
            citation.volume = groups[0] if groups else None
            citation.reporter = "I&N Dec."
            citation.page = groups[1] if len(groups) > 1 else None
            if len(groups) > 2 and groups[2]:
                # Parse year from parenthetical
                year_match = re.search(r"\d{4}", groups[2])
                if year_match:
                    citation.year = int(year_match.group())
                citation.court = groups[2]

        elif citation_type == CitationType.STATUTE:
            citation.volume = groups[0] if groups else None
            citation.reporter = "U.S.C."

        elif citation_type == CitationType.REGULATION:
            citation.volume = groups[0] if groups else None
            citation.reporter = "C.F.R."

        elif citation_type == CitationType.CASE_LAW:
            citation.volume = groups[0] if groups else None
            citation.page = groups[1] if len(groups) > 1 else None
            if len(groups) > 2 and groups[2]:
                year_match = re.search(r"\d{4}", groups[2])
                if year_match:
                    citation.year = int(year_match.group())

        return citation

    def _normalize(self, text: str, citation_type: CitationType) -> str:
        """Normalize citation format."""
        # Basic normalization
        normalized = re.sub(r"\s+", " ", text.strip())

        # Type-specific normalization
        if citation_type == CitationType.STATUTE:
            normalized = re.sub(r"U\.?S\.?C\.?", "U.S.C.", normalized)
        elif citation_type == CitationType.REGULATION:
            normalized = re.sub(r"C\.?F\.?R\.?", "C.F.R.", normalized)
        elif citation_type == CitationType.USCIS_DECISION:
            normalized = re.sub(r"I&N\s*Dec\.?", "I&N Dec.", normalized)

        return normalized


class CrossReferenceAnalyzer:
    """Analyze cross-references between citations."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.llm_call = llm_call
        self._relationship_keywords = {
            "cites": ["citing", "cited in", "see", "accord"],
            "follows": ["following", "consistent with", "pursuant to"],
            "distinguishes": ["distinguished", "distinguishing", "but see"],
            "overrules": ["overruled", "overruling", "no longer"],
            "supports": ["supporting", "support for", "bolsters"],
        }

    async def analyze(
        self,
        text: str,
        citations: list[Citation],
    ) -> list[CrossReference]:
        """Analyze cross-references in text."""
        cross_refs = []

        if len(citations) < 2:
            return cross_refs

        # Simple keyword-based analysis
        for i, source in enumerate(citations):
            for j, target in enumerate(citations):
                if i >= j:
                    continue

                # Check if citations appear near each other
                if abs(source.start_pos - target.start_pos) < 500:
                    # Look for relationship keywords between them
                    start = min(source.end_pos, target.end_pos)
                    end = max(source.start_pos, target.start_pos)
                    if start < end:
                        between_text = text[start:end].lower()
                        for rel, keywords in self._relationship_keywords.items():
                            if any(kw in between_text for kw in keywords):
                                cross_refs.append(
                                    CrossReference(
                                        source_citation_id=source.id,
                                        target_citation_id=target.id,
                                        relationship=rel,
                                        context=between_text[:200],
                                        confidence=0.7,
                                    )
                                )
                                break

        # LLM-enhanced analysis for complex relationships
        if self.llm_call and len(citations) <= 10:
            citation_list = "\n".join(f"{c.id}: {c.text}" for c in citations)
            prompt = f"""Analyze relationships between these legal citations:
{citation_list}

For each pair that has a relationship, indicate:
- Source citation ID
- Target citation ID
- Relationship type (cites, follows, distinguishes, overrules, supports)

Format: SOURCE_ID -> TARGET_ID: RELATIONSHIP"""

            try:
                result = await self.llm_call(prompt)
                for line in result.split("\n"):
                    if "->" in line and ":" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            ids = parts[0].split("->")
                            if len(ids) == 2:
                                rel = parts[1].strip().lower()
                                # Check if we already have this relationship
                                source_id = ids[0].strip()
                                target_id = ids[1].strip()
                                already_exists = any(
                                    cr.source_citation_id == source_id
                                    and cr.target_citation_id == target_id
                                    for cr in cross_refs
                                )
                                if not already_exists:
                                    cross_refs.append(
                                        CrossReference(
                                            source_citation_id=source_id,
                                            target_citation_id=target_id,
                                            relationship=rel,
                                            confidence=0.6,
                                        )
                                    )
            except Exception as e:
                logger.warning(f"LLM cross-reference analysis failed: {e}")

        return cross_refs


class CitationExtractor:
    """Main citation extraction and analysis class."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    ):
        self.llm_call = llm_call
        self.parser = CitationParser()
        self.xref_analyzer = CrossReferenceAnalyzer(llm_call)

    async def extract_citations(
        self,
        text: str,
        analyze_cross_refs: bool = True,
    ) -> dict[str, Any]:
        """Extract and analyze all citations from text."""
        citations = self.parser.parse(text)

        # Score relevance
        for citation in citations:
            citation.relevance_score = self._score_relevance(citation, text)

        # Sort by relevance
        citations.sort(key=lambda c: c.relevance_score, reverse=True)

        # Analyze cross-references
        cross_refs = []
        if analyze_cross_refs:
            cross_refs = await self.xref_analyzer.analyze(text, citations)

        return {
            "citations": citations,
            "cross_references": cross_refs,
            "summary": {
                "total_citations": len(citations),
                "by_type": self._count_by_type(citations),
                "key_cases": [c for c in citations if c.metadata.get("key_case")],
                "primary_authorities": [
                    c for c in citations if c.strength == CitationStrength.PRIMARY
                ],
            },
        }

    def _score_relevance(self, citation: Citation, text: str) -> float:
        """Score citation relevance to EB-1A context."""
        score = 0.5  # Base score

        # Key case bonus
        if citation.metadata.get("key_case"):
            score += 0.3

        # Primary authority bonus
        if citation.strength == CitationStrength.PRIMARY:
            score += 0.2

        # Matter of decisions are highly relevant
        if citation.citation_type == CitationType.MATTER_OF:
            score += 0.15

        # USCIS decisions are relevant
        if citation.citation_type == CitationType.USCIS_DECISION:
            score += 0.1

        # Immigration regulations
        if citation.citation_type == CitationType.REGULATION:
            if "8 C.F.R" in citation.text or "204.5" in citation.text:
                score += 0.15

        # Frequency bonus
        occurrences = text.lower().count(
            citation.case_name.lower() if citation.case_name else citation.text.lower()
        )
        score += min(occurrences * 0.05, 0.15)

        return min(score, 1.0)

    def _count_by_type(self, citations: list[Citation]) -> dict[str, int]:
        """Count citations by type."""
        counts = {}
        for citation in citations:
            type_name = citation.citation_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    async def validate_citation(
        self,
        citation: Citation,
    ) -> dict[str, Any]:
        """Validate a citation format and existence."""
        result = {
            "citation_id": citation.id,
            "format_valid": True,
            "known_case": False,
            "issues": [],
        }

        # Check format based on type
        if citation.citation_type == CitationType.CASE_LAW:
            if not citation.volume or not citation.page:
                result["format_valid"] = False
                result["issues"].append("Missing volume or page number")

        elif citation.citation_type == CitationType.STATUTE:
            if not citation.volume:
                result["format_valid"] = False
                result["issues"].append("Missing title number")

        # Check if it's a known key case
        for case_key, case_info in EB1A_KEY_CASES.items():
            if citation.case_name and case_key.replace("-", " ") in citation.case_name.lower():
                result["known_case"] = True
                result["case_info"] = case_info
                break

        return result


def create_citation_extractor(
    llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> CitationExtractor:
    """Factory function to create CitationExtractor instance."""
    return CitationExtractor(llm_call=llm_call)
