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
import re

from ..eb1a_coordinator import EB1ACriterion, EB1APetitionResult, SectionContent
from .checklists import ComplianceChecklist


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
class CheckResult:
    """Result of a single checklist item validation."""

    check_id: str  # Unique identifier for the check
    description: str  # What was checked
    passed: bool  # True if check passed
    severity: ValidationSeverity = ValidationSeverity.INFO
    evidence_found: str | None = None  # What evidence was found (if any)
    suggestion: str | None = None  # How to fix (if failed)


@dataclass
class SectionValidationResult:
    """Result of validating a single criterion section."""

    criterion: EB1ACriterion
    section_title: str
    is_valid: bool  # Overall section validity
    score: float  # Section quality score 0.0-1.0
    checks: list[CheckResult] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    word_count: int = 0
    evidence_count: int = 0
    citation_count: int = 0

    @property
    def passed_checks(self) -> list[CheckResult]:
        """Get all passed checks."""
        return [c for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [c for c in self.checks if not c.passed]

    @property
    def critical_failures(self) -> list[CheckResult]:
        """Get failed critical checks."""
        return [
            c for c in self.checks if not c.passed and c.severity == ValidationSeverity.CRITICAL
        ]

    @property
    def pass_rate(self) -> float:
        """Calculate check pass rate (0.0-1.0)."""
        if not self.checks:
            return 0.0
        return len(self.passed_checks) / len(self.checks)


@dataclass
class ValidationResult:
    """Result of petition validation."""

    is_valid: bool  # Overall pass/fail
    score: float  # Quality score 0.0-1.0
    issues: list[ValidationIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    section_results: dict[EB1ACriterion, SectionValidationResult] = field(default_factory=dict)

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

    @property
    def total_checks(self) -> int:
        """Total number of checks performed."""
        return len(self.passed_checks) + len(self.failed_checks)

    @property
    def overall_pass_rate(self) -> float:
        """Calculate overall pass rate (0.0-1.0)."""
        if self.total_checks == 0:
            return 0.0
        return len(self.passed_checks) / self.total_checks


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
        section_results: dict[EB1ACriterion, SectionValidationResult] = {}

        # 1. Validate minimum criteria requirement
        self._validate_minimum_criteria(petition, issues, passed, failed)

        # 2. Validate each section with detailed checks
        for criterion, section in petition.sections.items():
            # Basic validation
            self._validate_section(criterion, section, issues, passed, failed)
            # Detailed checklist validation
            section_result = self.validate_section_detailed(criterion, section)
            section_results[criterion] = section_result
            # Add section issues to overall issues
            issues.extend(section_result.issues)

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
            section_results=section_results,
        )

    def validate_section_detailed(
        self, criterion: EB1ACriterion, section: SectionContent
    ) -> SectionValidationResult:
        """
        Perform detailed validation of a single criterion section using checklists.

        This method provides granular, checklist-based validation for each criterion,
        going beyond the basic validation to check specific regulatory requirements.

        Args:
            criterion: The EB-1A criterion being validated
            section: The section content to validate

        Returns:
            Detailed section validation result with all checks

        Example:
            >>> validator = EB1AValidator()
            >>> section_result = validator.validate_section_detailed(
            ...     EB1ACriterion.AWARDS,
            ...     section_content
            ... )
            >>> print(f"Pass rate: {section_result.pass_rate:.1%}")
            >>> for check in section_result.failed_checks:
            ...     print(f"Failed: {check.description}")
        """
        checks: list[CheckResult] = []
        issues: list[ValidationIssue] = []

        # Get criterion-specific checklist
        checklist = ComplianceChecklist.get_criterion_checklist(criterion)

        # Run each checklist item
        for item in checklist:
            check_result = self._run_checklist_item(item, section, criterion)
            checks.append(check_result)

            # Convert failed required checks to issues
            if not check_result.passed and item.required:
                severity = (
                    ValidationSeverity.CRITICAL
                    if item.category == "regulatory"
                    else ValidationSeverity.WARNING
                )
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        category=item.category,
                        criterion=criterion,
                        message=f"Failed: {check_result.description}",
                        suggestion=check_result.suggestion or "Review and strengthen this aspect",
                        location=f"Section: {criterion.value}",
                    )
                )

        # Calculate section metrics
        word_count = section.word_count
        evidence_count = len(section.evidence_references)
        citation_count = len(section.legal_citations)

        # Calculate section score
        score = self._calculate_section_score(section, checks)

        # Determine if section is valid (no critical failures)
        critical_failures = [
            c for c in checks if not c.passed and c.severity == ValidationSeverity.CRITICAL
        ]
        is_valid = len(critical_failures) == 0

        return SectionValidationResult(
            criterion=criterion,
            section_title=section.title,
            is_valid=is_valid,
            score=score,
            checks=checks,
            issues=issues,
            word_count=word_count,
            evidence_count=evidence_count,
            citation_count=citation_count,
        )

    def _run_checklist_item(
        self,
        item: ComplianceChecklist.ChecklistItem,
        section: SectionContent,
        criterion: EB1ACriterion,
    ) -> CheckResult:
        """
        Run a single checklist item against section content.

        This method uses pattern matching and heuristics to determine
        if a checklist requirement is satisfied by the section content.

        Args:
            item: Checklist item to validate
            section: Section content to check
            criterion: Criterion being validated

        Returns:
            Result of the check with pass/fail and evidence
        """
        content = section.content.lower()
        severity = ValidationSeverity.CRITICAL if item.required else ValidationSeverity.WARNING

        # Evidence-based checks
        if "evidence" in item.item_id.lower() or "documentation" in item.item_id.lower():
            if section.evidence_references:
                return CheckResult(
                    check_id=item.item_id,
                    description=item.description,
                    passed=True,
                    severity=severity,
                    evidence_found=f"{len(section.evidence_references)} exhibits referenced",
                    suggestion=None,
                )
            return CheckResult(
                check_id=item.item_id,
                description=item.description,
                passed=False,
                severity=severity,
                evidence_found=None,
                suggestion="Add exhibit references to support this criterion",
            )

        # Content-based heuristics
        passed = False
        evidence_found = None

        # Awards criterion checks
        if criterion == EB1ACriterion.AWARDS:
            if "scope" in item.item_id.lower():
                keywords = ["national", "international", "worldwide", "global"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Scope keywords found" if passed else None
            elif "excellence" in item.item_id.lower():
                keywords = ["excellence", "outstanding", "exceptional", "achievement"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Excellence keywords found" if passed else None
            elif "prestige" in item.item_id.lower():
                keywords = ["prestigious", "renowned", "recognized", "eminent"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Prestige indicators found" if passed else None

        # Membership criterion checks
        elif criterion == EB1ACriterion.MEMBERSHIP:
            if "outstanding" in item.item_id.lower():
                keywords = ["outstanding", "achievements", "selective", "merit"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Merit-based language found" if passed else None
            elif "expert" in item.item_id.lower():
                keywords = ["expert", "peer review", "evaluated", "judged"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Expert evaluation mentioned" if passed else None

        # Press criterion checks
        elif criterion == EB1ACriterion.PRESS:
            if "major" in item.item_id.lower():
                keywords = ["major", "publication", "media", "press", "journal"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Major media mentioned" if passed else None
            elif "about" in item.item_id.lower():
                keywords = ["featured", "profiled", "about", "interview", "article about"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Coverage about beneficiary" if passed else None
            elif "circulation" in item.item_id.lower():
                # Look for numbers that might be circulation
                numbers = re.findall(r"\d{1,3}(?:,\d{3})+", section.content)
                passed = len(numbers) > 0
                evidence_found = f"Circulation numbers found: {numbers[:2]}" if passed else None

        # Judging criterion checks
        elif criterion == EB1ACriterion.JUDGING:
            if "role" in item.item_id.lower():
                keywords = ["judge", "reviewer", "panel", "committee", "evaluation"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Judging role mentioned" if passed else None
            elif "field" in item.item_id.lower():
                # Assume field relevance if criterion is claimed
                passed = True
                evidence_found = "Field relevance assumed"

        # Scholarly articles checks
        elif criterion == EB1ACriterion.SCHOLARLY_ARTICLES:
            if "author" in item.item_id.lower():
                keywords = ["author", "published", "co-author"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Authorship mentioned" if passed else None
            elif "scholarly" in item.item_id.lower():
                keywords = ["peer-reviewed", "journal", "scholarly", "academic"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Scholarly publication type" if passed else None
            elif "citation" in item.item_id.lower():
                # Look for citation metrics
                citation_keywords = ["citations", "cited", "h-index", "impact factor"]
                passed = any(kw in content for kw in citation_keywords)
                evidence_found = "Citation metrics mentioned" if passed else None

        # Original contribution checks
        elif criterion == EB1ACriterion.ORIGINAL_CONTRIBUTION:
            if "original" in item.item_id.lower():
                keywords = ["original", "novel", "innovative", "pioneering", "first"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Originality keywords found" if passed else None
            elif "major" in item.item_id.lower() or "significance" in item.item_id.lower():
                keywords = ["significant", "major", "impact", "breakthrough", "transformative"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Significance keywords found" if passed else None
            elif "impact" in item.item_id.lower():
                keywords = ["adopted", "used by", "implemented", "influenced"]
                passed = any(kw in content for kw in keywords)
                evidence_found = "Impact indicators found" if passed else None

        # Default: check for general content quality
        if not passed and not evidence_found:
            # Minimum word count as proxy for addressing the requirement
            min_words = 50 if item.required else 20
            passed = len(content.split()) >= min_words
            evidence_found = f"Content present ({len(content.split())} words)" if passed else None

        suggestion = None if passed else f"Add specific content addressing: {item.description}"

        return CheckResult(
            check_id=item.item_id,
            description=item.description,
            passed=passed,
            severity=severity,
            evidence_found=evidence_found,
            suggestion=suggestion,
        )

    def _calculate_section_score(self, section: SectionContent, checks: list[CheckResult]) -> float:
        """Calculate quality score for a section (0.0-1.0)."""
        if not checks:
            return section.confidence_score

        # Start with section's confidence score
        base_score = section.confidence_score

        # Calculate check pass rate
        passed_count = len([c for c in checks if c.passed])
        check_pass_rate = passed_count / len(checks) if checks else 0.0

        # Combine scores (60% confidence, 40% checklist completion)
        combined_score = (base_score * 0.6) + (check_pass_rate * 0.4)

        # Penalty for critical failures
        critical_failures = [
            c for c in checks if not c.passed and c.severity == ValidationSeverity.CRITICAL
        ]
        critical_penalty = len(critical_failures) * 0.15

        final_score = max(0.0, min(1.0, combined_score - critical_penalty))
        return final_score

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
