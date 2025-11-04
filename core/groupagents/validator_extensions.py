"""Extensions for ValidatorAgent - models and helper methods for self-correction and petition validation.

This module extends ValidatorAgent with:
- Models for self-correction results
- Models for petition validation results
- Helper methods for LLM-based improvements
- EB-1A specific validation logic
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class CorrectionIteration(BaseModel):
    """Single iteration of self-correction process."""

    iteration_number: int = Field(..., description="Iteration number (1-based)")
    score_before: float = Field(ge=0.0, le=1.0, description="Score before corrections")
    score_after: float = Field(ge=0.0, le=1.0, description="Score after corrections")
    corrections_applied: list[str] = Field(
        default_factory=list, description="List of corrections made"
    )
    issues_fixed: int = Field(ge=0, description="Number of issues fixed")
    execution_time_seconds: float = Field(ge=0.0, description="Time taken for iteration")


class SelfCorrectionResult(BaseModel):
    """Result of self-correction process."""

    initial_content: str = Field(..., description="Original content")
    corrected_content: str = Field(..., description="Improved content")
    initial_score: float = Field(ge=0.0, le=1.0, description="Initial quality score")
    final_score: float = Field(ge=0.0, le=1.0, description="Final quality score")
    improvement: float = Field(description="Score improvement (can be negative)")
    iterations_performed: int = Field(ge=0, le=10, description="Number of iterations run")
    iterations: list[CorrectionIteration] = Field(
        default_factory=list, description="Details of each iteration"
    )
    final_validation: Any = Field(..., description="Final validation report (ValidationReport)")
    total_execution_time_seconds: float = Field(ge=0.0, description="Total time taken")
    corrected_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChecks(BaseModel):
    """Result of document completeness checks."""

    all_required_present: bool = Field(..., description="All required documents present")
    missing_documents: list[str] = Field(default_factory=list, description="Missing documents")
    optional_documents_present: list[str] = Field(
        default_factory=list, description="Optional documents included"
    )
    document_count: int = Field(ge=0, description="Total document count")


class EvidencePortfolioValidation(BaseModel):
    """Validation result for evidence portfolio."""

    total_evidence_count: int = Field(ge=0, description="Total evidence items")
    evidence_per_criterion: dict[str, int] = Field(
        default_factory=dict, description="Evidence count per criterion"
    )
    weak_criteria: list[str] = Field(
        default_factory=list, description="Criteria with insufficient evidence"
    )
    strong_criteria: list[str] = Field(
        default_factory=list, description="Criteria with strong evidence"
    )
    missing_evidence_types: list[str] = Field(
        default_factory=list, description="Recommended evidence types to add"
    )
    portfolio_strength_score: float = Field(
        ge=0.0, le=100.0, description="Overall portfolio strength (0-100)"
    )


class CriterionCoverageCheck(BaseModel):
    """Check of EB-1A criterion coverage."""

    criteria_count: int = Field(ge=0, le=10, description="Number of criteria claimed")
    meets_minimum: bool = Field(..., description="Meets minimum 3 criteria requirement")
    satisfied_criteria: list[str] = Field(default_factory=list, description="Satisfied criteria")
    weak_criteria: list[str] = Field(default_factory=list, description="Borderline criteria")
    recommended_additional_criteria: list[str] = Field(
        default_factory=list, description="Recommended criteria to develop"
    )
    coverage_strength_score: float = Field(
        ge=0.0, le=100.0, description="Coverage strength (0-100)"
    )


class ConsistencyChecks(BaseModel):
    """Consistency checks between petition documents."""

    name_consistency: bool = Field(..., description="Beneficiary name consistent across documents")
    date_consistency: bool = Field(..., description="Dates are consistent and logical")
    facts_consistency: bool = Field(..., description="Facts match across documents")
    evidence_references_valid: bool = Field(..., description="All evidence references are valid")
    inconsistencies_found: list[str] = Field(
        default_factory=list, description="List of inconsistencies"
    )
    consistency_score: float = Field(ge=0.0, le=100.0, description="Overall consistency (0-100)")


class EvidenceMappingValidation(BaseModel):
    """Validation of evidence-to-argument mapping."""

    total_arguments: int = Field(ge=0, description="Total arguments in petition")
    arguments_with_evidence: int = Field(ge=0, description="Arguments supported by evidence")
    evidence_without_arguments: int = Field(ge=0, description="Evidence not referenced")
    weak_mappings: list[str] = Field(
        default_factory=list, description="Arguments with weak evidence"
    )
    strong_mappings: list[str] = Field(
        default_factory=list, description="Arguments with strong evidence"
    )
    mapping_score: float = Field(ge=0.0, le=100.0, description="Evidence mapping quality (0-100)")


class USCISComplianceResult(BaseModel):
    """USCIS compliance check result."""

    meets_regulatory_requirements: bool = Field(
        ..., description="Meets 8 CFR § 204.5(h)(3) requirements"
    )
    format_compliant: bool = Field(..., description="Format meets USCIS standards")
    legal_citations_present: bool = Field(..., description="Includes relevant legal citations")
    required_sections_present: bool = Field(..., description="All required sections present")
    compliance_issues: list[str] = Field(default_factory=list, description="Compliance issues")
    compliance_score: float = Field(ge=0.0, le=100.0, description="Compliance score (0-100)")


class PetitionValidationResult(BaseModel):
    """Comprehensive petition validation result."""

    petition_id: str = Field(..., description="Petition ID")
    beneficiary_name: str = Field(..., description="Beneficiary name")
    ready_for_filing: bool = Field(..., description="Ready to file with USCIS")
    readiness_score: float = Field(ge=0.0, le=100.0, description="Overall readiness (0-100)")

    # Component results
    document_checks: DocumentChecks
    evidence_validation: EvidencePortfolioValidation
    criterion_coverage: CriterionCoverageCheck
    consistency_checks: ConsistencyChecks
    evidence_mapping: EvidenceMappingValidation
    uscis_compliance: USCISComplianceResult

    # Issues and recommendations
    critical_issues: list[str] = Field(default_factory=list, description="Must-fix issues")
    recommendations: list[str] = Field(default_factory=list, description="Improvement suggestions")

    # Timing
    estimated_days_to_ready: int | None = Field(
        None, description="Estimated days until filing-ready"
    )
    validation_execution_time: float = Field(ge=0.0, description="Validation time in seconds")
    validated_at: datetime = Field(default_factory=datetime.utcnow)


# ========== HELPER METHODS TO ADD TO ValidatorAgent ==========


async def _fix_formatting(self, content: str, document_type: str) -> str:
    """Fix basic formatting issues."""
    fixed = content

    # Remove excessive whitespace
    import re

    fixed = re.sub(r"\n{3,}", "\n\n", fixed)  # Max 2 consecutive newlines
    fixed = re.sub(r"[ \t]+\n", "\n", fixed)  # Remove trailing whitespace
    fixed = re.sub(r"[ \t]{2,}", " ", fixed)  # Multiple spaces to single

    # Ensure proper paragraph spacing for petitions
    if "petition" in document_type.lower():
        # Ensure headers are followed by newline
        fixed = re.sub(r"(^#{1,6}\s+.+)(\n)(?!\n)", r"\1\n\n", fixed, flags=re.MULTILINE)

    return fixed


async def _apply_auto_fix(self, content: str, issue: Any) -> str:
    """Apply automatic fix for auto-fixable issue."""
    # Placeholder - can implement specific fixes based on issue type
    return content


async def _strengthen_arguments(self, content: str, issues: list[Any], document_type: str) -> str:
    """Strengthen weak arguments using LLM (placeholder for now)."""
    # In production, this would call an LLM to improve weak arguments
    # For now, return content unchanged
    return content


def _identify_missing_elements(
    self, content: str, document_type: str, issues: list[Any]
) -> list[str]:
    """Identify missing required elements."""
    missing = []

    content_lower = content.lower()

    if "petition" in document_type.lower():
        # Check for EB-1A petition elements
        if "executive summary" not in content_lower:
            missing.append("Executive Summary")
        if "conclusion" not in content_lower:
            missing.append("Conclusion")
        if "criterion" not in content_lower and "criteria" not in content_lower:
            missing.append("Criterion Sections")

    return missing


async def _add_missing_elements(
    self, content: str, missing_elements: list[str], document_type: str
) -> str:
    """Add missing elements to content."""
    # Placeholder - would generate missing sections
    enhanced = content

    for element in missing_elements:
        if element == "Executive Summary" and "executive summary" not in content.lower():
            enhanced = f"# EXECUTIVE SUMMARY\n\n[To be completed]\n\n{enhanced}"
        elif element == "Conclusion" and "conclusion" not in content.lower():
            enhanced = f"{enhanced}\n\n# CONCLUSION\n\n[To be completed]"

    return enhanced


async def _improve_clarity_and_tone(self, content: str, document_type: str) -> str:
    """Improve clarity and tone using LLM (placeholder)."""
    # In production, would use LLM to improve clarity
    return content


# ========== PETITION VALIDATION HELPER METHODS ==========


async def _check_required_documents(self, petition: Any) -> DocumentChecks:
    """Check for required petition documents."""
    required = [
        "Cover Letter",
        "Petition Letter",
        "Evidence Portfolio",
        "Exhibit Index",
    ]

    # Simplified check - in production would check actual documents
    all_present = len(petition.evidence) >= 5  # Basic check
    missing = [] if all_present else ["Evidence Portfolio incomplete"]

    return DocumentChecks(
        all_required_present=all_present,
        missing_documents=missing,
        optional_documents_present=[],
        document_count=len(petition.evidence),
    )


async def _validate_evidence_portfolio(self, petition: Any) -> EvidencePortfolioValidation:
    """Validate evidence portfolio."""
    evidence_per_criterion = {}
    for criterion in petition.primary_criteria:
        count = len([e for e in petition.evidence if e.criterion == criterion])
        evidence_per_criterion[criterion.value] = count

    total_count = len(petition.evidence)
    weak = [k for k, v in evidence_per_criterion.items() if v < 2]
    strong = [k for k, v in evidence_per_criterion.items() if v >= 3]

    # Portfolio strength: based on total evidence and distribution
    strength_score = min(100.0, (total_count / 15.0) * 100.0)

    return EvidencePortfolioValidation(
        total_evidence_count=total_count,
        evidence_per_criterion=evidence_per_criterion,
        weak_criteria=weak,
        strong_criteria=strong,
        missing_evidence_types=[],
        portfolio_strength_score=strength_score,
    )


async def _check_criterion_coverage(self, petition: Any) -> CriterionCoverageCheck:
    """Check criterion coverage."""
    criteria_count = len(petition.primary_criteria)
    meets_minimum = criteria_count >= 3

    # Simplified - would integrate with EvidenceAnalyzer in production
    satisfied = [c.value for c in petition.primary_criteria]
    weak = []

    coverage_score = min(100.0, (criteria_count / 3.0) * 70.0 + 30.0)

    return CriterionCoverageCheck(
        criteria_count=criteria_count,
        meets_minimum=meets_minimum,
        satisfied_criteria=satisfied,
        weak_criteria=weak,
        recommended_additional_criteria=[],
        coverage_strength_score=coverage_score,
    )


async def _validate_petition_consistency(self, petition: Any) -> ConsistencyChecks:
    """Validate consistency between petition elements."""
    # Basic consistency checks
    name_ok = bool(petition.beneficiary_name)
    dates_ok = True  # Placeholder
    facts_ok = True  # Placeholder
    references_ok = all(e.exhibit_number for e in petition.evidence if hasattr(e, "exhibit_number"))

    inconsistencies = []
    if not references_ok:
        inconsistencies.append("Some evidence items missing exhibit numbers")

    consistency_score = (
        (100.0 if name_ok else 0.0) * 0.3
        + (100.0 if dates_ok else 0.0) * 0.2
        + (100.0 if facts_ok else 0.0) * 0.3
        + (100.0 if references_ok else 0.0) * 0.2
    )

    return ConsistencyChecks(
        name_consistency=name_ok,
        date_consistency=dates_ok,
        facts_consistency=facts_ok,
        evidence_references_valid=references_ok,
        inconsistencies_found=inconsistencies,
        consistency_score=consistency_score,
    )


async def _validate_evidence_mapping(self, petition: Any) -> EvidenceMappingValidation:
    """Validate evidence-to-argument mapping."""
    # Simplified mapping validation
    total_args = len(petition.primary_criteria) * 3  # Assume 3 args per criterion
    args_with_evidence = len(petition.evidence)

    mapping_score = min(100.0, (args_with_evidence / total_args) * 100.0) if total_args > 0 else 0.0

    return EvidenceMappingValidation(
        total_arguments=total_args,
        arguments_with_evidence=min(args_with_evidence, total_args),
        evidence_without_arguments=max(0, len(petition.evidence) - total_args),
        weak_mappings=[],
        strong_mappings=[],
        mapping_score=mapping_score,
    )


async def _check_uscis_compliance(self, petition: Any) -> USCISComplianceResult:
    """Check USCIS compliance."""
    # Basic compliance checks
    has_min_criteria = len(petition.primary_criteria) >= 3
    format_ok = True  # Placeholder
    citations_ok = False  # Would check for legal citations
    sections_ok = len(petition.primary_criteria) > 0

    compliance_score = (
        (100.0 if has_min_criteria else 0.0) * 0.4
        + (100.0 if format_ok else 0.0) * 0.2
        + (100.0 if citations_ok else 50.0) * 0.2
        + (100.0 if sections_ok else 0.0) * 0.2
    )

    issues = []
    if not has_min_criteria:
        issues.append("Does not meet minimum 3 criteria requirement")
    if not citations_ok:
        issues.append("Missing legal precedent citations")

    return USCISComplianceResult(
        meets_regulatory_requirements=has_min_criteria,
        format_compliant=format_ok,
        legal_citations_present=citations_ok,
        required_sections_present=sections_ok,
        compliance_issues=issues,
        compliance_score=compliance_score,
    )


def _calculate_petition_readiness_score(
    self,
    document_checks: DocumentChecks,
    evidence_validation: EvidencePortfolioValidation,
    criterion_coverage: CriterionCoverageCheck,
    consistency: ConsistencyChecks,
    mapping: EvidenceMappingValidation,
    compliance: USCISComplianceResult,
) -> float:
    """Calculate overall petition readiness score (0-100)."""
    # Weighted average of component scores
    weights = {
        "documents": 0.15,
        "evidence": 0.25,
        "coverage": 0.25,
        "consistency": 0.15,
        "mapping": 0.10,
        "compliance": 0.10,
    }

    doc_score = 100.0 if document_checks.all_required_present else 50.0
    evidence_score = evidence_validation.portfolio_strength_score
    coverage_score = criterion_coverage.coverage_strength_score
    consistency_score = consistency.consistency_score
    mapping_score = mapping.mapping_score
    compliance_score = compliance.compliance_score

    overall = (
        doc_score * weights["documents"]
        + evidence_score * weights["evidence"]
        + coverage_score * weights["coverage"]
        + consistency_score * weights["consistency"]
        + mapping_score * weights["mapping"]
        + compliance_score * weights["compliance"]
    )

    return round(overall, 1)


def _identify_critical_petition_issues(
    self,
    document_checks: DocumentChecks,
    evidence_validation: EvidencePortfolioValidation,
    criterion_coverage: CriterionCoverageCheck,
    consistency_checks: ConsistencyChecks,
    mapping_validation: EvidenceMappingValidation,
    compliance_result: USCISComplianceResult,
) -> list[str]:
    """Identify critical issues blocking filing."""
    issues = []

    if not document_checks.all_required_present:
        issues.extend(
            [f"Missing required document: {doc}" for doc in document_checks.missing_documents]
        )

    if not criterion_coverage.meets_minimum:
        issues.append(
            f"Does not meet minimum 3 criteria (currently {criterion_coverage.criteria_count})"
        )

    if evidence_validation.total_evidence_count < 10:
        issues.append(
            f"Insufficient evidence ({evidence_validation.total_evidence_count} items, recommend 15+)"
        )

    issues.extend(compliance_result.compliance_issues)
    issues.extend(consistency_checks.inconsistencies_found)

    return issues


def _generate_petition_recommendations(
    self,
    readiness_score: float,
    critical_issues: list[str],
    document_checks: DocumentChecks,
    evidence_validation: EvidencePortfolioValidation,
    criterion_coverage: CriterionCoverageCheck,
) -> list[str]:
    """Generate prioritized recommendations."""
    recommendations = []

    if critical_issues:
        recommendations.append(f"CRITICAL: Address {len(critical_issues)} blocking issues first")

    if readiness_score < 70.0:
        recommendations.append(
            "Petition needs significant strengthening before filing (score < 70)"
        )

    if evidence_validation.weak_criteria:
        recommendations.append(
            f'Strengthen evidence for: {", ".join(evidence_validation.weak_criteria)}'
        )

    if criterion_coverage.criteria_count == 3:
        recommendations.append(
            "Consider developing 4th criterion to strengthen case (currently at minimum)"
        )

    if not critical_issues and readiness_score >= 80.0:
        recommendations.append("Petition is strong - conduct final review before filing")

    return recommendations


def _estimate_petition_time_to_ready(
    self, readiness_score: float, critical_issue_count: int, criteria_count: int
) -> int:
    """Estimate days until petition is filing-ready."""
    if readiness_score >= 90.0:
        return 14  # 2 weeks for final polish
    if readiness_score >= 80.0:
        return 30  # 1 month for improvements
    if readiness_score >= 70.0:
        return 60 + (critical_issue_count * 7)  # 2+ months
    if readiness_score >= 60.0:
        return 90 + (critical_issue_count * 14)  # 3+ months
    base = 120
    criteria_penalty = max(0, (3 - criteria_count) * 30)
    issue_penalty = critical_issue_count * 14
    return base + criteria_penalty + issue_penalty


async def _log_self_correction(self, result: SelfCorrectionResult, user_id: str) -> None:
    """Log self-correction completion."""
    await self._log_audit_event(
        user_id=user_id,
        action="self_correction_completed",
        payload={
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "improvement": result.improvement,
            "iterations": result.iterations_performed,
            "execution_time": result.total_execution_time_seconds,
        },
    )


async def _log_petition_validation(self, result: PetitionValidationResult, user_id: str) -> None:
    """Log petition validation completion."""
    await self._log_audit_event(
        user_id=user_id,
        action="petition_validation_completed",
        payload={
            "petition_id": result.petition_id,
            "beneficiary": result.beneficiary_name,
            "ready_for_filing": result.ready_for_filing,
            "readiness_score": result.readiness_score,
            "critical_issues": len(result.critical_issues),
            "execution_time": result.validation_execution_time,
        },
    )
