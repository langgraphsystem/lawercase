"""Specialized writer for Criterion 2.8: Leading or Critical Role."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
)
from .base_writer import BaseSectionWriter


class LeadingRoleWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.8: Leading or Critical Role.

    Regulatory requirement (8 CFR § 204.5(h)(3)(viii)):
    "Evidence that the alien has performed in a leading or critical
    role for organizations or establishments that have a distinguished
    reputation"

    Key elements to establish:
    - Leading or critical role (not routine position)
    - Organization has distinguished reputation
    - Role's impact on organization
    - Recognition of leadership
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns LEADING_ROLE criterion."""
        return EB1ACriterion.LEADING_ROLE

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate leading role section content.

        Emphasizes:
        - Leadership position and authority
        - Organization's distinguished reputation
        - Critical impact of role
        - Recognition and accomplishments
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has performed in {len(evidence)} leading or critical roles for organizations \
with distinguished reputations in {field}. These positions demonstrate {possessive} \
recognition as a leader whose expertise and judgment are essential to organizations' \
success and advancement of the field.

"""

        # Add detailed roles
        content += "**Leading and Critical Roles:**\n\n"

        for i, role in enumerate(evidence, 1):
            # Extract metadata
            meta = role.metadata
            organization = meta.get("organization", "Distinguished organization")
            position_title = meta.get("position", "Leadership position")
            org_reputation = meta.get("reputation", "Nationally/internationally recognized")
            role_type = meta.get("role_type", "Leading/Critical")
            impact = meta.get("impact", "Essential to organization's success")
            team_size = meta.get("team_size")

            # Format date and exhibit
            date_str = role.date.strftime("%B %Y") if role.date else "Present"
            exhibit_ref = f"Exhibit {role.exhibit_number}" if role.exhibit_number else "N/A"

            team_info = f"\n\n   **Team/Department Size:** {team_size}" if team_size else ""

            content += f"""{i}. **{position_title}** at **{organization}** ({date_str})

   **Organization's Reputation:** {org_reputation}

   **Role Type:** {role_type}{team_info}

   **Description:** {role.description}

   **Critical Impact:** {impact}

   **Evidence:** {exhibit_ref}

"""

        # Add role significance analysis
        content += self._generate_role_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

{possessive} performance in leading and critical roles for organizations with distinguished \
reputations satisfies the regulatory requirements of 8 CFR § 204.5(h)(3)(viii). The \
positions held, organizational reputations, and critical nature of {possessive} \
contributions demonstrate {possessive} extraordinary ability in {field}.

Per *Kazarian v. USCIS*, a leading or critical role for a distinguished organization \
establishes recognition and acclaim. {possessive} leadership positions at prestigious \
organizations, combined with the critical impact of {possessive} roles, clearly meet \
this criterion.
"""

        return content

    def _generate_role_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate role significance analysis section."""
        possessive = self._get_possessive(beneficiary)
        role_count = len(evidence)

        return f"""
**Analysis of Leadership Roles**

{possessive} leading and critical roles demonstrate extraordinary ability through:

1. **Leadership Authority:** The {role_count} positions represent senior leadership roles \
where {beneficiary.split()[-1]} exercises significant authority and decision-making power \
that shapes organizational direction and outcomes in {field}.

2. **Distinguished Organizations:** Each organization possesses a distinguished reputation \
in {field}, recognized nationally or internationally for excellence, innovation, and impact. \
These organizations seek leaders with demonstrated extraordinary ability.

3. **Critical Impact:** {possessive} roles are critical to organizational success—not \
routine positions, but roles where {possessive} expertise, judgment, and leadership are \
essential to achieving organizational missions and advancing {field}.

4. **Sustained Leadership:** The pattern of leading roles demonstrates sustained recognition \
by multiple distinguished organizations that {beneficiary.split()[-1]} possesses the \
exceptional qualifications necessary for positions of significant responsibility and impact.
"""
