"""Specialized writer for Criterion 2.4: Participation as Judge of Others' Work."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                 EB1APetitionRequest)
from .base_writer import BaseSectionWriter


class JudgingWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.4: Participation as Judge.

    Regulatory requirement (8 CFR § 204.5(h)(3)(iv)):
    "Evidence of the alien's participation, either individually or on a
    panel, as a judge of the work of others in the same or an allied
    field of specialization for which classification is sought"

    Key elements to establish:
    - Judging work of others in same/allied field
    - Individual or panel participation
    - Demonstrates peer recognition
    - Shows expert status in field
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns JUDGING criterion."""
        return EB1ACriterion.JUDGING

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate judging participation section content.

        Emphasizes:
        - Expert peer review role
        - Selectivity of judging invitations
        - Impact on field advancement
        - Recognition by peers
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has served as a judge and peer reviewer of others' work in {field} on \
{len(evidence)} occasions, demonstrating recognition by peers as an expert qualified to \
evaluate contributions to the field. This judging role reflects {possessive} standing as a \
leader whose expertise is sought by professional organizations and institutions.

"""

        # Add detailed judging activities
        content += "**Judging Activities:**\n\n"

        for i, activity in enumerate(evidence, 1):
            # Extract metadata
            meta = activity.metadata
            organization = meta.get("organization", "Professional organization")
            role = meta.get("role", "Peer reviewer/Judge")
            scope = meta.get("scope", "National/International")
            submissions_reviewed = meta.get("submissions_reviewed", "Multiple")

            # Format date and exhibit
            date_str = activity.date.strftime("%B %Y") if activity.date else "Ongoing"
            exhibit_ref = f"Exhibit {activity.exhibit_number}" if activity.exhibit_number else "N/A"

            content += f"""{i}. **{activity.title}** ({date_str})

   **Organization:** {organization}

   **Role:** {role}

   **Scope:** {scope}

   **Submissions Reviewed:** {submissions_reviewed}

   **Description:** {activity.description}

   **Evidence:** {exhibit_ref}

"""

        # Add judging significance analysis
        content += self._generate_judging_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

{possessive} extensive participation as a judge of others' work satisfies the regulatory \
requirements of 8 CFR § 204.5(h)(3)(iv). The invitations to serve in judging and peer \
review roles demonstrate that {beneficiary.split()[-1]} is recognized by peers and \
institutions as an expert qualified to evaluate contributions to {field}.

Per *Kazarian v. USCIS*, participation as a judge of others' work establishes peer \
recognition and expert status. {possessive} judging activities, spanning multiple \
prestigious organizations and venues, clearly meet this criterion.
"""

        return content

    def _generate_judging_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate judging significance analysis section."""
        possessive = self._get_possessive(beneficiary)
        activity_count = len(evidence)

        return f"""
**Analysis of Judging Participation**

{possessive} participation as a judge demonstrates extraordinary ability through:

1. **Peer Recognition:** The {activity_count} invitations to serve as a judge reflect \
recognition by professional organizations and peers that {beneficiary.split()[-1]} possesses \
the expertise and standing necessary to evaluate others' contributions to {field}.

2. **Expert Evaluation Role:** Judging requires deep knowledge of the field's standards, \
current state of the art, and ability to assess the significance of others' work—qualities \
possessed only by recognized experts.

3. **Gate-Keeping Function:** As a judge, {beneficiary.split()[-1]} helps determine which \
contributions advance the field, a responsibility entrusted only to those with demonstrated \
extraordinary ability.

4. **Sustained Engagement:** The ongoing nature and diversity of judging roles demonstrate \
sustained recognition of {possessive} expertise and leadership in {field}.
"""
