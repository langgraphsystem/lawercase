"""RFE (Request for Evidence) Pattern Analyzer.

Analyzes common RFE patterns from USCIS for EB-1A petitions and
provides recommendations to avoid them.

Based on research:
- Common RFE reasons and patterns
- Two-tier adjudication analysis (regulatory criteria + final merits)
- Success pattern matching from approved cases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RFECategory(str, Enum):
    """Categories of RFE issues."""

    CRITERION_SPECIFIC = "criterion_specific"  # Issues with specific criterion evidence
    GENERAL_EVIDENCE = "general_evidence"  # Overall evidence quality issues
    DOCUMENTATION = "documentation"  # Missing or incomplete documents
    FINAL_MERITS = "final_merits"  # Final merits determination issues
    PROCEDURAL = "procedural"  # Procedural/form issues


class RFEIssueType(str, Enum):
    """Specific types of RFE issues."""

    # Criterion-specific
    AWARDS_NOT_NATIONALLY_RECOGNIZED = "awards_not_nationally_recognized"
    MEMBERSHIP_NOT_REQUIRING_OUTSTANDING = "membership_not_requiring_outstanding"
    PUBLISHED_MATERIAL_SELF_AUTHORED = "published_material_self_authored"
    JUDGING_NOT_ESTABLISHED = "judging_not_established"
    CONTRIBUTION_NOT_MAJOR_SIGNIFICANCE = "contribution_not_major_significance"
    SCHOLARLY_INSUFFICIENT_CITATIONS = "scholarly_insufficient_citations"
    LEADING_ROLE_NOT_DISTINGUISHED_ORG = "leading_role_not_distinguished_org"
    HIGH_SALARY_NO_COMPARISON = "high_salary_no_comparison"

    # General evidence
    INSUFFICIENT_INDEPENDENT_EVIDENCE = "insufficient_independent_evidence"
    NO_THIRD_PARTY_VERIFICATION = "no_third_party_verification"
    OUTDATED_EVIDENCE = "outdated_evidence"
    INCONSISTENT_INFORMATION = "inconsistent_information"

    # Documentation
    MISSING_TRANSLATIONS = "missing_translations"
    MISSING_CERTIFICATIONS = "missing_certifications"
    INCOMPLETE_FORMS = "incomplete_forms"

    # Final merits
    NO_SUSTAINED_ACCLAIM = "no_sustained_acclaim"
    NOT_TOP_OF_FIELD = "not_top_of_field"
    NO_US_BENEFIT = "no_us_benefit"


@dataclass
class RFEPattern:
    """A known RFE pattern with remediation guidance."""

    pattern_id: str
    issue_type: RFEIssueType
    category: RFECategory
    title: str
    description: str
    common_triggers: list[str] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)
    example_language: str = ""
    frequency: float = 0.0  # How often this RFE occurs (0-1)
    severity: str = "medium"  # low, medium, high


@dataclass
class RFERiskAssessment:
    """Assessment of RFE risk for a case."""

    case_id: str
    potential_issues: list[RFEPattern] = field(default_factory=list)
    risk_score: float = 0.0  # 0-100
    risk_level: str = "medium"  # low, medium, high, critical

    # Specific weaknesses
    criterion_weaknesses: dict[str, list[str]] = field(default_factory=dict)
    general_weaknesses: list[str] = field(default_factory=list)
    final_merits_concerns: list[str] = field(default_factory=list)

    # Recommendations
    immediate_actions: list[str] = field(default_factory=list)
    evidence_to_add: list[str] = field(default_factory=list)
    documents_to_revise: list[str] = field(default_factory=list)

    assessed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SuccessPattern:
    """Pattern from successful EB-1A approvals."""

    pattern_id: str
    criterion: str
    description: str
    evidence_types: list[str] = field(default_factory=list)
    key_elements: list[str] = field(default_factory=list)
    example_language: str = ""
    success_rate: float = 0.0


class RFEAnalyzer:
    """
    Analyzes RFE patterns and provides recommendations.

    Features:
    - Known RFE pattern matching
    - Proactive issue detection
    - Remediation guidance
    - Success pattern recommendations
    """

    # Known RFE patterns from USCIS adjudications
    KNOWN_PATTERNS: list[RFEPattern] = [
        # Criterion-specific RFEs
        RFEPattern(
            pattern_id="rfe_awards_1",
            issue_type=RFEIssueType.AWARDS_NOT_NATIONALLY_RECOGNIZED,
            category=RFECategory.CRITERION_SPECIFIC,
            title="Awards Not Nationally/Internationally Recognized",
            description="USCIS questions whether the awards are actually recognized at a national or international level",
            common_triggers=[
                "Local or regional awards only",
                "Company-internal awards",
                "Awards without documented selection criteria",
                "No evidence of competitive selection process",
            ],
            remediation_steps=[
                "Provide evidence of award's national/international scope",
                "Document the selection criteria and process",
                "Show number of applicants/nominees vs recipients",
                "Include press coverage or announcements of the award",
                "Obtain letter from awarding organization explaining significance",
            ],
            example_language=(
                "The petitioner must demonstrate that the award is a nationally or "
                "internationally recognized prize or award for excellence in the field. "
                "Evidence should include documentation of the criteria for granting the "
                "award, the significance of the award, and the number of recipients."
            ),
            frequency=0.25,
            severity="high",
        ),
        RFEPattern(
            pattern_id="rfe_membership_1",
            issue_type=RFEIssueType.MEMBERSHIP_NOT_REQUIRING_OUTSTANDING,
            category=RFECategory.CRITERION_SPECIFIC,
            title="Membership Does Not Require Outstanding Achievements",
            description="USCIS questions whether the organization requires outstanding achievements as judged by recognized experts",
            common_triggers=[
                "Organizations open to general membership",
                "Membership based only on payment or education level",
                "No peer review process for admission",
                "Insufficient evidence of selection criteria",
            ],
            remediation_steps=[
                "Provide organization's bylaws showing membership requirements",
                "Document the peer review or selection process",
                "Show rejection rate or selective nature of membership",
                "Include statement from organization about membership criteria",
                "Demonstrate that members are recognized experts",
            ],
            frequency=0.20,
            severity="high",
        ),
        RFEPattern(
            pattern_id="rfe_contribution_1",
            issue_type=RFEIssueType.CONTRIBUTION_NOT_MAJOR_SIGNIFICANCE,
            category=RFECategory.CRITERION_SPECIFIC,
            title="Contributions Not of Major Significance",
            description="USCIS questions whether contributions are truly original and of major significance to the field",
            common_triggers=[
                "Routine work presented as original",
                "No evidence of adoption or impact",
                "Only self-assessment of significance",
                "No expert letters explaining significance",
            ],
            remediation_steps=[
                "Obtain letters from independent experts explaining significance",
                "Document how the contribution has been adopted by others",
                "Show citations to work or references in publications",
                "Provide evidence of industry impact (patents, licensing)",
                "Include comparative analysis showing originality",
            ],
            example_language=(
                "The petitioner must show that the contributions are original, "
                "meaning they were not previously known or practiced in the field, "
                "and of major significance, meaning they have had a notable impact "
                "on the field as a whole."
            ),
            frequency=0.30,
            severity="high",
        ),
        RFEPattern(
            pattern_id="rfe_scholarly_1",
            issue_type=RFEIssueType.SCHOLARLY_INSUFFICIENT_CITATIONS,
            category=RFECategory.CRITERION_SPECIFIC,
            title="Insufficient Evidence of Scholarly Impact",
            description="USCIS questions whether publications have significant impact in the field",
            common_triggers=[
                "Low citation counts",
                "Publications in low-impact journals",
                "No citation report provided",
                "Self-citations counted",
            ],
            remediation_steps=[
                "Provide comprehensive citation report from Google Scholar or Web of Science",
                "Highlight highly-cited publications",
                "Document journal impact factors",
                "Show how work has been cited by others in the field",
                "Include expert letters discussing significance of publications",
            ],
            frequency=0.22,
            severity="medium",
        ),
        RFEPattern(
            pattern_id="rfe_salary_1",
            issue_type=RFEIssueType.HIGH_SALARY_NO_COMPARISON,
            category=RFECategory.CRITERION_SPECIFIC,
            title="No Comparative Evidence for High Salary",
            description="USCIS requires evidence comparing salary to others in the field",
            common_triggers=[
                "No industry salary data provided",
                "Comparison to wrong geographic area",
                "Comparison to wrong position level",
                "No percentile ranking shown",
            ],
            remediation_steps=[
                "Provide industry salary surveys for the specific position",
                "Show salary percentile ranking in the field",
                "Include geographic-specific comparisons",
                "Document total compensation (not just base salary)",
                "Obtain expert opinion on salary significance",
            ],
            frequency=0.15,
            severity="medium",
        ),
        # General evidence RFEs
        RFEPattern(
            pattern_id="rfe_independent_1",
            issue_type=RFEIssueType.INSUFFICIENT_INDEPENDENT_EVIDENCE,
            category=RFECategory.GENERAL_EVIDENCE,
            title="Insufficient Independent Evidence",
            description="USCIS notes that most evidence is self-serving without third-party verification",
            common_triggers=[
                "Only recommendation letters from colleagues",
                "No press coverage or media articles",
                "No independent citation reports",
                "All evidence from employer",
            ],
            remediation_steps=[
                "Obtain letters from independent experts who don't know petitioner",
                "Include press coverage or media articles about work",
                "Add independent citation reports",
                "Provide third-party validation of claims",
                "Include evidence from external organizations",
            ],
            frequency=0.35,
            severity="high",
        ),
        # Final merits RFEs
        RFEPattern(
            pattern_id="rfe_final_1",
            issue_type=RFEIssueType.NO_SUSTAINED_ACCLAIM,
            category=RFECategory.FINAL_MERITS,
            title="No Evidence of Sustained National/International Acclaim",
            description="USCIS finds insufficient evidence of ongoing recognition at the top of the field",
            common_triggers=[
                "Evidence of one-time recognition only",
                "No recent achievements",
                "Recognition limited to local level",
                "No evidence of ongoing acclaim",
            ],
            remediation_steps=[
                "Document continuing recognition over time",
                "Show trajectory of achievements (not just one event)",
                "Provide evidence of national/international scope",
                "Include recent awards, publications, or recognitions",
                "Demonstrate ongoing expert status in the field",
            ],
            example_language=(
                "The petitioner must demonstrate sustained national or international "
                "acclaim and that his or her achievements have been recognized in the "
                "field through extensive documentation."
            ),
            frequency=0.28,
            severity="high",
        ),
    ]

    # Success patterns from approved cases
    SUCCESS_PATTERNS: list[SuccessPattern] = [
        SuccessPattern(
            pattern_id="success_tech_1",
            criterion="original_contribution",
            description="Strong original contribution evidence for tech professionals",
            evidence_types=[
                "Patents with citations",
                "Open source contributions with stars/forks",
                "Technical publications",
                "Expert letters from industry leaders",
            ],
            key_elements=[
                "Quantifiable impact (users, downloads, adoptions)",
                "Independent expert validation",
                "Media coverage of innovation",
                "Commercial licensing or acquisition",
            ],
            success_rate=0.85,
        ),
        SuccessPattern(
            pattern_id="success_researcher_1",
            criterion="scholarly_articles",
            description="Strong scholarly evidence for researchers",
            evidence_types=[
                "High-impact journal publications",
                "Citation report showing 100+ citations",
                "Invited reviews or editorials",
                "Conference keynotes",
            ],
            key_elements=[
                "H-index above field median",
                "Multiple first-author publications",
                "Citations from independent researchers",
                "Impact factor documentation",
            ],
            success_rate=0.80,
        ),
    ]

    def __init__(self):
        """Initialize RFE Analyzer."""
        self._analysis_history: list[RFERiskAssessment] = []
        logger.info("RFEAnalyzer initialized")

    def analyze_case(
        self,
        case_id: str,
        evidence_assessment: Any,
        documents: list[Any] | None = None,
    ) -> RFERiskAssessment:
        """
        Analyze a case for RFE risk.

        Args:
            case_id: Case identifier
            evidence_assessment: CaseEvidenceAssessment from EvidenceClassifier
            documents: Optional list of document classifications

        Returns:
            RFERiskAssessment with detailed analysis
        """
        assessment = RFERiskAssessment(case_id=case_id)

        # Match known RFE patterns
        for pattern in self.KNOWN_PATTERNS:
            if self._pattern_applies(pattern, evidence_assessment):
                assessment.potential_issues.append(pattern)

        # Analyze criterion-specific weaknesses
        assessment.criterion_weaknesses = self._analyze_criterion_weaknesses(evidence_assessment)

        # Analyze general evidence weaknesses
        assessment.general_weaknesses = self._analyze_general_weaknesses(evidence_assessment)

        # Analyze final merits concerns
        assessment.final_merits_concerns = self._analyze_final_merits(evidence_assessment)

        # Calculate risk score
        assessment.risk_score = self._calculate_risk_score(assessment)
        assessment.risk_level = self._determine_risk_level(assessment.risk_score)

        # Generate recommendations
        assessment.immediate_actions = self._generate_immediate_actions(assessment)
        assessment.evidence_to_add = self._identify_evidence_gaps(assessment)
        assessment.documents_to_revise = self._identify_documents_to_revise(assessment)

        self._analysis_history.append(assessment)

        logger.info(
            "RFE analysis complete",
            case_id=case_id,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            issues_count=len(assessment.potential_issues),
        )

        return assessment

    def get_remediation_guide(
        self,
        issue_type: RFEIssueType,
    ) -> dict[str, Any]:
        """
        Get detailed remediation guide for a specific issue.

        Args:
            issue_type: The RFE issue type

        Returns:
            Remediation guide with steps and examples
        """
        for pattern in self.KNOWN_PATTERNS:
            if pattern.issue_type == issue_type:
                return {
                    "title": pattern.title,
                    "description": pattern.description,
                    "remediation_steps": pattern.remediation_steps,
                    "example_language": pattern.example_language,
                    "common_triggers": pattern.common_triggers,
                    "severity": pattern.severity,
                }

        return {"error": f"Unknown issue type: {issue_type}"}

    def get_success_patterns(
        self,
        criterion: str | None = None,
    ) -> list[SuccessPattern]:
        """
        Get success patterns, optionally filtered by criterion.

        Args:
            criterion: Optional criterion to filter by

        Returns:
            List of relevant success patterns
        """
        if criterion:
            return [p for p in self.SUCCESS_PATTERNS if p.criterion == criterion]
        return self.SUCCESS_PATTERNS

    def _pattern_applies(
        self,
        pattern: RFEPattern,
        evidence_assessment: Any,
    ) -> bool:
        """Check if an RFE pattern applies to the case."""
        # Simplified logic - in production would be more sophisticated
        if pattern.category == RFECategory.CRITERION_SPECIFIC:
            # Check if relevant criterion is weak
            criterion_name = pattern.issue_type.value.split("_")[0]
            if hasattr(evidence_assessment, "criteria_weak"):
                for crit in evidence_assessment.criteria_weak:
                    if criterion_name in crit.value.lower():
                        return True

        elif pattern.category == RFECategory.GENERAL_EVIDENCE:
            # Check general evidence quality
            if hasattr(evidence_assessment, "overall_score"):
                if evidence_assessment.overall_score < 60:
                    return True

        elif pattern.category == RFECategory.FINAL_MERITS:
            # Check criteria count
            if hasattr(evidence_assessment, "criteria_met"):
                if len(evidence_assessment.criteria_met) < 3:
                    return True

        return False

    def _analyze_criterion_weaknesses(
        self,
        evidence_assessment: Any,
    ) -> dict[str, list[str]]:
        """Analyze weaknesses in criterion evidence."""
        weaknesses: dict[str, list[str]] = {}

        if not hasattr(evidence_assessment, "criterion_evidence"):
            return weaknesses

        for criterion, evidence in evidence_assessment.criterion_evidence.items():
            criterion_weaknesses = []

            if evidence.confidence < 0.5:
                criterion_weaknesses.append("Low overall evidence confidence")

            if evidence.evidence_strength == "weak":
                criterion_weaknesses.append("Insufficient supporting documents")

            if evidence.missing_elements:
                criterion_weaknesses.extend(evidence.missing_elements)

            if criterion_weaknesses:
                weaknesses[criterion.value] = criterion_weaknesses

        return weaknesses

    def _analyze_general_weaknesses(
        self,
        evidence_assessment: Any,
    ) -> list[str]:
        """Analyze general evidence weaknesses."""
        weaknesses = []

        if hasattr(evidence_assessment, "rfe_risk_factors"):
            weaknesses.extend(evidence_assessment.rfe_risk_factors)

        if hasattr(evidence_assessment, "consistency_issues"):
            weaknesses.extend(evidence_assessment.consistency_issues)

        return weaknesses

    def _analyze_final_merits(
        self,
        evidence_assessment: Any,
    ) -> list[str]:
        """Analyze final merits determination concerns."""
        concerns = []

        if hasattr(evidence_assessment, "criteria_met"):
            criteria_count = len(evidence_assessment.criteria_met)
            if criteria_count < 3:
                concerns.append(f"Only {criteria_count} criteria met; need at least 3 for EB-1A")

        # Check for sustained acclaim
        if hasattr(evidence_assessment, "overall_score"):
            if evidence_assessment.overall_score < 50:
                concerns.append(
                    "Evidence may not demonstrate sustained national/international acclaim"
                )

        return concerns

    def _calculate_risk_score(self, assessment: RFERiskAssessment) -> float:
        """Calculate overall RFE risk score."""
        score = 0.0

        # Add points for each potential issue
        for issue in assessment.potential_issues:
            severity_points = {"low": 5, "medium": 10, "high": 20}
            score += severity_points.get(issue.severity, 10)
            score += issue.frequency * 20  # Weight by frequency

        # Add points for weaknesses
        for weaknesses in assessment.criterion_weaknesses.values():
            score += len(weaknesses) * 5

        score += len(assessment.general_weaknesses) * 8
        score += len(assessment.final_merits_concerns) * 15

        return min(100, score)

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        if score >= 70:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 30:
            return "medium"
        return "low"

    def _generate_immediate_actions(self, assessment: RFERiskAssessment) -> list[str]:
        """Generate immediate action items."""
        actions = []

        # Address high-severity issues first
        for issue in assessment.potential_issues:
            if issue.severity == "high":
                actions.append(f"Address: {issue.title}")
                actions.extend(issue.remediation_steps[:2])

        # Address final merits concerns
        if assessment.final_merits_concerns:
            actions.append("Review and strengthen final merits evidence")

        return actions[:10]

    def _identify_evidence_gaps(self, assessment: RFERiskAssessment) -> list[str]:
        """Identify evidence that should be added."""
        evidence = []

        for weaknesses in assessment.criterion_weaknesses.values():
            for weakness in weaknesses:
                if "missing" in weakness.lower():
                    evidence.append(weakness)

        # Check for common missing evidence types
        common_missing = [
            "Independent expert letters",
            "Citation report",
            "Media coverage",
            "Comparative salary data",
        ]

        for item in common_missing:
            if any(item.lower() in w.lower() for w in assessment.general_weaknesses):
                evidence.append(f"Add: {item}")

        return list(set(evidence))

    def _identify_documents_to_revise(self, assessment: RFERiskAssessment) -> list[str]:
        """Identify documents that should be revised."""
        documents = []

        # Look for quality issues in potential issues
        for issue in assessment.potential_issues:
            if "documentation" in issue.category.value.lower():
                documents.append(f"Revise documentation for: {issue.title}")

        return documents


# Singleton
_rfe_analyzer: RFEAnalyzer | None = None


def get_rfe_analyzer() -> RFEAnalyzer:
    """Get or create global RFEAnalyzer instance."""
    global _rfe_analyzer

    if _rfe_analyzer is None:
        _rfe_analyzer = RFEAnalyzer()

    return _rfe_analyzer
