"""EB-1A Petition Coordinator - Main orchestrator for EB-1A petition generation.

This module coordinates the entire EB-1A petition workflow:
1. Evidence research and gathering
2. Section-by-section petition writing (2.1-2.10 criteria)
3. Quality validation and legal compliance
4. PDF assembly with exhibits
5. Final review and recommendations
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ...memory.memory_manager import MemoryManager


class EB1ACriterion(str, Enum):
    """10 criteria for EB-1A extraordinary ability (8 CFR § 204.5(h)(3))."""

    AWARDS = "2.1_awards"  # Receipt of nationally or internationally recognized prizes/awards
    MEMBERSHIP = "2.2_membership"  # Membership in associations requiring outstanding achievements
    PRESS = "2.3_press"  # Published material about the person in major media
    JUDGING = "2.4_judging"  # Participation as a judge of the work of others
    ORIGINAL_CONTRIBUTION = (
        "2.5_original_contribution"  # Original contributions of major significance
    )
    SCHOLARLY_ARTICLES = "2.6_scholarly_articles"  # Authorship of scholarly articles
    ARTISTIC_EXHIBITION = "2.7_artistic_exhibition"  # Artistic exhibitions or showcases
    LEADING_ROLE = "2.8_leading_role"  # Leading or critical role in distinguished organizations
    HIGH_SALARY = "2.9_high_salary"  # High salary or remuneration
    COMMERCIAL_SUCCESS = "2.10_commercial_success"  # Commercial success in performing arts


class EvidenceType(str, Enum):
    """Types of supporting evidence for EB-1A petitions."""

    AWARD_CERTIFICATE = "award_certificate"
    MEMBERSHIP_LETTER = "membership_letter"
    PRESS_ARTICLE = "press_article"
    RECOMMENDATION_LETTER = "recommendation_letter"
    PUBLICATION = "publication"
    CITATION_REPORT = "citation_report"
    PATENT = "patent"
    EMPLOYMENT_LETTER = "employment_letter"
    SALARY_EVIDENCE = "salary_evidence"
    IMPACT_METRICS = "impact_metrics"


class EB1AEvidence(BaseModel):
    """Single piece of evidence supporting EB-1A petition."""

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    criterion: EB1ACriterion
    evidence_type: EvidenceType
    title: str = Field(..., description="Short title of evidence")
    description: str = Field(..., description="Detailed description")
    date: datetime | None = Field(default=None, description="Date of evidence")
    source: str | None = Field(default=None, description="Source/origin of evidence")
    exhibit_number: str | None = Field(default=None, description="Exhibit number (e.g., 'A-1')")
    file_path: str | None = Field(default=None, description="Path to evidence file")
    metadata: dict[str, Any] = Field(default_factory=dict)


class EB1APetitionRequest(BaseModel):
    """Request to generate EB-1A petition."""

    beneficiary_name: str = Field(..., description="Full name of beneficiary")
    field_of_expertise: str = Field(..., description="Field of extraordinary ability")
    country_of_birth: str
    current_position: str
    current_employer: str

    # Evidence portfolio
    evidence: list[EB1AEvidence] = Field(default_factory=list)

    # Criteria to emphasize (must have at least 3)
    primary_criteria: list[EB1ACriterion] = Field(
        ...,
        min_length=3,
        description="Primary criteria to emphasize (need 3 of 10)",
    )

    # Additional context
    background_summary: str | None = Field(default=None, description="Brief background")
    accomplishments: list[str] = Field(default_factory=list, description="Key accomplishments")
    publications: list[dict[str, Any]] = Field(default_factory=list)
    citations_count: int | None = Field(default=None)
    h_index: int | None = Field(default=None)

    # Generation preferences
    tone: str = Field(default="formal", description="professional, formal, persuasive")
    max_pages: int = Field(default=15, ge=5, le=30, description="Target page count")
    include_comparative_analysis: bool = Field(
        default=True, description="Compare beneficiary to peers"
    )


class SectionContent(BaseModel):
    """Generated content for a petition section."""

    criterion: EB1ACriterion
    title: str
    content: str = Field(..., description="Main narrative content")
    evidence_references: list[str] = Field(
        default_factory=list, description="Referenced exhibit numbers"
    )
    legal_citations: list[str] = Field(default_factory=list, description="Legal case citations")
    word_count: int
    confidence_score: float = Field(ge=0.0, le=1.0, description="Quality confidence score")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


class EB1APetitionResult(BaseModel):
    """Complete EB-1A petition generation result."""

    petition_id: str = Field(default_factory=lambda: str(uuid4()))
    beneficiary_name: str
    field_of_expertise: str

    # Generated sections
    executive_summary: str
    sections: dict[EB1ACriterion, SectionContent] = Field(default_factory=dict)
    conclusion: str

    # Quality metrics
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall petition quality")
    criteria_coverage: int = Field(ge=3, le=10, description="Number of criteria covered")
    total_word_count: int
    total_exhibits: int

    # Recommendations
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_time_seconds: float | None = None


class EB1ACoordinator:
    """
    Main coordinator for EB-1A petition generation workflow.

    Orchestrates:
    1. Evidence research and validation
    2. Section-by-section content generation
    3. Quality assurance and legal compliance
    4. Final assembly and recommendations

    Example:
        >>> coordinator = EB1ACoordinator(memory_manager=memory)
        >>> request = EB1APetitionRequest(
        ...     beneficiary_name="Dr. Jane Smith",
        ...     field_of_expertise="Artificial Intelligence",
        ...     country_of_birth="India",
        ...     current_position="Senior AI Researcher",
        ...     current_employer="Tech Corp",
        ...     primary_criteria=[
        ...         EB1ACriterion.AWARDS,
        ...         EB1ACriterion.SCHOLARLY_ARTICLES,
        ...         EB1ACriterion.JUDGING
        ...     ]
        ... )
        >>> result = await coordinator.generate_petition(request)
        >>> print(result.overall_score)
        0.89
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Initialize EB-1A Coordinator.

        Args:
            memory_manager: Memory manager for context and evidence storage
        """
        self.memory = memory_manager or MemoryManager()

        # Will be initialized lazily
        self._section_writers: dict[EB1ACriterion, Any] = {}
        self._evidence_researcher: Any | None = None
        self._validator: Any | None = None

    async def generate_petition(self, request: EB1APetitionRequest) -> EB1APetitionResult:
        """
        Generate complete EB-1A petition from request.

        Args:
            request: Petition generation request with beneficiary info and evidence

        Returns:
            Complete petition with all sections and quality metrics

        Raises:
            ValueError: If request has fewer than 3 primary criteria
        """
        start_time = datetime.utcnow()

        # Validate request
        if len(request.primary_criteria) < 3:
            raise ValueError("EB-1A requires at least 3 of 10 criteria to be satisfied")

        # Step 1: Research and gather additional evidence
        await self._research_evidence(request)

        # Step 2: Generate executive summary
        executive_summary = await self._generate_executive_summary(request)

        # Step 3: Generate each criterion section
        sections: dict[EB1ACriterion, SectionContent] = {}
        for criterion in request.primary_criteria:
            section = await self._generate_section(criterion, request)
            sections[criterion] = section

        # Step 4: Generate conclusion
        conclusion = await self._generate_conclusion(request, sections)

        # Step 5: Calculate quality metrics
        overall_score = self._calculate_overall_score(sections)
        total_word_count = sum(s.word_count for s in sections.values())
        total_exhibits = len(request.evidence)

        # Step 6: Generate recommendations
        strengths = self._identify_strengths(sections)
        weaknesses = self._identify_weaknesses(sections)
        recommendations = self._generate_recommendations(sections, request)

        # Calculate generation time
        generation_time = (datetime.utcnow() - start_time).total_seconds()

        return EB1APetitionResult(
            beneficiary_name=request.beneficiary_name,
            field_of_expertise=request.field_of_expertise,
            executive_summary=executive_summary,
            sections=sections,
            conclusion=conclusion,
            overall_score=overall_score,
            criteria_coverage=len(sections),
            total_word_count=total_word_count,
            total_exhibits=total_exhibits,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            generation_time_seconds=generation_time,
        )

    async def _research_evidence(self, request: EB1APetitionRequest) -> None:
        """
        Research additional evidence using RAG and external sources.

        This method enriches the petition with:
        - Legal precedents and case law
        - Industry statistics and benchmarks
        - Peer comparisons
        - Citation analysis
        """
        # TODO: Implement evidence researcher integration
        # from .evidence_researcher import EvidenceResearcher
        # researcher = self._get_evidence_researcher()
        # additional_evidence = await researcher.research(request)
        # request.evidence.extend(additional_evidence)

    async def _generate_executive_summary(self, request: EB1APetitionRequest) -> str:
        """
        Generate compelling executive summary introducing the beneficiary.

        The summary should:
        - Introduce beneficiary and field of expertise
        - Highlight key achievements
        - Preview the criteria being claimed
        - Establish extraordinary ability
        """
        # Placeholder implementation
        summary = f"""
EXECUTIVE SUMMARY

{request.beneficiary_name} is an individual of extraordinary ability in the field of
{request.field_of_expertise}. This petition demonstrates that {request.beneficiary_name.split()[-1]}
meets at least three of the ten criteria set forth in 8 CFR § 204.5(h)(3), thereby
establishing eligibility for an EB-1A visa classification.

Specifically, this petition will establish that {request.beneficiary_name}:

"""
        for i, criterion in enumerate(request.primary_criteria, 1):
            criterion_name = criterion.value.split("_", 1)[1].replace("_", " ").title()
            summary += f"{i}. Satisfies the criterion for {criterion_name}\n"

        summary += f"""
{request.beneficiary_name}'s work in {request.field_of_expertise} has had significant
impact on the field, as evidenced by the extensive documentation provided in this petition.
The beneficiary's extraordinary ability is further demonstrated through sustained national
and international acclaim, recognition by peers, and contributions that have advanced the
field substantially.
"""
        return summary.strip()

    async def _generate_section(
        self, criterion: EB1ACriterion, request: EB1APetitionRequest
    ) -> SectionContent:
        """
        Generate content for a specific EB-1A criterion section.

        Args:
            criterion: The criterion to write about
            request: Full petition request with evidence

        Returns:
            Generated section with evidence references and quality metrics
        """
        # Get criterion-specific evidence
        relevant_evidence = [e for e in request.evidence if e.criterion == criterion]

        # Placeholder implementation - would delegate to specialized section writers
        criterion_name = criterion.value.split("_", 1)[1].replace("_", " ").title()
        title = f"Criterion: {criterion_name}"

        content = f"""
{title}

[PLACEHOLDER - This section would be generated by a specialized writer for {criterion_name}]

The beneficiary {request.beneficiary_name} satisfies this criterion through the following evidence:

"""
        evidence_refs = []
        for evidence in relevant_evidence:
            content += f"- {evidence.title}\n"
            if evidence.exhibit_number:
                evidence_refs.append(evidence.exhibit_number)

        # Calculate metrics
        word_count = len(content.split())
        confidence_score = 0.7  # Placeholder

        return SectionContent(
            criterion=criterion,
            title=title,
            content=content,
            evidence_references=evidence_refs,
            legal_citations=[],  # Would be populated by writer
            word_count=word_count,
            confidence_score=confidence_score,
            suggestions=["Add more specific examples", "Include peer comparisons"],
        )

    async def _generate_conclusion(
        self, request: EB1APetitionRequest, sections: dict[EB1ACriterion, SectionContent]
    ) -> str:
        """Generate strong conclusion tying together all evidence."""
        conclusion = f"""
CONCLUSION

As demonstrated throughout this petition, {request.beneficiary_name} possesses extraordinary
ability in {request.field_of_expertise}. The beneficiary has satisfied {len(sections)} of the
ten regulatory criteria, exceeding the minimum requirement of three criteria.

The totality of evidence establishes that {request.beneficiary_name} has:
- Achieved sustained national and international acclaim
- Been recognized by peers and experts in the field
- Made original contributions of major significance
- Demonstrated continued excellence and impact

Based on the foregoing, {request.beneficiary_name} clearly qualifies for classification as
an individual of extraordinary ability under INA § 203(b)(1)(A) and 8 CFR § 204.5(h)(3).

We respectfully request that this petition be approved.
"""
        return conclusion.strip()

    def _calculate_overall_score(self, sections: dict[EB1ACriterion, SectionContent]) -> float:
        """Calculate overall petition quality score (0.0-1.0)."""
        if not sections:
            return 0.0

        # Average confidence scores across sections
        scores = [section.confidence_score for section in sections.values()]
        avg_score = sum(scores) / len(scores)

        # Bonus for covering more than 3 criteria
        criteria_bonus = min(0.1, (len(sections) - 3) * 0.02)

        return min(1.0, avg_score + criteria_bonus)

    def _identify_strengths(self, sections: dict[EB1ACriterion, SectionContent]) -> list[str]:
        """Identify strong points of the petition."""
        strengths = []

        # Check for high-confidence sections
        high_confidence = [s for s in sections.values() if s.confidence_score >= 0.8]
        if high_confidence:
            strengths.append(
                f"Strong evidence for {len(high_confidence)} criteria (confidence ≥ 0.8)"
            )

        # Check for good evidence coverage
        total_evidence = sum(len(s.evidence_references) for s in sections.values())
        if total_evidence >= 15:
            strengths.append(f"Comprehensive evidence portfolio ({total_evidence} exhibits)")

        # Check for legal citations
        total_citations = sum(len(s.legal_citations) for s in sections.values())
        if total_citations >= 5:
            strengths.append(f"Well-supported with legal precedents ({total_citations} citations)")

        return strengths

    def _identify_weaknesses(self, sections: dict[EB1ACriterion, SectionContent]) -> list[str]:
        """Identify weak points needing improvement."""
        weaknesses = []

        # Check for low-confidence sections
        low_confidence = [s for s in sections.values() if s.confidence_score < 0.6]
        if low_confidence:
            criteria_names = ", ".join(s.criterion.value for s in low_confidence)
            weaknesses.append(f"Weak evidence for: {criteria_names}")

        # Check for insufficient evidence
        total_evidence = sum(len(s.evidence_references) for s in sections.values())
        if total_evidence < 10:
            weaknesses.append(
                f"Limited evidence portfolio ({total_evidence} exhibits, recommend 15+)"
            )

        # Check for missing legal citations
        sections_without_citations = [s for s in sections.values() if not s.legal_citations]
        if len(sections_without_citations) > len(sections) / 2:
            weaknesses.append("Insufficient legal precedent citations")

        return weaknesses

    def _generate_recommendations(
        self, sections: dict[EB1ACriterion, SectionContent], request: EB1APetitionRequest
    ) -> list[str]:
        """Generate actionable recommendations for improving petition."""
        recommendations = []

        # Analyze each section's suggestions
        all_suggestions = []
        for section in sections.values():
            all_suggestions.extend(section.suggestions)

        # Deduplicate and prioritize
        unique_suggestions = list(set(all_suggestions))
        recommendations.extend(unique_suggestions[:5])  # Top 5

        # Add general recommendations
        if len(sections) == 3:
            recommendations.append(
                "Consider developing evidence for additional criteria (currently at minimum 3)"
            )

        if not request.include_comparative_analysis:
            recommendations.append("Add comparative analysis with peers to strengthen claims")

        return recommendations

    def _get_evidence_researcher(self):
        """Lazy initialization of evidence researcher."""
        if self._evidence_researcher is None:
            # TODO: Initialize EvidenceResearcher
            # from .evidence_researcher import EvidenceResearcher
            # self._evidence_researcher = EvidenceResearcher(self.memory)
            pass
        return self._evidence_researcher
