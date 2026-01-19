"""
EB-1A Criteria Skill - Core Implementation.

Provides comprehensive evaluation and documentation for all 10 EB-1A
extraordinary ability criteria as defined by 8 CFR 204.5(h)(3).

Based on USCIS Policy Manual and Kazarian v. USCIS two-step analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class CriterionType(str, Enum):
    """10 EB-1A criteria types + comparable evidence."""

    # 8 CFR 204.5(h)(3)(i) - Awards
    AWARDS = "awards"

    # 8 CFR 204.5(h)(3)(ii) - Membership
    MEMBERSHIP = "membership"

    # 8 CFR 204.5(h)(3)(iii) - Published material about the person
    PUBLISHED_MATERIAL = "published_material"

    # 8 CFR 204.5(h)(3)(iv) - Judging
    JUDGING = "judging"

    # 8 CFR 204.5(h)(3)(v) - Original contributions
    ORIGINAL_CONTRIBUTIONS = "original_contributions"

    # 8 CFR 204.5(h)(3)(vi) - Scholarly articles
    SCHOLARLY_ARTICLES = "scholarly_articles"

    # 8 CFR 204.5(h)(3)(vii) - Artistic exhibitions
    EXHIBITIONS = "exhibitions"

    # 8 CFR 204.5(h)(3)(viii) - Leading/critical role
    LEADING_ROLE = "leading_role"

    # 8 CFR 204.5(h)(3)(ix) - High salary
    HIGH_SALARY = "high_salary"

    # 8 CFR 204.5(h)(3)(x) - Commercial success
    COMMERCIAL_SUCCESS = "commercial_success"

    # Comparable evidence per 8 CFR 204.5(h)(4)
    COMPARABLE_EVIDENCE = "comparable_evidence"


class EvidenceStrength(str, Enum):
    """Strength rating for evidence."""

    EXCEPTIONAL = "exceptional"  # 90-100% - Exceeds requirements significantly
    STRONG = "strong"            # 75-89% - Clearly meets requirements
    MODERATE = "moderate"        # 50-74% - Meets basic requirements
    WEAK = "weak"                # 25-49% - Partially meets, needs strengthening
    INSUFFICIENT = "insufficient"  # 0-24% - Does not meet requirements


@dataclass
class Evidence:
    """Single piece of evidence for a criterion."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    document_type: str = ""  # e.g., "certificate", "letter", "article"
    source: str = ""
    date: datetime | None = None
    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceEvaluation:
    """Evaluation result for a single piece of evidence."""

    evidence_id: str
    criterion: CriterionType
    strength: EvidenceStrength
    score: float  # 0-100
    analysis: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    uscis_alignment: str = ""  # How it aligns with USCIS requirements
    kazarian_step1: bool = False  # Meets initial evidence threshold
    kazarian_step2: bool = False  # Contributes to overall extraordinary ability


@dataclass
class CriterionEvaluation:
    """Evaluation result for an entire criterion."""

    criterion: CriterionType
    criterion_met: bool
    overall_strength: EvidenceStrength
    overall_score: float  # 0-100
    evidence_evaluations: list[EvidenceEvaluation] = field(default_factory=list)
    summary: str = ""
    narrative: str = ""  # Draft petition narrative for this criterion
    recommendations: list[str] = field(default_factory=list)
    required_documents: list[str] = field(default_factory=list)


@dataclass
class CriteriaAnalysisResult:
    """Complete analysis result for all criteria."""

    case_id: str
    analysis_date: datetime = field(default_factory=datetime.utcnow)
    criteria_met: list[CriterionType] = field(default_factory=list)
    criteria_evaluations: dict[CriterionType, CriterionEvaluation] = field(default_factory=dict)
    overall_recommendation: str = ""
    overall_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    estimated_approval_probability: float = 0.0


class EB1ACriteriaSkill:
    """
    Main skill class for EB-1A criteria evaluation.

    Integrates with:
    - IntakeAgent: Collects evidence through questionnaire
    - ResearcherAgent: Finds supporting materials and precedents
    - WriterAgent: Generates petition narratives
    - ReviewerAgent: Validates evidence quality
    - ValidatorAgent: Final compliance check
    """

    # Minimum criteria required for EB-1A (must meet at least 3)
    MIN_CRITERIA_REQUIRED = 3

    # USCIS Policy Manual references
    POLICY_REFERENCES = {
        CriterionType.AWARDS: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(1)",
        CriterionType.MEMBERSHIP: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(2)",
        CriterionType.PUBLISHED_MATERIAL: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(3)",
        CriterionType.JUDGING: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(4)",
        CriterionType.ORIGINAL_CONTRIBUTIONS: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(5)",
        CriterionType.SCHOLARLY_ARTICLES: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(6)",
        CriterionType.EXHIBITIONS: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(7)",
        CriterionType.LEADING_ROLE: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(8)",
        CriterionType.HIGH_SALARY: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(9)",
        CriterionType.COMMERCIAL_SUCCESS: "USCIS Policy Manual Vol. 6, Part F, Ch. 2(A)(10)",
        CriterionType.COMPARABLE_EVIDENCE: "8 CFR 204.5(h)(4)",
    }

    # Criterion descriptions (Russian + English)
    CRITERION_DESCRIPTIONS = {
        CriterionType.AWARDS: {
            "en": "Evidence of receipt of lesser nationally or internationally recognized prizes or awards for excellence",
            "ru": "Доказательства получения национально или международно признанных наград за выдающиеся достижения",
            "key_elements": [
                "Award must be for excellence in the field",
                "Award must have national or international recognition",
                "Petitioner must be a recipient (team awards acceptable if listed as recipient)",
            ],
        },
        CriterionType.MEMBERSHIP: {
            "en": "Evidence of membership in associations that require outstanding achievements",
            "ru": "Доказательства членства в ассоциациях, требующих выдающихся достижений",
            "key_elements": [
                "Association must be in the field of expertise",
                "Membership must require outstanding achievements",
                "Membership criteria must be judged by recognized experts",
            ],
        },
        CriterionType.PUBLISHED_MATERIAL: {
            "en": "Evidence of published material about the person in professional or major trade publications",
            "ru": "Доказательства публикаций о заявителе в профессиональных или крупных изданиях",
            "key_elements": [
                "Material must be ABOUT the petitioner, not BY the petitioner",
                "Publication must be professional or major trade publication",
                "Must include title, date, author, and publication details",
            ],
        },
        CriterionType.JUDGING: {
            "en": "Evidence of participation as a judge of the work of others",
            "ru": "Доказательства участия в качестве судьи работ других",
            "key_elements": [
                "Must be individual or panel judging",
                "Must judge work of others in the field",
                "Review activities (peer review, grant review) count",
            ],
        },
        CriterionType.ORIGINAL_CONTRIBUTIONS: {
            "en": "Evidence of original scientific, scholarly, artistic, athletic, or business-related contributions of major significance",
            "ru": "Доказательства оригинального вклада значительной важности в области",
            "key_elements": [
                "Contribution must be original",
                "Must have major significance to the field",
                "Recommendation letters should explain impact",
            ],
        },
        CriterionType.SCHOLARLY_ARTICLES: {
            "en": "Evidence of authorship of scholarly articles in professional or major trade publications",
            "ru": "Доказательства авторства научных статей в профессиональных изданиях",
            "key_elements": [
                "Articles must be scholarly/academic",
                "Published in professional or major trade publications",
                "Citations and impact factor can strengthen evidence",
            ],
        },
        CriterionType.EXHIBITIONS: {
            "en": "Evidence that work has been displayed at artistic exhibitions or showcases",
            "ru": "Доказательства демонстрации работ на художественных выставках",
            "key_elements": [
                "Work must be created by the petitioner",
                "Displayed at artistic exhibitions or showcases",
                "Can include scientific/technical exhibitions if presenting own work",
            ],
        },
        CriterionType.LEADING_ROLE: {
            "en": "Evidence of performance of a leading or critical role in distinguished organizations",
            "ru": "Доказательства ведущей или критически важной роли в выдающихся организациях",
            "key_elements": [
                "Role must be leading OR critical",
                "Organization must have distinguished reputation",
                "Letters from supervisors explaining significance",
            ],
        },
        CriterionType.HIGH_SALARY: {
            "en": "Evidence of high salary or other significantly high remuneration in relation to others in the field",
            "ru": "Доказательства высокой зарплаты по сравнению с другими в области",
            "key_elements": [
                "Salary must be high relative to field/location",
                "Comparative data from BLS/DOL required",
                "Can include contracts/offers for prospective salary",
            ],
        },
        CriterionType.COMMERCIAL_SUCCESS: {
            "en": "Evidence of commercial successes in the performing arts",
            "ru": "Доказательства коммерческого успеха в исполнительских искусствах",
            "key_elements": [
                "Primarily for performing arts",
                "Box office receipts, sales records",
                "Must show commercial success relative to others",
            ],
        },
        CriterionType.COMPARABLE_EVIDENCE: {
            "en": "Comparable evidence when standard criteria don't apply",
            "ru": "Сопоставимые доказательства, когда стандартные критерии не применимы",
            "key_elements": [
                "Used when standard criteria don't readily apply",
                "Must explain why standard criteria don't apply",
                "Evidence must be comparable in significance",
            ],
        },
    }

    def __init__(
        self,
        memory_manager: Any | None = None,
        llm_router: Any | None = None,
    ):
        """Initialize the EB-1A criteria skill."""
        self.memory_manager = memory_manager
        self.llm_router = llm_router
        self._evaluators: dict[CriterionType, Any] = {}

    async def analyze_case(
        self,
        case_id: str,
        case_data: dict[str, Any],
    ) -> CriteriaAnalysisResult:
        """
        Analyze a case against all EB-1A criteria.

        Args:
            case_id: The case identifier
            case_data: Case data including evidence and questionnaire answers

        Returns:
            Complete criteria analysis result
        """
        logger.info("eb1a.criteria.analysis.started", case_id=case_id)

        result = CriteriaAnalysisResult(case_id=case_id)

        # Analyze each criterion
        for criterion in CriterionType:
            evaluation = await self.evaluate_criterion(
                case_id=case_id,
                criterion=criterion,
                case_data=case_data,
            )
            result.criteria_evaluations[criterion] = evaluation

            if evaluation.criterion_met:
                result.criteria_met.append(criterion)

        # Calculate overall score and recommendation
        result.overall_score = self._calculate_overall_score(result)
        result.overall_recommendation = self._generate_recommendation(result)
        result.estimated_approval_probability = self._estimate_approval_probability(result)

        # Generate strengths and weaknesses
        result.strengths = self._identify_strengths(result)
        result.weaknesses = self._identify_weaknesses(result)
        result.next_steps = self._generate_next_steps(result)

        logger.info(
            "eb1a.criteria.analysis.completed",
            case_id=case_id,
            criteria_met=len(result.criteria_met),
            overall_score=result.overall_score,
        )

        return result

    async def evaluate_criterion(
        self,
        case_id: str,
        criterion: CriterionType,
        case_data: dict[str, Any],
    ) -> CriterionEvaluation:
        """
        Evaluate a single criterion.

        Args:
            case_id: The case identifier
            criterion: The criterion to evaluate
            case_data: Case data with evidence

        Returns:
            Criterion evaluation result
        """
        logger.info(
            "eb1a.criterion.evaluation.started",
            case_id=case_id,
            criterion=criterion.value,
        )

        # Get evidence for this criterion
        evidence_list = self._extract_evidence_for_criterion(criterion, case_data)

        # Get the evaluation prompt from criterion class
        prompt = self._get_criterion_prompt(criterion, case_data, evidence_list)

        # Evaluate using LLM if available
        if self.llm_router:
            evaluation = await self._llm_evaluate(criterion, prompt, evidence_list)
        else:
            evaluation = self._rule_based_evaluate(criterion, evidence_list)

        return evaluation

    def _get_criterion_prompt(
        self,
        criterion: CriterionType,
        case_context: dict[str, Any],
        evidence_list: list[Evidence],
    ) -> str:
        """
        Get the evaluation prompt for a specific criterion.

        Args:
            criterion: The criterion type
            case_context: Case data and context
            evidence_list: List of evidence items

        Returns:
            Formatted prompt string
        """
        from .criteria import CRITERION_CLASSES

        # Get criterion class and its PROMPT
        criterion_class = CRITERION_CLASSES.get(criterion.value)
        if criterion_class is None:
            return ""

        template = getattr(criterion_class, "PROMPT", "")

        # Format evidence list
        evidence_str = ""
        for i, ev in enumerate(evidence_list, 1):
            evidence_str += f"""
{i}. {ev.title}
   Description: {ev.description}
   Type: {ev.document_type}
   Source: {ev.source}
"""

        if not evidence_str:
            evidence_str = "No evidence provided for this criterion yet."

        # Format case context
        context_str = "\n".join(
            f"- {k}: {v}"
            for k, v in case_context.items()
            if k not in ["evidence", "documents"]
        )

        return template.format(
            evidence_list=evidence_str,
            case_context=context_str or "No additional context provided.",
        )

    def _extract_evidence_for_criterion(
        self,
        criterion: CriterionType,
        case_data: dict[str, Any],
    ) -> list[Evidence]:
        """Extract evidence relevant to a specific criterion."""
        evidence_list = []

        # Map criterion to intake questionnaire sections
        criterion_mapping = {
            CriterionType.AWARDS: ["awards", "prizes", "honors"],
            CriterionType.MEMBERSHIP: ["memberships", "associations", "professional_organizations"],
            CriterionType.PUBLISHED_MATERIAL: ["media_coverage", "press", "publications_about"],
            CriterionType.JUDGING: ["judging", "peer_review", "panel_participation"],
            CriterionType.ORIGINAL_CONTRIBUTIONS: ["contributions", "innovations", "patents", "projects"],
            CriterionType.SCHOLARLY_ARTICLES: ["publications", "articles", "papers", "research"],
            CriterionType.EXHIBITIONS: ["exhibitions", "showcases", "presentations", "demos"],
            CriterionType.LEADING_ROLE: ["roles", "leadership", "positions", "employment"],
            CriterionType.HIGH_SALARY: ["salary", "compensation", "remuneration", "income"],
            CriterionType.COMMERCIAL_SUCCESS: ["sales", "revenue", "commercial", "business_success"],
            CriterionType.COMPARABLE_EVIDENCE: ["other_evidence", "comparable", "additional"],
        }

        # Extract from case data
        relevant_keys = criterion_mapping.get(criterion, [])
        for key in relevant_keys:
            if key in case_data:
                items = case_data[key]
                if isinstance(items, list):
                    for item in items:
                        evidence_list.append(Evidence(
                            title=item.get("title", ""),
                            description=item.get("description", ""),
                            document_type=item.get("type", ""),
                            source=item.get("source", ""),
                            metadata=item,
                        ))
                elif isinstance(items, dict):
                    evidence_list.append(Evidence(
                        title=items.get("title", ""),
                        description=items.get("description", ""),
                        document_type=items.get("type", ""),
                        source=items.get("source", ""),
                        metadata=items,
                    ))

        return evidence_list

    async def _llm_evaluate(
        self,
        criterion: CriterionType,
        prompt: str,
        evidence_list: list[Evidence],
    ) -> CriterionEvaluation:
        """Evaluate criterion using LLM."""
        # Implementation would call llm_router with structured output
        # For now, return a placeholder
        return self._rule_based_evaluate(criterion, evidence_list)

    def _rule_based_evaluate(
        self,
        criterion: CriterionType,
        evidence_list: list[Evidence],
    ) -> CriterionEvaluation:
        """Basic rule-based evaluation as fallback."""
        evidence_count = len(evidence_list)

        # Simple scoring based on evidence count
        if evidence_count == 0:
            strength = EvidenceStrength.INSUFFICIENT
            score = 0.0
            criterion_met = False
        elif evidence_count == 1:
            strength = EvidenceStrength.WEAK
            score = 30.0
            criterion_met = False
        elif evidence_count == 2:
            strength = EvidenceStrength.MODERATE
            score = 55.0
            criterion_met = True
        elif evidence_count <= 4:
            strength = EvidenceStrength.STRONG
            score = 75.0
            criterion_met = True
        else:
            strength = EvidenceStrength.EXCEPTIONAL
            score = 90.0
            criterion_met = True

        return CriterionEvaluation(
            criterion=criterion,
            criterion_met=criterion_met,
            overall_strength=strength,
            overall_score=score,
            summary=f"Found {evidence_count} pieces of evidence for {criterion.value}",
            narrative="",  # Would be generated by WriterAgent
            recommendations=[
                "Obtain recommendation letters explaining significance"
                if evidence_count > 0 else "Gather evidence for this criterion"
            ],
        )

    def _calculate_overall_score(self, result: CriteriaAnalysisResult) -> float:
        """Calculate overall case score."""
        if not result.criteria_evaluations:
            return 0.0

        total_score = sum(
            crit_eval.overall_score for crit_eval in result.criteria_evaluations.values()
        )
        return total_score / len(result.criteria_evaluations)

    def _generate_recommendation(self, result: CriteriaAnalysisResult) -> str:
        """Generate overall recommendation."""
        criteria_met = len(result.criteria_met)

        if criteria_met >= 5:
            return "STRONG CASE - Recommend filing. Exceeds minimum requirements with robust evidence."
        if criteria_met >= 3:
            return "VIABLE CASE - Recommend filing with focused narrative on strongest criteria."
        if criteria_met >= 2:
            return "BORDERLINE CASE - Consider strengthening evidence before filing."
        return "WEAK CASE - Additional evidence needed before filing is advisable."

    def _estimate_approval_probability(self, result: CriteriaAnalysisResult) -> float:
        """Estimate approval probability based on evidence strength."""
        criteria_met = len(result.criteria_met)
        avg_score = result.overall_score

        # Base probability from criteria count
        if criteria_met >= 5:
            base = 0.85
        elif criteria_met >= 4:
            base = 0.75
        elif criteria_met >= 3:
            base = 0.60
        elif criteria_met >= 2:
            base = 0.35
        else:
            base = 0.15

        # Adjust based on average score
        adjustment = (avg_score - 50) / 100 * 0.2  # ±20% adjustment

        return min(0.95, max(0.05, base + adjustment))

    def _identify_strengths(self, result: CriteriaAnalysisResult) -> list[str]:
        """Identify case strengths."""
        strengths = []

        for criterion, evaluation in result.criteria_evaluations.items():
            if evaluation.overall_strength in [EvidenceStrength.STRONG, EvidenceStrength.EXCEPTIONAL]:
                strengths.append(
                    f"{self.CRITERION_DESCRIPTIONS[criterion]['en']}: "
                    f"{evaluation.summary}"
                )

        return strengths

    def _identify_weaknesses(self, result: CriteriaAnalysisResult) -> list[str]:
        """Identify case weaknesses."""
        weaknesses = []

        for criterion, evaluation in result.criteria_evaluations.items():
            if evaluation.overall_strength in [EvidenceStrength.INSUFFICIENT, EvidenceStrength.WEAK]:
                weaknesses.append(
                    f"{self.CRITERION_DESCRIPTIONS[criterion]['en']}: Needs strengthening"
                )

        return weaknesses

    def _generate_next_steps(self, result: CriteriaAnalysisResult) -> list[str]:
        """Generate recommended next steps."""
        next_steps = []

        # Priority: strengthen weakest criteria that are close to meeting threshold
        for criterion, evaluation in result.criteria_evaluations.items():
            if evaluation.overall_strength == EvidenceStrength.MODERATE:
                next_steps.append(
                    f"Strengthen {criterion.value}: {', '.join(evaluation.recommendations)}"
                )

        # If less than 3 criteria met, suggest gathering more evidence
        if len(result.criteria_met) < 3:
            next_steps.insert(0, "CRITICAL: Need to meet at least 3 criteria. Focus on gathering additional evidence.")

        return next_steps[:5]  # Return top 5 next steps

    def get_criterion_info(self, criterion: CriterionType) -> dict[str, Any]:
        """Get detailed information about a criterion."""
        return {
            "type": criterion.value,
            "description": self.CRITERION_DESCRIPTIONS[criterion],
            "policy_reference": self.POLICY_REFERENCES[criterion],
        }

    def get_all_criteria_info(self) -> dict[CriterionType, dict[str, Any]]:
        """Get information about all criteria."""
        return {
            criterion: self.get_criterion_info(criterion)
            for criterion in CriterionType
        }
