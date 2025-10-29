"""Example: Using EB1A Evidence Analyzer to assess petition strength.

This example demonstrates:
1. Creating evidence items for different EB-1A criteria
2. Analyzing individual evidence quality
3. Evaluating criterion satisfaction
4. Calculating overall case strength with recommendations
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.groupagents.eb1a_evidence_analyzer import EB1AEvidenceAnalyzer
from core.memory.memory_manager import MemoryManager
from core.workflows.eb1a.eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                                  EvidenceType)


async def main():
    """Run EB1A evidence analysis example."""
    print("=" * 80)
    print("EB-1A EVIDENCE ANALYZER EXAMPLE")
    print("=" * 80)

    # Initialize analyzer
    memory = MemoryManager()
    analyzer = EB1AEvidenceAnalyzer(memory_manager=memory)

    # ========== 1. Create Evidence Portfolio ==========
    print("\n📋 CREATING EVIDENCE PORTFOLIO\n")

    # Awards Criterion - Strong evidence
    award_1 = EB1AEvidence(
        criterion=EB1ACriterion.AWARDS,
        evidence_type=EvidenceType.AWARD_CERTIFICATE,
        title="ACM Turing Award",
        description=(
            "Received the ACM A.M. Turing Award, widely regarded as the 'Nobel Prize of Computing', "
            "for pioneering contributions to deep learning and artificial intelligence. "
            "This internationally recognized award is presented to individuals who have made "
            "contributions of lasting and major technical importance to computer science."
        ),
        date=datetime(2023, 6, 1),
        source="Association for Computing Machinery - International",
        exhibit_number="A-1",
        file_path="/evidence/turing_award_certificate.pdf",
        metadata={"verified": True, "international_recognition": True},
    )

    award_2 = EB1AEvidence(
        criterion=EB1ACriterion.AWARDS,
        evidence_type=EvidenceType.AWARD_CERTIFICATE,
        title="IEEE Fellow",
        description=(
            "Elected as IEEE Fellow for outstanding contributions to neural network architectures. "
            "IEEE Fellow is the highest grade of IEEE membership, limited to no more than 0.1% of "
            "the total voting membership."
        ),
        date=datetime(2022, 1, 1),
        source="Institute of Electrical and Electronics Engineers",
        exhibit_number="A-2",
        metadata={"verified": True},
    )

    # Scholarly Articles - Strong evidence
    article_1 = EB1AEvidence(
        criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
        evidence_type=EvidenceType.PUBLICATION,
        title="Attention Is All You Need (Transformer Architecture)",
        description=(
            "Published groundbreaking paper in NeurIPS introducing the Transformer architecture "
            "that revolutionized natural language processing. The paper has been cited over 85,000 times "
            "and is the foundation for models like GPT, BERT, and countless applications."
        ),
        date=datetime(2017, 12, 1),
        source="NeurIPS (Neural Information Processing Systems)",
        exhibit_number="B-1",
        file_path="/evidence/transformer_paper.pdf",
        metadata={"citations": 85000, "h_index": 120, "journal_impact_factor": 8.5},
    )

    citation_report = EB1AEvidence(
        criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
        evidence_type=EvidenceType.CITATION_REPORT,
        title="Google Scholar Citation Metrics",
        description=(
            "Google Scholar profile showing 250,000+ total citations, h-index of 120, "
            "and i10-index of 200. Multiple papers with over 10,000 citations each. "
            "Ranked in top 0.1% of AI researchers worldwide."
        ),
        date=datetime.now(),
        source="Google Scholar",
        exhibit_number="B-2",
        metadata={"total_citations": 250000, "h_index": 120, "i10_index": 200},
    )

    # Press Coverage - Moderate evidence
    press_1 = EB1AEvidence(
        criterion=EB1ACriterion.PRESS,
        evidence_type=EvidenceType.PRESS_ARTICLE,
        title="Profile in MIT Technology Review",
        description=(
            "Featured in MIT Technology Review's '35 Innovators Under 35' with extensive profile "
            "discussing contributions to AI. The article reached international audience and "
            "highlighted the transformative impact of the research."
        ),
        date=datetime(2023, 9, 1),
        source="MIT Technology Review - International",
        exhibit_number="C-1",
        metadata={"reach": 500000, "circulation": "international"},
    )

    # Judging - Strong evidence
    judging_1 = EB1AEvidence(
        criterion=EB1ACriterion.JUDGING,
        evidence_type=EvidenceType.RECOMMENDATION_LETTER,
        title="Program Committee Service",
        description=(
            "Served as Area Chair and Senior Program Committee member for top-tier conferences: "
            "NeurIPS, ICML, ICLR, CVPR. Reviewed over 100 papers annually. "
            "Also served as Associate Editor for Journal of Machine Learning Research (JMLR)."
        ),
        source="Conference Organizing Committees",
        exhibit_number="D-1",
        metadata={"papers_reviewed": 300, "conferences": ["NeurIPS", "ICML", "ICLR"]},
    )

    # Original Contribution - Strong evidence
    contribution_1 = EB1AEvidence(
        criterion=EB1ACriterion.ORIGINAL_CONTRIBUTION,
        evidence_type=EvidenceType.PATENT,
        title="Transformer Neural Network Architecture (Patent)",
        description=(
            "Patent granted for novel Transformer architecture that has become the foundation "
            "of modern language models. The architecture has been adopted by Google, OpenAI, "
            "Meta, and thousands of researchers worldwide, fundamentally changing NLP."
        ),
        date=datetime(2020, 3, 1),
        source="US Patent Office",
        exhibit_number="E-1",
        file_path="/evidence/transformer_patent.pdf",
        metadata={"patent_number": "US10,650,000", "citations": 500, "adoptions": 10000},
    )

    # Create evidence portfolio
    evidence_by_criterion = {
        EB1ACriterion.AWARDS: [award_1, award_2],
        EB1ACriterion.SCHOLARLY_ARTICLES: [article_1, citation_report],
        EB1ACriterion.PRESS: [press_1],
        EB1ACriterion.JUDGING: [judging_1],
        EB1ACriterion.ORIGINAL_CONTRIBUTION: [contribution_1],
    }

    total_evidence = sum(len(v) for v in evidence_by_criterion.values())
    print(
        f"✅ Created portfolio with {total_evidence} evidence items across {len(evidence_by_criterion)} criteria\n"
    )

    # ========== 2. Analyze Individual Evidence ==========
    print("\n🔍 ANALYZING INDIVIDUAL EVIDENCE\n")
    print("-" * 80)

    # Analyze the Turing Award evidence
    print(f"\n📄 Evidence: {award_1.title}")
    award_analysis = await analyzer.analyze_evidence(award_1)

    print("\n  Quality Metrics:")
    print(f"    Completeness:  {award_analysis.quality_metrics.completeness:.2f}")
    print(f"    Credibility:   {award_analysis.quality_metrics.credibility:.2f}")
    print(f"    Relevance:     {award_analysis.quality_metrics.relevance:.2f}")
    print(f"    Impact:        {award_analysis.quality_metrics.impact:.2f}")
    print(f"    Overall Score: {award_analysis.quality_metrics.strength_score:.2f}")

    print("\n  Classifications:")
    print(f"    Source Credibility: {award_analysis.source_credibility.value}")
    print(f"    Relevance Level:    {award_analysis.relevance_level.value}")
    print(f"    Impact Level:       {award_analysis.impact_level.value}")

    if award_analysis.missing_elements:
        print("\n  ⚠️  Missing Elements:")
        for gap in award_analysis.missing_elements:
            print(f"    - {gap}")

    if award_analysis.recommendations:
        print("\n  💡 Recommendations:")
        for rec in award_analysis.recommendations[:3]:
            print(f"    - {rec}")

    # ========== 3. Evaluate Criterion Satisfaction ==========
    print("\n\n📊 EVALUATING CRITERION SATISFACTION\n")
    print("-" * 80)

    for criterion, evidence_list in evidence_by_criterion.items():
        print(f"\n{criterion.value.upper()}")
        print(f"Evidence items: {len(evidence_list)}")

        evaluation = await analyzer.evaluate_criterion_satisfaction(criterion, evidence_list)

        status = "✅ SATISFIED" if evaluation.is_satisfied else "❌ NOT SATISFIED"
        print(f"Status: {status}")
        print(f"Strength Score: {evaluation.strength_score:.1f}/100")
        print(f"Confidence Level: {evaluation.confidence_level:.2f}")
        print(
            f"Strong Evidence Count: {evaluation.strong_evidence_count}/{evaluation.total_evidence_count}"
        )

        if evaluation.missing_elements:
            print("\nMissing Elements:")
            for gap in evaluation.missing_elements[:2]:
                print(f"  - {gap}")

        if evaluation.recommendations:
            print("\nTop Recommendation:")
            print(f"  - {evaluation.recommendations[0]}")

    # ========== 4. Calculate Overall Case Strength ==========
    print("\n\n🎯 OVERALL CASE STRENGTH ANALYSIS\n")
    print("=" * 80)

    case_analysis = await analyzer.calculate_case_strength(evidence_by_criterion)

    print("\n📈 SUMMARY METRICS:")
    print(f"  Overall Score:          {case_analysis.overall_score:.1f}/100")
    print(f"  Approval Probability:   {case_analysis.approval_probability:.1%}")
    print(f"  Risk Level:             {case_analysis.risk_level.value.upper()}")
    print(f"  Criteria Satisfied:     {case_analysis.satisfied_criteria_count}/10")
    print(
        f"  Meets Minimum (3):      {'✅ YES' if case_analysis.meets_minimum_criteria else '❌ NO'}"
    )
    print(f"  Est. Days to Ready:     {case_analysis.estimated_days_to_ready} days")

    if case_analysis.strengths:
        print("\n💪 STRENGTHS:")
        for strength in case_analysis.strengths:
            print(f"  ✅ {strength}")

    if case_analysis.risks:
        print("\n⚠️  RISKS:")
        for risk in case_analysis.risks:
            print(f"  ⚠️  {risk}")

    if case_analysis.priority_recommendations:
        print("\n🔥 PRIORITY RECOMMENDATIONS:")
        for i, rec in enumerate(case_analysis.priority_recommendations, 1):
            print(f"  {i}. {rec}")

    if case_analysis.secondary_recommendations:
        print("\n💡 SECONDARY RECOMMENDATIONS:")
        for i, rec in enumerate(case_analysis.secondary_recommendations, 1):
            print(f"  {i}. {rec}")

    # ========== 5. Detailed Criterion Breakdown ==========
    print("\n\n📋 DETAILED CRITERION BREAKDOWN\n")
    print("=" * 80)

    for criterion, evaluation in case_analysis.criterion_evaluations.items():
        status_symbol = "✅" if evaluation.is_satisfied else "❌"
        print(f"\n{status_symbol} {criterion.value.upper()}")
        print(
            f"   Score: {evaluation.strength_score:.1f}/100 | Confidence: {evaluation.confidence_level:.2f}"
        )
        print(
            f"   Evidence: {evaluation.strong_evidence_count} strong / {evaluation.total_evidence_count} total"
        )

        # Show individual evidence scores
        for i, evidence_analysis in enumerate(evaluation.evidence_analyses, 1):
            score = evidence_analysis.quality_metrics.strength_score
            strength_indicator = "💪" if score > 0.6 else "⚠️"
            print(
                f"      {strength_indicator} Evidence {i}: {score:.2f} - {evidence_analysis.impact_level.value}"
            )

    # ========== 6. Filing Readiness Assessment ==========
    print("\n\n📝 FILING READINESS ASSESSMENT\n")
    print("=" * 80)

    if case_analysis.overall_score >= 80 and case_analysis.satisfied_criteria_count >= 4:
        print("\n✅ CASE IS STRONG - Ready for filing consideration")
        print(
            f"   - Exceeds minimum criteria requirement ({case_analysis.satisfied_criteria_count} criteria)"
        )
        print(f"   - High overall score ({case_analysis.overall_score:.1f}/100)")
        print(f"   - Good approval probability ({case_analysis.approval_probability:.1%})")
        print("\n   Recommendation: Proceed with petition preparation")

    elif case_analysis.overall_score >= 70 and case_analysis.satisfied_criteria_count >= 3:
        print("\n⚠️  CASE IS MODERATE - Consider strengthening before filing")
        print(
            f"   - Meets minimum criteria requirement ({case_analysis.satisfied_criteria_count} criteria)"
        )
        print(f"   - Moderate overall score ({case_analysis.overall_score:.1f}/100)")
        print(f"   - Moderate approval probability ({case_analysis.approval_probability:.1%})")
        print("\n   Recommendation: Address priority recommendations before filing")

    else:
        print("\n❌ CASE NEEDS SIGNIFICANT IMPROVEMENT")
        print(
            f"   - Below minimum or weak criteria ({case_analysis.satisfied_criteria_count} satisfied)"
        )
        print(f"   - Low overall score ({case_analysis.overall_score:.1f}/100)")
        print(f"   - Low approval probability ({case_analysis.approval_probability:.1%})")
        print("\n   Recommendation: Develop stronger evidence portfolio before filing")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
