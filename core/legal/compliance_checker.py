"""Compliance Checker.

Checks documents for compliance with regulations and standards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .document_parser import LegalDocument


class ComplianceStandard(str, Enum):
    """Compliance standards."""

    GDPR = "gdpr"  # General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    SOC2 = "soc2"  # Service Organization Control 2
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard
    FCRA = "fcra"  # Fair Credit Reporting Act
    COPPA = "coppa"  # Children's Online Privacy Protection Act
    ADA = "ada"  # Americans with Disabilities Act
    CUSTOM = "custom"


class ComplianceStatus(str, Enum):
    """Compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    REQUIRES_REVIEW = "requires_review"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceRule:
    """Individual compliance rule."""

    rule_id: str
    standard: ComplianceStandard
    title: str
    description: str
    required_elements: list[str] = field(default_factory=list)
    prohibited_elements: list[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class ComplianceResult:
    """Result of compliance check."""

    document: LegalDocument
    standard: ComplianceStandard
    status: ComplianceStatus
    compliance_score: float  # 0-100
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    missing_elements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)


class ComplianceChecker:
    """
    Check documents for regulatory compliance.

    Features:
    - GDPR compliance checking
    - CCPA compliance checking
    - HIPAA compliance checking
    - Custom rule definition
    - Gap analysis
    - Recommendations generation

    Example:
        >>> checker = ComplianceChecker()
        >>> result = checker.check_compliance(document, ComplianceStandard.GDPR)
        >>> print(f"Status: {result.status}")
        >>> print(f"Score: {result.compliance_score}%")
    """

    def __init__(self):
        """Initialize compliance checker."""
        # Define compliance rules
        self.rules = self._load_compliance_rules()

    def check_compliance(
        self,
        document: LegalDocument,
        standard: ComplianceStandard,
    ) -> ComplianceResult:
        """
        Check document compliance with standard.

        Args:
            document: Legal document to check
            standard: Compliance standard to check against

        Returns:
            Compliance check result
        """
        # Get rules for this standard
        standard_rules = [r for r in self.rules if r.standard == standard]

        if not standard_rules:
            return ComplianceResult(
                document=document,
                standard=standard,
                status=ComplianceStatus.NOT_APPLICABLE,
                compliance_score=0.0,
                warnings=["No rules defined for this standard"],
            )

        # Check each rule
        passed_rules = []
        failed_rules = []
        warnings = []
        missing_elements = []

        for rule in standard_rules:
            rule_passed, rule_warnings, rule_missing = self._check_rule(
                document,
                rule,
            )

            if rule_passed:
                passed_rules.append(rule.rule_id)
            else:
                failed_rules.append(rule.rule_id)

            warnings.extend(rule_warnings)
            missing_elements.extend(rule_missing)

        # Calculate compliance score
        total_rules = len(standard_rules)
        compliance_score = (
            (len(passed_rules) / total_rules * 100) if total_rules > 0 else 0
        )

        # Determine overall status
        status = self._determine_status(compliance_score, failed_rules, standard_rules)

        # Generate recommendations
        recommendations = self._generate_compliance_recommendations(
            failed_rules,
            missing_elements,
            standard_rules,
        )

        return ComplianceResult(
            document=document,
            standard=standard,
            status=status,
            compliance_score=compliance_score,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            warnings=warnings,
            recommendations=recommendations,
            missing_elements=missing_elements,
        )

    def _check_rule(
        self,
        document: LegalDocument,
        rule: ComplianceRule,
    ) -> tuple[bool, list[str], list[str]]:
        """Check a single compliance rule."""
        warnings = []
        missing = []
        passed = True

        # Check for required elements
        for element in rule.required_elements:
            if not self._contains_element(document.content, element):
                passed = False
                missing.append(element)
                warnings.append(
                    f"Missing required element: {element} (Rule: {rule.rule_id})",
                )

        # Check for prohibited elements
        for element in rule.prohibited_elements:
            if self._contains_element(document.content, element):
                passed = False
                warnings.append(
                    f"Contains prohibited element: {element} (Rule: {rule.rule_id})",
                )

        return passed, warnings, missing

    def _contains_element(self, text: str, element: str) -> bool:
        """Check if text contains element (case-insensitive)."""
        # Try exact match first
        if element.lower() in text.lower():
            return True

        # Try as regex pattern
        try:
            if re.search(element, text, re.IGNORECASE):
                return True
        except re.error:
            pass

        return False

    def _determine_status(
        self,
        score: float,
        failed_rules: list[str],
        all_rules: list[ComplianceRule],
    ) -> ComplianceStatus:
        """Determine overall compliance status."""
        # Check if any critical rules failed
        critical_failures = [
            r.rule_id
            for r in all_rules
            if r.rule_id in failed_rules and r.severity == "critical"
        ]

        if critical_failures:
            return ComplianceStatus.NON_COMPLIANT

        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 70:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        elif score >= 50:
            return ComplianceStatus.REQUIRES_REVIEW
        else:
            return ComplianceStatus.NON_COMPLIANT

    def _generate_compliance_recommendations(
        self,
        failed_rules: list[str],
        missing_elements: list[str],
        all_rules: list[ComplianceRule],
    ) -> list[str]:
        """Generate recommendations based on failures."""
        recommendations = []

        # Add specific recommendations for failed rules
        for rule_id in failed_rules:
            rule = next((r for r in all_rules if r.rule_id == rule_id), None)
            if rule:
                recommendations.append(
                    f"Address {rule.title}: {rule.description}",
                )

        # Add recommendations for missing elements
        if missing_elements:
            recommendations.append(
                f"Add the following required elements: {', '.join(set(missing_elements))}",
            )

        return recommendations

    def _load_compliance_rules(self) -> list[ComplianceRule]:
        """Load compliance rules."""
        rules = []

        # GDPR Rules
        rules.extend(
            [
                ComplianceRule(
                    rule_id="GDPR-001",
                    standard=ComplianceStandard.GDPR,
                    title="Right to Access",
                    description="Must provide data subjects right to access their data",
                    required_elements=[
                        r"right\s+to\s+access",
                        r"access\s+(?:your|personal)\s+data",
                    ],
                    severity="high",
                ),
                ComplianceRule(
                    rule_id="GDPR-002",
                    standard=ComplianceStandard.GDPR,
                    title="Right to Erasure",
                    description="Must provide data subjects right to erasure (right to be forgotten)",
                    required_elements=[
                        r"right\s+to\s+erasure",
                        r"right\s+to\s+be\s+forgotten",
                        r"delete\s+(?:your|personal)\s+data",
                    ],
                    severity="high",
                ),
                ComplianceRule(
                    rule_id="GDPR-003",
                    standard=ComplianceStandard.GDPR,
                    title="Data Portability",
                    description="Must provide right to data portability",
                    required_elements=[
                        r"data\s+portability",
                        r"transfer\s+(?:your|personal)\s+data",
                    ],
                    severity="medium",
                ),
                ComplianceRule(
                    rule_id="GDPR-004",
                    standard=ComplianceStandard.GDPR,
                    title="Lawful Basis",
                    description="Must specify lawful basis for processing",
                    required_elements=[
                        r"lawful\s+basis",
                        r"legal\s+basis\s+for\s+processing",
                        r"consent|contract|legal\s+obligation",
                    ],
                    severity="critical",
                ),
                ComplianceRule(
                    rule_id="GDPR-005",
                    standard=ComplianceStandard.GDPR,
                    title="Data Protection Officer",
                    description="Must designate DPO contact if required",
                    required_elements=[
                        r"data\s+protection\s+officer",
                        r"DPO",
                    ],
                    severity="medium",
                ),
            ],
        )

        # CCPA Rules
        rules.extend(
            [
                ComplianceRule(
                    rule_id="CCPA-001",
                    standard=ComplianceStandard.CCPA,
                    title="Right to Know",
                    description="Must disclose data collection and use",
                    required_elements=[
                        r"right\s+to\s+know",
                        r"categories\s+of\s+personal\s+information",
                    ],
                    severity="high",
                ),
                ComplianceRule(
                    rule_id="CCPA-002",
                    standard=ComplianceStandard.CCPA,
                    title="Right to Delete",
                    description="Must provide right to request deletion",
                    required_elements=[
                        r"right\s+to\s+delete",
                        r"request\s+deletion",
                    ],
                    severity="high",
                ),
                ComplianceRule(
                    rule_id="CCPA-003",
                    standard=ComplianceStandard.CCPA,
                    title="Do Not Sell",
                    description="Must provide opt-out of sale of personal information",
                    required_elements=[
                        r"do\s+not\s+sell",
                        r"opt[- ]out\s+of\s+sale",
                    ],
                    severity="critical",
                ),
                ComplianceRule(
                    rule_id="CCPA-004",
                    standard=ComplianceStandard.CCPA,
                    title="Non-Discrimination",
                    description="Must not discriminate against consumers exercising rights",
                    required_elements=[
                        r"non[- ]discrimination",
                        r"will\s+not\s+discriminate",
                    ],
                    severity="high",
                ),
            ],
        )

        # HIPAA Rules
        rules.extend(
            [
                ComplianceRule(
                    rule_id="HIPAA-001",
                    standard=ComplianceStandard.HIPAA,
                    title="Privacy Notice",
                    description="Must provide notice of privacy practices",
                    required_elements=[
                        r"notice\s+of\s+privacy\s+practices",
                        r"NPP",
                    ],
                    severity="critical",
                ),
                ComplianceRule(
                    rule_id="HIPAA-002",
                    standard=ComplianceStandard.HIPAA,
                    title="Protected Health Information",
                    description="Must define PHI and its protection",
                    required_elements=[
                        r"protected\s+health\s+information",
                        r"PHI",
                        r"health\s+information",
                    ],
                    severity="critical",
                ),
                ComplianceRule(
                    rule_id="HIPAA-003",
                    standard=ComplianceStandard.HIPAA,
                    title="Authorized Uses",
                    description="Must specify authorized uses and disclosures",
                    required_elements=[
                        r"authorized\s+uses",
                        r"permitted\s+disclosures",
                    ],
                    severity="high",
                ),
                ComplianceRule(
                    rule_id="HIPAA-004",
                    standard=ComplianceStandard.HIPAA,
                    title="Individual Rights",
                    description="Must describe patient rights under HIPAA",
                    required_elements=[
                        r"individual\s+rights",
                        r"patient\s+rights",
                        r"right\s+to\s+request\s+restrictions",
                    ],
                    severity="high",
                ),
            ],
        )

        return rules

    def add_custom_rule(self, rule: ComplianceRule) -> None:
        """Add a custom compliance rule."""
        self.rules.append(rule)

    def get_rules_for_standard(
        self,
        standard: ComplianceStandard,
    ) -> list[ComplianceRule]:
        """Get all rules for a compliance standard."""
        return [r for r in self.rules if r.standard == standard]


# Global singleton
_compliance_checker: ComplianceChecker | None = None


def get_compliance_checker() -> ComplianceChecker:
    """Get or create global ComplianceChecker instance."""
    global _compliance_checker
    if _compliance_checker is None:
        _compliance_checker = ComplianceChecker()
    return _compliance_checker
