"""
Base classes for EB-1A Criteria.

Provides abstract base class that all criterion classes inherit from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CriterionType(str, Enum):
    """Types of EB-1A criteria per 8 CFR 204.5(h)(3)."""

    AWARDS = "awards"
    MEMBERSHIP = "membership"
    PUBLISHED_MATERIAL = "published_material"
    JUDGING = "judging"
    ORIGINAL_CONTRIBUTIONS = "original_contributions"
    SCHOLARLY_ARTICLES = "scholarly_articles"
    EXHIBITIONS = "exhibitions"
    LEADING_ROLE = "leading_role"
    HIGH_SALARY = "high_salary"
    COMMERCIAL_SUCCESS = "commercial_success"
    COMPARABLE_EVIDENCE = "comparable_evidence"


class EvidenceStrength(str, Enum):
    """Strength rating for evidence."""

    EXCEPTIONAL = "exceptional"  # Превосходно - очень сильное доказательство
    STRONG = "strong"  # Сильное - убедительное доказательство
    MODERATE = "moderate"  # Умеренное - требует дополнительной поддержки
    WEAK = "weak"  # Слабое - значительные пробелы
    INSUFFICIENT = "insufficient"  # Недостаточно - не соответствует критерию


@dataclass
class Evidence:
    """Evidence item for a criterion."""

    id: str
    title: str
    description: str
    document_type: str
    source: str
    file_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvaluationResult:
    """Result of criterion evaluation."""

    criterion_type: CriterionType
    strength: EvidenceStrength
    score: float  # 0.0 - 1.0
    part1_analysis: str  # Анализ первой части (получение/наличие)
    part2_analysis: str  # Анализ второй части (признание/значимость)
    evidence_summary: list[str]
    missing_documents: list[str]
    recommendations: list[str]
    draft_petition_text: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "criterion_type": self.criterion_type.value,
            "strength": self.strength.value,
            "score": self.score,
            "part1_analysis": self.part1_analysis,
            "part2_analysis": self.part2_analysis,
            "evidence_summary": self.evidence_summary,
            "missing_documents": self.missing_documents,
            "recommendations": self.recommendations,
            "draft_petition_text": self.draft_petition_text,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result of petition text validation."""

    is_valid: bool
    issues: list[str]
    suggestions: list[str]
    missing_elements: list[str]
    score: float  # 0.0 - 1.0


@dataclass
class PetitionSection:
    """Generated petition section for a criterion."""

    criterion_type: CriterionType
    title: str
    content: str
    attachments: list[str]
    word_count: int
    created_at: datetime = field(default_factory=datetime.utcnow)


class CriterionBase(ABC):
    """
    Abstract base class for EB-1A criterion evaluation.

    Each criterion class must implement:
    - PROMPT: Full evaluation prompt from the document
    - CRITERION_TYPE: The type of criterion
    - evaluate(): Evaluate evidence against the criterion
    - write_section(): Generate petition section text
    - validate(): Validate existing petition text
    """

    # To be overridden by subclasses
    PROMPT: str = ""
    CRITERION_TYPE: CriterionType = CriterionType.AWARDS
    CFR_REFERENCE: str = ""
    TITLE_EN: str = ""
    TITLE_RU: str = ""

    def __init__(
        self,
        llm_router: Any | None = None,
        memory_manager: Any | None = None,
    ):
        """
        Initialize the criterion.

        Args:
            llm_router: LLM router for API calls
            memory_manager: Memory manager for context
        """
        self.llm_router = llm_router
        self.memory_manager = memory_manager

    @abstractmethod
    async def evaluate(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Evaluate evidence against this criterion.

        Used by EB1Agent for criteria assessment.

        Args:
            evidence: List of evidence items
            case_context: Additional case context

        Returns:
            EvaluationResult with analysis
        """
        pass

    @abstractmethod
    async def write_section(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> PetitionSection:
        """
        Generate petition section text for this criterion.

        Used by WriterAgent for document generation.

        Args:
            evidence: List of evidence items
            case_context: Additional case context

        Returns:
            PetitionSection with generated text
        """
        pass

    @abstractmethod
    async def validate(
        self,
        petition_text: str,
        evidence: list[Evidence] | None = None,
    ) -> ValidationResult:
        """
        Validate petition text for this criterion.

        Used by ValidatorAgent for quality checks.

        Args:
            petition_text: Text to validate
            evidence: Optional evidence for cross-reference

        Returns:
            ValidationResult with issues and suggestions
        """
        pass

    def get_prompt(
        self,
        evidence: list[Evidence],
        case_context: dict[str, Any] | None = None,
    ) -> str:
        """
        Format the evaluation prompt with evidence and context.

        Args:
            evidence: List of evidence items
            case_context: Additional case context

        Returns:
            Formatted prompt string
        """
        # Format evidence list
        evidence_str = ""
        for i, ev in enumerate(evidence, 1):
            evidence_str += f"""
{i}. {ev.title}
   Description: {ev.description}
   Type: {ev.document_type}
   Source: {ev.source}
"""

        if not evidence_str:
            evidence_str = "No evidence provided for this criterion yet."

        # Format case context
        context_str = ""
        if case_context:
            context_str = "\n".join(
                f"- {k}: {v}"
                for k, v in case_context.items()
                if k not in ["evidence", "documents"]
            )

        return self.PROMPT.format(
            evidence_list=evidence_str,
            case_context=context_str or "No additional context provided.",
        )

    def _calculate_strength(self, score: float) -> EvidenceStrength:
        """Calculate evidence strength from score."""
        if score >= 0.9:
            return EvidenceStrength.EXCEPTIONAL
        elif score >= 0.75:
            return EvidenceStrength.STRONG
        elif score >= 0.5:
            return EvidenceStrength.MODERATE
        elif score >= 0.25:
            return EvidenceStrength.WEAK
        else:
            return EvidenceStrength.INSUFFICIENT


__all__ = [
    "CriterionBase",
    "CriterionType",
    "Evidence",
    "EvaluationResult",
    "EvidenceStrength",
    "PetitionSection",
    "ValidationResult",
]
