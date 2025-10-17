"""Specialized writer for Criterion 2.5: Original Contributions of Major Significance."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
)
from .base_writer import BaseSectionWriter


class ContributionsWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.5: Original Contributions of Major Significance.

    Regulatory requirement (8 CFR § 204.5(h)(3)(v)):
    "Evidence of the alien's original scientific, scholarly, artistic,
    athletic, or business-related contributions of major significance
    to the field"

    Key elements to establish:
    - Original (not derivative or incremental)
    - Major significance (not minor improvements)
    - Impact on the field
    - Recognition by experts
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns ORIGINAL_CONTRIBUTION criterion."""
        return EB1ACriterion.ORIGINAL_CONTRIBUTION

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate original contributions section content.

        Emphasizes:
        - Originality and innovation
        - Major significance and impact
        - Expert recognition
        - Field advancement
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has made {len(evidence)} original contributions of major significance to \
{field}, fundamentally advancing the state of the art and generating widespread recognition \
from experts in the field. These contributions have had demonstrable impact on research, \
practice, and policy within {field}.

"""

        # Add detailed contributions
        content += "**Original Contributions:**\n\n"

        for i, contribution in enumerate(evidence, 1):
            # Extract metadata
            meta = contribution.metadata
            contribution_type = meta.get("type", "Research innovation")
            impact = meta.get("impact", "Significant advancement in the field")
            recognition = meta.get("recognition", "Cited by leading experts")
            adoption = meta.get("adoption", "Widely adopted by practitioners")

            # Format date and exhibit
            date_str = contribution.date.strftime("%B %Y") if contribution.date else "N/A"
            exhibit_ref = (
                f"Exhibit {contribution.exhibit_number}" if contribution.exhibit_number else "N/A"
            )

            content += f"""{i}. **{contribution.title}** ({date_str})

   **Type of Contribution:** {contribution_type}

   **Description:** {contribution.description}

   **Impact on Field:** {impact}

   **Recognition:** {recognition}

   **Adoption/Implementation:** {adoption}

   **Evidence:** {exhibit_ref}

"""

        # Add contributions impact analysis
        content += self._generate_contributions_analysis(beneficiary, field, evidence, request)

        # Add closing with legal citation
        content += f"""
**Conclusion**

These original contributions of major significance satisfy the regulatory requirements of \
8 CFR § 204.5(h)(3)(v). The contributions' originality, impact, and recognition by experts \
demonstrate {possessive} extraordinary ability in {field}.

As established in *Visinscaia v. Beers* and *Kazarian v. USCIS*, original contributions \
must be of major significance as evidenced by expert recognition and field impact. \
{possessive} contributions meet and exceed these standards through their demonstrated \
influence on research, practice, and advancement of {field}.
"""

        return content

    def _generate_contributions_analysis(
        self,
        beneficiary: str,
        field: str,
        evidence: list[EB1AEvidence],
        request: EB1APetitionRequest,
    ) -> str:
        """Generate contributions impact analysis section."""
        possessive = self._get_possessive(beneficiary)
        contribution_count = len(evidence)

        # Add citation metrics if available
        citation_info = ""
        if request.citations_count:
            citation_info = f"\n\n**Citation Impact:** {possessive} contributions have been \
cited {request.citations_count:,} times by researchers worldwide"
            if request.h_index:
                citation_info += f", with an h-index of {request.h_index}"
            citation_info += ", demonstrating sustained influence and recognition."

        return f"""
**Analysis of Contribution Significance**

{possessive} contributions demonstrate extraordinary ability through:

1. **Originality:** Each contribution represents novel work that advanced {field} beyond \
the existing state of the art. These are not incremental improvements but fundamental \
innovations that opened new research directions.

2. **Major Significance:** The contributions have had measurable impact on {field}, as \
evidenced by adoption by other researchers, integration into industry practice, and \
influence on standards and policy.{citation_info}

3. **Expert Recognition:** Leading experts in {field} have recognized the significance of \
{possessive} work through citations, commentary, adoption of methodologies, and invitations \
to speak and collaborate.

4. **Sustained Impact:** The {contribution_count} contributions span multiple areas within \
{field}, demonstrating sustained production of original work of major significance rather \
than a single isolated achievement.
"""
