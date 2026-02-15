"""Robust extraction and normalisation of common legal citation formats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class CitationType(str, Enum):
    """Categorisation of legal citations."""

    CASE = "case"
    STATUTE = "statute"
    REGULATION = "regulation"
    CONSTITUTION = "constitution"
    TREATY = "treaty"
    OTHER = "other"


@dataclass(slots=True)
class LegalCitation:
    """Normalised legal citation details."""

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
    """Extract case law and statutory citations using Bluebook-style patterns."""

    # Bluebook compliant case citation patterns (e.g. "Smith v. Jones, 123 F.3d 456 (9th Cir. 2000)")
    _CASE_PATTERN = re.compile(
        r"""
        (?P<case_name>[A-Z][\w.&\s]+?\s+v\.?\s+[A-Z][\w.&\s]+?)      # Case name
        ,?\s+
        (?P<volume>\d+)\s+
        (?P<reporter>[A-Z][A-Za-z.\d]+)\s+
        (?P<page>\d+)
        (?:\s*\(
            (?P<court>[^)0-9]*?)?
            \s*
            (?P<year>\d{4})
        \))?
        """,
        re.VERBOSE,
    )

    # Short reporter-only citations (e.g. "123 F.3d 456")
    _SHORT_CASE_PATTERN = re.compile(
        r"(?P<volume>\d+)\s+(?P<reporter>[A-Z]\.?[A-Za-z.\d]+)\s+(?P<page>\d+)"
    )

    # Statutory references (USC, CFR, state codes).
    _STATUTE_PATTERNS = [
        re.compile(r"(?P<title>\d+)\s+U\.?S\.?C\.?\s+§+\s*(?P<section>[\w\.-]+)"),
        re.compile(r"(?P<title>\d+)\s+C\.?F\.?R\.?\s+§+\s*(?P<section>[\w\.-]+)"),
        re.compile(r"(?P<section>Art\.?\s+\w+)\s+Const\."),
    ]

    def extract(self, text: str) -> list[LegalCitation]:
        """Return all citations found within `text`."""
        citations: list[LegalCitation] = []
        seen_offsets: set[tuple[int, int]] = set()

        for match in self._CASE_PATTERN.finditer(text):
            start, end = match.span()
            if (start, end) in seen_offsets:
                continue
            seen_offsets.add((start, end))
            citation = self._parse_case_citation(match)
            if citation:
                citations.append(citation)

        for match in self._SHORT_CASE_PATTERN.finditer(text):
            start, end = match.span()
            if (start, end) in seen_offsets:
                continue
            seen_offsets.add((start, end))
            citations.append(
                LegalCitation(
                    citation_text=match.group(0),
                    citation_type=CitationType.CASE,
                    volume=match.group("volume"),
                    reporter=match.group("reporter"),
                    page=match.group("page"),
                    normalized=f"{match.group('volume')} {match.group('reporter')} {match.group('page')}",
                )
            )

        for pattern in self._STATUTE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.span()
                if (start, end) in seen_offsets:
                    continue
                seen_offsets.add((start, end))
                citations.append(self._parse_statute_citation(match))

        return citations

    def _parse_case_citation(self, match: re.Match) -> LegalCitation | None:
        """Convert a regex match to a `LegalCitation`."""
        groups = match.groupdict()
        case_name = groups.get("case_name")
        volume = groups.get("volume")
        reporter = groups.get("reporter")
        page = groups.get("page")
        year = groups.get("year")
        court = groups.get("court")

        normalized = None
        if case_name and volume and reporter and page:
            parts = [case_name.strip(), f"{volume} {reporter} {page}"]
            if court or year:
                paren_content = " ".join(filter(None, [court and court.strip(), year]))
                if paren_content:
                    parts[-1] = f"{parts[-1]} ({paren_content})"
            normalized = ", ".join(parts)

        return LegalCitation(
            citation_text=match.group(0),
            citation_type=CitationType.CASE,
            reporter=reporter,
            volume=volume,
            page=page,
            year=year,
            court=court.strip() if court else None,
            normalized=normalized,
        )

    def _parse_statute_citation(self, match: re.Match) -> LegalCitation:
        """Parse statutory citation matches."""
        volume = match.group("title") if "title" in match.groupdict() else None
        section = match.group("section")
        citation_text = match.group(0)
        normalized = citation_text.replace("  ", " ").strip()
        return LegalCitation(
            citation_text=citation_text,
            citation_type=CitationType.STATUTE,
            volume=volume,
            page=section,
            normalized=normalized,
        )
