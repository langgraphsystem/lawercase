"""EB-1A petition validator for quality and regulatory compliance.

This module validates EB-1A petitions against:
- USCIS regulatory requirements (8 CFR § 204.5(h)(3))
- Legal precedents (Kazarian, Visinscaia, etc.)
- Best practices for petition writing
- Evidence quality and sufficiency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..eb1a_coordinator import EB1ACriterion, EB1APetitionResult, SectionContent


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Must fix before filing
    WARNING = "warning"  # Should fix, may impact approval
    INFO = "info"  # Informational, nice to have


@dataclass
class ValidationIssue:
    """Single validation issue found in petition."""

    severity: ValidationSeverity
    category: str  # e.g., "evidence", "legal", "formatting"
    criterion: EB1ACriterion | None
    message: str
    suggestion: str  # How to fix
    location: str | None = None  # Section/page reference


@dataclass
class ValidationResult:
    """Result of petition validation."""

    is_valid: bool  # Overall pass/fail
    score: float  # Quality score 0.0-1.0
    issues: list[ValidationIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)

    @property
    def critical_issues(self) -> list[ValidationIssue]:
        """Get critical issues that must be fixed."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def info(self) -> list[ValidationIssue]:
        """Get informational issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]


class EB1AValidator:
    """
    Comprehensive validator for EB-1A petitions.

    Validates:
    1. Regulatory compliance (minimum 3 criteria, proper evidence)
    2. Evidence quality and relevance
    3. Legal citations and precedents
    4. Writing quality and persuasiveness
    5. Formatting and structure

    Example:
        >>> validator = EB1AValidator()
        >>> result = validator.validate(petition_result)
        >>> if not result.is_valid:
        ...     for issue in result.critical_issues:
        ...         print(f"CRITICAL: {issue.message}")
    """

    def __init__(self, strict: bool = True):
        """
        Initialize validator.

        Args:
            strict: If True, apply stricter validation rules
        """
        self.strict = strict

    def validate(self, petition: EB1APetitionResult) -> ValidationResult:
        """
        Validate complete EB-1A petition.

        Args:
            petition: Generated petition result

        Returns:
            Validation result with issues and score
        """
        issues: list[ValidationIssue] = []
        passed: list[str] = []
        failed: list[str] = []

        # 1. Validate minimum criteria requirement
        self._validate_minimum_criteria(petition, issues, passed, failed)

        # 2. Validate each section
        for criterion, section in petition.sections.items():
            self._validate_section(criterion, section, issues, passed, failed)

        # 3. Validate evidence portfolio
        self._validate_evidence_portfolio(petition, issues, passed, failed)

        # 4. Validate legal citations
        self._validate_legal_citations(petition, issues, passed, failed)

        # 5. Validate content quality
        self._validate_content_quality(petition, issues, passed, failed)

        # 6. Validate structure and formatting
        self._validate_structure(petition, issues, passed, failed)

        # Calculate overall validity and score
        has_critical = any(i.severity == ValidationSeverity.CRITICAL for i in issues)
        is_valid = not has_critical

        # Score calculation
        score = self._calculate_score(petition, issues, passed, failed)

        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues,
            passed_checks=passed,
            failed_checks=failed,
        )

    def _validate_minimum_criteria(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate that petition meets minimum 3 criteria requirement."""
        check_name = "Minimum 3 criteria requirement"

        if petition.criteria_coverage < 3:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="regulatory",
                    criterion=None,
                    message=(
                        f"Petition only covers {petition.criteria_coverage} criteria. "
                        "Minimum 3 required by 8 CFR § 204.5(h)(3)."
                    ),
                    suggestion="Develop evidence for additional criteria to meet minimum requirement.",
                    location="Overall structure",
                )
            )
            failed.append(check_name)
        else:
            passed.append(check_name)

        # Recommendation for more than minimum
        if petition.criteria_coverage == 3 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="strategy",
                    criterion=None,
                    message="Petition only meets minimum 3 criteria. Consider adding more for stronger case.",
                    suggestion="Develop evidence for 1-2 additional criteria to strengthen petition.",
                    location="Overall structure",
                )
            )

    def _validate_section(
        self,
        criterion: EB1ACriterion,
        section: SectionContent,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate individual criterion section."""
        criterion_name = criterion.value

        # Check confidence score
        if section.confidence_score < 0.5:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="evidence",
                    criterion=criterion,
                    message=f"Section has low confidence score ({section.confidence_score:.2f}).",
                    suggestion="Strengthen evidence or remove this criterion and add stronger one.",
                    location=f"Section: {criterion_name}",
                )
            )
            failed.append(f"{criterion_name} confidence")
        elif section.confidence_score < 0.7:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="evidence",
                    criterion=criterion,
                    message=f"Section has moderate confidence score ({section.confidence_score:.2f}).",
                    suggestion="Consider adding more evidence or stronger examples.",
                    location=f"Section: {criterion_name}",
                )
            )
            failed.append(f"{criterion_name} confidence")
        else:
            passed.append(f"{criterion_name} confidence")

        # Check evidence references
        if not section.evidence_references:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="evidence",
                    criterion=criterion,
                    message="Section has no evidence references.",
                    suggestion="Add exhibit references to support claims.",
                    location=f"Section: {criterion_name}",
                )
            )
            failed.append(f"{criterion_name} evidence")
        elif len(section.evidence_references) < 2 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="evidence",
                    criterion=criterion,
                    message=f"Section only has {len(section.evidence_references)} evidence item(s).",
                    suggestion="Add more evidence items (recommend 3-5 per criterion).",
                    location=f"Section: {criterion_name}",
                )
            )
        else:
            passed.append(f"{criterion_name} evidence")

        # Check word count
        if section.word_count < 200:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="content",
                    criterion=criterion,
                    message=f"Section is very short ({section.word_count} words).",
                    suggestion="Expand section with more detail and analysis (target 300-500 words).",
                    location=f"Section: {criterion_name}",
                )
            )
        elif section.word_count > 1000:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="content",
                    criterion=criterion,
                    message=f"Section is very long ({section.word_count} words).",
                    suggestion="Consider condensing to focus on strongest evidence.",
                    location=f"Section: {criterion_name}",
                )
            )
        else:
            passed.append(f"{criterion_name} length")

    def _validate_evidence_portfolio(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate overall evidence portfolio."""
        check_name = "Evidence portfolio sufficiency"

        if petition.total_exhibits < 10:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="evidence",
                    criterion=None,
                    message=f"Limited evidence portfolio ({petition.total_exhibits} exhibits).",
                    suggestion="Add more supporting evidence (recommend 15-20 exhibits).",
                    location="Evidence portfolio",
                )
            )
            failed.append(check_name)
        elif petition.total_exhibits < 15 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="evidence",
                    criterion=None,
                    message=f"Good but not comprehensive evidence ({petition.total_exhibits} exhibits).",
                    suggestion="Consider adding 3-5 more exhibits for stronger case.",
                    location="Evidence portfolio",
                )
            )
        else:
            passed.append(check_name)

    def _validate_legal_citations(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate legal citations and precedents."""
        check_name = "Legal citations"

        total_citations = sum(len(s.legal_citations) for s in petition.sections.values())

        if total_citations == 0 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="legal",
                    criterion=None,
                    message="No legal precedents cited.",
                    suggestion=(
                        "Add citations to relevant cases (e.g., Kazarian v. USCIS) "
                        "to strengthen legal arguments."
                    ),
                    location="Legal citations",
                )
            )
            failed.append(check_name)
        elif total_citations < 3 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="legal",
                    criterion=None,
                    message=f"Limited legal citations ({total_citations}).",
                    suggestion="Consider adding 2-3 more relevant precedent citations.",
                    location="Legal citations",
                )
            )
        else:
            passed.append(check_name)

    def _validate_content_quality(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate overall content quality."""
        # Check executive summary
        if not petition.executive_summary:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="content",
                    criterion=None,
                    message="Missing executive summary.",
                    suggestion="Add compelling executive summary introducing beneficiary.",
                    location="Executive summary",
                )
            )
            failed.append("Executive summary")
        else:
            passed.append("Executive summary")

        # Check conclusion
        if not petition.conclusion:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="content",
                    criterion=None,
                    message="Missing conclusion.",
                    suggestion="Add strong conclusion tying together all evidence.",
                    location="Conclusion",
                )
            )
            failed.append("Conclusion")
        else:
            passed.append("Conclusion")

        # Check overall score
        if petition.overall_score < 0.6:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="quality",
                    criterion=None,
                    message=f"Low overall quality score ({petition.overall_score:.2f}).",
                    suggestion="Review and strengthen weak sections before filing.",
                    location="Overall quality",
                )
            )
            failed.append("Overall quality")
        else:
            passed.append("Overall quality")

    def _validate_structure(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> None:
        """Validate petition structure and formatting."""
        # Check word count
        if petition.total_word_count < 2000:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="formatting",
                    criterion=None,
                    message=f"Petition is quite short ({petition.total_word_count} words).",
                    suggestion="Expand with more detail and analysis (target 3000-5000 words).",
                    location="Overall structure",
                )
            )
            failed.append("Word count")
        elif petition.total_word_count > 8000 and self.strict:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="formatting",
                    criterion=None,
                    message=f"Petition is quite long ({petition.total_word_count} words).",
                    suggestion="Consider condensing to maintain reader attention.",
                    location="Overall structure",
                )
            )
        else:
            passed.append("Word count")

    def _calculate_score(
        self,
        petition: EB1APetitionResult,
        issues: list[ValidationIssue],
        passed: list[str],
        failed: list[str],
    ) -> float:
        """Calculate overall validation score."""
        # Start with petition's overall score
        base_score = petition.overall_score

        # Deduct points for issues
        critical_penalty = (
            len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]) * 0.15
        )
        warning_penalty = (
            len([i for i in issues if i.severity == ValidationSeverity.WARNING]) * 0.05
        )

        # Add points for passed checks
        total_checks = len(passed) + len(failed)
        if total_checks > 0:
            pass_rate = len(passed) / total_checks
            pass_bonus = (pass_rate - 0.5) * 0.2  # Bonus for >50% pass rate
        else:
            pass_bonus = 0

        final_score = base_score - critical_penalty - warning_penalty + pass_bonus

        return max(0.0, min(1.0, final_score))
