"""Contract Analyzer.

Analyzes contracts and extracts key clauses and terms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Any

from .document_parser import LegalDocument


class ClauseType(str, Enum):
    """Types of contract clauses."""

    PAYMENT = "payment"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    INDEMNIFICATION = "indemnification"
    LIABILITY = "liability"
    WARRANTY = "warranty"
    FORCE_MAJEURE = "force_majeure"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GOVERNING_LAW = "governing_law"
    AMENDMENT = "amendment"
    ASSIGNMENT = "assignment"
    SEVERABILITY = "severability"
    ENTIRE_AGREEMENT = "entire_agreement"
    NON_COMPETE = "non_compete"
    NON_SOLICITATION = "non_solicitation"
    RENEWAL = "renewal"
    NOTICE = "notice"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk levels for contract clauses."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class ContractClause:
    """Contract clause."""

    clause_type: ClauseType
    title: str
    content: str
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    section_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractAnalysisResult:
    """Result of contract analysis."""

    document: LegalDocument
    clauses: list[ContractClause]
    obligations: list[str]
    rights: list[str]
    payment_terms: dict[str, Any]
    termination_conditions: list[str]
    risks: list[dict[str, Any]]
    recommendations: list[str]
    overall_risk_score: float  # 0-100
    metadata: dict[str, Any] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    def get_clauses_by_type(self, clause_type: ClauseType) -> list[ContractClause]:
        """Get all clauses of a specific type."""
        return [c for c in self.clauses if c.clause_type == clause_type]

    def get_high_risk_clauses(self) -> list[ContractClause]:
        """Get all high or critical risk clauses."""
        return [c for c in self.clauses if c.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]


class ContractAnalyzer:
    """
    Analyze contracts and extract key information.

    Features:
    - Clause identification and classification
    - Risk assessment
    - Payment terms extraction
    - Obligation and rights identification
    - Termination conditions analysis
    - Recommendations generation

    Example:
        >>> analyzer = ContractAnalyzer()
        >>> result = analyzer.analyze(legal_document)
        >>> print(f"Risk Score: {result.overall_risk_score}")
        >>> for clause in result.get_high_risk_clauses():
        ...     print(f"  - {clause.title}: {clause.risk_level}")
    """

    def __init__(self):
        """Initialize contract analyzer."""
        # Clause detection patterns
        self.clause_patterns = {
            ClauseType.PAYMENT: [
                r"payment\s+terms?",
                r"compensation",
                r"fees?\s+and\s+charges",
                r"price\s+and\s+payment",
            ],
            ClauseType.TERMINATION: [
                r"termination",
                r"cancellation",
                r"early\s+termination",
            ],
            ClauseType.CONFIDENTIALITY: [
                r"confidential(?:ity)?",
                r"non-disclosure",
                r"proprietary\s+information",
            ],
            ClauseType.INTELLECTUAL_PROPERTY: [
                r"intellectual\s+property",
                r"copyright",
                r"patent",
                r"trademark",
                r"IP\s+rights",
            ],
            ClauseType.INDEMNIFICATION: [
                r"indemnif(?:y|ication)",
                r"hold\s+harmless",
            ],
            ClauseType.LIABILITY: [
                r"liability",
                r"limitation\s+of\s+liability",
                r"damages",
            ],
            ClauseType.WARRANTY: [
                r"warrant(?:y|ies)",
                r"representations?\s+and\s+warrant(?:y|ies)",
            ],
            ClauseType.FORCE_MAJEURE: [
                r"force\s+majeure",
                r"acts?\s+of\s+god",
            ],
            ClauseType.DISPUTE_RESOLUTION: [
                r"dispute\s+resolution",
                r"arbitration",
                r"mediation",
            ],
            ClauseType.GOVERNING_LAW: [
                r"governing\s+law",
                r"choice\s+of\s+law",
            ],
            ClauseType.NON_COMPETE: [
                r"non-compete",
                r"non\s+competition",
            ],
            ClauseType.ASSIGNMENT: [
                r"assignment",
                r"transfer\s+of\s+rights",
            ],
        }

        # Risk indicators
        self.risk_indicators = {
            RiskLevel.CRITICAL: [
                r"unlimited\s+liability",
                r"automatic\s+renewal",
                r"perpetual\s+license",
                r"exclusive\s+(?:jurisdiction|venue)",
            ],
            RiskLevel.HIGH: [
                r"without\s+(?:notice|cause)",
                r"sole\s+discretion",
                r"as-is",
                r"no\s+warranty",
                r"indemnify.*any\s+and\s+all",
            ],
            RiskLevel.MEDIUM: [
                r"may\s+(?:modify|change|amend)",
                r"subject\s+to\s+change",
                r"reasonable\s+efforts",
            ],
        }

    def analyze(self, document: LegalDocument) -> ContractAnalysisResult:
        """
        Analyze contract document.

        Args:
            document: Parsed legal document

        Returns:
            Contract analysis result
        """
        # Extract clauses
        clauses = self._extract_clauses(document)

        # Assess risks for each clause
        for clause in clauses:
            self._assess_clause_risk(clause)

        # Extract obligations and rights
        obligations = self._extract_obligations(document)
        rights = self._extract_rights(document)

        # Extract payment terms
        payment_terms = self._extract_payment_terms(document)

        # Extract termination conditions
        termination_conditions = self._extract_termination_conditions(document)

        # Identify overall risks
        risks = self._identify_risks(document, clauses)

        # Generate recommendations
        recommendations = self._generate_recommendations(document, clauses, risks)

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(clauses, risks)

        return ContractAnalysisResult(
            document=document,
            clauses=clauses,
            obligations=obligations,
            rights=rights,
            payment_terms=payment_terms,
            termination_conditions=termination_conditions,
            risks=risks,
            recommendations=recommendations,
            overall_risk_score=risk_score,
        )

    def _extract_clauses(self, document: LegalDocument) -> list[ContractClause]:
        """Extract and classify clauses."""
        clauses = []

        # Check each section
        for section in document.sections:
            clause_type = self._classify_clause(section.title, section.content)

            if clause_type != ClauseType.OTHER:
                clauses.append(
                    ContractClause(
                        clause_type=clause_type,
                        title=section.title,
                        content=section.content,
                        section_reference=section.section_number,
                    ),
                )

        # Also check for clauses in main content if no sections
        if not clauses:
            clauses = self._extract_clauses_from_text(document.content)

        return clauses

    def _classify_clause(self, title: str, content: str) -> ClauseType:
        """Classify clause by title and content."""
        combined_text = f"{title} {content}".lower()

        # Check patterns for each clause type
        for clause_type, patterns in self.clause_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return clause_type

        return ClauseType.OTHER

    def _extract_clauses_from_text(self, text: str) -> list[ContractClause]:
        """Extract clauses from unstructured text."""
        clauses = []

        # Split by paragraphs
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            if len(paragraph.strip()) < 50:  # Skip short paragraphs
                continue

            clause_type = self._classify_clause("", paragraph)

            if clause_type != ClauseType.OTHER:
                # Extract title (first sentence or first line)
                title = paragraph.split(".")[0][:100]

                clauses.append(
                    ContractClause(
                        clause_type=clause_type,
                        title=title,
                        content=paragraph,
                    ),
                )

        return clauses

    def _assess_clause_risk(self, clause: ContractClause) -> None:
        """Assess risk level of a clause."""
        content_lower = clause.content.lower()

        # Check for risk indicators
        for risk_level, patterns in self.risk_indicators.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    clause.risk_level = risk_level
                    clause.risks.append(f"Contains '{pattern}' language")

        # Specific risk checks by clause type
        if clause.clause_type == ClauseType.LIABILITY:
            if "unlimited" in content_lower or "no limit" in content_lower:
                clause.risk_level = RiskLevel.CRITICAL
                clause.risks.append("Unlimited liability exposure")

        elif clause.clause_type == ClauseType.TERMINATION:
            if "without cause" in content_lower or "at will" in content_lower:
                clause.risk_level = RiskLevel.HIGH
                clause.risks.append("Termination without cause allowed")

        elif clause.clause_type == ClauseType.WARRANTY:
            if "as-is" in content_lower or "no warranty" in content_lower:
                clause.risk_level = RiskLevel.HIGH
                clause.risks.append("No warranties provided")

        # Generate recommendations based on risks
        if clause.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._add_clause_recommendations(clause)

    def _add_clause_recommendations(self, clause: ContractClause) -> None:
        """Add recommendations for risky clauses."""
        if clause.clause_type == ClauseType.LIABILITY:
            clause.recommendations.append("Consider negotiating liability cap")
            clause.recommendations.append("Review insurance coverage requirements")

        elif clause.clause_type == ClauseType.TERMINATION:
            clause.recommendations.append(
                "Negotiate for termination for cause only",
            )
            clause.recommendations.append("Add notice period requirement")

        elif clause.clause_type == ClauseType.WARRANTY:
            clause.recommendations.append("Request minimum warranty period")
            clause.recommendations.append("Define specific warranty terms")

        elif clause.clause_type == ClauseType.INDEMNIFICATION:
            clause.recommendations.append("Ensure mutual indemnification")
            clause.recommendations.append("Limit indemnification scope")

    def _extract_obligations(self, document: LegalDocument) -> list[str]:
        """Extract obligations from contract."""
        obligations = []

        # Patterns for obligations
        obligation_patterns = [
            r"(?:shall|must|agrees?\s+to|obligated\s+to)\s+([^.]+)",
            r"responsible\s+for\s+([^.]+)",
            r"required\s+to\s+([^.]+)",
        ]

        for pattern in obligation_patterns:
            matches = re.finditer(pattern, document.content, re.IGNORECASE)
            for match in matches:
                obligation = match.group(1).strip()
                if len(obligation) > 10 and obligation not in obligations:
                    obligations.append(obligation)

        return obligations[:20]  # Limit to top 20

    def _extract_rights(self, document: LegalDocument) -> list[str]:
        """Extract rights from contract."""
        rights = []

        # Patterns for rights
        rights_patterns = [
            r"(?:entitled\s+to|right\s+to|may)\s+([^.]+)",
            r"permitted\s+to\s+([^.]+)",
        ]

        for pattern in rights_patterns:
            matches = re.finditer(pattern, document.content, re.IGNORECASE)
            for match in matches:
                right = match.group(1).strip()
                if len(right) > 10 and right not in rights:
                    rights.append(right)

        return rights[:20]  # Limit to top 20

    def _extract_payment_terms(self, document: LegalDocument) -> dict[str, Any]:
        """Extract payment terms."""
        payment_terms: dict[str, Any] = {
            "amounts": [],
            "schedule": None,
            "methods": [],
            "currency": None,
        }

        # Extract monetary amounts
        money_pattern = r"\$\s*[\d,]+(?:\.\d{2})?"
        amounts = re.findall(money_pattern, document.content)
        payment_terms["amounts"] = amounts

        # Extract payment schedule
        schedule_pattern = r"(?:pay|payment).*?(?:monthly|quarterly|annually|upon\s+\w+)"
        schedule_match = re.search(schedule_pattern, document.content, re.IGNORECASE)
        if schedule_match:
            payment_terms["schedule"] = schedule_match.group(0)

        # Extract currency
        currency_pattern = r"\b(USD|EUR|GBP|CAD|AUD)\b"
        currency_match = re.search(currency_pattern, document.content)
        if currency_match:
            payment_terms["currency"] = currency_match.group(1)

        return payment_terms

    def _extract_termination_conditions(self, document: LegalDocument) -> list[str]:
        """Extract termination conditions."""
        conditions = []

        # Find termination clause
        termination_section = None
        for section in document.sections:
            if "termination" in section.title.lower():
                termination_section = section
                break

        if termination_section:
            # Extract conditions from termination section
            condition_patterns = [
                r"(?:may\s+terminate|terminated).*?(?:if|upon|in\s+the\s+event)\s+([^.]+)",
                r"(?:breach|violation|default)\s+of\s+([^.]+)",
            ]

            for pattern in condition_patterns:
                matches = re.finditer(
                    pattern,
                    termination_section.content,
                    re.IGNORECASE,
                )
                for match in matches:
                    condition = match.group(1).strip()
                    if condition not in conditions:
                        conditions.append(condition)

        return conditions

    def _identify_risks(
        self,
        document: LegalDocument,
        clauses: list[ContractClause],
    ) -> list[dict[str, Any]]:
        """Identify overall contract risks."""
        risks = []

        # Aggregate clause-level risks
        for clause in clauses:
            if clause.risks:
                risks.append(
                    {
                        "source": clause.title,
                        "risk_level": clause.risk_level.value,
                        "description": "; ".join(clause.risks),
                        "clause_type": clause.clause_type.value,
                    },
                )

        # Check for missing critical clauses
        critical_clauses = [
            ClauseType.TERMINATION,
            ClauseType.LIABILITY,
            ClauseType.GOVERNING_LAW,
        ]

        existing_types = {c.clause_type for c in clauses}

        for critical_type in critical_clauses:
            if critical_type not in existing_types:
                risks.append(
                    {
                        "source": "Missing Clause",
                        "risk_level": RiskLevel.HIGH.value,
                        "description": f"Missing {critical_type.value} clause",
                        "clause_type": "missing",
                    },
                )

        return risks

    def _generate_recommendations(
        self,
        document: LegalDocument,
        clauses: list[ContractClause],
        risks: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Add clause-specific recommendations
        for clause in clauses:
            recommendations.extend(clause.recommendations)

        # Add general recommendations
        if len(risks) > 5:
            recommendations.append(
                "Consider comprehensive legal review due to multiple risks",
            )

        if not document.jurisdiction:
            recommendations.append("Specify governing jurisdiction")

        if not document.effective_date:
            recommendations.append("Add clear effective date")

        # Check for one-sided terms
        high_risk_count = sum(1 for r in risks if r["risk_level"] in ["high", "critical"])
        if high_risk_count > 3:
            recommendations.append(
                "Multiple high-risk clauses detected - negotiate for more balanced terms",
            )

        return list(set(recommendations))  # Remove duplicates

    def _calculate_risk_score(
        self,
        clauses: list[ContractClause],
        risks: list[dict[str, Any]],
    ) -> float:
        """Calculate overall risk score (0-100)."""
        if not clauses:
            return 50.0  # Medium risk if no clauses found

        # Weight by risk level
        risk_weights = {
            RiskLevel.CRITICAL: 30,
            RiskLevel.HIGH: 20,
            RiskLevel.MEDIUM: 10,
            RiskLevel.LOW: 5,
            RiskLevel.INFORMATIONAL: 0,
        }

        total_risk = sum(risk_weights.get(clause.risk_level, 0) for clause in clauses)

        # Normalize to 0-100 scale
        max_possible_risk = len(clauses) * risk_weights[RiskLevel.CRITICAL]
        risk_score = (total_risk / max_possible_risk * 100) if max_possible_risk > 0 else 0

        return min(100.0, risk_score)


# Global singleton
_contract_analyzer: ContractAnalyzer | None = None


def get_contract_analyzer() -> ContractAnalyzer:
    """Get or create global ContractAnalyzer instance."""
    global _contract_analyzer
    if _contract_analyzer is None:
        _contract_analyzer = ContractAnalyzer()
    return _contract_analyzer
