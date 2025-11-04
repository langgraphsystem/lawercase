"""Specialized writer for Criterion 2.2: Membership in Associations."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                 EB1APetitionRequest)
from .base_writer import BaseSectionWriter


class MembershipWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.2: Membership in Associations.

    Regulatory requirement (8 CFR § 204.5(h)(3)(ii)):
    "Documentation of the alien's membership in associations in the field
    for which classification is sought, which require outstanding achievements
    of their members, as judged by recognized national or international experts
    in their disciplines or fields"

    Key elements to establish:
    - Membership requires outstanding achievements (not just payment)
    - Judged by recognized experts
    - Selective/competitive admission
    - Field-specific relevance
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns MEMBERSHIP criterion."""
        return EB1ACriterion.MEMBERSHIP

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate membership section content.

        Emphasizes:
        - Selective nature of membership
        - Outstanding achievement requirement
        - Expert peer review process
        - Prestige of associations
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} holds {len(evidence)} prestigious memberships in professional \
associations that require demonstration of outstanding achievements as a prerequisite \
for membership. These memberships were granted based on rigorous evaluation by \
recognized experts in {field}.

"""

        # Add detailed membership descriptions
        content += "**Memberships:**\n\n"

        for i, membership in enumerate(evidence, 1):
            # Extract metadata
            meta = membership.metadata
            member_since = meta.get("member_since", "N/A")
            membership_type = meta.get("membership_type", "Fellow/Senior Member")
            criteria = meta.get(
                "selection_criteria", "Outstanding achievements reviewed by expert panel"
            )
            acceptance_rate = meta.get("acceptance_rate", "Less than 10%")
            notable_members = meta.get("notable_members", "Leading experts in the field")

            exhibit_ref = (
                f"Exhibit {membership.exhibit_number}" if membership.exhibit_number else "N/A"
            )

            content += f"""{i}. **{membership.title}**

   **Member Since:** {member_since}

   **Membership Type:** {membership_type}

   **Selection Criteria:** {criteria}

   **Acceptance Rate:** {acceptance_rate}

   **Distinguished Members Include:** {notable_members}

   **Description:** {membership.description}

   **Evidence:** {exhibit_ref}

"""

        # Add analysis
        content += self._generate_membership_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

These selective memberships, each requiring demonstration of outstanding achievements \
and expert peer review, collectively establish {possessive} extraordinary ability in \
{field}. The associations' rigorous admission standards and distinguished membership \
rosters satisfy the regulatory requirements of 8 CFR § 204.5(h)(3)(ii).

As established in *Kazarian v. USCIS* and *Visinscaia v. Beers*, membership in \
associations that require outstanding achievements, judged by recognized experts, \
is strong evidence of extraordinary ability. {possessive} memberships meet these \
standards through their competitive selection processes and expert evaluation requirements.
"""

        return content

    def _generate_membership_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate membership analysis section."""
        possessive = self._get_possessive(beneficiary)

        return f"""
**Analysis of Membership Significance**

The memberships held by {beneficiary} are distinguished by their highly selective \
nature and requirement for outstanding achievements:

1. **Expert Peer Review:** Each membership required evaluation by recognized experts \
in {field}, who assessed {possessive} contributions and achievements against \
rigorous standards.

2. **Competitive Selection:** The acceptance rates for these memberships (typically \
under 10%) place {beneficiary.split()[-1]} in an elite category of professionals \
in {field}.

3. **Sustained Achievement:** Maintaining these memberships requires continued \
demonstration of excellence, evidencing {possessive} sustained contributions to \
the field.

4. **Peer Recognition:** The membership offers from these prestigious associations \
constitute formal recognition of {possessive} extraordinary ability by leading \
experts in {field}.
"""
