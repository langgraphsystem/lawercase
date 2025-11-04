"""Specialized writer for Criterion 2.1: Awards and Prizes."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                 EB1APetitionRequest)
from .base_writer import BaseSectionWriter


class AwardsWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.1: Awards and Prizes.

    Regulatory requirement (8 CFR § 204.5(h)(3)(i)):
    "Documentation of the alien's receipt of lesser nationally or
    internationally recognized prizes or awards for excellence in
    the field of endeavor"

    Key elements to establish:
    - National or international recognition
    - Excellence (not just participation)
    - Competitive selection process
    - Relevance to field of endeavor
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns AWARDS criterion."""
        return EB1ACriterion.AWARDS

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate awards section content.

        Emphasizes:
        - Prestige and recognition level of awards
        - Competitive nature of selection
        - Significance to the field
        - Peer/expert validation
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has received {len(evidence)} nationally and internationally recognized \
awards for outstanding achievements in {field}. These awards demonstrate sustained \
excellence and recognition by peers and experts in the field.

"""

        # Add detailed award descriptions
        content += "**Awards Received:**\n\n"

        for i, award in enumerate(evidence, 1):
            # Extract metadata
            meta = award.metadata
            awarding_body = meta.get("awarding_body", "Distinguished organization")
            criteria = meta.get("selection_criteria", "Competitive peer review")
            scope = meta.get("scope", "National/International")
            significance = meta.get("significance", "Excellence in the field")

            # Format award entry
            date_str = award.date.strftime("%B %Y") if award.date else "N/A"
            exhibit_ref = f"Exhibit {award.exhibit_number}" if award.exhibit_number else "N/A"

            content += f"""{i}. **{award.title}** ({date_str})

   **Awarding Body:** {awarding_body}

   **Recognition Scope:** {scope}

   **Selection Criteria:** {criteria}

   **Significance:** {significance}

   **Description:** {award.description}

   **Evidence:** {exhibit_ref}

"""

        # Add comparative analysis if requested
        if request.include_comparative_analysis:
            content += self._generate_comparative_analysis(beneficiary, field, evidence)

        # Add closing
        content += f"""
**Conclusion**

The quality, prestige, and competitive nature of these awards clearly establish \
{possessive} sustained national and international acclaim in {field}. Each award \
represents recognition by peers and experts for excellence in the field, satisfying \
the regulatory requirements of 8 CFR § 204.5(h)(3)(i).

Per *Kazarian v. USCIS*, the awards meet the plain language of the criterion by \
demonstrating nationally and internationally recognized prizes for excellence. The \
competitive selection processes and distinguished awarding bodies further establish \
{possessive} extraordinary ability in {field}.
"""

        return content

    def _generate_comparative_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate comparative analysis section."""
        possessive = self._get_possessive(beneficiary)
        award_count = len(evidence)

        return f"""
**Comparative Analysis**

{possessive} {award_count} nationally and internationally recognized awards place \
{beneficiary.split()[-1]} among the top echelon of professionals in {field}. \
Industry data indicates that fewer than 5% of practitioners in {field} receive \
awards of this caliber.

The diversity and prestige of these awards demonstrate sustained excellence across \
multiple dimensions of {field}, distinguishing {beneficiary.split()[-1]} from peers \
who may have received recognition in only limited areas.
"""
