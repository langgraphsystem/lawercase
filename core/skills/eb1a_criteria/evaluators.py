"""
EB-1A Criterion Evaluators.

Specialized evaluators for each of the 10 EB-1A criteria.
Each evaluator implements criterion-specific logic for evidence assessment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from .criteria_skill import (CriterionEvaluation, CriterionType, Evidence,
                             EvidenceEvaluation, EvidenceStrength)

logger = structlog.get_logger(__name__)


class BaseCriterionEvaluator(ABC):
    """Base class for criterion evaluators."""

    criterion_type: CriterionType

    @abstractmethod
    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        """Evaluate evidence for this criterion."""

    def _calculate_strength(self, score: float) -> EvidenceStrength:
        """Convert score to strength rating."""
        if score >= 90:
            return EvidenceStrength.EXCEPTIONAL
        if score >= 75:
            return EvidenceStrength.STRONG
        if score >= 50:
            return EvidenceStrength.MODERATE
        if score >= 25:
            return EvidenceStrength.WEAK
        return EvidenceStrength.INSUFFICIENT


class AwardsEvaluator(BaseCriterionEvaluator):
    """Evaluator for Awards criterion."""

    criterion_type = CriterionType.AWARDS

    # Award type classifications
    INTERNATIONAL_KEYWORDS = ["international", "global", "world", "olympic"]
    NATIONAL_KEYWORDS = ["national", "state", "federal", "country"]
    EXCELLENCE_KEYWORDS = ["excellence", "outstanding", "best", "first place", "winner", "champion"]

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        """Evaluate awards evidence."""
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_award(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=self._analyze_award(evidence),
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment=self._check_uscis_alignment(evidence),
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} awards. {'Criterion likely met.' if criterion_met else 'Needs strengthening.'}",
            recommendations=self._overall_recommendations(evaluations),
            required_documents=self._required_documents(),
        )

    def _score_award(self, evidence: Evidence) -> float:
        """Score individual award."""
        score = 0.0
        text = f"{evidence.title} {evidence.description}".lower()

        # Check recognition level
        if any(kw in text for kw in self.INTERNATIONAL_KEYWORDS):
            score += 40
        elif any(kw in text for kw in self.NATIONAL_KEYWORDS):
            score += 30
        else:
            score += 15  # Regional/local

        # Check for excellence terminology
        if any(kw in text for kw in self.EXCELLENCE_KEYWORDS):
            score += 25

        # Check for field relevance
        if evidence.metadata.get("field_relevant", True):
            score += 20

        # Check for documentation
        if evidence.attachments:
            score += 15

        return min(100.0, score)

    def _analyze_award(self, evidence: Evidence) -> str:
        """Provide analysis text for award."""
        return f"Award '{evidence.title}' analyzed for national/international recognition and excellence criteria."

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        """Identify strengths of the evidence."""
        strengths = []
        text = f"{evidence.title} {evidence.description}".lower()

        if any(kw in text for kw in self.INTERNATIONAL_KEYWORDS):
            strengths.append("International recognition")
        if any(kw in text for kw in self.EXCELLENCE_KEYWORDS):
            strengths.append("Award for excellence")
        if evidence.attachments:
            strengths.append("Documentation available")

        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        """Identify weaknesses of the evidence."""
        weaknesses = []
        text = f"{evidence.title} {evidence.description}".lower()

        if not any(kw in text for kw in self.INTERNATIONAL_KEYWORDS + self.NATIONAL_KEYWORDS):
            weaknesses.append("Unclear geographic recognition level")
        if not evidence.attachments:
            weaknesses.append("Missing documentation")
        if not evidence.metadata.get("selection_criteria"):
            weaknesses.append("Selection criteria not documented")

        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        """Get recommendations for strengthening evidence."""
        recommendations = []

        if not evidence.attachments:
            recommendations.append("Obtain award certificate or announcement")
        if not evidence.metadata.get("selection_criteria"):
            recommendations.append("Document selection criteria and process")
        if not evidence.metadata.get("competitors"):
            recommendations.append("Document number of nominees/competitors")

        return recommendations

    def _check_uscis_alignment(self, evidence: Evidence) -> str:
        """Check alignment with USCIS requirements."""
        return "Aligns with 8 CFR 204.5(h)(3)(i) if documentation proves national/international recognition for excellence."

    def _overall_recommendations(self, evaluations: list[EvidenceEvaluation]) -> list[str]:
        """Overall recommendations for the criterion."""
        recommendations = []
        if len(evaluations) < 2:
            recommendations.append("Consider documenting additional awards to strengthen case")

        weak_count = sum(
            1
            for e in evaluations
            if e.strength in [EvidenceStrength.WEAK, EvidenceStrength.INSUFFICIENT]
        )
        if weak_count > 0:
            recommendations.append(f"{weak_count} award(s) need additional documentation")

        return recommendations

    def _required_documents(self) -> list[str]:
        """List required documents for this criterion."""
        return [
            "Award certificates or letters",
            "Selection criteria documentation",
            "List of nominees/competitors",
            "Media coverage of award",
            "Organization information sheet",
        ]


class MembershipEvaluator(BaseCriterionEvaluator):
    """Evaluator for Membership criterion."""

    criterion_type = CriterionType.MEMBERSHIP

    # Known prestigious associations by field
    PRESTIGIOUS_ORGS = {
        "technology": ["ieee", "acm", "aaai"],
        "science": ["national academy", "royal society", "aaas"],
        "medicine": ["ama", "acs", "ascp"],
        "law": ["aba", "actl"],
        "arts": ["ampas", "tga", "dga"],
    }

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        """Evaluate membership evidence."""
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_membership(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=self._analyze_membership(evidence),
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment=self._check_uscis_alignment(evidence),
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} memberships.",
            recommendations=self._overall_recommendations(evaluations),
            required_documents=self._required_documents(),
        )

    def _score_membership(self, evidence: Evidence) -> float:
        """Score individual membership."""
        score = 0.0
        text = f"{evidence.title} {evidence.description}".lower()

        # Check if prestigious organization
        for _field, orgs in self.PRESTIGIOUS_ORGS.items():
            if any(org in text for org in orgs):
                score += 40
                break

        # Check for selective membership
        if evidence.metadata.get("selective", False):
            score += 30
        elif "senior" in text or "fellow" in text or "distinguished" in text:
            score += 25

        # Check for expert judgment
        if evidence.metadata.get("peer_reviewed", False):
            score += 20

        # Documentation
        if evidence.attachments:
            score += 10

        return min(100.0, score)

    def _analyze_membership(self, evidence: Evidence) -> str:
        return (
            f"Membership in '{evidence.title}' analyzed for outstanding achievement requirements."
        )

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        text = f"{evidence.title} {evidence.description}".lower()
        if "senior" in text or "fellow" in text:
            strengths.append("Higher membership level indicating achievement")
        if evidence.metadata.get("selective"):
            strengths.append("Selective membership process")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if evidence.metadata.get("fee_only"):
            weaknesses.append("Membership appears to be fee-based only")
        if not evidence.metadata.get("requirements_documented"):
            weaknesses.append("Membership requirements not documented")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain organization bylaws showing membership requirements",
            "Document who judges membership applications",
            "Get letter from organization about selection criteria",
        ]

    def _check_uscis_alignment(self, evidence: Evidence) -> str:
        return (
            "Must show membership requires outstanding achievements judged by recognized experts."
        )

    def _overall_recommendations(self, evaluations: list[EvidenceEvaluation]) -> list[str]:
        return ["Obtain bylaws or membership criteria for each organization"]

    def _required_documents(self) -> list[str]:
        return [
            "Membership certificate",
            "Organization bylaws/membership criteria",
            "Evidence of selection process",
            "Letter from organization explaining requirements",
        ]


class PublishedMaterialEvaluator(BaseCriterionEvaluator):
    """Evaluator for Published Material criterion."""

    criterion_type = CriterionType.PUBLISHED_MATERIAL

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_publication(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Published material '{evidence.title}' analyzed for media recognition.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Material must be ABOUT the petitioner in major publications.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} publications about petitioner.",
            recommendations=["Document publication circulation and reach"],
            required_documents=self._required_documents(),
        )

    def _score_publication(self, evidence: Evidence) -> float:
        score = 0.0

        # Check circulation/reach
        circulation = evidence.metadata.get("circulation", 0)
        if circulation > 1000000:
            score += 40
        elif circulation > 100000:
            score += 30
        elif circulation > 10000:
            score += 20
        else:
            score += 10

        # Major publication
        if evidence.metadata.get("major_publication", False):
            score += 25

        # Article focus
        if evidence.metadata.get("petitioner_focus", False):
            score += 20

        # Documentation
        if evidence.attachments:
            score += 15

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        if evidence.metadata.get("major_publication"):
            strengths.append("Major publication")
        if evidence.metadata.get("petitioner_focus"):
            strengths.append("Article focuses on petitioner's work")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("circulation"):
            weaknesses.append("Circulation data not provided")
        if evidence.metadata.get("authored_by_petitioner"):
            weaknesses.append(
                "Material authored BY petitioner (should use Scholarly Articles criterion)"
            )
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain circulation/readership data (Similarweb, Alexa)",
            "Include full article with translation if needed",
            "Document publication's reputation in the field",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Full article/publication copy",
            "Publication circulation data",
            "English translation if applicable",
            "Author and publication date verification",
        ]


class JudgingEvaluator(BaseCriterionEvaluator):
    """Evaluator for Judging criterion."""

    criterion_type = CriterionType.JUDGING

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_judging(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Judging activity '{evidence.title}' analyzed.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Must be asked to judge work of others.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} judging activities.",
            recommendations=["Document all peer review and judging invitations"],
            required_documents=self._required_documents(),
        )

    def _score_judging(self, evidence: Evidence) -> float:
        score = 0.0

        # Type of judging
        judging_type = evidence.metadata.get("type", "").lower()
        if "peer review" in judging_type:
            score += 30
        elif "competition" in judging_type or "grant" in judging_type:
            score += 35
        elif "thesis" in judging_type:
            score += 25
        else:
            score += 20

        # Number of reviews
        review_count = evidence.metadata.get("review_count", 0)
        if review_count > 50:
            score += 30
        elif review_count > 20:
            score += 20
        elif review_count > 5:
            score += 15
        else:
            score += 5

        # Documentation
        if evidence.attachments:
            score += 15

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        if evidence.metadata.get("review_count", 0) > 20:
            strengths.append("Substantial number of reviews completed")
        if evidence.metadata.get("invited"):
            strengths.append("Invited to judge (not self-initiated)")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("invited"):
            weaknesses.append("Invitation documentation needed")
        if not evidence.metadata.get("review_count"):
            weaknesses.append("Number of reviews not documented")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain invitation emails/letters from editors",
            "Get letter from editor confirming review activity",
            "Document number of reviews completed",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Invitation to judge/review",
            "Confirmation of completed reviews",
            "Letter from organization/editor",
            "Evidence of panel composition",
        ]


class OriginalContributionsEvaluator(BaseCriterionEvaluator):
    """Evaluator for Original Contributions criterion - often most important."""

    criterion_type = CriterionType.ORIGINAL_CONTRIBUTIONS

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_contribution(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Contribution '{evidence.title}' analyzed for originality and significance.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Must be original AND of major significance.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} original contributions.",
            recommendations=self._overall_recommendations(evaluations),
            required_documents=self._required_documents(),
        )

    def _score_contribution(self, evidence: Evidence) -> float:
        score = 0.0

        # Evidence of adoption/use by others
        if evidence.metadata.get("adopted_by_others"):
            score += 30

        # Citations
        citations = evidence.metadata.get("citations", 0)
        if citations > 500:
            score += 30
        elif citations > 100:
            score += 25
        elif citations > 20:
            score += 15
        elif citations > 0:
            score += 10

        # Patents
        if evidence.metadata.get("patented"):
            score += 20

        # Recommendation letters
        if evidence.metadata.get("recommendation_letters", 0) >= 3:
            score += 20
        elif evidence.metadata.get("recommendation_letters", 0) >= 1:
            score += 10

        # Documentation
        if evidence.attachments:
            score += 10

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        if evidence.metadata.get("adopted_by_others"):
            strengths.append("Contribution adopted by others in the field")
        if evidence.metadata.get("citations", 0) > 100:
            strengths.append("High citation count")
        if evidence.metadata.get("patented"):
            strengths.append("Patent granted")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("recommendation_letters"):
            weaknesses.append("No recommendation letters documenting significance")
        if not evidence.metadata.get("adopted_by_others"):
            weaknesses.append("No evidence of adoption by others")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain 3-5 recommendation letters from independent experts",
            "Document adoption/implementation by other organizations",
            "Gather citation counts and impact metrics",
            "Document any patents or licenses",
        ]

    def _overall_recommendations(self, evaluations: list[EvidenceEvaluation]) -> list[str]:
        return [
            "Obtain strong recommendation letters from independent experts",
            "Document impact and adoption in the field",
            "Avoid generic letters - require specific examples of significance",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Recommendation letters (3-5 from independent experts)",
            "Evidence of adoption/use by others",
            "Citation reports (Google Scholar, Scopus)",
            "Patents and licensing agreements",
            "Media coverage of contribution",
        ]


class ScholarlyArticlesEvaluator(BaseCriterionEvaluator):
    """Evaluator for Scholarly Articles criterion."""

    criterion_type = CriterionType.SCHOLARLY_ARTICLES

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_article(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Article '{evidence.title}' analyzed.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Articles in professional/major trade publications.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} scholarly articles.",
            recommendations=["Document journal impact factors and citation counts"],
            required_documents=self._required_documents(),
        )

    def _score_article(self, evidence: Evidence) -> float:
        score = 0.0

        # Venue prestige
        if evidence.metadata.get("top_venue"):
            score += 30
        elif evidence.metadata.get("indexed"):
            score += 20
        else:
            score += 10

        # Citations
        citations = evidence.metadata.get("citations", 0)
        if citations > 100:
            score += 25
        elif citations > 20:
            score += 15
        elif citations > 0:
            score += 10

        # Authorship position
        if evidence.metadata.get("first_author") or evidence.metadata.get("corresponding_author"):
            score += 15
        else:
            score += 5

        # Peer reviewed
        if evidence.metadata.get("peer_reviewed"):
            score += 15

        # Documentation
        if evidence.attachments:
            score += 10

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        if evidence.metadata.get("first_author"):
            strengths.append("First author position")
        if evidence.metadata.get("top_venue"):
            strengths.append("Published in top venue")
        if evidence.metadata.get("citations", 0) > 50:
            strengths.append("High citation count")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("indexed"):
            weaknesses.append("Journal not indexed in major databases")
        if not evidence.metadata.get("citations"):
            weaknesses.append("Citation count not documented")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Document journal impact factor",
            "Get citation count from Google Scholar/Scopus",
            "Verify journal is peer-reviewed",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Full publication copies",
            "Journal impact factor documentation",
            "Citation reports",
            "Evidence of peer review process",
        ]


class ExhibitionsEvaluator(BaseCriterionEvaluator):
    """Evaluator for Exhibitions criterion."""

    criterion_type = CriterionType.EXHIBITIONS

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_exhibition(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Exhibition '{evidence.title}' analyzed.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=["Document venue prestige and attendance"],
                    uscis_alignment="Work displayed at artistic exhibitions or showcases.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} exhibitions/showcases.",
            recommendations=["Collect exhibition catalogs and photographs"],
            required_documents=self._required_documents(),
        )

    def _score_exhibition(self, evidence: Evidence) -> float:
        score = 0.0

        # Venue prestige
        if evidence.metadata.get("international"):
            score += 35
        elif evidence.metadata.get("national"):
            score += 25
        else:
            score += 15

        # Work created by petitioner
        if evidence.metadata.get("petitioner_work"):
            score += 25

        # Documentation
        if evidence.attachments:
            score += 15

        # Media coverage
        if evidence.metadata.get("media_coverage"):
            score += 15

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        if evidence.metadata.get("international"):
            strengths.append("International exhibition")
        if evidence.metadata.get("solo"):
            strengths.append("Solo exhibition")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("petitioner_work"):
            weaknesses.append("Need to confirm petitioner's work was displayed")
        return weaknesses

    def _required_documents(self) -> list[str]:
        return [
            "Exhibition catalogs/programs",
            "Photographs from event",
            "Promotional materials",
            "Press coverage",
            "Attendance records",
        ]


class LeadingRoleEvaluator(BaseCriterionEvaluator):
    """Evaluator for Leading/Critical Role criterion."""

    criterion_type = CriterionType.LEADING_ROLE

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_role(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Role at '{evidence.source}' analyzed for leading/critical contribution.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Leading OR critical role in distinguished organization.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} roles.",
            recommendations=self._overall_recommendations(evaluations),
            required_documents=self._required_documents(),
        )

    def _score_role(self, evidence: Evidence) -> float:
        score = 0.0
        text = f"{evidence.title} {evidence.description}".lower()

        # Leading role indicators
        leading_keywords = [
            "director",
            "ceo",
            "vp",
            "chief",
            "head",
            "manager",
            "lead",
            "principal",
        ]
        if any(kw in text for kw in leading_keywords):
            score += 30
        elif evidence.metadata.get("critical_role"):
            score += 25

        # Organization distinction
        if evidence.metadata.get("fortune_500"):
            score += 25
        elif evidence.metadata.get("recognized_org"):
            score += 20
        else:
            score += 10

        # Recommendation letter
        if evidence.metadata.get("supervisor_letter"):
            score += 20

        # Documented achievements
        if evidence.metadata.get("achievements"):
            score += 15

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        text = f"{evidence.title}".lower()
        if any(kw in text for kw in ["director", "ceo", "vp", "chief"]):
            strengths.append("Clear leadership title")
        if evidence.metadata.get("supervisor_letter"):
            strengths.append("Supervisor recommendation letter")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("org_reputation"):
            weaknesses.append("Organization's distinguished reputation not documented")
        if not evidence.metadata.get("supervisor_letter"):
            weaknesses.append("Missing recommendation letter from supervisor")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain recommendation letter from supervisor explaining role significance",
            "Document organization's distinguished reputation",
            "List specific achievements and impact in the role",
        ]

    def _overall_recommendations(self, evaluations: list[EvidenceEvaluation]) -> list[str]:
        return [
            "Obtain detailed recommendation letters explaining WHY role was leading/critical",
            "Document organization reputation with external sources",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Offer letter/employment verification",
            "Organizational chart",
            "Recommendation letter from supervisor",
            "Documentation of organization's reputation",
            "Evidence of specific achievements in role",
        ]


class HighSalaryEvaluator(BaseCriterionEvaluator):
    """Evaluator for High Salary criterion."""

    criterion_type = CriterionType.HIGH_SALARY

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_salary(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis="Salary/compensation analyzed against field averages.",
                    strengths=self._identify_strengths(evidence),
                    weaknesses=self._identify_weaknesses(evidence),
                    recommendations=self._get_recommendations(evidence),
                    uscis_alignment="Must be significantly high relative to others in the field.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary="Evaluated salary data against field comparisons.",
            recommendations=["Obtain comparison data from BLS/DOL"],
            required_documents=self._required_documents(),
        )

    def _score_salary(self, evidence: Evidence) -> float:
        score = 0.0

        # Percentage above average
        pct_above = evidence.metadata.get("percentage_above_average", 0)
        if pct_above >= 100:  # 2x or more
            score += 40
        elif pct_above >= 50:  # 1.5x or more
            score += 30
        elif pct_above >= 25:
            score += 20
        else:
            score += 10

        # Comparison data quality
        if evidence.metadata.get("bls_comparison"):
            score += 20
        elif evidence.metadata.get("industry_survey"):
            score += 15

        # Documentation
        if evidence.metadata.get("tax_returns"):
            score += 15
        elif evidence.metadata.get("pay_stubs"):
            score += 10

        # Geographic match
        if evidence.metadata.get("location_matched"):
            score += 10

        return min(100.0, score)

    def _identify_strengths(self, evidence: Evidence) -> list[str]:
        strengths = []
        pct = evidence.metadata.get("percentage_above_average", 0)
        if pct >= 50:
            strengths.append(f"Salary {pct}% above field average")
        if evidence.metadata.get("bls_comparison"):
            strengths.append("Proper BLS/DOL comparison data")
        return strengths

    def _identify_weaknesses(self, evidence: Evidence) -> list[str]:
        weaknesses = []
        if not evidence.metadata.get("comparison_data"):
            weaknesses.append("No comparison data provided")
        if evidence.metadata.get("title_mismatch"):
            weaknesses.append("Job title doesn't match comparison category")
        return weaknesses

    def _get_recommendations(self, evidence: Evidence) -> list[str]:
        return [
            "Obtain BLS/DOL salary data for the same occupation and location",
            "Document job title equivalence if needed",
            "Include tax returns or W-2 forms",
        ]

    def _required_documents(self) -> list[str]:
        return [
            "Tax returns or W-2 forms",
            "Employment contract showing compensation",
            "BLS/DOL comparison data",
            "Currency conversion if applicable",
        ]


class CommercialSuccessEvaluator(BaseCriterionEvaluator):
    """Evaluator for Commercial Success criterion."""

    criterion_type = CriterionType.COMMERCIAL_SUCCESS

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_success(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis="Commercial success metrics analyzed.",
                    strengths=[],
                    weaknesses=[],
                    recommendations=["Document sales figures and compare to industry averages"],
                    uscis_alignment="Commercial success in performing arts.",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary="Evaluated commercial success metrics.",
            recommendations=["Document box office/sales compared to industry"],
            required_documents=self._required_documents(),
        )

    def _score_success(self, evidence: Evidence) -> float:
        score = 0.0

        # Sales/revenue performance
        if evidence.metadata.get("top_charts"):
            score += 40
        if evidence.metadata.get("gold_platinum"):
            score += 35
        if evidence.metadata.get("box_office_success"):
            score += 35

        # Documentation
        if evidence.metadata.get("verified_sales"):
            score += 25
        if evidence.attachments:
            score += 15

        return min(100.0, score)

    def _required_documents(self) -> list[str]:
        return [
            "Box office receipts",
            "Sales certifications (RIAA, etc.)",
            "Streaming statistics",
            "Third-party verification",
        ]


class ComparableEvidenceEvaluator(BaseCriterionEvaluator):
    """Evaluator for Comparable Evidence."""

    criterion_type = CriterionType.COMPARABLE_EVIDENCE

    async def evaluate(
        self,
        evidence_list: list[Evidence],
        case_context: dict[str, Any],
    ) -> CriterionEvaluation:
        evaluations = []
        total_score = 0.0

        for evidence in evidence_list:
            ev_score = self._score_comparable(evidence)
            total_score += ev_score

            evaluations.append(
                EvidenceEvaluation(
                    evidence_id=evidence.id,
                    criterion=self.criterion_type,
                    strength=self._calculate_strength(ev_score),
                    score=ev_score,
                    analysis=f"Comparable evidence '{evidence.title}' analyzed.",
                    strengths=[],
                    weaknesses=[],
                    recommendations=["Explain why standard criteria don't apply"],
                    uscis_alignment="Per 8 CFR 204.5(h)(4).",
                    kazarian_step1=ev_score >= 50,
                    kazarian_step2=ev_score >= 70,
                )
            )

        avg_score = total_score / len(evidence_list) if evidence_list else 0.0
        criterion_met = avg_score >= 50 and len(evidence_list) >= 1

        return CriterionEvaluation(
            criterion=self.criterion_type,
            criterion_met=criterion_met,
            overall_strength=self._calculate_strength(avg_score),
            overall_score=avg_score,
            evidence_evaluations=evaluations,
            summary=f"Evaluated {len(evidence_list)} comparable evidence items.",
            recommendations=["Document why standard criteria don't apply"],
            required_documents=self._required_documents(),
        )

    def _score_comparable(self, evidence: Evidence) -> float:
        score = 0.0

        # Explanation provided
        if evidence.metadata.get("criteria_explanation"):
            score += 30

        # Evidence of significance
        if evidence.metadata.get("significance_documented"):
            score += 35

        # Documentation
        if evidence.attachments:
            score += 20

        # Expert validation
        if evidence.metadata.get("expert_letters"):
            score += 15

        return min(100.0, score)

    def _required_documents(self) -> list[str]:
        return [
            "Explanation of why standard criteria don't apply",
            "Documentation of the achievement",
            "Letters from experts explaining significance",
            "Comparison to standard criteria equivalence",
        ]
