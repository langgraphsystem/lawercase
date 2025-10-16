"""Compliance checklists for EB-1A petitions.

This module provides comprehensive checklists for:
- USCIS regulatory compliance
- Evidence requirements per criterion
- Filing requirements
- Quality standards
"""

from __future__ import annotations

from dataclasses import dataclass

from ..eb1a_coordinator import EB1ACriterion


@dataclass
class ChecklistItem:
    """Single item in a compliance checklist."""

    item_id: str
    description: str
    required: bool  # True if mandatory, False if recommended
    category: str
    reference: str | None = None  # Regulatory or case law reference


class ComplianceChecklist:
    """
    Comprehensive compliance checklists for EB-1A petitions.

    Organized by:
    - Overall petition requirements
    - Per-criterion requirements
    - Filing requirements
    - Evidence standards
    """

    # Overall petition requirements
    OVERALL_REQUIREMENTS = [
        ChecklistItem(
            item_id="MIN_CRITERIA",
            description="Petition establishes at least 3 of 10 criteria",
            required=True,
            category="regulatory",
            reference="8 CFR § 204.5(h)(3)",
        ),
        ChecklistItem(
            item_id="SUSTAINED_ACCLAIM",
            description="Evidence demonstrates sustained national/international acclaim",
            required=True,
            category="regulatory",
            reference="INA § 203(b)(1)(A)",
        ),
        ChecklistItem(
            item_id="FIELD_RELEVANCE",
            description="All evidence relates to claimed field of expertise",
            required=True,
            category="regulatory",
            reference="8 CFR § 204.5(h)(3)",
        ),
        ChecklistItem(
            item_id="CONTINUED_WORK",
            description="Beneficiary intends to continue work in field in U.S.",
            required=True,
            category="intent",
            reference="8 CFR § 204.5(h)(5)",
        ),
        ChecklistItem(
            item_id="EXECUTIVE_SUMMARY",
            description="Petition includes executive summary",
            required=False,
            category="best_practice",
        ),
        ChecklistItem(
            item_id="TOTALITY_ANALYSIS",
            description="Final merits determination considers totality of evidence",
            required=True,
            category="legal",
            reference="Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)",
        ),
    ]

    # Evidence requirements by criterion
    CRITERION_REQUIREMENTS: dict[EB1ACriterion, list[ChecklistItem]] = {
        EB1ACriterion.AWARDS: [
            ChecklistItem(
                item_id="AWARD_SCOPE",
                description="Awards are nationally or internationally recognized",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(i)",
            ),
            ChecklistItem(
                item_id="AWARD_EXCELLENCE",
                description="Awards given for excellence (not just participation)",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="AWARD_DOC",
                description="Certificate, letter, or official documentation provided",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="AWARD_CRITERIA",
                description="Selection criteria and competitive nature documented",
                required=False,
                category="best_practice",
            ),
            ChecklistItem(
                item_id="AWARD_PRESTIGE",
                description="Prestige and significance of award explained",
                required=False,
                category="best_practice",
            ),
        ],
        EB1ACriterion.MEMBERSHIP: [
            ChecklistItem(
                item_id="MEMBERSHIP_OUTSTANDING",
                description="Membership requires outstanding achievements",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(ii)",
            ),
            ChecklistItem(
                item_id="MEMBERSHIP_EXPERT_JUDGED",
                description="Selection judged by recognized experts",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="MEMBERSHIP_DOC",
                description="Membership certificate or letter provided",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="MEMBERSHIP_CRITERIA",
                description="Association's admission criteria documented",
                required=False,
                category="best_practice",
            ),
        ],
        EB1ACriterion.PRESS: [
            ChecklistItem(
                item_id="PRESS_MAJOR",
                description="Published in professional or major trade publications or major media",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(iii)",
            ),
            ChecklistItem(
                item_id="PRESS_ABOUT",
                description="Material is about the beneficiary (not just mention)",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="PRESS_METADATA",
                description="Title, date, and author of material included",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(iii)",
            ),
            ChecklistItem(
                item_id="PRESS_TRANSLATION",
                description="Translation provided if not in English",
                required=True,
                category="filing",
            ),
            ChecklistItem(
                item_id="PRESS_CIRCULATION",
                description="Circulation/reach of publication documented",
                required=False,
                category="best_practice",
            ),
        ],
        EB1ACriterion.JUDGING: [
            ChecklistItem(
                item_id="JUDGING_ROLE",
                description="Evidence of participation as judge (individual or panel)",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(iv)",
            ),
            ChecklistItem(
                item_id="JUDGING_FIELD",
                description="Judging in same or allied field",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="JUDGING_DOC",
                description="Letter or documentation of judging role",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="JUDGING_EXAMPLES",
                description="Specific examples of work judged provided",
                required=False,
                category="best_practice",
            ),
        ],
        EB1ACriterion.ORIGINAL_CONTRIBUTION: [
            ChecklistItem(
                item_id="CONTRIB_ORIGINAL",
                description="Contribution is original (not derivative)",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(v)",
            ),
            ChecklistItem(
                item_id="CONTRIB_MAJOR",
                description="Contribution is of major significance",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="CONTRIB_FIELD",
                description="Contribution is in the field of endeavor",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="CONTRIB_IMPACT",
                description="Impact and adoption of contribution documented",
                required=False,
                category="best_practice",
            ),
            ChecklistItem(
                item_id="CONTRIB_LETTERS",
                description="Expert letters explaining significance provided",
                required=False,
                category="best_practice",
            ),
        ],
        EB1ACriterion.SCHOLARLY_ARTICLES: [
            ChecklistItem(
                item_id="ARTICLE_AUTHORED",
                description="Beneficiary is author (not just co-author)",
                required=True,
                category="evidence",
                reference="8 CFR § 204.5(h)(3)(vi)",
            ),
            ChecklistItem(
                item_id="ARTICLE_SCHOLARLY",
                description="Articles are scholarly (peer-reviewed preferred)",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="ARTICLE_MAJOR",
                description="Published in professional or major publications",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="ARTICLE_FIELD",
                description="Articles are in the field",
                required=True,
                category="evidence",
            ),
            ChecklistItem(
                item_id="ARTICLE_CITATIONS",
                description="Citation counts and h-index provided",
                required=False,
                category="best_practice",
            ),
        ],
    }

    # Filing requirements
    FILING_REQUIREMENTS = [
        ChecklistItem(
            item_id="FORM_I140",
            description="Form I-140 completed and signed",
            required=True,
            category="filing",
            reference="8 CFR § 204.5",
        ),
        ChecklistItem(
            item_id="FILING_FEE",
            description="Filing fee paid",
            required=True,
            category="filing",
        ),
        ChecklistItem(
            item_id="EXHIBITS_LABELED",
            description="All exhibits clearly labeled and indexed",
            required=True,
            category="filing",
        ),
        ChecklistItem(
            item_id="TRANSLATIONS",
            description="Certified translations for non-English documents",
            required=True,
            category="filing",
        ),
        ChecklistItem(
            item_id="COVER_LETTER",
            description="Cover letter summarizing petition",
            required=False,
            category="best_practice",
        ),
        ChecklistItem(
            item_id="TABLE_OF_CONTENTS",
            description="Table of contents for easy navigation",
            required=False,
            category="best_practice",
        ),
        ChecklistItem(
            item_id="COPIES",
            description="Sufficient copies provided (if required)",
            required=True,
            category="filing",
        ),
    ]

    # Evidence quality standards
    EVIDENCE_STANDARDS = [
        ChecklistItem(
            item_id="EVIDENCE_AUTHENTIC",
            description="All evidence appears authentic and verifiable",
            required=True,
            category="quality",
        ),
        ChecklistItem(
            item_id="EVIDENCE_RECENT",
            description="Evidence demonstrates recent and sustained activity",
            required=True,
            category="quality",
        ),
        ChecklistItem(
            item_id="EVIDENCE_RELEVANT",
            description="All evidence directly relates to claimed criteria",
            required=True,
            category="quality",
        ),
        ChecklistItem(
            item_id="EVIDENCE_SUFFICIENT",
            description="Sufficient quantity of evidence (15-20 exhibits recommended)",
            required=False,
            category="best_practice",
        ),
        ChecklistItem(
            item_id="EVIDENCE_DIVERSE",
            description="Evidence comes from diverse, independent sources",
            required=False,
            category="best_practice",
        ),
        ChecklistItem(
            item_id="EVIDENCE_CHRONOLOGICAL",
            description="Evidence organized chronologically or by criterion",
            required=False,
            category="best_practice",
        ),
    ]

    @classmethod
    def get_criterion_checklist(cls, criterion: EB1ACriterion) -> list[ChecklistItem]:
        """
        Get checklist for specific criterion.

        Args:
            criterion: EB-1A criterion

        Returns:
            List of checklist items for that criterion
        """
        return cls.CRITERION_REQUIREMENTS.get(criterion, [])

    @classmethod
    def get_all_required_items(cls) -> list[ChecklistItem]:
        """Get all required checklist items across all categories."""
        all_items: list[ChecklistItem] = []

        # Overall requirements
        all_items.extend([item for item in cls.OVERALL_REQUIREMENTS if item.required])

        # Criterion requirements
        for items in cls.CRITERION_REQUIREMENTS.values():
            all_items.extend([item for item in items if item.required])

        # Filing requirements
        all_items.extend([item for item in cls.FILING_REQUIREMENTS if item.required])

        # Evidence standards
        all_items.extend([item for item in cls.EVIDENCE_STANDARDS if item.required])

        return all_items

    @classmethod
    def get_recommended_items(cls) -> list[ChecklistItem]:
        """Get all recommended (not required) checklist items."""
        all_items: list[ChecklistItem] = []

        # Overall requirements
        all_items.extend([item for item in cls.OVERALL_REQUIREMENTS if not item.required])

        # Criterion requirements
        for items in cls.CRITERION_REQUIREMENTS.values():
            all_items.extend([item for item in items if not item.required])

        # Filing requirements
        all_items.extend([item for item in cls.FILING_REQUIREMENTS if not item.required])

        # Evidence standards
        all_items.extend([item for item in cls.EVIDENCE_STANDARDS if not item.required])

        return all_items
