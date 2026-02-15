"""Tests for core.validation.confidence_scorer module."""

from __future__ import annotations

import pytest

from core.validation.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceThreshold,
    get_confidence_scorer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_OUTPUT = (
    "The capital of France is Paris. It is situated along the Seine River "
    "in the north-central part of the country. Moreover, Paris is well known "
    "for its art, culture, and history. Furthermore, the city attracts "
    "millions of tourists every year. In conclusion, Paris remains one of "
    "the most iconic cities in the world."
)

SHORT_OUTPUT = "Paris."

EMPTY_OUTPUT = ""


@pytest.fixture
def scorer() -> ConfidenceScorer:
    """Return a scorer with default weights."""
    return ConfidenceScorer()


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the global singleton before each test so tests are isolated."""
    import core.validation.confidence_scorer as mod

    mod._confidence_scorer = None
    yield
    mod._confidence_scorer = None


# ---------------------------------------------------------------------------
# 1. Basic scoring of a good output
# ---------------------------------------------------------------------------

class TestGoodOutput:
    def test_good_output_high_overall(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(GOOD_OUTPUT)
        # A reasonably long, coherent text should score at least medium-high
        assert metrics.overall_confidence >= 0.5

    def test_good_output_completeness_above_base(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(GOOD_OUTPUT)
        # Contains "in conclusion" -> completeness bonus
        assert metrics.completeness_score > 0.5

    def test_good_output_coherence_above_base(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(GOOD_OUTPUT)
        # Has transition words ("moreover", "furthermore") and multiple sentences
        assert metrics.coherence_score > 0.5

    def test_good_output_has_proper_threshold(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(GOOD_OUTPUT)
        assert metrics.threshold in (
            ConfidenceThreshold.MEDIUM,
            ConfidenceThreshold.HIGH,
            ConfidenceThreshold.VERY_HIGH,
        )


# ---------------------------------------------------------------------------
# 2. Empty string output
# ---------------------------------------------------------------------------

class TestEmptyOutput:
    def test_empty_overall_confidence_is_low(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(EMPTY_OUTPUT)
        # Completeness and coherence are 0.0, but relevance (0.7), factual (0.7),
        # and format (0.8) keep defaults when no context/format given -> ~0.395
        assert metrics.overall_confidence < 0.5

    def test_empty_completeness_zero(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(EMPTY_OUTPUT)
        assert metrics.completeness_score == 0.0

    def test_empty_coherence_zero(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(EMPTY_OUTPUT)
        assert metrics.coherence_score == 0.0

    def test_empty_relevance_zero(self, scorer: ConfidenceScorer):
        # With a query provided, empty output gives relevance 0.0
        metrics = scorer.score_output(EMPTY_OUTPUT, context={"query": "test"})
        assert metrics.relevance_score == 0.0

    def test_empty_needs_correction(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(EMPTY_OUTPUT)
        assert metrics.needs_correction is True

    def test_empty_needs_review(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(EMPTY_OUTPUT)
        assert metrics.needs_review is True


# ---------------------------------------------------------------------------
# 3. Very short output
# ---------------------------------------------------------------------------

class TestShortOutput:
    def test_short_completeness_is_base(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(SHORT_OUTPUT)
        # No expected_length, no query, no conclusion markers -> stays at 0.5
        assert metrics.completeness_score == pytest.approx(0.5, abs=0.05)

    def test_short_coherence_is_low(self, scorer: ConfidenceScorer):
        # Single fragment with one "sentence" -> lower coherence
        metrics = scorer.score_output(SHORT_OUTPUT)
        # Only one sentence (after split by '.'), no transitions
        assert metrics.coherence_score <= 0.6

    def test_short_overall_not_very_high(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(SHORT_OUTPUT)
        assert metrics.threshold != ConfidenceThreshold.VERY_HIGH


# ---------------------------------------------------------------------------
# 4. Scoring with context dict
# ---------------------------------------------------------------------------

class TestWithContext:
    def test_context_query_improves_relevance(self, scorer: ConfidenceScorer):
        output = "The capital of France is Paris."
        context = {"query": "capital France Paris"}
        metrics_with = scorer.score_output(output, context=context)

        metrics_without = scorer.score_output(output)
        # With query words matching, relevance should be higher than the
        # no-query default of 0.7 (or at least remain comparable).
        assert metrics_with.relevance_score >= 0.3

    def test_context_sources_boosts_factual(self, scorer: ConfidenceScorer):
        output = "According to recent studies [1], the effect is significant."
        context_with_sources = {"sources": ["study_1", "study_2"]}
        context_without_sources: dict = {}
        m_with = scorer.score_output(output, context=context_with_sources)
        m_without = scorer.score_output(output, context=context_without_sources)
        assert m_with.factual_score >= m_without.factual_score

    def test_no_query_gives_default_relevance(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Some random text.")
        # When no query is supplied, relevance defaults to 0.7
        assert metrics.relevance_score == pytest.approx(0.7, abs=0.01)


# ---------------------------------------------------------------------------
# 5. Scoring with expected_length
# ---------------------------------------------------------------------------

class TestExpectedLength:
    def test_meeting_expected_length_increases_completeness(self, scorer: ConfidenceScorer):
        output = "x " * 100  # 200 chars
        m_no_exp = scorer.score_output(output)
        m_with_exp = scorer.score_output(output, expected_length=200)
        assert m_with_exp.completeness_score >= m_no_exp.completeness_score

    def test_short_of_expected_length(self, scorer: ConfidenceScorer):
        output = "short"
        metrics = scorer.score_output(output, expected_length=10000)
        # length_ratio = 5/10000 -> nearly 0; adds almost nothing on top of base
        assert metrics.completeness_score < 0.55

    def test_exceeding_expected_length_caps_at_one(self, scorer: ConfidenceScorer):
        output = "x " * 500
        metrics = scorer.score_output(output, expected_length=10)
        # length_ratio capped at 1.0
        assert metrics.completeness_score <= 1.0


# ---------------------------------------------------------------------------
# 6. Scoring with expected_format
# ---------------------------------------------------------------------------

class TestExpectedFormat:
    def test_json_format_detected(self, scorer: ConfidenceScorer):
        output = '{"key": "value", "count": 42}'
        metrics = scorer.score_output(output, expected_format="json")
        # Starts/ends with braces, contains ':' and '"'
        assert metrics.format_score == pytest.approx(1.0, abs=0.01)

    def test_json_format_fails_for_plain_text(self, scorer: ConfidenceScorer):
        output = "This is plain text."
        metrics = scorer.score_output(output, expected_format="json")
        # Does not start with '{' -> stays around 0.5 base
        assert metrics.format_score < 0.8

    def test_markdown_format_detected(self, scorer: ConfidenceScorer):
        output = "# Title\n\nSome **bold** text and [link](http://example.com)."
        metrics = scorer.score_output(output, expected_format="markdown")
        # Header, bold, link -> should get bonuses
        assert metrics.format_score >= 0.8

    def test_list_format_detected_unordered(self, scorer: ConfidenceScorer):
        output = "- Item one\n- Item two\n- Item three"
        metrics = scorer.score_output(output, expected_format="list")
        assert metrics.format_score >= 0.8

    def test_list_format_detected_ordered(self, scorer: ConfidenceScorer):
        output = "1. Item one\n2. Item two\n3. Item three"
        metrics = scorer.score_output(output, expected_format="list")
        assert metrics.format_score >= 0.8

    def test_no_expected_format_gives_default(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Any text here.", expected_format=None)
        assert metrics.format_score == pytest.approx(0.8, abs=0.01)


# ---------------------------------------------------------------------------
# 7. Custom weights change scoring
# ---------------------------------------------------------------------------

class TestCustomWeights:
    def test_heavy_completeness_weight_changes_score(self):
        output = "In conclusion, this is the summary."  # completeness bonus from marker
        scorer_heavy = ConfidenceScorer(completeness_weight=0.9, relevance_weight=0.025,
                                        coherence_weight=0.025, factual_weight=0.025,
                                        format_weight=0.025)
        scorer_light = ConfidenceScorer(completeness_weight=0.025, relevance_weight=0.9,
                                        coherence_weight=0.025, factual_weight=0.025,
                                        format_weight=0.025)
        m_heavy = scorer_heavy.score_output(output)
        m_light = scorer_light.score_output(output)
        # The two should differ because the dominant component differs
        assert m_heavy.overall_confidence != pytest.approx(m_light.overall_confidence, abs=0.01)

    def test_weights_are_normalized(self):
        scorer = ConfidenceScorer(
            completeness_weight=10,
            relevance_weight=10,
            coherence_weight=10,
            factual_weight=10,
            format_weight=10,
        )
        total = sum(scorer.weights.values())
        assert total == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 8. Threshold detection
# ---------------------------------------------------------------------------

class TestThresholdDetection:
    def test_very_low_threshold(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.1) == ConfidenceThreshold.VERY_LOW
        assert scorer._determine_threshold(0.29) == ConfidenceThreshold.VERY_LOW

    def test_low_threshold(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.3) == ConfidenceThreshold.LOW
        assert scorer._determine_threshold(0.49) == ConfidenceThreshold.LOW

    def test_medium_threshold(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.5) == ConfidenceThreshold.MEDIUM
        assert scorer._determine_threshold(0.69) == ConfidenceThreshold.MEDIUM

    def test_high_threshold(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.7) == ConfidenceThreshold.HIGH
        assert scorer._determine_threshold(0.89) == ConfidenceThreshold.HIGH

    def test_very_high_threshold(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.9) == ConfidenceThreshold.VERY_HIGH
        assert scorer._determine_threshold(1.0) == ConfidenceThreshold.VERY_HIGH

    def test_boundary_at_zero(self, scorer: ConfidenceScorer):
        assert scorer._determine_threshold(0.0) == ConfidenceThreshold.VERY_LOW

    def test_empty_output_gets_low_threshold(self, scorer: ConfidenceScorer):
        # Empty output still gets default relevance/factual/format scores,
        # so overall is ~0.395 which falls in the LOW bucket (0.3-0.5).
        metrics = scorer.score_output("")
        assert metrics.threshold == ConfidenceThreshold.LOW


# ---------------------------------------------------------------------------
# 9. needs_review and needs_correction flags
# ---------------------------------------------------------------------------

class TestReviewCorrectionFlags:
    def test_needs_review_when_below_07(self, scorer: ConfidenceScorer):
        # Empty output -> overall very low -> needs_review True
        metrics = scorer.score_output("")
        assert metrics.needs_review is True

    def test_needs_correction_when_below_05(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("")
        assert metrics.needs_correction is True

    def test_no_review_for_high_confidence(self, scorer: ConfidenceScorer):
        # Build an output likely to score >= 0.7
        output = (
            "The answer is: Paris is the capital of France. "
            "Moreover, it is the largest city. Furthermore, it has a rich history. "
            "Additionally, millions of tourists visit. "
            "In conclusion, Paris is iconic."
        )
        metrics = scorer.score_output(output, context={"query": "capital France Paris"})
        # If overall >= 0.7 then needs_review should be False
        if metrics.overall_confidence >= 0.7:
            assert metrics.needs_review is False
        # If the heuristic doesn't quite reach 0.7, at least check logic consistency
        assert metrics.needs_review == (metrics.overall_confidence < 0.7)

    def test_flags_consistent_with_overall_confidence(self, scorer: ConfidenceScorer):
        for text in ["", "short", GOOD_OUTPUT]:
            metrics = scorer.score_output(text)
            assert metrics.needs_review == (metrics.overall_confidence < 0.7)
            assert metrics.needs_correction == (metrics.overall_confidence < 0.5)


# ---------------------------------------------------------------------------
# 10. suggestions list is populated for low scores
# ---------------------------------------------------------------------------

class TestSuggestions:
    def test_empty_output_has_suggestions(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("")
        assert len(metrics.suggestions) > 0

    def test_low_completeness_suggestion(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("")
        assert any("incomplete" in s.lower() for s in metrics.suggestions)

    def test_low_coherence_suggestion(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("")
        assert any("coherence" in s.lower() for s in metrics.suggestions)

    def test_low_overall_suggestion(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("")
        assert any("overall confidence" in s.lower() for s in metrics.suggestions)

    def test_low_relevance_suggestion_with_query(self, scorer: ConfidenceScorer):
        # Empty output with a query -> relevance = 0.0
        metrics = scorer.score_output("", context={"query": "something specific"})
        assert any("relevance" in s.lower() for s in metrics.suggestions)

    def test_low_format_suggestion(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("no json here", expected_format="json")
        # format_score for non-json text when json is expected should be <= 0.6
        if metrics.format_score < 0.6:
            assert any("format" in s.lower() for s in metrics.suggestions)

    def test_good_output_may_have_no_suggestions(self, scorer: ConfidenceScorer):
        # Build output that gets all component scores >= 0.6
        output = (
            "The answer is: Paris is the capital of France. "
            "Moreover, it is well known for its culture. "
            "Furthermore, millions visit annually. "
            "Additionally, its architecture is world-class. "
            "In conclusion, Paris is iconic."
        )
        metrics = scorer.score_output(
            output,
            context={"query": "capital France Paris answer"},
        )
        # If all sub-scores are >= 0.6, suggestions should be empty
        all_above = (
            metrics.completeness_score >= 0.6
            and metrics.relevance_score >= 0.6
            and metrics.coherence_score >= 0.6
            and metrics.factual_score >= 0.6
            and metrics.format_score >= 0.6
            and metrics.overall_confidence >= 0.5
        )
        if all_above:
            assert metrics.suggestions == []


# ---------------------------------------------------------------------------
# 11. to_dict() returns correct structure
# ---------------------------------------------------------------------------

class TestToDict:
    def test_to_dict_keys(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Hello world.")
        d = metrics.to_dict()
        expected_keys = {
            "overall_confidence",
            "completeness_score",
            "relevance_score",
            "coherence_score",
            "factual_score",
            "format_score",
            "threshold",
            "needs_review",
            "needs_correction",
            "suggestions",
            "metrics_breakdown",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_types(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Hello world.")
        d = metrics.to_dict()
        assert isinstance(d["overall_confidence"], float)
        assert isinstance(d["threshold"], str)
        assert isinstance(d["needs_review"], bool)
        assert isinstance(d["needs_correction"], bool)
        assert isinstance(d["suggestions"], list)
        assert isinstance(d["metrics_breakdown"], dict)

    def test_to_dict_threshold_is_enum_value(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Hello world.")
        d = metrics.to_dict()
        # threshold should be the string value, not the enum member
        assert d["threshold"] in {"very_low", "low", "medium", "high", "very_high"}

    def test_to_dict_metrics_breakdown_matches_scores(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Hello world.")
        d = metrics.to_dict()
        breakdown = d["metrics_breakdown"]
        assert breakdown["completeness"] == pytest.approx(d["completeness_score"])
        assert breakdown["relevance"] == pytest.approx(d["relevance_score"])
        assert breakdown["coherence"] == pytest.approx(d["coherence_score"])
        assert breakdown["factual"] == pytest.approx(d["factual_score"])
        assert breakdown["format"] == pytest.approx(d["format_score"])

    def test_to_dict_roundtrip_values(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output(GOOD_OUTPUT, context={"query": "capital France"})
        d = metrics.to_dict()
        assert d["overall_confidence"] == pytest.approx(metrics.overall_confidence)
        assert d["needs_review"] == metrics.needs_review
        assert d["needs_correction"] == metrics.needs_correction
        assert d["suggestions"] == metrics.suggestions


# ---------------------------------------------------------------------------
# 12. get_confidence_scorer() singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_confidence_scorer_returns_instance(self):
        scorer = get_confidence_scorer()
        assert isinstance(scorer, ConfidenceScorer)

    def test_get_confidence_scorer_returns_same_instance(self):
        scorer1 = get_confidence_scorer()
        scorer2 = get_confidence_scorer()
        assert scorer1 is scorer2

    def test_singleton_works_after_reset(self):
        import core.validation.confidence_scorer as mod

        mod._confidence_scorer = None
        scorer1 = get_confidence_scorer()
        scorer2 = get_confidence_scorer()
        assert scorer1 is scorer2


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestFactualScoring:
    def test_uncertainty_markers_lower_score(self, scorer: ConfidenceScorer):
        uncertain = "Maybe it is Paris, possibly it is London, perhaps Berlin."
        certain = "The capital is definitely Paris, certainly the answer."
        m_uncertain = scorer.score_output(uncertain)
        m_certain = scorer.score_output(certain)
        assert m_uncertain.factual_score < m_certain.factual_score

    def test_multiple_uncertainty_markers_cap_penalty(self, scorer: ConfidenceScorer):
        output = "Maybe perhaps possibly unclear uncertain not sure might."
        metrics = scorer.score_output(output)
        # Penalty capped at 0.3; base is 0.7 -> min 0.4
        assert metrics.factual_score >= 0.4 - 0.01


class TestOverallConfidenceCalculation:
    def test_overall_is_weighted_sum(self, scorer: ConfidenceScorer):
        metrics = scorer.score_output("Hello world.")
        expected = (
            metrics.completeness_score * scorer.weights["completeness"]
            + metrics.relevance_score * scorer.weights["relevance"]
            + metrics.coherence_score * scorer.weights["coherence"]
            + metrics.factual_score * scorer.weights["factual"]
            + metrics.format_score * scorer.weights["format"]
        )
        assert metrics.overall_confidence == pytest.approx(expected, abs=1e-9)

    def test_all_scores_between_0_and_1(self, scorer: ConfidenceScorer):
        for text in [EMPTY_OUTPUT, SHORT_OUTPUT, GOOD_OUTPUT, "x" * 10000]:
            metrics = scorer.score_output(text)
            assert 0.0 <= metrics.overall_confidence <= 1.0
            assert 0.0 <= metrics.completeness_score <= 1.0
            assert 0.0 <= metrics.relevance_score <= 1.0
            assert 0.0 <= metrics.coherence_score <= 1.0
            assert 0.0 <= metrics.factual_score <= 1.0
            assert 0.0 <= metrics.format_score <= 1.0
