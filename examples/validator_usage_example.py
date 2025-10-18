"""Example: Using ValidatorAgent for document validation and self-correction.

This example demonstrates:
1. Basic document validation with custom rules
2. Self-correction with iterative improvement
3. Complete EB-1A petition validation
4. Error recovery and recommendations
"""

from __future__ import annotations

import asyncio

from core.groupagents.validator_agent import (
    ValidationCategory,
    ValidationLevel,
    ValidationRequest,
    ValidationRuleType,
    ValidatorAgent,
)
from core.groupagents.validator_extensions import PetitionValidationResult, SelfCorrectionResult
from core.memory.memory_manager import MemoryManager
from core.workflows.eb1a.eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
    EvidenceType,
)


async def example_1_basic_validation():
    """Example 1: Basic document validation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: BASIC DOCUMENT VALIDATION")
    print("=" * 80)

    # Initialize validator
    memory = MemoryManager()
    validator = ValidatorAgent(memory_manager=memory)

    # Sample document (with some issues)
    document_content = """
    This is a short document.
    It has some issues with formatting.



    Multiple blank lines.
    Missing title.
    """

    # Create validation request
    request = ValidationRequest(
        document_id="doc_001",
        content=document_content,
        document_type="cover_letter",
        validation_level=ValidationLevel.STANDARD,
        categories=[
            ValidationCategory.FORMAL,
            ValidationCategory.STRUCTURE,
            ValidationCategory.CONTENT,
        ],
        user_id="user_001",
    )

    # Validate document
    print("\n📋 Validating document...")
    validation_result = await validator.avalidate(request)

    print("\n✅ Validation Complete!")
    print(f"   Valid: {validation_result.is_valid}")
    print(f"   Score: {validation_result.score:.2f}")
    print(f"   Errors: {len(validation_result.errors)}")
    print(f"   Warnings: {len(validation_result.warnings)}")

    if validation_result.errors:
        print("\n❌ Errors:")
        for error in validation_result.errors:
            print(f"   - {error}")

    if validation_result.warnings:
        print("\n⚠️  Warnings:")
        for warning in validation_result.warnings:
            print(f"   - {warning}")


async def example_2_self_correction():
    """Example 2: Automatic self-correction."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: SELF-CORRECTION WITH ITERATIVE IMPROVEMENT")
    print("=" * 80)

    # Initialize validator
    memory = MemoryManager()
    validator = ValidatorAgent(memory_manager=memory)

    # Sample document with multiple issues
    draft_document = """
I am writing to apply for extraordinary ability visa.

I have done some good work in my field.
I won some awards.


I published papers.
"""

    print(f"\n📄 Original Document ({len(draft_document)} chars):")
    print("-" * 80)
    print(draft_document)
    print("-" * 80)

    # Run self-correction
    print("\n🔧 Running self-correction (max 3 iterations)...")

    correction_result: SelfCorrectionResult = await validator.aself_correct(
        content=draft_document,
        document_type="petition_draft",
        max_iterations=3,
        user_id="user_001",
    )

    # Display results
    print("\n✅ Self-Correction Complete!")
    print(f"   Initial Score:  {correction_result.initial_score:.2f}")
    print(f"   Final Score:    {correction_result.final_score:.2f}")
    print(f"   Improvement:    +{correction_result.improvement:.2f}")
    print(f"   Iterations:     {correction_result.iterations_performed}")
    print(f"   Execution Time: {correction_result.total_execution_time_seconds:.2f}s")

    # Show iteration details
    print("\n📊 Iteration Details:")
    for iteration in correction_result.iterations:
        print(f"\n   Iteration {iteration.iteration_number}:")
        print(f"     Score: {iteration.score_before:.2f} → {iteration.score_after:.2f}")
        print(f"     Issues Fixed: {iteration.issues_fixed}")
        print("     Corrections Applied:")
        for correction in iteration.corrections_applied:
            print(f"       - {correction}")

    # Show corrected document
    print(f"\n📄 Corrected Document ({len(correction_result.corrected_content)} chars):")
    print("-" * 80)
    print(correction_result.corrected_content)
    print("-" * 80)


async def example_3_petition_validation():
    """Example 3: Complete EB-1A petition validation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: COMPLETE EB-1A PETITION VALIDATION")
    print("=" * 80)

    # Initialize validator
    memory = MemoryManager()
    validator = ValidatorAgent(memory_manager=memory)

    # Create sample petition
    petition = EB1APetitionRequest(
        beneficiary_name="Dr. Jane Smith",
        field_of_expertise="Artificial Intelligence",
        country_of_birth="Canada",
        current_position="Senior AI Researcher",
        current_employer="Tech Corp",
        # Evidence portfolio
        evidence=[
            EB1AEvidence(
                criterion=EB1ACriterion.AWARDS,
                evidence_type=EvidenceType.AWARD_CERTIFICATE,
                title="ACM Turing Award",
                description="Received Turing Award for contributions to deep learning",
                exhibit_number="A-1",
            ),
            EB1AEvidence(
                criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
                evidence_type=EvidenceType.PUBLICATION,
                title="Transformer Architecture Paper",
                description="Published seminal paper on transformers",
                exhibit_number="B-1",
            ),
            EB1AEvidence(
                criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
                evidence_type=EvidenceType.CITATION_REPORT,
                title="Google Scholar Citations",
                description="85,000+ citations",
                exhibit_number="B-2",
            ),
            EB1AEvidence(
                criterion=EB1ACriterion.PRESS,
                evidence_type=EvidenceType.PRESS_ARTICLE,
                title="MIT Technology Review Profile",
                description="Featured in '35 Under 35' list",
                exhibit_number="C-1",
            ),
        ],
        # Primary criteria (3 minimum required)
        primary_criteria=[
            EB1ACriterion.AWARDS,
            EB1ACriterion.SCHOLARLY_ARTICLES,
            EB1ACriterion.PRESS,
        ],
        background_summary="Leading AI researcher with groundbreaking contributions",
        accomplishments=[
            "Developed Transformer architecture",
            "85,000+ citations",
            "ACM Turing Award recipient",
        ],
        citations_count=85000,
        h_index=120,
    )

    print(f"\n📋 Validating EB-1A Petition for: {petition.beneficiary_name}")
    print(f"   Field: {petition.field_of_expertise}")
    print(f"   Criteria: {len(petition.primary_criteria)}")
    print(f"   Evidence Items: {len(petition.evidence)}")

    # Validate petition
    print("\n🔍 Running comprehensive petition validation...")

    petition_result: PetitionValidationResult = await validator.avalidate_petition(
        petition=petition,
        user_id="user_001",
    )

    # Display results
    print("\n" + "=" * 80)
    print("PETITION VALIDATION RESULTS")
    print("=" * 80)

    print("\n📊 OVERALL ASSESSMENT:")
    print(f"   Ready for Filing: {'✅ YES' if petition_result.ready_for_filing else '❌ NO'}")
    print(f"   Readiness Score:  {petition_result.readiness_score:.1f}/100")
    print(f"   Execution Time:   {petition_result.validation_execution_time:.2f}s")

    if petition_result.estimated_days_to_ready:
        print(f"   Est. Days to Ready: {petition_result.estimated_days_to_ready} days")

    # Document checks
    print("\n📁 DOCUMENT COMPLETENESS:")
    print(
        f"   All Required Present: {'✅' if petition_result.document_checks.all_required_present else '❌'}"
    )
    print(f"   Document Count: {petition_result.document_checks.document_count}")
    if petition_result.document_checks.missing_documents:
        print("   Missing:")
        for doc in petition_result.document_checks.missing_documents:
            print(f"     - {doc}")

    # Evidence portfolio
    print("\n📚 EVIDENCE PORTFOLIO:")
    print(f"   Total Evidence: {petition_result.evidence_validation.total_evidence_count}")
    print(
        f"   Portfolio Strength: {petition_result.evidence_validation.portfolio_strength_score:.1f}/100"
    )
    print("   Evidence per Criterion:")
    for criterion, count in petition_result.evidence_validation.evidence_per_criterion.items():
        status = "✅" if count >= 2 else "⚠️"
        print(f"     {status} {criterion}: {count} items")

    if petition_result.evidence_validation.weak_criteria:
        print("   ⚠️  Weak Criteria:")
        for criterion in petition_result.evidence_validation.weak_criteria:
            print(f"     - {criterion}")

    # Criterion coverage
    print("\n✅ CRITERION COVERAGE:")
    print(f"   Criteria Count: {petition_result.criterion_coverage.criteria_count}")
    print(
        f"   Meets Minimum (3): {'✅ YES' if petition_result.criterion_coverage.meets_minimum else '❌ NO'}"
    )
    print(
        f"   Coverage Score: {petition_result.criterion_coverage.coverage_strength_score:.1f}/100"
    )

    # Consistency checks
    print("\n🔗 CONSISTENCY CHECKS:")
    print(
        f"   Name Consistent: {'✅' if petition_result.consistency_checks.name_consistency else '❌'}"
    )
    print(
        f"   Dates Consistent: {'✅' if petition_result.consistency_checks.date_consistency else '❌'}"
    )
    print(
        f"   Evidence References Valid: {'✅' if petition_result.consistency_checks.evidence_references_valid else '❌'}"
    )
    print(f"   Consistency Score: {petition_result.consistency_checks.consistency_score:.1f}/100")

    if petition_result.consistency_checks.inconsistencies_found:
        print("   ⚠️  Inconsistencies:")
        for inconsistency in petition_result.consistency_checks.inconsistencies_found:
            print(f"     - {inconsistency}")

    # Evidence mapping
    print("\n🔗 EVIDENCE MAPPING:")
    print(f"   Total Arguments: {petition_result.evidence_mapping.total_arguments}")
    print(f"   Arguments with Evidence: {petition_result.evidence_mapping.arguments_with_evidence}")
    print(f"   Mapping Score: {petition_result.evidence_mapping.mapping_score:.1f}/100")

    # USCIS compliance
    print("\n⚖️  USCIS COMPLIANCE:")
    print(
        f"   Regulatory Requirements: {'✅' if petition_result.uscis_compliance.meets_regulatory_requirements else '❌'}"
    )
    print(
        f"   Format Compliant: {'✅' if petition_result.uscis_compliance.format_compliant else '❌'}"
    )
    print(
        f"   Legal Citations: {'✅' if petition_result.uscis_compliance.legal_citations_present else '❌'}"
    )
    print(f"   Compliance Score: {petition_result.uscis_compliance.compliance_score:.1f}/100")

    if petition_result.uscis_compliance.compliance_issues:
        print("   ⚠️  Compliance Issues:")
        for issue in petition_result.uscis_compliance.compliance_issues:
            print(f"     - {issue}")

    # Critical issues
    if petition_result.critical_issues:
        print(f"\n❌ CRITICAL ISSUES ({len(petition_result.critical_issues)}):")
        for issue in petition_result.critical_issues:
            print(f"   - {issue}")

    # Recommendations
    if petition_result.recommendations:
        print("\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(petition_result.recommendations, 1):
            print(f"   {i}. {rec}")

    # Final assessment
    print("\n" + "=" * 80)
    if petition_result.ready_for_filing:
        print("✅ PETITION IS READY FOR FILING")
        print("   Recommendation: Conduct final review and submit to USCIS")
    elif petition_result.readiness_score >= 70:
        print("⚠️  PETITION NEEDS IMPROVEMENTS")
        print("   Recommendation: Address recommendations before filing")
    else:
        print("❌ PETITION REQUIRES SIGNIFICANT WORK")
        print("   Recommendation: Strengthen evidence and address critical issues")
    print("=" * 80)


async def example_4_custom_rules():
    """Example 4: Adding custom validation rules."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: CUSTOM VALIDATION RULES")
    print("=" * 80)

    # Initialize validator
    memory = MemoryManager()
    validator = ValidatorAgent(memory_manager=memory)

    # Add custom rule
    custom_rule = {
        "name": "EB-1A Beneficiary Name Required",
        "category": ValidationCategory.FORMAL,
        "rule_type": ValidationRuleType.REQUIRED,
        "required_fields": ["beneficiary", "petitioner"],
        "severity": "error",
        "message": "EB-1A petition must identify beneficiary and petitioner",
    }

    rule = await validator.aadd_validation_rule(custom_rule, user_id="user_001")
    print(f"\n✅ Added custom rule: {rule.name}")
    print(f"   Rule ID: {rule.rule_id}")
    print(f"   Category: {rule.category.value}")
    print(f"   Severity: {rule.severity}")

    # Test with document missing required fields
    test_document = "This is a petition without proper identification."

    request = ValidationRequest(
        document_id="doc_002",
        content=test_document,
        document_type="eb1a_petition",
        validation_level=ValidationLevel.STRICT,
        user_id="user_001",
    )

    result = await validator.avalidate(request)

    print("\n📋 Validation with custom rule:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Errors: {len(result.errors)}")

    for error in result.errors[:3]:  # Show first 3 errors
        print(f"   - {error}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("VALIDATOR AGENT - COMPREHENSIVE EXAMPLES")
    print("=" * 80)

    await example_1_basic_validation()
    await example_2_self_correction()
    await example_3_petition_validation()
    await example_4_custom_rules()

    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
