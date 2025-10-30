"""Example: Complete EB-1A petition generation workflow.

This example demonstrates:
1. Creating petition request with evidence
2. Generating complete petition
3. Validating petition quality
4. Using templates and language patterns
5. Producing final report

Run:
    python examples/eb1a_workflow_example.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.memory.memory_manager import MemoryManager
from core.workflows.eb1a import EB1ACoordinator, EB1APetitionRequest
from core.workflows.eb1a.eb1a_coordinator import EB1ACriterion, EB1AEvidence, EvidenceType
from core.workflows.eb1a.templates import LanguagePatterns, SectionTemplates
from core.workflows.eb1a.validators import EB1AValidator, ValidationReportGenerator


async def main():
    """Run complete EB-1A workflow example."""
    print("=" * 80)
    print("EB-1A PETITION GENERATION WORKFLOW EXAMPLE")
    print("=" * 80)
    print()

    # Step 1: Initialize components
    print("Step 1: Initializing EB-1A Coordinator...")
    memory = MemoryManager()
    coordinator = EB1ACoordinator(memory_manager=memory)
    validator = EB1AValidator(strict=True)
    print("✓ Initialized\n")

    # Step 2: Prepare evidence portfolio
    print("Step 2: Preparing evidence portfolio...")
    evidence = [
        # Awards
        EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Best Paper Award - International Conference on Machine Learning (ICML)",
            description=(
                "Received Best Paper Award at ICML 2024 for groundbreaking work on "
                "transformer architectures. Selected from 5,000+ submissions."
            ),
            date=datetime(2024, 7, 15),
            source="ICML 2024 Committee",
            exhibit_number="A-1",
        ),
        EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="IEEE Outstanding Young Researcher Award",
            description=(
                "Recognized by IEEE for exceptional contributions to artificial intelligence "
                "research. Given to top 5 researchers worldwide under age 35."
            ),
            date=datetime(2023, 11, 20),
            source="IEEE Computer Society",
            exhibit_number="A-2",
        ),
        # Scholarly Articles
        EB1AEvidence(
            criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
            evidence_type=EvidenceType.PUBLICATION,
            title="Attention Is All You Need 2.0: Enhanced Transformer Architecture",
            description=(
                "Published in Nature Machine Intelligence (Impact Factor: 25.8). "
                "Cited 450 times in 18 months."
            ),
            date=datetime(2023, 3, 1),
            source="Nature Machine Intelligence",
            exhibit_number="B-1",
        ),
        EB1AEvidence(
            criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
            evidence_type=EvidenceType.CITATION_REPORT,
            title="Google Scholar Citation Report",
            description=(
                "Total citations: 2,450+, h-index: 28, i10-index: 45. "
                "Demonstrates significant scholarly impact."
            ),
            date=datetime(2024, 10, 1),
            source="Google Scholar",
            exhibit_number="B-2",
        ),
        # Judging
        EB1AEvidence(
            criterion=EB1ACriterion.JUDGING,
            evidence_type=EvidenceType.RECOMMENDATION_LETTER,
            title="Program Committee Member - NeurIPS 2024",
            description=(
                "Invited to serve on program committee for NeurIPS, world's premier "
                "AI conference. Reviewed 25+ papers."
            ),
            date=datetime(2024, 5, 1),
            source="NeurIPS 2024 Organizing Committee",
            exhibit_number="C-1",
        ),
        EB1AEvidence(
            criterion=EB1ACriterion.JUDGING,
            evidence_type=EvidenceType.RECOMMENDATION_LETTER,
            title="NSF Grant Review Panelist",
            description=(
                "Selected by National Science Foundation to review research proposals "
                "in artificial intelligence. Reviewed $5M+ in grant applications."
            ),
            date=datetime(2024, 3, 15),
            source="National Science Foundation",
            exhibit_number="C-2",
        ),
        # Original Contributions
        EB1AEvidence(
            criterion=EB1ACriterion.ORIGINAL_CONTRIBUTION,
            evidence_type=EvidenceType.PATENT,
            title="Novel Attention Mechanism for Neural Networks (US Patent)",
            description=(
                "Patented novel attention mechanism now used in major AI systems. "
                "Licensed by 3 Fortune 500 companies."
            ),
            date=datetime(2023, 9, 1),
            source="USPTO",
            exhibit_number="D-1",
        ),
        # Press Coverage
        EB1AEvidence(
            criterion=EB1ACriterion.PRESS,
            evidence_type=EvidenceType.PRESS_ARTICLE,
            title="'AI Researcher Revolutionizes Machine Learning' - Wired Magazine",
            description=(
                "Featured profile in Wired Magazine (circulation: 1.5M) discussing "
                "contributions to transformer architectures."
            ),
            date=datetime(2024, 2, 1),
            source="Wired Magazine",
            exhibit_number="E-1",
        ),
    ]
    print(f"✓ Prepared {len(evidence)} evidence items\n")

    # Step 3: Create petition request
    print("Step 3: Creating petition request...")
    request = EB1APetitionRequest(
        beneficiary_name="Dr. Jane Smith",
        field_of_expertise="Artificial Intelligence and Machine Learning",
        country_of_birth="India",
        current_position="Senior AI Researcher",
        current_employer="Tech Research Institute",
        evidence=evidence,
        primary_criteria=[
            EB1ACriterion.AWARDS,
            EB1ACriterion.SCHOLARLY_ARTICLES,
            EB1ACriterion.JUDGING,
            EB1ACriterion.ORIGINAL_CONTRIBUTION,
            EB1ACriterion.PRESS,
        ],
        background_summary=(
            "Dr. Smith is a leading researcher in artificial intelligence with focus on "
            "transformer architectures and attention mechanisms."
        ),
        accomplishments=[
            "Developed novel attention mechanism used in state-of-the-art AI systems",
            "Published 35+ peer-reviewed papers with 2,450+ citations",
            "Received 2 major international awards",
            "Served as reviewer for top-tier conferences and NSF",
        ],
        citations_count=2450,
        h_index=28,
        tone="professional",
        max_pages=15,
        include_comparative_analysis=True,
    )
    print("✓ Request created\n")

    # Step 4: Generate petition
    print("Step 4: Generating complete petition...")
    print("(This would normally take 2-5 minutes with real LLM calls)")
    result = await coordinator.generate_petition(request)
    print(f"✓ Generated petition with {result.criteria_coverage} criteria sections")
    print(f"  - Total word count: {result.total_word_count:,}")
    print(f"  - Total exhibits: {result.total_exhibits}")
    print(f"  - Overall score: {result.overall_score:.2f}\n")

    # Step 5: Validate petition
    print("Step 5: Validating petition quality...")
    validation = validator.validate(result)
    print("✓ Validation complete")
    print(f"  - Valid: {validation.is_valid}")
    print(f"  - Score: {validation.score:.2%}")
    print(f"  - Pass Rate: {validation.overall_pass_rate:.1%}")
    print(f"  - Passed checks: {len(validation.passed_checks)}/{validation.total_checks}")
    print(f"  - Section results: {len(validation.section_results)} sections analyzed")
    print(f"  - Critical issues: {len(validation.critical_issues)}")
    print(f"  - Warnings: {len(validation.warnings)}")
    print()

    # Step 6: Display section-level validation results
    print("Step 6: Section-Level Validation Results...")
    if validation.section_results:
        for criterion, section_result in validation.section_results.items():
            status = "✅" if section_result.is_valid else "❌"
            print(f"  {status} {criterion.value}")
            print(
                f"     Score: {section_result.score:.2%} | Pass Rate: {section_result.pass_rate:.1%}"
            )
            print(
                f"     Checks: {len(section_result.passed_checks)}/{len(section_result.checks)} passed"
            )
            if section_result.failed_checks:
                print(f"     Failed: {len(section_result.failed_checks)} checks")
                for check in section_result.failed_checks[:2]:  # Show first 2
                    print(f"       • {check.description}")
    print()

    # Step 7: Display validation issues
    if validation.critical_issues:
        print("CRITICAL ISSUES (must fix before filing):")
        for issue in validation.critical_issues:
            print(f"  ❌ [{issue.category}] {issue.message}")
            print(f"     → {issue.suggestion}")
        print()

    if validation.warnings:
        print("WARNINGS (recommended to fix):")
        for issue in validation.warnings[:5]:  # Show top 5
            print(f"  ⚠️  [{issue.category}] {issue.message}")
            print(f"     → {issue.suggestion}")
        print()

    # Step 8: Generate validation reports
    print("Step 8: Generating validation reports...")
    report_generator = ValidationReportGenerator()

    # Print console summary
    report_generator.print_summary(validation)

    # Save detailed reports
    try:
        report_generator.save_markdown_report(validation, "petition_validation.md")
        print("✓ Saved Markdown report: petition_validation.md")
    except Exception as e:
        print(f"  Note: Could not save Markdown report: {e}")

    try:
        report_generator.save_html_report(validation, "petition_validation.html")
        print("✓ Saved HTML report: petition_validation.html")
    except Exception as e:
        print(f"  Note: Could not save HTML report: {e}")
    print()

    # Step 7: Display petition summary
    print("=" * 80)
    print("PETITION SUMMARY")
    print("=" * 80)
    print()
    print(f"Beneficiary: {result.beneficiary_name}")
    print(f"Field: {result.field_of_expertise}")
    print(f"Criteria covered: {result.criteria_coverage}/10")
    print()

    print("Sections:")
    for criterion, section in result.sections.items():
        print(f"  • {criterion.value}")
        print(f"    - Confidence: {section.confidence_score:.2f}")
        print(f"    - Evidence items: {len(section.evidence_references)}")
        print(f"    - Word count: {section.word_count}")
    print()

    print("Strengths:")
    for strength in result.strengths:
        print(f"  ✓ {strength}")
    print()

    if result.weaknesses:
        print("Weaknesses:")
        for weakness in result.weaknesses:
            print(f"  ⚠️  {weakness}")
        print()

    print("Recommendations:")
    for rec in result.recommendations[:5]:  # Top 5
        print(f"  → {rec}")
    print()

    # Step 8: Demonstrate template usage
    print("=" * 80)
    print("TEMPLATE EXAMPLES")
    print("=" * 80)
    print()

    print("Example 1: Get awards template")
    awards_template = SectionTemplates.get_template("2.1")
    print(f"Criterion: {awards_template.criterion_name}")
    print(f"Regulatory text: {awards_template.regulatory_text}")
    print()

    print("Example 2: Format impact statement")
    impact = LanguagePatterns.format_impact_statement(
        field="artificial intelligence",
        specific_impact="novel attention mechanism that reduces computational complexity by 40%",
        evidence="Exhibit D-1",
    )
    print(f"Impact statement:\n{impact}")
    print()

    print("Example 3: Format comparative statement")
    comparison = LanguagePatterns.format_comparative_statement(
        beneficiary_name="Dr. Smith",
        field="artificial intelligence",
        metric="h-index",
        value=28,
        context="top 5% of AI researchers worldwide",
    )
    print(f"Comparative statement:\n{comparison}")
    print()

    print("Example 4: Legal citation")
    kazarian = LanguagePatterns.get_precedent_citation("kazarian")
    citation = LanguagePatterns.format_legal_citation(
        case_name=kazarian["full_name"],
        citation=kazarian["citation"],
        principle=kazarian["principle"],
    )
    print(f"Legal citation:\n{citation}...")
    print()

    # Step 9: Performance metrics
    print("=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)
    print()
    print(f"Generation time: {result.generation_time_seconds:.2f} seconds")
    print("Validation time: <1 second")
    print(f"Total processing: {result.generation_time_seconds + 0.5:.2f} seconds")
    print()

    # Step 10: Next steps
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Review and address any critical issues")
    print("2. Enhance weak sections with additional evidence")
    print("3. Add legal citations where recommended")
    print("4. Generate PDF with exhibits using pdf_assembly module")
    print("5. Have attorney review before filing")
    print("6. Submit Form I-140 with petition to USCIS")
    print()

    print("✅ EB-1A Workflow Example Complete!")


if __name__ == "__main__":
    asyncio.run(main())
