"""EB-1A Evidence Analyzer Agent.

This module provides comprehensive evidence analysis for EB-1A petitions:
1. Individual evidence quality assessment (completeness, credibility, relevance, impact)
2. Criterion satisfaction evaluation (strength scoring, gap analysis)
3. Overall case strength calculation (approval probability, risk assessment)

The analyzer integrates with MemoryManager for evidence retrieval and uses
weighted scoring algorithms to provide actionable recommendations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..workflows.eb1a.eb1a_coordinator import EB1ACriterion, EB1AEvidence

logger = structlog.get_logger(__name__)


# =============================================================================
# LLM Prompts for Evidence Analysis (Immigration Lawyer Style)
# =============================================================================

LLM_CREDIBILITY_PROMPT = """You are an experienced EB-1A immigration attorney evaluating evidence credibility.

EVIDENCE TO EVALUATE:
Title: {title}
Description: {description}
Source: {source}
Criterion: {criterion}

Evaluate the SOURCE CREDIBILITY on a scale of 0-100:
- 90-100: International recognition (Nobel, IEEE Fellow, ACM Fellow, major international awards)
- 70-89: National recognition (NSF grants, federal appointments, national awards)
- 50-69: Regional/state recognition (state awards, regional conferences)
- 30-49: Local recognition (local awards, company recognition)
- 10-29: Unknown or minimal source credibility

Respond with ONLY a JSON object:
{{"score": <0-100>, "level": "<international|national|regional|local|unknown>", "reasoning": "<brief explanation>"}}"""

LLM_RELEVANCE_PROMPT = """You are an experienced EB-1A immigration attorney evaluating evidence relevance.

EVIDENCE TO EVALUATE:
Title: {title}
Description: {description}
Criterion: {criterion}

EB-1A CRITERION REQUIREMENTS FOR "{criterion}":
{criterion_requirements}

Evaluate how RELEVANT this evidence is to the claimed criterion on a scale of 0-100:
- 90-100: Exact match - directly satisfies the criterion requirement
- 70-89: Strong relevance - clearly supports the criterion
- 50-69: Moderate relevance - somewhat related
- 30-49: Partial relevance - tangentially related
- 0-29: Weak/no relevance - does not support this criterion

Respond with ONLY a JSON object:
{{"score": <0-100>, "level": "<exact_match|strong|moderate|partial|weak>", "reasoning": "<brief explanation>"}}"""

LLM_IMPACT_PROMPT = """You are an experienced EB-1A immigration attorney evaluating evidence impact.

EVIDENCE TO EVALUATE:
Title: {title}
Description: {description}
Metrics: {metrics}

Evaluate the MEASURABLE IMPACT on a scale of 0-100:
- 90-100: Exceptional impact (field-changing, widely adopted, transformed industry)
- 70-89: High impact (significant influence, recognized by peers, notable adoption)
- 50-69: Moderate impact (some measurable results, modest recognition)
- 30-49: Low impact (limited scope, minimal measurable outcomes)
- 0-29: No measurable impact

Respond with ONLY a JSON object:
{{"score": <0-100>, "level": "<exceptional|high|moderate|low|none>", "reasoning": "<brief explanation>"}}"""

LLM_FEEDBACK_PROMPT = """You are an experienced EB-1A immigration attorney providing actionable advice.

CASE ANALYSIS:
Overall Score: {overall_score}/100
Approval Probability: {approval_probability}%
Criteria Satisfied: {satisfied_count}/10
Risk Level: {risk_level}

WEAK AREAS:
{weak_areas}

As an experienced immigration lawyer, provide SPECIFIC, ACTIONABLE advice to strengthen this case.
Focus on:
1. What specific evidence can be gathered?
2. Where to find this evidence?
3. How to present it effectively?

Respond in a warm but professional tone, giving the applicant hope while being realistic.

Provide 3-5 specific recommendations:"""

# Criterion requirements for relevance assessment
CRITERION_REQUIREMENTS = {
    "awards": "Major nationally or internationally recognized prizes or awards for excellence in the field",
    "membership": "Membership in associations requiring outstanding achievements as judged by recognized experts",
    "press": "Published material in professional or major trade publications about the alien's work",
    "judging": "Participation as a judge of the work of others in the same or allied field",
    "original_contribution": "Original scientific, scholarly, or business-related contributions of major significance",
    "scholarly_articles": "Authorship of scholarly articles in professional journals or major media",
    "artistic_exhibitions": "Display of work at artistic exhibitions or showcases",
    "leading_role": "Performed in a leading or critical role for organizations with distinguished reputation",
    "high_salary": "Commanded a high salary or remuneration relative to others in the field",
    "commercial_success": "Commercial successes in the performing arts shown by box office receipts",
}


class SourceCredibility(str, Enum):
    """Credibility level of evidence source."""

    INTERNATIONAL = "international"  # Global recognition (score: 1.0)
    NATIONAL = "national"  # National level (score: 0.8)
    REGIONAL = "regional"  # Regional/state level (score: 0.5)
    LOCAL = "local"  # Local level (score: 0.3)
    UNKNOWN = "unknown"  # Unknown source (score: 0.1)


class RelevanceLevel(str, Enum):
    """Relevance of evidence to criterion."""

    EXACT_MATCH = "exact_match"  # Directly satisfies criterion (score: 1.0)
    STRONG = "strong"  # Strongly relevant (score: 0.8)
    MODERATE = "moderate"  # Moderately relevant (score: 0.6)
    PARTIAL = "partial"  # Partially relevant (score: 0.4)
    TANGENTIAL = "tangential"  # Tangentially related (score: 0.2)


class ImpactLevel(str, Enum):
    """Measured impact of evidence."""

    EXCEPTIONAL = "exceptional"  # Exceptional impact (score: 1.0)
    HIGH = "high"  # High impact (score: 0.8)
    MODERATE = "moderate"  # Moderate impact (score: 0.6)
    LOW = "low"  # Low impact (score: 0.4)
    MINIMAL = "minimal"  # Minimal impact (score: 0.2)
    NONE = "none"  # No measurable impact (score: 0.0)


class EvidenceQualityMetrics(BaseModel):
    """Quality metrics for individual evidence."""

    completeness: float = Field(ge=0.0, le=1.0, description="Documentation completeness")
    credibility: float = Field(ge=0.0, le=1.0, description="Source credibility score")
    relevance: float = Field(ge=0.0, le=1.0, description="Relevance to criterion")
    impact: float = Field(ge=0.0, le=1.0, description="Measurable impact")
    strength_score: float = Field(ge=0.0, le=1.0, description="Overall strength (weighted)")


class EvidenceAnalysisResult(BaseModel):
    """Result of analyzing individual evidence."""

    evidence_id: str
    criterion: EB1ACriterion
    quality_metrics: EvidenceQualityMetrics
    source_credibility: SourceCredibility
    relevance_level: RelevanceLevel
    impact_level: ImpactLevel

    # Gap analysis
    missing_elements: list[str] = Field(
        default_factory=list, description="Missing documentation or details"
    )
    recommendations: list[str] = Field(default_factory=list, description="Improvement suggestions")

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class CriterionEvaluation(BaseModel):
    """Evaluation of how well a criterion is satisfied."""

    criterion: EB1ACriterion
    is_satisfied: bool = Field(description="Whether criterion meets threshold")
    strength_score: float = Field(
        ge=0.0, le=100.0, description="Overall criterion strength (0-100)"
    )
    confidence_level: float = Field(ge=0.0, le=1.0, description="Confidence in evaluation")

    # Evidence analysis
    total_evidence_count: int = Field(ge=0, description="Total evidence items")
    strong_evidence_count: int = Field(ge=0, description="Strong evidence items (score > 0.6)")
    evidence_analyses: list[EvidenceAnalysisResult] = Field(default_factory=list)

    # Gap analysis
    missing_elements: list[str] = Field(
        default_factory=list, description="Key missing elements for criterion"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations to strengthen criterion"
    )

    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"  # Strong case, high approval probability
    MODERATE = "moderate"  # Decent case, moderate approval probability
    HIGH = "high"  # Weak case, low approval probability
    CRITICAL = "critical"  # Very weak case, likely denial


class CaseStrengthAnalysis(BaseModel):
    """Comprehensive case strength analysis."""

    # Overall metrics
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall case score (0-100)")
    approval_probability: float = Field(
        ge=0.0, le=1.0, description="Estimated approval probability"
    )
    risk_level: RiskLevel

    # Criteria analysis
    satisfied_criteria_count: int = Field(ge=0, description="Number of satisfied criteria")
    criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation] = Field(default_factory=dict)

    # Minimum requirement check
    meets_minimum_criteria: bool = Field(description="Meets minimum 3 criteria requirement")

    # Strengths and weaknesses
    strengths: list[str] = Field(default_factory=list, description="Case strengths")
    risks: list[str] = Field(default_factory=list, description="Identified risks")

    # Recommendations (prioritized)
    priority_recommendations: list[str] = Field(
        default_factory=list, description="High-priority actions"
    )
    secondary_recommendations: list[str] = Field(
        default_factory=list, description="Secondary improvements"
    )

    # Timeline estimate
    estimated_days_to_ready: int | None = Field(
        default=None, description="Estimated days to filing readiness"
    )

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class EB1AEvidenceAnalyzer:
    """
    Agent for comprehensive EB-1A evidence analysis.

    Provides three levels of analysis:
    1. Individual evidence quality assessment
    2. Criterion-level satisfaction evaluation
    3. Overall case strength calculation

    Example:
        >>> analyzer = EB1AEvidenceAnalyzer(memory_manager=memory)
        >>> evidence = EB1AEvidence(
        ...     criterion=EB1ACriterion.AWARDS,
        ...     evidence_type=EvidenceType.AWARD_CERTIFICATE,
        ...     title="Nobel Prize in Physics",
        ...     description="Awarded for groundbreaking research..."
        ... )
        >>> result = await analyzer.analyze_evidence(evidence)
        >>> print(f"Strength: {result.quality_metrics.strength_score:.2f}")
        Strength: 0.95
    """

    # Scoring thresholds
    STRONG_EVIDENCE_THRESHOLD = 0.6  # Evidence with score > 0.6 is "strong"
    CRITERION_SATISFIED_THRESHOLD = 70.0  # Criterion score >= 70 is "satisfied"
    MINIMUM_STRONG_EVIDENCE = 2  # Minimum 2 strong evidence items per criterion

    # Weights for strength score calculation
    WEIGHTS = {
        "completeness": 0.20,
        "credibility": 0.30,
        "relevance": 0.30,
        "impact": 0.20,
    }

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        use_llm: bool = True,
        llm_client: Any | None = None,
    ):
        """
        Initialize EB-1A Evidence Analyzer with LLM support.

        Args:
            memory_manager: Memory manager for evidence retrieval and storage
            use_llm: If True, use LLM for semantic analysis; if False, use heuristics only
            llm_client: Optional pre-configured LLM client (OpenAIClient)
        """
        self.memory = memory_manager or MemoryManager()
        self.logger = logger.bind(agent="eb1a_evidence_analyzer")
        self.use_llm = use_llm
        self._llm_client = llm_client

    async def _get_llm_client(self) -> Any:
        """Lazy initialization of LLM client."""
        if self._llm_client is None and self.use_llm:
            try:
                from ..llm_interface.openai_client import OpenAIClient

                self._llm_client = OpenAIClient(
                    model="gpt-5.1",
                    reasoning_effort="low",  # Fast responses for evidence analysis
                    max_tokens=500,
                )
                self.logger.info("llm_client.initialized", model="gpt-5.1")
            except Exception as e:
                self.logger.warning("llm_client.init_failed", error=str(e))
                self.use_llm = False
        return self._llm_client

    async def _llm_assess_credibility(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[SourceCredibility, float]:
        """Assess source credibility using LLM."""
        try:
            llm = await self._get_llm_client()
            if not llm:
                return self._assess_credibility_heuristic(evidence, context)

            prompt = LLM_CREDIBILITY_PROMPT.format(
                title=evidence.title or "N/A",
                description=(evidence.description or "")[:500],
                source=evidence.source or "Unknown",
                criterion=evidence.criterion.value,
            )

            result = await llm.acomplete(prompt)
            output = result.get("output", "")

            # Parse JSON response
            import json

            try:
                data = json.loads(output)
                score = data.get("score", 50) / 100.0
                level = data.get("level", "unknown")
                reasoning = data.get("reasoning", "")

                self.logger.debug(
                    "llm.credibility.assessed",
                    score=score,
                    level=level,
                    reasoning=reasoning[:100],
                )

                level_map = {
                    "international": SourceCredibility.INTERNATIONAL,
                    "national": SourceCredibility.NATIONAL,
                    "regional": SourceCredibility.REGIONAL,
                    "local": SourceCredibility.LOCAL,
                    "unknown": SourceCredibility.UNKNOWN,
                }
                return level_map.get(level, SourceCredibility.UNKNOWN), score
            except json.JSONDecodeError:
                self.logger.warning("llm.credibility.parse_failed", output=output[:100])
                return self._assess_credibility_heuristic(evidence, context)

        except Exception as e:
            self.logger.warning("llm.credibility.error", error=str(e))
            return self._assess_credibility_heuristic(evidence, context)

    async def _llm_assess_relevance(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[RelevanceLevel, float]:
        """Assess relevance using LLM."""
        try:
            llm = await self._get_llm_client()
            if not llm:
                return self._assess_relevance_heuristic(evidence, context)

            criterion_key = evidence.criterion.value.split("_", 1)[-1].lower()
            criterion_req = CRITERION_REQUIREMENTS.get(criterion_key, "N/A")

            prompt = LLM_RELEVANCE_PROMPT.format(
                title=evidence.title or "N/A",
                description=(evidence.description or "")[:500],
                criterion=evidence.criterion.value,
                criterion_requirements=criterion_req,
            )

            result = await llm.acomplete(prompt)
            output = result.get("output", "")

            import json

            try:
                data = json.loads(output)
                score = data.get("score", 50) / 100.0
                level = data.get("level", "moderate")

                level_map = {
                    "exact_match": RelevanceLevel.EXACT_MATCH,
                    "strong": RelevanceLevel.STRONG,
                    "moderate": RelevanceLevel.MODERATE,
                    "partial": RelevanceLevel.PARTIAL,
                    "weak": RelevanceLevel.TANGENTIAL,
                }
                return level_map.get(level, RelevanceLevel.MODERATE), score
            except json.JSONDecodeError:
                return self._assess_relevance_heuristic(evidence, context)

        except Exception as e:
            self.logger.warning("llm.relevance.error", error=str(e))
            return self._assess_relevance_heuristic(evidence, context)

    async def _llm_assess_impact(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[ImpactLevel, float]:
        """Assess impact using LLM."""
        try:
            llm = await self._get_llm_client()
            if not llm:
                return self._assess_impact_heuristic(evidence, context)

            metadata = evidence.metadata or {}
            metrics_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() if v)
            if not metrics_str:
                metrics_str = "No specific metrics provided"

            prompt = LLM_IMPACT_PROMPT.format(
                title=evidence.title or "N/A",
                description=(evidence.description or "")[:500],
                metrics=metrics_str,
            )

            result = await llm.acomplete(prompt)
            output = result.get("output", "")

            import json

            try:
                data = json.loads(output)
                score = data.get("score", 40) / 100.0
                level = data.get("level", "moderate")

                level_map = {
                    "exceptional": ImpactLevel.EXCEPTIONAL,
                    "high": ImpactLevel.HIGH,
                    "moderate": ImpactLevel.MODERATE,
                    "low": ImpactLevel.LOW,
                    "none": ImpactLevel.NONE,
                }
                return level_map.get(level, ImpactLevel.MODERATE), score
            except json.JSONDecodeError:
                return self._assess_impact_heuristic(evidence, context)

        except Exception as e:
            self.logger.warning("llm.impact.error", error=str(e))
            return self._assess_impact_heuristic(evidence, context)

    async def generate_feedback(self, analysis: CaseStrengthAnalysis) -> str:
        """
        Generate actionable feedback for weak cases using LLM.

        This implements the Feedback Loop from TAST.txt:
        - If Risk: HIGH, suggest improvements automatically
        - Provide specific advice on what evidence to gather and where

        Args:
            analysis: The CaseStrengthAnalysis result

        Returns:
            Human-readable feedback with specific recommendations
        """
        if not self.use_llm:
            return self._generate_feedback_heuristic(analysis)

        try:
            llm = await self._get_llm_client()
            if not llm:
                return self._generate_feedback_heuristic(analysis)

            # Collect weak areas
            weak_areas = []
            for crit, evaluation in analysis.criterion_evaluations.items():
                if not evaluation.is_satisfied:
                    weak_areas.append(
                        f"- {crit.value}: Score {evaluation.strength_score:.0f}/100 "
                        f"(needs {self.CRITERION_SATISFIED_THRESHOLD}+)"
                    )
                    if evaluation.missing_elements:
                        weak_areas.append(
                            f"  Missing: {', '.join(evaluation.missing_elements[:2])}"
                        )

            if analysis.risks:
                weak_areas.append("\nRisks:")
                weak_areas.extend([f"- {r}" for r in analysis.risks[:3]])

            prompt = LLM_FEEDBACK_PROMPT.format(
                overall_score=analysis.overall_score,
                approval_probability=analysis.approval_probability * 100,
                satisfied_count=analysis.satisfied_criteria_count,
                risk_level=analysis.risk_level.value.upper(),
                weak_areas=(
                    "\n".join(weak_areas) if weak_areas else "No major weaknesses identified"
                ),
            )

            result = await llm.acomplete(prompt, max_tokens=800)
            return result.get("output", self._generate_feedback_heuristic(analysis))

        except Exception as e:
            self.logger.warning("llm.feedback.error", error=str(e))
            return self._generate_feedback_heuristic(analysis)

    def _generate_feedback_heuristic(self, analysis: CaseStrengthAnalysis) -> str:
        """Generate feedback using heuristics (fallback)."""
        lines = [
            "📊 Case Analysis Summary",
            "",
            f"Overall Score: {analysis.overall_score:.0f}/100",
            f"Approval Probability: {analysis.approval_probability:.0%}",
            f"Risk Level: {analysis.risk_level.value.upper()}",
            "",
        ]

        if not analysis.meets_minimum_criteria:
            lines.append("⚠️ CRITICAL: You need at least 3 criteria satisfied.")
            lines.append(f"Currently: {analysis.satisfied_criteria_count} criteria met.")
            lines.append("")

        if analysis.priority_recommendations:
            lines.append("📝 Priority Actions:")
            for rec in analysis.priority_recommendations[:3]:
                lines.append(f"  • {rec}")

        return "\n".join(lines)

    async def analyze_evidence(
        self,
        evidence: EB1AEvidence,
        context: dict[str, Any] | None = None,
    ) -> EvidenceAnalysisResult:
        """
        Analyze individual evidence for quality, credibility, and impact.

        Evaluates:
        - Completeness: Are all necessary fields documented?
        - Credibility: How credible is the source?
        - Relevance: How relevant to the claimed criterion?
        - Impact: What measurable impact does it show?

        Args:
            evidence: Evidence to analyze
            context: Additional context for analysis (field standards, peer data, etc.)

        Returns:
            Detailed evidence analysis with quality metrics and recommendations
        """
        self.logger.info(
            "analyzing_evidence",
            evidence_id=evidence.evidence_id,
            criterion=evidence.criterion.value,
        )

        context = context or {}

        # 1. Assess completeness (0-1) - always use heuristic (fast)
        completeness = self._assess_completeness(evidence)

        # 2. Assess source credibility (0-1) - use LLM if enabled
        if self.use_llm:
            credibility_enum, credibility = await self._llm_assess_credibility(evidence, context)
        else:
            credibility_enum, credibility = self._assess_credibility_heuristic(evidence, context)

        # 3. Assess relevance to criterion (0-1) - use LLM if enabled
        if self.use_llm:
            relevance_enum, relevance = await self._llm_assess_relevance(evidence, context)
        else:
            relevance_enum, relevance = self._assess_relevance_heuristic(evidence, context)

        # 4. Assess measurable impact (0-1) - use LLM if enabled
        if self.use_llm:
            impact_enum, impact = await self._llm_assess_impact(evidence, context)
        else:
            impact_enum, impact = self._assess_impact_heuristic(evidence, context)

        # 5. Calculate weighted strength score
        strength_score = (
            completeness * self.WEIGHTS["completeness"]
            + credibility * self.WEIGHTS["credibility"]
            + relevance * self.WEIGHTS["relevance"]
            + impact * self.WEIGHTS["impact"]
        )

        # 6. Identify gaps and missing elements
        missing_elements = self._identify_gaps(
            evidence, completeness, credibility, relevance, impact
        )

        # 7. Generate recommendations
        recommendations = self._generate_evidence_recommendations(
            evidence, strength_score, missing_elements
        )

        quality_metrics = EvidenceQualityMetrics(
            completeness=completeness,
            credibility=credibility,
            relevance=relevance,
            impact=impact,
            strength_score=strength_score,
        )

        return EvidenceAnalysisResult(
            evidence_id=evidence.evidence_id,
            criterion=evidence.criterion,
            quality_metrics=quality_metrics,
            source_credibility=credibility_enum,
            relevance_level=relevance_enum,
            impact_level=impact_enum,
            missing_elements=missing_elements,
            recommendations=recommendations,
        )

    async def evaluate_criterion_satisfaction(
        self,
        criterion: EB1ACriterion,
        evidence_list: list[EB1AEvidence],
        context: dict[str, Any] | None = None,
    ) -> CriterionEvaluation:
        """
        Evaluate whether a criterion is satisfied based on evidence.

        Criterion is satisfied if:
        - At least 2 strong evidence items (score > 0.6)
        - Overall criterion strength >= 70/100
        - Confidence level >= 0.6

        Args:
            criterion: The EB-1A criterion to evaluate
            evidence_list: All evidence supporting this criterion
            context: Additional context for evaluation

        Returns:
            Comprehensive criterion evaluation with satisfaction determination
        """
        self.logger.info(
            "evaluating_criterion",
            criterion=criterion.value,
            evidence_count=len(evidence_list),
        )

        context = context or {}

        # Analyze each piece of evidence
        evidence_analyses: list[EvidenceAnalysisResult] = []
        for evidence in evidence_list:
            analysis = await self.analyze_evidence(evidence, context)
            evidence_analyses.append(analysis)

        # Count strong evidence
        strong_evidence = [
            a
            for a in evidence_analyses
            if a.quality_metrics.strength_score > self.STRONG_EVIDENCE_THRESHOLD
        ]
        strong_count = len(strong_evidence)

        # Calculate overall criterion strength (0-100)
        if evidence_analyses:
            avg_strength = sum(a.quality_metrics.strength_score for a in evidence_analyses) / len(
                evidence_analyses
            )
            strength_score = avg_strength * 100

            # Bonus for having multiple strong evidence items
            if strong_count >= self.MINIMUM_STRONG_EVIDENCE:
                strength_score = min(100.0, strength_score + 10.0)
        else:
            strength_score = 0.0

        # Calculate confidence level based on evidence quality and quantity
        confidence_level = self._calculate_confidence(evidence_analyses, strong_count)

        # Determine if criterion is satisfied
        is_satisfied = (
            strong_count >= self.MINIMUM_STRONG_EVIDENCE
            and strength_score >= self.CRITERION_SATISFIED_THRESHOLD
            and confidence_level >= 0.6
        )

        # Identify missing elements for this criterion
        missing_elements = self._identify_criterion_gaps(criterion, evidence_analyses)

        # Generate recommendations to strengthen criterion
        recommendations = self._generate_criterion_recommendations(
            criterion, is_satisfied, strength_score, evidence_analyses, missing_elements
        )

        return CriterionEvaluation(
            criterion=criterion,
            is_satisfied=is_satisfied,
            strength_score=strength_score,
            confidence_level=confidence_level,
            total_evidence_count=len(evidence_list),
            strong_evidence_count=strong_count,
            evidence_analyses=evidence_analyses,
            missing_elements=missing_elements,
            recommendations=recommendations,
        )

    async def calculate_case_strength(
        self,
        evidence_by_criterion: dict[EB1ACriterion, list[EB1AEvidence]],
        context: dict[str, Any] | None = None,
    ) -> CaseStrengthAnalysis:
        """
        Calculate comprehensive case strength analysis.

        Analyzes entire petition to determine:
        - Overall score (0-100)
        - Approval probability (0-1)
        - Risk level (low/moderate/high/critical)
        - Strengths and risks
        - Prioritized recommendations
        - Estimated time to readiness

        EB-1A requirements:
        - Minimum 3 of 10 criteria must be satisfied
        - Each criterion needs strong evidence
        - Overall case strength should be high

        Args:
            evidence_by_criterion: Dictionary mapping criteria to evidence lists
            context: Additional context (field standards, case precedents, etc.)

        Returns:
            Comprehensive case strength analysis with actionable recommendations
        """
        self.logger.info(
            "calculating_case_strength",
            criteria_count=len(evidence_by_criterion),
        )

        context = context or {}

        # Evaluate each criterion
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation] = {}
        for criterion, evidence_list in evidence_by_criterion.items():
            evaluation = await self.evaluate_criterion_satisfaction(
                criterion, evidence_list, context
            )
            criterion_evaluations[criterion] = evaluation

        # Count satisfied criteria
        satisfied_criteria = [
            crit for crit, eval in criterion_evaluations.items() if eval.is_satisfied
        ]
        satisfied_count = len(satisfied_criteria)

        # Check minimum 3 criteria requirement
        meets_minimum = satisfied_count >= 3

        # Calculate overall score (0-100)
        if criterion_evaluations:
            # Weighted average of criterion scores
            criterion_scores = [eval.strength_score for eval in criterion_evaluations.values()]
            base_score = sum(criterion_scores) / len(criterion_scores)

            # Bonus for exceeding minimum criteria
            if satisfied_count > 3:
                criteria_bonus = min(15.0, (satisfied_count - 3) * 5.0)
                overall_score = min(100.0, base_score + criteria_bonus)
            else:
                overall_score = base_score

            # Penalty if below minimum
            if not meets_minimum:
                overall_score = min(overall_score, 50.0)
        else:
            overall_score = 0.0

        # Calculate approval probability (0-1)
        approval_probability = self._calculate_approval_probability(
            overall_score, satisfied_count, criterion_evaluations
        )

        # Determine risk level
        risk_level = self._determine_risk_level(approval_probability, satisfied_count)

        # Identify strengths
        strengths = self._identify_case_strengths(criterion_evaluations, satisfied_count)

        # Identify risks
        risks = self._identify_case_risks(
            criterion_evaluations, satisfied_count, meets_minimum, overall_score
        )

        # Generate prioritized recommendations
        priority_recommendations, secondary_recommendations = self._generate_case_recommendations(
            criterion_evaluations, meets_minimum, risks
        )

        # Estimate time to readiness
        estimated_days = self._estimate_time_to_ready(
            overall_score, satisfied_count, risks, criterion_evaluations
        )

        return CaseStrengthAnalysis(
            overall_score=overall_score,
            approval_probability=approval_probability,
            risk_level=risk_level,
            satisfied_criteria_count=satisfied_count,
            criterion_evaluations=criterion_evaluations,
            meets_minimum_criteria=meets_minimum,
            strengths=strengths,
            risks=risks,
            priority_recommendations=priority_recommendations,
            secondary_recommendations=secondary_recommendations,
            estimated_days_to_ready=estimated_days,
        )

    # ========== Private Helper Methods ==========

    def _assess_completeness(self, evidence: EB1AEvidence) -> float:
        """Assess documentation completeness (0-1)."""
        score = 0.0
        total_fields = 8  # Total important fields

        # Required fields
        if evidence.title:
            score += 1.0
        if evidence.description and len(evidence.description) >= 50:
            score += 2.0  # Description is important, weight more
        elif evidence.description:
            score += 1.0

        # Supplementary fields
        if evidence.date:
            score += 1.0
        if evidence.source:
            score += 1.0
        if evidence.exhibit_number:
            score += 1.0
        if evidence.file_path:
            score += 1.0
        if evidence.metadata:
            score += 1.0

        return min(1.0, score / total_fields)

    def _assess_credibility_heuristic(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[SourceCredibility, float]:
        """Assess source credibility using heuristics (0-1)."""
        source = (evidence.source or "").lower()
        metadata = evidence.metadata or {}

        # Check for international indicators
        international_keywords = ["international", "global", "world", "nobel", "ieee", "acm"]
        if any(kw in source for kw in international_keywords):
            return SourceCredibility.INTERNATIONAL, 1.0

        # Check for national indicators
        national_keywords = ["national", "federal", "usa", "united states", "nsf", "nih"]
        if any(kw in source for kw in national_keywords):
            return SourceCredibility.NATIONAL, 0.8

        # Check for regional indicators
        regional_keywords = ["regional", "state", "province"]
        if any(kw in source for kw in regional_keywords):
            return SourceCredibility.REGIONAL, 0.5

        # Check for local indicators
        local_keywords = ["local", "city", "town", "county"]
        if any(kw in source for kw in local_keywords):
            return SourceCredibility.LOCAL, 0.3

        # Check metadata for credibility hints
        if metadata.get("verified"):
            return SourceCredibility.NATIONAL, 0.8

        # Default to unknown
        return SourceCredibility.UNKNOWN, 0.1

    def _assess_relevance_heuristic(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[RelevanceLevel, float]:
        """Assess relevance to criterion using heuristics (0-1)."""
        # Map evidence type to criterion for relevance scoring
        criterion = evidence.criterion
        evidence_type = evidence.evidence_type

        # Define strong matches
        strong_matches = {
            EB1ACriterion.AWARDS: ["award_certificate"],
            EB1ACriterion.MEMBERSHIP: ["membership_letter"],
            EB1ACriterion.PRESS: ["press_article"],
            EB1ACriterion.JUDGING: ["recommendation_letter"],
            EB1ACriterion.SCHOLARLY_ARTICLES: ["publication", "citation_report"],
            EB1ACriterion.ORIGINAL_CONTRIBUTION: ["patent", "publication"],
            EB1ACriterion.HIGH_SALARY: ["employment_letter", "salary_evidence"],
        }

        # Check for exact match
        if evidence_type.value in strong_matches.get(criterion, []):
            return RelevanceLevel.EXACT_MATCH, 1.0

        # Check description for relevance keywords
        description = (evidence.description or "").lower()
        title = (evidence.title or "").lower()
        combined_text = f"{title} {description}"

        # Criterion-specific keyword matching
        if criterion == EB1ACriterion.AWARDS:
            if any(kw in combined_text for kw in ["award", "prize", "honor", "recognition"]):
                return RelevanceLevel.STRONG, 0.8
        elif criterion == EB1ACriterion.PRESS:
            if any(
                kw in combined_text for kw in ["article", "press", "media", "publication about"]
            ):
                return RelevanceLevel.STRONG, 0.8
        elif criterion == EB1ACriterion.SCHOLARLY_ARTICLES:
            if any(kw in combined_text for kw in ["published", "journal", "conference", "paper"]):
                return RelevanceLevel.STRONG, 0.8

        # Default to moderate
        return RelevanceLevel.MODERATE, 0.6

    def _assess_impact_heuristic(
        self, evidence: EB1AEvidence, context: dict[str, Any]
    ) -> tuple[ImpactLevel, float]:
        """Assess measurable impact using heuristics (0-1)."""
        metadata = evidence.metadata or {}
        description = (evidence.description or "").lower()

        # Check for quantifiable metrics in metadata
        citations = metadata.get("citations", 0)
        attendees = metadata.get("attendees", 0)
        reach = metadata.get("reach", 0)
        downloads = metadata.get("downloads", 0)

        # High impact indicators
        if citations >= 1000 or reach >= 1000000:
            return ImpactLevel.EXCEPTIONAL, 1.0

        if citations >= 100 or attendees >= 10000 or reach >= 100000:
            return ImpactLevel.HIGH, 0.8

        if citations >= 10 or attendees >= 1000 or downloads >= 1000:
            return ImpactLevel.MODERATE, 0.6

        # Check description for impact keywords
        high_impact_keywords = [
            "transformed",
            "revolutionary",
            "breakthrough",
            "widely adopted",
            "industry standard",
        ]
        moderate_impact_keywords = [
            "significant",
            "influential",
            "adopted by",
            "recognized by",
            "cited",
        ]

        if any(kw in description for kw in high_impact_keywords):
            return ImpactLevel.HIGH, 0.8

        if any(kw in description for kw in moderate_impact_keywords):
            return ImpactLevel.MODERATE, 0.6

        # Default to low if some evidence exists
        if evidence.description:
            return ImpactLevel.LOW, 0.4

        return ImpactLevel.NONE, 0.0

    def _identify_gaps(
        self,
        evidence: EB1AEvidence,
        completeness: float,
        credibility: float,
        relevance: float,
        impact: float,
    ) -> list[str]:
        """Identify missing elements in evidence."""
        gaps = []

        if completeness < 0.7:
            if not evidence.date:
                gaps.append("Missing date of evidence")
            if not evidence.source:
                gaps.append("Missing source/origin documentation")
            if not evidence.file_path:
                gaps.append("Missing supporting document file")
            if not evidence.description or len(evidence.description) < 50:
                gaps.append("Insufficient description (needs detailed context)")

        if credibility < 0.5:
            gaps.append(
                "Source credibility not established (need verification from recognized entity)"
            )

        if relevance < 0.6:
            gaps.append(
                f"Weak relevance to {evidence.criterion.value} criterion (need more direct evidence)"
            )

        if impact < 0.4:
            gaps.append("No measurable impact metrics (citations, reach, adoption, etc.)")

        return gaps

    def _generate_evidence_recommendations(
        self,
        evidence: EB1AEvidence,
        strength_score: float,
        missing_elements: list[str],
    ) -> list[str]:
        """Generate recommendations for improving evidence."""
        recommendations = []

        if strength_score < 0.6:
            recommendations.append(
                f"CRITICAL: Evidence strength ({strength_score:.2f}) below threshold (0.6). "
                "Consider replacing with stronger evidence or supplementing significantly."
            )
        elif strength_score < 0.8:
            recommendations.append(
                f"Evidence strength ({strength_score:.2f}) is moderate. "
                "Strengthen with additional documentation."
            )

        # Add specific recommendations based on gaps
        for gap in missing_elements[:3]:  # Top 3 gaps
            if "description" in gap.lower():
                recommendations.append(
                    "Expand description with specific details: dates, scope, significance, and outcomes"
                )
            elif "measurable impact" in gap.lower():
                recommendations.append(
                    "Add quantifiable metrics: citations, users, revenue, awards, or adoption statistics"
                )
            elif "source credibility" in gap.lower():
                recommendations.append(
                    "Obtain verification letter from recognized authority or organization"
                )
            elif "file" in gap.lower():
                recommendations.append(
                    "Attach supporting documentation (certificate, letter, publication)"
                )

        return recommendations

    def _calculate_confidence(
        self, evidence_analyses: list[EvidenceAnalysisResult], strong_count: int
    ) -> float:
        """Calculate confidence level in criterion evaluation."""
        if not evidence_analyses:
            return 0.0

        # Base confidence from average evidence strength
        avg_strength = sum(a.quality_metrics.strength_score for a in evidence_analyses) / len(
            evidence_analyses
        )

        # Boost for having multiple strong evidence
        quantity_factor = min(1.0, strong_count / 3.0)  # Optimal: 3+ strong evidence

        # Combined confidence (70% quality, 30% quantity)
        confidence = (avg_strength * 0.7) + (quantity_factor * 0.3)

        return min(1.0, confidence)

    def _identify_criterion_gaps(
        self, criterion: EB1ACriterion, evidence_analyses: list[EvidenceAnalysisResult]
    ) -> list[str]:
        """Identify missing elements for specific criterion."""
        gaps = []

        # Criterion-specific requirements
        if criterion == EB1ACriterion.AWARDS:
            has_international = any(
                a.source_credibility == SourceCredibility.INTERNATIONAL for a in evidence_analyses
            )
            if not has_international:
                gaps.append("No international or nationally recognized awards")

        elif criterion == EB1ACriterion.SCHOLARLY_ARTICLES:
            high_impact = [
                a
                for a in evidence_analyses
                if a.impact_level in [ImpactLevel.HIGH, ImpactLevel.EXCEPTIONAL]
            ]
            if len(high_impact) < 2:
                gaps.append("Need evidence of high citation impact or influence")

        elif criterion == EB1ACriterion.PRESS:
            major_media = [
                a
                for a in evidence_analyses
                if a.source_credibility
                in [SourceCredibility.INTERNATIONAL, SourceCredibility.NATIONAL]
            ]
            if not major_media:
                gaps.append("Need coverage from major professional publications or media")

        elif criterion == EB1ACriterion.ORIGINAL_CONTRIBUTION:
            impact_evidence = [a for a in evidence_analyses if a.impact_level != ImpactLevel.NONE]
            if len(impact_evidence) < 2:
                gaps.append("Need evidence of major significance and field impact")

        # General gaps
        weak_evidence = [a for a in evidence_analyses if a.quality_metrics.strength_score < 0.5]
        if len(weak_evidence) > len(evidence_analyses) / 2:
            gaps.append("Majority of evidence is weak - need stronger documentation")

        return gaps

    def _generate_criterion_recommendations(
        self,
        criterion: EB1ACriterion,
        is_satisfied: bool,
        strength_score: float,
        evidence_analyses: list[EvidenceAnalysisResult],
        missing_elements: list[str],
    ) -> list[str]:
        """Generate recommendations to strengthen criterion."""
        recommendations = []

        if not is_satisfied:
            recommendations.append(
                f"CRITICAL: Criterion not satisfied (score: {strength_score:.1f}/100, threshold: 70). "
                "Consider focusing on stronger criteria or gathering additional evidence."
            )

        # Add evidence quantity recommendations
        strong_count = len([a for a in evidence_analyses if a.quality_metrics.strength_score > 0.6])
        if strong_count < self.MINIMUM_STRONG_EVIDENCE:
            needed = self.MINIMUM_STRONG_EVIDENCE - strong_count
            recommendations.append(
                f"Add {needed} more strong evidence item(s) to meet minimum requirement"
            )

        # Add quality recommendations
        if strength_score < 80 and is_satisfied:
            recommendations.append(
                "Strengthen evidence quality to increase approval probability (target: 80+)"
            )

        # Add gap-specific recommendations
        for gap in missing_elements[:2]:  # Top 2 gaps
            recommendations.append(f"Address gap: {gap}")

        return recommendations

    def _calculate_approval_probability(
        self,
        overall_score: float,
        satisfied_count: int,
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation],
    ) -> float:
        """Calculate estimated approval probability (0-1)."""
        # Base probability from overall score
        base_prob = overall_score / 100.0

        # Adjust for criteria count
        if satisfied_count < 3:
            criteria_factor = 0.3  # Very low if below minimum
        elif satisfied_count == 3:
            criteria_factor = 0.8  # Decent if at minimum
        elif satisfied_count == 4:
            criteria_factor = 1.0  # Good with 4 criteria
        else:
            criteria_factor = 1.0 + (satisfied_count - 4) * 0.05  # Bonus for 5+

        # Adjust for confidence levels
        if criterion_evaluations:
            avg_confidence = sum(e.confidence_level for e in criterion_evaluations.values()) / len(
                criterion_evaluations
            )
            confidence_factor = avg_confidence
        else:
            confidence_factor = 0.5

        # Combined probability (50% score, 30% criteria, 20% confidence)
        probability = (base_prob * 0.5) + (criteria_factor * 0.3) + (confidence_factor * 0.2)

        return min(1.0, max(0.0, probability))

    def _determine_risk_level(self, approval_probability: float, satisfied_count: int) -> RiskLevel:
        """Determine risk level based on approval probability."""
        if satisfied_count < 3:
            return RiskLevel.CRITICAL

        if approval_probability >= 0.75:
            return RiskLevel.LOW
        if approval_probability >= 0.55:
            return RiskLevel.MODERATE
        if approval_probability >= 0.35:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def _identify_case_strengths(
        self,
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation],
        satisfied_count: int,
    ) -> list[str]:
        """Identify case strengths."""
        strengths = []

        if satisfied_count >= 4:
            strengths.append(
                f"Exceeds minimum criteria requirement ({satisfied_count} criteria satisfied)"
            )

        # Find strong criteria
        strong_criteria = [
            (crit, eval)
            for crit, eval in criterion_evaluations.items()
            if eval.is_satisfied and eval.strength_score >= 80
        ]

        if strong_criteria:
            criteria_names = ", ".join(crit.value.split("_", 1)[1] for crit, _ in strong_criteria)
            strengths.append(f"Strong evidence for: {criteria_names} (scores ≥ 80)")

        # Check total evidence count
        total_evidence = sum(eval.total_evidence_count for eval in criterion_evaluations.values())
        if total_evidence >= 15:
            strengths.append(f"Comprehensive evidence portfolio ({total_evidence} items)")

        # Check for high confidence
        high_confidence = [
            eval for eval in criterion_evaluations.values() if eval.confidence_level >= 0.8
        ]
        if len(high_confidence) >= 3:
            strengths.append(f"High confidence in {len(high_confidence)} criteria")

        return strengths

    def _identify_case_risks(
        self,
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation],
        satisfied_count: int,
        meets_minimum: bool,
        overall_score: float,
    ) -> list[str]:
        """Identify case risks."""
        risks = []

        if not meets_minimum:
            risks.append(
                f"CRITICAL: Only {satisfied_count} criteria satisfied (minimum 3 required)"
            )
        elif satisfied_count == 3:
            risks.append(
                "WARNING: At minimum criteria threshold (3) - one weak criterion could jeopardize case"
            )

        # Check for weak satisfied criteria
        weak_satisfied = [
            (crit, eval)
            for crit, eval in criterion_evaluations.items()
            if eval.is_satisfied and eval.strength_score < 75
        ]

        if weak_satisfied:
            criteria_names = ", ".join(crit.value.split("_", 1)[1] for crit, _ in weak_satisfied)
            risks.append(f"Borderline criteria (score < 75): {criteria_names}")

        # Check overall score
        if overall_score < 70:
            risks.append(
                f"Low overall score ({overall_score:.1f}/100) - significant improvements needed"
            )

        # Check for low confidence
        low_confidence = [
            (crit, eval)
            for crit, eval in criterion_evaluations.items()
            if eval.confidence_level < 0.6
        ]

        if low_confidence:
            criteria_names = ", ".join(crit.value.split("_", 1)[1] for crit, _ in low_confidence)
            risks.append(f"Low confidence in: {criteria_names}")

        return risks

    def _generate_case_recommendations(
        self,
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation],
        meets_minimum: bool,
        risks: list[str],
    ) -> tuple[list[str], list[str]]:
        """Generate prioritized case recommendations."""
        priority = []
        secondary = []

        # Critical: Must meet minimum criteria
        if not meets_minimum:
            unsatisfied = [
                crit for crit, eval in criterion_evaluations.items() if not eval.is_satisfied
            ]
            priority.append(
                f"URGENT: Develop evidence for additional criteria. "
                f"Target: {', '.join(c.value.split('_', 1)[1] for c in unsatisfied[:2])}"
            )

        # High priority: Strengthen weak criteria
        weak_criteria = [
            (crit, eval)
            for crit, eval in criterion_evaluations.items()
            if eval.is_satisfied and eval.strength_score < 75
        ]

        if weak_criteria:
            for crit, eval in weak_criteria[:2]:  # Top 2 weak criteria
                if eval.recommendations:
                    priority.append(f"{crit.value}: {eval.recommendations[0]}")

        # Medium priority: Improve strong criteria further
        strong_criteria = [
            (crit, eval)
            for crit, eval in criterion_evaluations.items()
            if eval.is_satisfied and eval.strength_score >= 75
        ]

        for crit, eval in strong_criteria[:2]:
            if eval.recommendations:
                secondary.append(f"{crit.value}: {eval.recommendations[0]}")

        # General recommendations
        if len(criterion_evaluations) == 3:
            secondary.append(
                "Consider developing evidence for 4th criterion to strengthen overall case"
            )

        return priority, secondary

    def _estimate_time_to_ready(
        self,
        overall_score: float,
        satisfied_count: int,
        risks: list[str],
        criterion_evaluations: dict[EB1ACriterion, CriterionEvaluation],
    ) -> int | None:
        """Estimate days until case is filing-ready."""
        # If already strong, could be ready soon
        if overall_score >= 80 and satisfied_count >= 4 and not any("CRITICAL" in r for r in risks):
            return 14  # ~2 weeks for final review

        # If decent but needs improvement
        if overall_score >= 70 and satisfied_count >= 3:
            # Estimate based on number of weak criteria
            weak_count = len([e for e in criterion_evaluations.values() if e.strength_score < 75])
            return 30 + (weak_count * 14)  # ~1 month + 2 weeks per weak criterion

        # If needs substantial work
        if satisfied_count >= 3:
            return 60 + (len(risks) * 7)  # ~2 months + 1 week per risk

        # If critical issues (below minimum)
        criteria_needed = 3 - satisfied_count
        return 90 + (criteria_needed * 30)  # ~3 months + 1 month per missing criterion


# =============================================================================
# Bridge Functions: Intake → EB-1A Analysis
# =============================================================================


async def analyze_intake_for_eb1a(
    case_id: str,
    user_id: str,
    memory_manager: MemoryManager,
) -> CaseStrengthAnalysis:
    """
    Analyze intake questionnaire data for EB-1A criteria satisfaction.

    This bridge function:
    1. Fetches all semantic memory records for a case
    2. Maps intake tags to EB-1A criteria
    3. Converts MemoryRecord to EB1AEvidence format
    4. Runs the full EB1AEvidenceAnalyzer analysis

    Args:
        case_id: The case ID to analyze
        user_id: The user ID (for logging)
        memory_manager: MemoryManager with SupabaseSemanticStore

    Returns:
        CaseStrengthAnalysis with overall score, criteria evaluations,
        and recommendations
    """

    logger.info(
        "analyze_intake_for_eb1a.start",
        case_id=case_id,
        user_id=user_id,
    )

    # 1. Fetch all intake records for this case
    records = await memory_manager.semantic.afetch_by_case_id(case_id)

    if not records:
        logger.warning("analyze_intake_for_eb1a.no_records", case_id=case_id)
        return CaseStrengthAnalysis(
            overall_score=0.0,
            approval_probability=0.0,
            risk_level=RiskLevel.CRITICAL,
            satisfied_criteria_count=0,
            meets_minimum_criteria=False,
            risks=["No intake data found for this case"],
            priority_recommendations=["Complete intake questionnaire first"],
        )

    logger.info(
        "analyze_intake_for_eb1a.records_found",
        case_id=case_id,
        record_count=len(records),
    )

    # 2. Map intake tags to EB-1A criteria
    tag_to_criterion: dict[str, EB1ACriterion] = {
        # Awards criterion
        "major_awards": EB1ACriterion.AWARDS,
        "awards": EB1ACriterion.AWARDS,
        "achievements": EB1ACriterion.AWARDS,
        # Membership criterion
        "associations_memberships": EB1ACriterion.MEMBERSHIP,
        "memberships": EB1ACriterion.MEMBERSHIP,
        "professional_associations": EB1ACriterion.MEMBERSHIP,
        # Press criterion
        "media_press": EB1ACriterion.PRESS,
        "press_coverage": EB1ACriterion.PRESS,
        "publications_about": EB1ACriterion.PRESS,
        # Judging criterion
        "expert_roles": EB1ACriterion.JUDGING,
        "judging": EB1ACriterion.JUDGING,
        "peer_review": EB1ACriterion.JUDGING,
        # Original contribution criterion
        "patents": EB1ACriterion.ORIGINAL_CONTRIBUTION,
        "projects_research": EB1ACriterion.ORIGINAL_CONTRIBUTION,
        "innovations": EB1ACriterion.ORIGINAL_CONTRIBUTION,
        # Scholarly articles criterion
        "conferences_talks": EB1ACriterion.SCHOLARLY_ARTICLES,
        "publications": EB1ACriterion.SCHOLARLY_ARTICLES,
        "scholarly": EB1ACriterion.SCHOLARLY_ARTICLES,
        # Leading role criterion
        "leadership": EB1ACriterion.LEADING_ROLE,
        "career": EB1ACriterion.LEADING_ROLE,
        "management": EB1ACriterion.LEADING_ROLE,
        # High salary criterion
        "salary": EB1ACriterion.HIGH_SALARY,
        "compensation": EB1ACriterion.HIGH_SALARY,
        # Commercial success criterion
        "commercial_products": EB1ACriterion.COMMERCIAL_SUCCESS,
        "business_success": EB1ACriterion.COMMERCIAL_SUCCESS,
    }

    # 3. Convert MemoryRecords to EB1AEvidence and group by criterion
    evidence_by_criterion: dict[EB1ACriterion, list[EB1AEvidence]] = {}

    for record in records:
        for tag in record.tags:
            if tag in TAG_TO_CRITERION:
                criterion = TAG_TO_CRITERION[tag]
                evidence = _convert_memory_to_evidence(record, criterion)
                evidence_by_criterion.setdefault(criterion, []).append(evidence)

    logger.info(
        "analyze_intake_for_eb1a.criteria_mapped",
        case_id=case_id,
        criteria_count=len(evidence_by_criterion),
        criteria=list(evidence_by_criterion.keys()),
    )

    # 4. Run analysis using EB1AEvidenceAnalyzer
    analyzer = EB1AEvidenceAnalyzer(memory_manager)
    analysis = await analyzer.calculate_case_strength(evidence_by_criterion)

    logger.info(
        "analyze_intake_for_eb1a.complete",
        case_id=case_id,
        overall_score=analysis.overall_score,
        satisfied_criteria=analysis.satisfied_criteria_count,
        meets_minimum=analysis.meets_minimum_criteria,
    )

    return analysis


def _convert_memory_to_evidence(
    record: MemoryRecord,
    criterion: EB1ACriterion,
) -> EB1AEvidence:
    """
    Convert a MemoryRecord from intake to EB1AEvidence format.

    Args:
        record: The MemoryRecord from semantic memory
        criterion: The EB-1A criterion this evidence supports

    Returns:
        EB1AEvidence object for the analyzer
    """
    from ..workflows.eb1a.eb1a_coordinator import EvidenceType

    # Determine evidence type based on criterion
    criterion_to_evidence_type = {
        EB1ACriterion.AWARDS: EvidenceType.AWARD_CERTIFICATE,
        EB1ACriterion.MEMBERSHIP: EvidenceType.MEMBERSHIP_LETTER,
        EB1ACriterion.PRESS: EvidenceType.PRESS_ARTICLE,
        EB1ACriterion.JUDGING: EvidenceType.RECOMMENDATION_LETTER,
        EB1ACriterion.ORIGINAL_CONTRIBUTION: EvidenceType.PATENT,
        EB1ACriterion.SCHOLARLY_ARTICLES: EvidenceType.PUBLICATION,
        EB1ACriterion.LEADING_ROLE: EvidenceType.EMPLOYMENT_LETTER,
        EB1ACriterion.HIGH_SALARY: EvidenceType.SALARY_EVIDENCE,
        EB1ACriterion.COMMERCIAL_SUCCESS: EvidenceType.IMPACT_METRICS,
        EB1ACriterion.ARTISTIC_EXHIBITION: EvidenceType.IMPACT_METRICS,
    }

    evidence_type = criterion_to_evidence_type.get(criterion, EvidenceType.IMPACT_METRICS)

    # Create title from tags
    tags_str = ", ".join(record.tags[:3]) if record.tags else "intake data"

    return EB1AEvidence(
        criterion=criterion,
        evidence_type=evidence_type,
        title=f"Intake: {tags_str}",
        description=record.text,
        date=record.created_at,
        source=record.source or "intake_questionnaire",
        metadata=record.metadata or {},
    )


# =============================================================================
# Result Model for Analysis + Draft Generation
# =============================================================================


class AnalysisWithDraft(BaseModel):
    """Result of analyze_and_generate_draft function."""

    analysis: CaseStrengthAnalysis
    draft_generated: bool = False
    draft_document_id: str | None = None
    draft_content: str | None = None
    feedback: str | None = None


# =============================================================================
# Auto-trigger WriterAgent: Analysis + Draft Generation
# =============================================================================

# Threshold for auto-generating petition draft
DRAFT_GENERATION_THRESHOLD = 70.0


async def analyze_and_generate_draft(
    case_id: str,
    user_id: str,
    memory_manager: MemoryManager,
    beneficiary_name: str | None = None,
    field: str | None = None,
    auto_generate: bool = True,
) -> AnalysisWithDraft:
    """
    Analyze intake data and auto-generate petition draft if score >= 70%.

    This function combines:
    1. EB-1A criteria analysis (via analyze_intake_for_eb1a)
    2. LLM-based feedback generation for weak cases
    3. Auto-triggering WriterAgent for strong cases (score >= 70%)

    Per TAST.txt requirements:
    - "Next Step -> Writer: Автоматический запуск генерации черновика, если оценка > 70%"
    - Generates Cover Letter draft when analysis passes threshold

    Args:
        case_id: The case ID to analyze
        user_id: The user ID for audit logging
        memory_manager: MemoryManager with semantic store
        beneficiary_name: Optional name for document generation
        field: Optional field of expertise
        auto_generate: Whether to auto-generate draft (default: True)

    Returns:
        AnalysisWithDraft containing:
        - analysis: Full CaseStrengthAnalysis
        - draft_generated: Whether a draft was created
        - draft_document_id: ID of generated document (if any)
        - draft_content: Content preview of draft (if any)
        - feedback: LLM-generated feedback for weak cases
    """
    logger.info(
        "analyze_and_generate_draft.start",
        case_id=case_id,
        user_id=user_id,
        auto_generate=auto_generate,
    )

    # 1. Run EB-1A analysis
    analysis = await analyze_intake_for_eb1a(case_id, user_id, memory_manager)

    result = AnalysisWithDraft(analysis=analysis)

    # 2. Generate feedback for weak cases (score < 70)
    if analysis.overall_score < DRAFT_GENERATION_THRESHOLD:
        logger.info(
            "analyze_and_generate_draft.weak_case",
            case_id=case_id,
            score=analysis.overall_score,
            threshold=DRAFT_GENERATION_THRESHOLD,
        )

        # Generate LLM feedback
        try:
            analyzer = EB1AEvidenceAnalyzer(memory_manager, use_llm=True)
            feedback = await analyzer.generate_feedback(analysis)
            result.feedback = feedback
            logger.info(
                "analyze_and_generate_draft.feedback_generated",
                case_id=case_id,
                feedback_length=len(feedback),
            )
        except Exception as e:
            logger.warning(
                "analyze_and_generate_draft.feedback_error",
                case_id=case_id,
                error=str(e),
            )
            result.feedback = _generate_basic_feedback(analysis)

        return result

    # 3. Auto-generate draft for strong cases (score >= 70)
    if not auto_generate:
        logger.info(
            "analyze_and_generate_draft.skip_generation",
            case_id=case_id,
            reason="auto_generate=False",
        )
        return result

    logger.info(
        "analyze_and_generate_draft.generating_draft",
        case_id=case_id,
        score=analysis.overall_score,
    )

    try:
        # Import WriterAgent
        from .writer_agent import (DocumentRequest, DocumentType,
                                   GeneratedDocument, Language, ToneStyle,
                                   WriterAgent)

        # Initialize WriterAgent
        writer = WriterAgent(memory_manager)

        # Prepare client data for document generation
        satisfied_criteria = [
            crit.value
            for crit, eval_result in (analysis.criterion_evaluations or {}).items()
            if eval_result.is_satisfied
        ]

        content_data = {
            "recipient": "United States Citizenship and Immigration Services",
            "recipient_name": "USCIS Officer",
            "content": _build_cover_letter_content(
                analysis=analysis,
                beneficiary_name=beneficiary_name or "The Petitioner",
                field=field or "their field of expertise",
                satisfied_criteria=satisfied_criteria,
            ),
            "closing": "We respectfully request that this petition be approved.",
            "sender": beneficiary_name or "Petitioner",
            "subject": "I-140 Petition for Alien Worker - EB-1A Extraordinary Ability",
            "date": datetime.now().strftime("%B %d, %Y"),
        }

        # Create document request
        request = DocumentRequest(
            document_type=DocumentType.PETITION,
            content_data=content_data,
            language=Language.ENGLISH,
            tone=ToneStyle.FORMAL,
            case_id=case_id,
            approval_required=True,  # Require human review
            custom_instructions="Immigration law petition for EB-1A extraordinary ability",
        )

        # Generate the document
        document: GeneratedDocument = await writer.agenerate_letter(request, user_id)

        result.draft_generated = True
        result.draft_document_id = document.document_id
        result.draft_content = (
            document.content[:500] + "..." if len(document.content) > 500 else document.content
        )

        logger.info(
            "analyze_and_generate_draft.draft_complete",
            case_id=case_id,
            document_id=document.document_id,
            content_length=len(document.content),
        )

    except Exception as e:
        logger.exception(
            "analyze_and_generate_draft.draft_error",
            case_id=case_id,
            error=str(e),
        )
        # Don't fail the whole operation, just skip draft generation
        result.draft_generated = False

    return result


def _build_cover_letter_content(
    analysis: CaseStrengthAnalysis,
    beneficiary_name: str,
    field: str,
    satisfied_criteria: list[str],
) -> str:
    """Build cover letter content based on analysis results."""
    criteria_text = ", ".join(crit.replace("_", " ").title() for crit in satisfied_criteria[:5])

    content = f"""This petition is filed on behalf of {beneficiary_name}, an individual of extraordinary ability in {field}.

**Summary of Qualifications:**

{beneficiary_name} satisfies {analysis.satisfied_criteria_count} of the 10 criteria for EB-1A classification, exceeding the minimum requirement of 3 criteria. The satisfied criteria include: {criteria_text}.

**Case Strength Assessment:**
- Overall Score: {analysis.overall_score:.1f}/100
- Approval Probability: {analysis.approval_probability:.0%}
- Risk Level: {analysis.risk_level.value.upper()}

**Evidence Summary:**

The enclosed documentation demonstrates that {beneficiary_name} has achieved sustained national and international acclaim and recognition for achievements in {field}. This evidence includes:

"""

    # Add strengths if available
    if analysis.strengths:
        for i, strength in enumerate(analysis.strengths[:4], 1):
            content += f"{i}. {strength}\n"

    content += f"""
**Conclusion:**

Based on the comprehensive evidence presented, {beneficiary_name} clearly qualifies for classification as an alien of extraordinary ability under 8 CFR § 204.5(h). The evidence demonstrates that {beneficiary_name} has risen to the very top of {field} and is one of the small percentage who have achieved extraordinary ability.
"""

    return content


def _generate_basic_feedback(analysis: CaseStrengthAnalysis) -> str:
    """Generate basic feedback without LLM for fallback."""
    lines = [
        "📊 **EB-1A Case Assessment**",
        "",
        f"Your case currently scores {analysis.overall_score:.0f}/100.",
        f"Criteria satisfied: {analysis.satisfied_criteria_count}/10",
        "",
    ]

    if not analysis.meets_minimum_criteria:
        lines.append("⚠️ **Action Required:** You need to satisfy at least 3 criteria.")
        lines.append("")

    if analysis.priority_recommendations:
        lines.append("📝 **Priority Recommendations:**")
        for rec in analysis.priority_recommendations[:3]:
            lines.append(f"• {rec}")
        lines.append("")

    if analysis.risks:
        lines.append("⚠️ **Risks to Address:**")
        for risk in analysis.risks[:3]:
            lines.append(f"• {risk}")

    return "\n".join(lines)
