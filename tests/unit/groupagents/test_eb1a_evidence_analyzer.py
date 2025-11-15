"""Unit tests for EB1A Evidence Analyzer."""

from __future__ import annotations

from datetime import datetime

import pytest

from core.groupagents.eb1a_evidence_analyzer import (
    CaseStrengthAnalysis,
    CriterionEvaluation,
    EB1AEvidenceAnalyzer,
    EvidenceAnalysisResult,
    ImpactLevel,
    RelevanceLevel,
    RiskLevel,
    SourceCredibility,
)
from core.memory.memory_manager import MemoryManager
from core.workflows.eb1a.eb1a_coordinator import EB1ACriterion, EB1AEvidence, EvidenceType


@pytest.fixture
def memory_manager():
    """Create memory manager for tests."""
    return MemoryManager()


@pytest.fixture
def analyzer(memory_manager):
    """Create analyzer instance."""
    return EB1AEvidenceAnalyzer(memory_manager=memory_manager)


@pytest.fixture
def strong_award_evidence():
    """Create strong award evidence."""
    return EB1AEvidence(
        criterion=EB1ACriterion.AWARDS,
        evidence_type=EvidenceType.AWARD_CERTIFICATE,
        title="Nobel Prize in Physics",
        description=(
            "Awarded the Nobel Prize in Physics for groundbreaking research in quantum computing. "
            "This internationally recognized award demonstrates exceptional contributions to the field. "
            "The work has been cited over 5000 times and has transformed the industry."
        ),
        date=datetime(2022, 10, 1),
        source="The Nobel Foundation - International",
        exhibit_number="A-1",
        file_path="/evidence/nobel_certificate.pdf",
        metadata={"citations": 5000, "verified": True, "impact": "transformative"},
    )


@pytest.fixture
def weak_award_evidence():
    """Create weak award evidence."""
    return EB1AEvidence(
        criterion=EB1ACriterion.AWARDS,
        evidence_type=EvidenceType.AWARD_CERTIFICATE,
        title="Local Award",
        description="Received award",
        source="Local organization",
        metadata={},
    )


@pytest.fixture
def scholarly_evidence():
    """Create scholarly article evidence."""
    return EB1AEvidence(
        criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
        evidence_type=EvidenceType.PUBLICATION,
        title="Breakthrough Research in AI",
        description=(
            "Published peer-reviewed article in Nature on revolutionary AI algorithms. "
            "The paper has been cited 1200 times and influenced major research directions."
        ),
        date=datetime(2021, 5, 15),
        source="Nature Journal - International",
        exhibit_number="B-3",
        file_path="/evidence/nature_paper.pdf",
        metadata={"citations": 1200, "journal_impact_factor": 42.7},
    )


@pytest.fixture
def press_evidence():
    """Create press coverage evidence."""
    return EB1AEvidence(
        criterion=EB1ACriterion.PRESS,
        evidence_type=EvidenceType.PRESS_ARTICLE,
        title="Profile in New York Times",
        description=(
            "Featured profile article in The New York Times discussing groundbreaking work in AI. "
            "The article reached over 2 million readers and highlighted major contributions."
        ),
        date=datetime(2023, 3, 10),
        source="The New York Times - National",
        exhibit_number="C-2",
        metadata={"reach": 2000000, "circulation": "national"},
    )


class TestEvidenceAnalysis:
    """Test individual evidence analysis."""

    @pytest.mark.asyncio
    async def test_analyze_strong_evidence(self, analyzer, strong_award_evidence):
        """Test analysis of strong evidence."""
        result = await analyzer.analyze_evidence(strong_award_evidence)

        assert isinstance(result, EvidenceAnalysisResult)
        assert result.evidence_id == strong_award_evidence.evidence_id
        assert result.criterion == EB1ACriterion.AWARDS

        # Check quality metrics
        assert result.quality_metrics.completeness >= 0.8
        assert result.quality_metrics.credibility >= 0.9
        assert result.quality_metrics.relevance >= 0.9
        assert result.quality_metrics.impact >= 0.9
        assert result.quality_metrics.strength_score >= 0.8

        # Check classifications
        assert result.source_credibility == SourceCredibility.INTERNATIONAL
        assert result.relevance_level == RelevanceLevel.EXACT_MATCH
        assert result.impact_level in [ImpactLevel.EXCEPTIONAL, ImpactLevel.HIGH]

        # Should have minimal gaps
        assert len(result.missing_elements) <= 1

    @pytest.mark.asyncio
    async def test_analyze_weak_evidence(self, analyzer, weak_award_evidence):
        """Test analysis of weak evidence."""
        result = await analyzer.analyze_evidence(weak_award_evidence)

        # Should have lower scores
        assert result.quality_metrics.strength_score < 0.6
        assert result.quality_metrics.completeness < 0.7

        # Should identify gaps
        assert len(result.missing_elements) > 0
        assert any("description" in gap.lower() for gap in result.missing_elements)

        # Should have critical recommendations
        assert len(result.recommendations) > 0
        assert any("CRITICAL" in rec for rec in result.recommendations)

    @pytest.mark.asyncio
    async def test_completeness_assessment(self, analyzer):
        """Test completeness scoring."""
        # Complete evidence
        complete = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Award Title",
            description="Detailed description with sufficient context and information about the award significance.",
            date=datetime.now(),
            source="Source Organization",
            exhibit_number="A-1",
            file_path="/path/to/file.pdf",
            metadata={"verified": True},
        )

        result = await analyzer.analyze_evidence(complete)
        assert result.quality_metrics.completeness >= 0.9

        # Incomplete evidence
        incomplete = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Award",
            description="Brief",
        )

        result = await analyzer.analyze_evidence(incomplete)
        assert result.quality_metrics.completeness < 0.5

    @pytest.mark.asyncio
    async def test_credibility_assessment(self, analyzer):
        """Test source credibility scoring."""
        test_cases = [
            ("Nobel Prize - International", SourceCredibility.INTERNATIONAL, 1.0),
            ("National Science Foundation", SourceCredibility.NATIONAL, 0.8),
            ("State University", SourceCredibility.REGIONAL, 0.5),
            ("City Award", SourceCredibility.LOCAL, 0.3),
            ("Unknown Organization", SourceCredibility.UNKNOWN, 0.1),
        ]

        for source, expected_cred, expected_score in test_cases:
            evidence = EB1AEvidence(
                criterion=EB1ACriterion.AWARDS,
                evidence_type=EvidenceType.AWARD_CERTIFICATE,
                title="Test Award",
                description="Test description for credibility assessment",
                source=source,
            )

            result = await analyzer.analyze_evidence(evidence)
            assert result.source_credibility == expected_cred
            assert abs(result.quality_metrics.credibility - expected_score) < 0.2

    @pytest.mark.asyncio
    async def test_impact_assessment(self, analyzer):
        """Test impact scoring based on metrics."""
        # High impact with citations
        high_impact = EB1AEvidence(
            criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
            evidence_type=EvidenceType.CITATION_REPORT,
            title="Highly Cited Research",
            description="Research paper with significant impact",
            metadata={"citations": 1500},
        )

        result = await analyzer.analyze_evidence(high_impact)
        assert result.impact_level in [ImpactLevel.EXCEPTIONAL, ImpactLevel.HIGH]
        assert result.quality_metrics.impact >= 0.8

        # Low impact
        low_impact = EB1AEvidence(
            criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
            evidence_type=EvidenceType.PUBLICATION,
            title="Paper",
            description="Published paper",
            metadata={},
        )

        result = await analyzer.analyze_evidence(low_impact)
        assert result.quality_metrics.impact < 0.5


class TestCriterionEvaluation:
    """Test criterion-level evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_strong_criterion(
        self, analyzer, strong_award_evidence, scholarly_evidence
    ):
        """Test evaluation of strong criterion with multiple evidence."""
        # Create additional strong evidence
        evidence2 = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="ACM Turing Award",
            description=(
                "Received ACM Turing Award for contributions to computer science. "
                "Internationally recognized as the 'Nobel Prize of Computing'."
            ),
            source="Association for Computing Machinery - International",
            metadata={"verified": True},
        )

        evidence_list = [strong_award_evidence, evidence2]

        result = await analyzer.evaluate_criterion_satisfaction(EB1ACriterion.AWARDS, evidence_list)

        assert isinstance(result, CriterionEvaluation)
        assert result.criterion == EB1ACriterion.AWARDS
        assert result.is_satisfied is True
        assert result.strength_score >= 70.0
        assert result.confidence_level >= 0.6
        assert result.total_evidence_count == 2
        assert result.strong_evidence_count >= 2

    @pytest.mark.asyncio
    async def test_evaluate_weak_criterion(self, analyzer, weak_award_evidence):
        """Test evaluation of weak criterion."""
        result = await analyzer.evaluate_criterion_satisfaction(
            EB1ACriterion.AWARDS, [weak_award_evidence]
        )

        assert result.is_satisfied is False
        assert result.strength_score < 70.0
        assert result.strong_evidence_count < 2
        assert len(result.missing_elements) > 0
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_criterion_with_no_evidence(self, analyzer):
        """Test criterion evaluation with no evidence."""
        result = await analyzer.evaluate_criterion_satisfaction(EB1ACriterion.JUDGING, [])

        assert result.is_satisfied is False
        assert result.strength_score == 0.0
        assert result.confidence_level == 0.0
        assert result.total_evidence_count == 0
        assert result.strong_evidence_count == 0

    @pytest.mark.asyncio
    async def test_criterion_confidence_calculation(self, analyzer, strong_award_evidence):
        """Test confidence level calculation."""
        # Single strong evidence - moderate confidence
        result = await analyzer.evaluate_criterion_satisfaction(
            EB1ACriterion.AWARDS, [strong_award_evidence]
        )
        single_confidence = result.confidence_level

        # Multiple strong evidence - higher confidence
        evidence2 = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="International Award",
            description="Another strong international award with verified documentation.",
            source="International Organization",
            metadata={"verified": True},
        )

        result2 = await analyzer.evaluate_criterion_satisfaction(
            EB1ACriterion.AWARDS, [strong_award_evidence, evidence2]
        )
        multiple_confidence = result2.confidence_level

        # More evidence should increase confidence
        assert multiple_confidence >= single_confidence

    @pytest.mark.asyncio
    async def test_criterion_gap_identification(self, analyzer):
        """Test identification of criterion-specific gaps."""
        # Awards criterion without international recognition
        local_award = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Regional Award",
            description="Award from regional organization",
            source="Regional Committee",
        )

        result = await analyzer.evaluate_criterion_satisfaction(EB1ACriterion.AWARDS, [local_award])

        # Should identify lack of international recognition
        assert any("international" in gap.lower() for gap in result.missing_elements)


class TestCaseStrengthAnalysis:
    """Test overall case strength calculation."""

    @pytest.mark.asyncio
    async def test_strong_case_analysis(
        self, analyzer, strong_award_evidence, scholarly_evidence, press_evidence
    ):
        """Test analysis of strong case meeting requirements."""
        # Create evidence for 4 criteria (exceeds minimum 3)
        judging_evidence = EB1AEvidence(
            criterion=EB1ACriterion.JUDGING,
            evidence_type=EvidenceType.RECOMMENDATION_LETTER,
            title="Peer Review Service",
            description=(
                "Served as reviewer for top-tier international conferences and journals including NeurIPS, "
                "ICML, and Nature. Reviewed over 50 papers in the last 3 years. "
                "Panel member for prestigious grant committees and international awards."
            ),
            source="International Conference Committee",
            metadata={"papers_reviewed": 50, "verified": True},
        )

        evidence_by_criterion = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],  # 2 strong
            EB1ACriterion.SCHOLARLY_ARTICLES: [scholarly_evidence, scholarly_evidence],  # 2 strong
            EB1ACriterion.PRESS: [press_evidence, press_evidence],  # 2 items
            EB1ACriterion.JUDGING: [judging_evidence, judging_evidence],  # 2 strong
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        assert isinstance(result, CaseStrengthAnalysis)
        assert result.meets_minimum_criteria is True
        assert result.satisfied_criteria_count >= 3
        assert result.overall_score >= 70.0
        assert result.approval_probability >= 0.6
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]
        assert len(result.strengths) > 0
        assert result.estimated_days_to_ready is not None

    @pytest.mark.asyncio
    async def test_weak_case_analysis(self, analyzer, weak_award_evidence):
        """Test analysis of weak case below requirements."""
        evidence_by_criterion = {
            EB1ACriterion.AWARDS: [weak_award_evidence],
            EB1ACriterion.MEMBERSHIP: [weak_award_evidence],  # Reusing for test
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        assert result.meets_minimum_criteria is False
        assert result.satisfied_criteria_count < 3
        assert result.overall_score < 60.0
        assert result.approval_probability < 0.5
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(result.risks) > 0
        assert any("CRITICAL" in risk for risk in result.risks)

    @pytest.mark.asyncio
    async def test_minimum_criteria_case(self, analyzer, strong_award_evidence):
        """Test case at exactly minimum 3 criteria."""
        evidence_by_criterion = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.SCHOLARLY_ARTICLES: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.PRESS: [strong_award_evidence, strong_award_evidence],
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        assert result.meets_minimum_criteria is True
        assert result.satisfied_criteria_count == 3

        # Should have warning about being at minimum
        assert any(
            "minimum" in risk.lower() or "minimum" in rec.lower()
            for risk in result.risks
            + result.priority_recommendations
            + result.secondary_recommendations
        )

    @pytest.mark.asyncio
    async def test_case_with_no_evidence(self, analyzer):
        """Test case with no evidence."""
        result = await analyzer.calculate_case_strength({})

        assert result.meets_minimum_criteria is False
        assert result.satisfied_criteria_count == 0
        assert result.overall_score == 0.0
        assert result.approval_probability < 0.3  # Very low probability
        assert result.risk_level == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_approval_probability_calculation(self, analyzer, strong_award_evidence):
        """Test approval probability increases with strength."""
        # Weak case
        weak_case = {EB1ACriterion.AWARDS: [strong_award_evidence]}  # Only 1 criterion
        weak_result = await analyzer.calculate_case_strength(weak_case)

        # Strong case
        strong_case = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.SCHOLARLY_ARTICLES: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.PRESS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.JUDGING: [strong_award_evidence, strong_award_evidence],
        }
        strong_result = await analyzer.calculate_case_strength(strong_case)

        # Stronger case should have higher probability
        assert strong_result.approval_probability > weak_result.approval_probability

    @pytest.mark.asyncio
    async def test_risk_level_determination(
        self, analyzer, strong_award_evidence, weak_award_evidence
    ):
        """Test risk level classification."""
        # Critical risk - below minimum criteria
        critical_case = {EB1ACriterion.AWARDS: [weak_award_evidence]}
        critical_result = await analyzer.calculate_case_strength(critical_case)
        assert critical_result.risk_level == RiskLevel.CRITICAL

        # Lower risk - meets requirements
        good_case = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.SCHOLARLY_ARTICLES: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.PRESS: [strong_award_evidence, strong_award_evidence],
        }
        good_result = await analyzer.calculate_case_strength(good_case)
        assert good_result.risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]

    @pytest.mark.asyncio
    async def test_strength_identification(self, analyzer, strong_award_evidence):
        """Test identification of case strengths."""
        # Case exceeding minimum with strong evidence
        evidence_by_criterion = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.SCHOLARLY_ARTICLES: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.PRESS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.JUDGING: [strong_award_evidence, strong_award_evidence],
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        # Should identify exceeding minimum
        assert any("exceed" in s.lower() for s in result.strengths)

        # Should identify strong criteria
        assert len(result.strengths) > 0

    @pytest.mark.asyncio
    async def test_recommendations_prioritization(self, analyzer, weak_award_evidence):
        """Test that recommendations are properly prioritized."""
        # Mixed case - some satisfied, some not
        strong = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Strong Award",
            description="Strong international award with comprehensive documentation and impact.",
            source="International Organization",
            metadata={"verified": True, "citations": 1000},
        )

        evidence_by_criterion = {
            EB1ACriterion.AWARDS: [strong, strong],  # Strong
            EB1ACriterion.MEMBERSHIP: [weak_award_evidence],  # Weak
            EB1ACriterion.PRESS: [weak_award_evidence],  # Weak
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        # Should have priority recommendations for critical issues
        assert len(result.priority_recommendations) > 0

        # If satisfied criteria >= 3, might have secondary recommendations
        if result.satisfied_criteria_count >= 3:
            # May have secondary recommendations for improvements
            pass

    @pytest.mark.asyncio
    async def test_time_estimation(self, analyzer, strong_award_evidence, weak_award_evidence):
        """Test time-to-ready estimation."""
        # Nearly ready case
        ready_case = {
            EB1ACriterion.AWARDS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.SCHOLARLY_ARTICLES: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.PRESS: [strong_award_evidence, strong_award_evidence],
            EB1ACriterion.JUDGING: [strong_award_evidence, strong_award_evidence],
        }
        ready_result = await analyzer.calculate_case_strength(ready_case)

        # Weak case needing work
        weak_case = {
            EB1ACriterion.AWARDS: [weak_award_evidence],
            EB1ACriterion.MEMBERSHIP: [weak_award_evidence],
        }
        weak_result = await analyzer.calculate_case_strength(weak_case)

        # Weak case should take longer
        assert weak_result.estimated_days_to_ready > ready_result.estimated_days_to_ready


class TestScoringThresholds:
    """Test scoring thresholds and weights."""

    @pytest.mark.asyncio
    async def test_strong_evidence_threshold(self, analyzer):
        """Test that evidence above threshold is considered strong."""
        # Create evidence right at threshold
        threshold_evidence = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Threshold Award",
            description="Award with documentation meeting minimum threshold requirements.",
            source="National Organization",
            metadata={"verified": True},
        )

        result = await analyzer.analyze_evidence(threshold_evidence)

        # Should be close to threshold
        assert abs(result.quality_metrics.strength_score - 0.6) < 0.3

    @pytest.mark.asyncio
    async def test_criterion_satisfied_threshold(self, analyzer, strong_award_evidence):
        """Test criterion satisfaction threshold of 70."""
        result = await analyzer.evaluate_criterion_satisfaction(
            EB1ACriterion.AWARDS, [strong_award_evidence, strong_award_evidence]
        )

        if result.is_satisfied:
            assert result.strength_score >= 70.0
        else:
            assert result.strength_score < 70.0

    def test_scoring_weights(self, analyzer):
        """Test that scoring weights sum to 1.0."""
        total_weight = sum(analyzer.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.01  # Should sum to 1.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_evidence_with_missing_fields(self, analyzer):
        """Test handling of evidence with missing optional fields."""
        minimal_evidence = EB1AEvidence(
            criterion=EB1ACriterion.AWARDS,
            evidence_type=EvidenceType.AWARD_CERTIFICATE,
            title="Minimal Evidence",
            description="Minimal description",
        )

        result = await analyzer.analyze_evidence(minimal_evidence)

        # Should still produce result
        assert isinstance(result, EvidenceAnalysisResult)
        assert 0.0 <= result.quality_metrics.strength_score <= 1.0

    @pytest.mark.asyncio
    async def test_evidence_with_empty_metadata(self, analyzer):
        """Test handling of evidence with empty metadata."""
        evidence = EB1AEvidence(
            criterion=EB1ACriterion.SCHOLARLY_ARTICLES,
            evidence_type=EvidenceType.PUBLICATION,
            title="Paper",
            description="Research paper",
            metadata={},
        )

        result = await analyzer.analyze_evidence(evidence)

        # Should handle gracefully
        assert isinstance(result, EvidenceAnalysisResult)

    @pytest.mark.asyncio
    async def test_criterion_with_duplicate_evidence(self, analyzer, strong_award_evidence):
        """Test handling of duplicate evidence IDs."""
        # Same evidence instance multiple times
        result = await analyzer.evaluate_criterion_satisfaction(
            EB1ACriterion.AWARDS, [strong_award_evidence, strong_award_evidence]
        )

        # Should process both
        assert result.total_evidence_count == 2

    @pytest.mark.asyncio
    async def test_all_criteria_satisfied(self, analyzer, strong_award_evidence):
        """Test case where all 10 criteria are satisfied."""
        # Create evidence for all criteria
        evidence_by_criterion = {
            criterion: [strong_award_evidence, strong_award_evidence] for criterion in EB1ACriterion
        }

        result = await analyzer.calculate_case_strength(evidence_by_criterion)

        assert result.satisfied_criteria_count <= 10
        assert result.overall_score >= 80.0  # Should be very high
        assert result.risk_level == RiskLevel.LOW
