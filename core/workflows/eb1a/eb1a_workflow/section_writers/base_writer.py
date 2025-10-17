"""Base writer class for EB-1A criterion sections.

Provides common functionality for all criterion-specific writers including:
- Template integration
- LLM-powered content generation
- Evidence formatting
- Quality scoring
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
    SectionContent,
)
from ...templates.language_patterns import LanguagePatterns
from ...templates.section_templates import SectionTemplates


class BaseSectionWriter(ABC):
    """
    Abstract base class for criterion-specific section writers.

    Each criterion writer inherits from this class and implements:
    - Criterion-specific content generation logic
    - Evidence selection and prioritization
    - Legal citation integration
    - Quality assessment

    Example:
        >>> class AwardsWriter(BaseSectionWriter):
        ...     def get_criterion(self) -> EB1ACriterion:
        ...         return EB1ACriterion.AWARDS
        ...
        ...     async def generate_content(self, request, evidence):
        ...         # Custom logic for awards section
        ...         return "Generated awards content..."
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Initialize section writer.

        Args:
            memory_manager: Memory manager for context and LLM access
        """
        self.memory = memory_manager or MemoryManager()
        self.templates = SectionTemplates()
        self.language = LanguagePatterns()

    @abstractmethod
    def get_criterion(self) -> EB1ACriterion:
        """
        Get the criterion this writer handles.

        Returns:
            EB1ACriterion enum value
        """

    async def write_section(
        self, request: EB1APetitionRequest, evidence_list: list[EB1AEvidence]
    ) -> SectionContent:
        """
        Generate complete section content for criterion.

        Args:
            request: Full petition request
            evidence_list: Evidence items for this criterion

        Returns:
            Generated section with metadata
        """
        criterion = self.get_criterion()

        # Filter evidence for this criterion
        relevant_evidence = [e for e in evidence_list if e.criterion == criterion]

        if not relevant_evidence:
            # Return minimal section if no evidence
            return self._create_empty_section(criterion, request)

        # Get template for this criterion
        criterion_code = self._get_criterion_code(criterion)
        template = self.templates.get_template(criterion_code)

        # Generate main content
        content = await self.generate_content(request, relevant_evidence, template)

        # Extract evidence references
        evidence_refs = [e.exhibit_number for e in relevant_evidence if e.exhibit_number]

        # Get legal citations
        legal_citations = self.get_legal_citations(criterion, relevant_evidence)

        # Calculate quality metrics
        word_count = len(content.split())
        confidence_score = self.calculate_confidence(relevant_evidence, content)
        suggestions = self.generate_suggestions(relevant_evidence, content, confidence_score)

        return SectionContent(
            criterion=criterion,
            title=template.criterion_name,
            content=content,
            evidence_references=evidence_refs,
            legal_citations=legal_citations,
            word_count=word_count,
            confidence_score=confidence_score,
            suggestions=suggestions,
        )

    @abstractmethod
    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate criterion-specific content.

        Must be implemented by each criterion writer.

        Args:
            request: Petition request
            evidence: Relevant evidence for this criterion
            template: Section template

        Returns:
            Generated section content
        """

    def get_legal_citations(
        self, criterion: EB1ACriterion, evidence: list[EB1AEvidence]
    ) -> list[str]:
        """
        Get relevant legal citations for criterion.

        Args:
            criterion: Criterion being written
            evidence: Evidence items

        Returns:
            List of legal case citations
        """
        citations: list[str] = []

        # Always cite Kazarian for framework
        citations.append("Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)")

        # Criterion-specific citations
        criterion_citations = {
            EB1ACriterion.AWARDS: ["Buletini v. INS, 860 F. Supp. 1222 (E.D. Mich. 1994)"],
            EB1ACriterion.MEMBERSHIP: ["Visinscaia v. Beers, 4 F. Supp. 3d 126 (D.D.C. 2013)"],
            EB1ACriterion.PRESS: ["Grimson v. INS, No. 96-1426 (4th Cir. 1997)"],
            EB1ACriterion.ORIGINAL_CONTRIBUTION: [
                "Visinscaia v. Beers, 4 F. Supp. 3d 126 (D.D.C. 2013)"
            ],
            EB1ACriterion.SCHOLARLY_ARTICLES: [
                "Matter of Price, 20 I&N Dec. 953 (Assoc. Comm'r 1994)"
            ],
        }

        if criterion in criterion_citations:
            citations.extend(criterion_citations[criterion])

        return citations

    def calculate_confidence(self, evidence: list[EB1AEvidence], content: str) -> float:
        """
        Calculate confidence score for generated section.

        Args:
            evidence: Evidence items
            content: Generated content

        Returns:
            Confidence score (0.0-1.0)
        """
        score = 0.5  # Base score

        # Evidence quantity bonus
        evidence_count = len(evidence)
        if evidence_count >= 5:
            score += 0.2
        elif evidence_count >= 3:
            score += 0.1
        elif evidence_count >= 1:
            score += 0.05

        # Content length bonus
        word_count = len(content.split())
        if 300 <= word_count <= 700:
            score += 0.1
        elif 200 <= word_count <= 900:
            score += 0.05

        # Evidence diversity bonus
        evidence_types = {e.evidence_type for e in evidence}
        if len(evidence_types) >= 3:
            score += 0.1
        elif len(evidence_types) >= 2:
            score += 0.05

        # Content quality indicators
        if "demonstrat" in content.lower():
            score += 0.02
        if "establish" in content.lower():
            score += 0.02
        if "extraordinar" in content.lower():
            score += 0.02

        return min(1.0, score)

    def generate_suggestions(
        self, evidence: list[EB1AEvidence], content: str, confidence: float
    ) -> list[str]:
        """
        Generate improvement suggestions.

        Args:
            evidence: Evidence items
            content: Generated content
            confidence: Confidence score

        Returns:
            List of suggestions
        """
        suggestions: list[str] = []

        # Evidence-based suggestions
        if len(evidence) < 3:
            suggestions.append("Add more evidence items (recommend 3-5 per criterion)")

        evidence_types = {e.evidence_type for e in evidence}
        if len(evidence_types) < 2:
            suggestions.append("Diversify evidence types for stronger case")

        # Content-based suggestions
        word_count = len(content.split())
        if word_count < 200:
            suggestions.append("Expand content with more detail and analysis")
        elif word_count > 800:
            suggestions.append("Consider condensing to focus on strongest evidence")

        # Quality-based suggestions
        if confidence < 0.7:
            suggestions.append("Strengthen evidence or add comparative analysis")

        if "peer" not in content.lower():
            suggestions.append("Emphasize peer recognition and expert validation")

        return suggestions[:5]  # Limit to top 5

    def _create_empty_section(
        self, criterion: EB1ACriterion, request: EB1APetitionRequest
    ) -> SectionContent:
        """Create minimal section when no evidence available."""
        return SectionContent(
            criterion=criterion,
            title=f"Criterion: {criterion.value}",
            content="[No evidence available for this criterion]",
            evidence_references=[],
            legal_citations=[],
            word_count=0,
            confidence_score=0.0,
            suggestions=["Add evidence for this criterion"],
        )

    def _get_criterion_code(self, criterion: EB1ACriterion) -> str:
        """Extract criterion code from enum value."""
        # Extract "2.X" from "2.X_criterion_name"
        return criterion.value.split("_")[0]

    def _format_evidence_list(self, evidence: list[EB1AEvidence]) -> str:
        """Format evidence items for inclusion in content."""
        formatted: list[str] = []

        for i, ev in enumerate(evidence, 1):
            exhibit_ref = f" (Exhibit {ev.exhibit_number})" if ev.exhibit_number else ""
            formatted.append(f"{i}. {ev.title}{exhibit_ref}\n   {ev.description[:200]}...")

        return "\n\n".join(formatted)

    def _get_possessive(self, name: str) -> str:
        """Get possessive form of name."""
        last_name = name.split()[-1]
        return f"{last_name}'s" if not last_name.endswith("s") else f"{last_name}'"
