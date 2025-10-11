"""Legal Document Parser.

Parses legal documents and extracts structured information.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LegalDocumentType(str, Enum):
    """Types of legal documents."""

    CONTRACT = "contract"
    AGREEMENT = "agreement"
    POLICY = "policy"
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    LICENSE = "license"
    LEASE = "lease"
    EMPLOYMENT = "employment"
    NDA = "nda"
    POWER_OF_ATTORNEY = "power_of_attorney"
    WILL = "will"
    TRUST = "trust"
    COURT_FILING = "court_filing"
    STATUTE = "statute"
    REGULATION = "regulation"
    CASE_LAW = "case_law"
    OPINION = "opinion"
    BRIEF = "brief"
    MOTION = "motion"
    OTHER = "other"


@dataclass
class DocumentSection:
    """Section of a legal document."""

    section_number: str
    title: str
    content: str
    subsections: list[DocumentSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    start_position: int = 0
    end_position: int = 0


@dataclass
class LegalDocument:
    """Structured legal document."""

    doc_id: str
    title: str
    doc_type: LegalDocumentType
    content: str
    sections: list[DocumentSection] = field(default_factory=list)
    parties: list[str] = field(default_factory=list)
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    jurisdiction: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_section(self, section_number: str) -> DocumentSection | None:
        """Get section by number."""
        for section in self.sections:
            if section.section_number == section_number:
                return section
        return None

    def search_content(self, query: str, case_sensitive: bool = False) -> list[str]:
        """Search for text in document content."""
        flags = 0 if case_sensitive else re.IGNORECASE
        matches = re.finditer(re.escape(query), self.content, flags)
        return [match.group() for match in matches]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type.value,
            "content": self.content,
            "sections": [
                {
                    "section_number": s.section_number,
                    "title": s.title,
                    "content": s.content,
                }
                for s in self.sections
            ],
            "parties": self.parties,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "jurisdiction": self.jurisdiction,
            "metadata": self.metadata,
        }


class DocumentParser:
    """
    Parse legal documents and extract structure.

    Features:
    - Document type detection
    - Section extraction (numbered and titled)
    - Party identification
    - Date extraction (effective, expiration)
    - Metadata extraction

    Example:
        >>> parser = DocumentParser()
        >>> doc = parser.parse(text, doc_id="contract_001")
        >>> print(f"Type: {doc.doc_type}")
        >>> print(f"Sections: {len(doc.sections)}")
    """

    def __init__(self):
        """Initialize document parser."""
        # Section patterns
        self.section_patterns = [
            # "1. Title" or "1.1 Title"
            re.compile(r"^(\d+(?:\.\d+)*)\.\s+([A-Z][^\n]+)", re.MULTILINE),
            # "Article I" or "Section A"
            re.compile(
                r"^(Article|Section|Part|Chapter)\s+([IVX]+|[A-Z])\.\s+([A-Z][^\n]+)",
                re.MULTILINE,
            ),
            # "SECTION 1 - TITLE" (all caps)
            re.compile(r"^(SECTION|ARTICLE)\s+(\d+)\s*[-–]\s*([A-Z\s]+)", re.MULTILINE),
        ]

        # Date patterns
        self.date_patterns = [
            re.compile(
                r"effective\s+(?:date|as\s+of)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                re.IGNORECASE,
            ),
            re.compile(
                r"dated\s+(?:as\s+of\s+)?(\w+\s+\d{1,2},\s+\d{4})",
                re.IGNORECASE,
            ),
            re.compile(
                r"(\d{4}-\d{2}-\d{2})",
            ),
        ]

        # Party patterns
        self.party_patterns = [
            re.compile(
                r"between\s+([A-Z][^\n,]+?)(?:\s+\([\"']?([A-Z][^\)]+)[\"']?\))?\s+and\s+([A-Z][^\n,]+?)(?:\s+\([\"']?([A-Z][^\)]+)[\"']?\))?",
                re.IGNORECASE,
            ),
            re.compile(
                r"Party\s+[A-Z]:\s+([A-Z][^\n]+)",
                re.IGNORECASE,
            ),
        ]

    def parse(
        self,
        text: str,
        doc_id: str | None = None,
        doc_type: LegalDocumentType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LegalDocument:
        """
        Parse legal document.

        Args:
            text: Document text
            doc_id: Optional document ID
            doc_type: Optional document type (will be detected if not provided)
            metadata: Optional metadata

        Returns:
            Parsed LegalDocument
        """
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = f"doc_{hash(text[:100]) % 1000000}"

        # Detect document type
        if not doc_type:
            doc_type = self._detect_document_type(text)

        # Extract title
        title = self._extract_title(text)

        # Extract sections
        sections = self._extract_sections(text)

        # Extract parties
        parties = self._extract_parties(text)

        # Extract dates
        effective_date = self._extract_effective_date(text)
        expiration_date = self._extract_expiration_date(text)

        # Extract jurisdiction
        jurisdiction = self._extract_jurisdiction(text)

        return LegalDocument(
            doc_id=doc_id,
            title=title,
            doc_type=doc_type,
            content=text,
            sections=sections,
            parties=parties,
            effective_date=effective_date,
            expiration_date=expiration_date,
            jurisdiction=jurisdiction,
            metadata=metadata or {},
        )

    def _detect_document_type(self, text: str) -> LegalDocumentType:
        """Detect document type from content."""
        text_lower = text.lower()

        # Check for specific keywords
        type_keywords = {
            LegalDocumentType.CONTRACT: ["contract", "agreement"],
            LegalDocumentType.NDA: [
                "non-disclosure agreement",
                "confidentiality agreement",
            ],
            LegalDocumentType.EMPLOYMENT: [
                "employment agreement",
                "employment contract",
            ],
            LegalDocumentType.LEASE: ["lease agreement", "rental agreement"],
            LegalDocumentType.LICENSE: ["license agreement", "licensing"],
            LegalDocumentType.TERMS_OF_SERVICE: [
                "terms of service",
                "terms and conditions",
            ],
            LegalDocumentType.PRIVACY_POLICY: ["privacy policy", "privacy notice"],
            LegalDocumentType.POWER_OF_ATTORNEY: ["power of attorney"],
            LegalDocumentType.WILL: ["last will", "testament"],
            LegalDocumentType.COURT_FILING: ["court filing", "complaint", "petition"],
            LegalDocumentType.MOTION: ["motion to", "motion for"],
            LegalDocumentType.BRIEF: ["brief in support", "memorandum of law"],
        }

        for doc_type, keywords in type_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type

        return LegalDocumentType.OTHER

    def _extract_title(self, text: str) -> str:
        """Extract document title."""
        # Try to find title in first few lines
        lines = text.split("\n")[:10]

        # Look for all-caps title
        for raw_line in lines:
            line = raw_line.strip()
            if line and line.isupper() and len(line) > 10:
                return line

        # Look for first non-empty line
        for raw_line in lines:
            line = raw_line.strip()
            if line and len(line) > 5:
                return line

        return "Untitled Document"

    def _extract_sections(self, text: str) -> list[DocumentSection]:
        """Extract document sections."""
        sections = []

        # Try each pattern
        for pattern in self.section_patterns:
            matches = list(pattern.finditer(text))

            if matches:
                for i, match in enumerate(matches):
                    groups = match.groups()

                    # Extract section number and title based on pattern
                    if len(groups) == 2:
                        # Pattern: "1. Title"
                        section_num = groups[0]
                        section_title = groups[1].strip()
                    elif len(groups) >= 3:
                        # Pattern: "Article I. Title" or "SECTION 1 - TITLE"
                        section_num = groups[1] if groups[1] else groups[0]
                        section_title = groups[2].strip() if len(groups) > 2 else groups[1].strip()
                    else:
                        continue

                    # Get content until next section
                    start_pos = match.end()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    content = text[start_pos:end_pos].strip()

                    sections.append(
                        DocumentSection(
                            section_number=section_num,
                            title=section_title,
                            content=content,
                            start_position=start_pos,
                            end_position=end_pos,
                        ),
                    )

                # If we found sections, stop trying other patterns
                if sections:
                    break

        return sections

    def _extract_parties(self, text: str) -> list[str]:
        """Extract parties from document."""
        parties = []

        for pattern in self.party_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract all captured groups
                for group in match.groups():
                    if group and len(group) > 2:
                        party = group.strip()
                        if party not in parties:
                            parties.append(party)

        return parties

    def _extract_effective_date(self, text: str) -> datetime | None:
        """Extract effective date."""
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                date_str = match.group(1)
                try:
                    # Try parsing different formats
                    return self._parse_date(date_str)
                except (ValueError, AttributeError):
                    continue
        return None

    def _extract_expiration_date(self, text: str) -> datetime | None:
        """Extract expiration/termination date."""
        expiration_pattern = re.compile(
            r"(?:expiration|termination|end)\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            re.IGNORECASE,
        )

        match = expiration_pattern.search(text)
        if match:
            try:
                return self._parse_date(match.group(1))
            except (ValueError, AttributeError):
                pass
        return None

    def _extract_jurisdiction(self, text: str) -> str | None:
        """Extract jurisdiction."""
        jurisdiction_pattern = re.compile(
            r"(?:jurisdiction|governing\s+law|laws\s+of)\s*:?\s*(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            re.IGNORECASE,
        )

        match = jurisdiction_pattern.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        from dateutil import parser

        return parser.parse(date_str)


# Global singleton
_document_parser: DocumentParser | None = None


def get_document_parser() -> DocumentParser:
    """Get or create global DocumentParser instance."""
    global _document_parser
    if _document_parser is None:
        _document_parser = DocumentParser()
    return _document_parser
