"""Specialized writer for Criterion 2.3: Published Material About Beneficiary."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                 EB1APetitionRequest)
from .base_writer import BaseSectionWriter


class PressWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.3: Published Material About Beneficiary.

    Regulatory requirement (8 CFR § 204.5(h)(3)(iii)):
    "Published material about the alien in professional or major trade
    publications or other major media, relating to the alien's work in
    the field for which classification is sought"

    Key elements to establish:
    - Published in professional/major trade publications or major media
    - Material is ABOUT the beneficiary (not BY the beneficiary)
    - Relates to beneficiary's work in the field
    - Demonstrates recognition and acclaim
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns PRESS criterion."""
        return EB1ACriterion.PRESS

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate press coverage section content.

        Emphasizes:
        - Prominence of publication outlets
        - Focus on beneficiary's achievements
        - Independent third-party recognition
        - Geographic reach and circulation
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has been featured in {len(evidence)} professional publications and major \
media outlets, demonstrating widespread recognition of {possessive} contributions to \
{field}. This extensive media coverage by independent third parties establishes sustained \
national and international acclaim.

"""

        # Add detailed press coverage descriptions
        content += "**Published Material:**\n\n"

        for i, article in enumerate(evidence, 1):
            # Extract metadata
            meta = article.metadata
            publication = meta.get("publication", "Major publication")
            circulation = meta.get("circulation", "National/International")
            author = meta.get("author", "Independent journalist")
            focus = meta.get("focus", "Beneficiary's achievements and impact")

            # Format date and exhibit
            date_str = article.date.strftime("%B %Y") if article.date else "N/A"
            exhibit_ref = f"Exhibit {article.exhibit_number}" if article.exhibit_number else "N/A"

            content += f"""{i}. **{article.title}** ({date_str})

   **Publication:** {publication}

   **Circulation/Reach:** {circulation}

   **Author:** {author}

   **Focus:** {focus}

   **Description:** {article.description}

   **Evidence:** {exhibit_ref}

"""

        # Add media analysis
        content += self._generate_media_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

The extensive coverage of {possessive} work in professional publications and major media \
outlets satisfies the regulatory requirements of 8 CFR § 204.5(h)(3)(iii). These \
independent third-party publications demonstrate sustained recognition and acclaim in \
{field}.

As established in *Kazarian v. USCIS* and *Grimson v. INS*, published material about \
the beneficiary in professional or major trade publications is strong evidence of \
extraordinary ability. The volume, prominence, and geographic reach of {possessive} \
media coverage meet these standards.
"""

        return content

    def _generate_media_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate media coverage analysis section."""
        possessive = self._get_possessive(beneficiary)
        coverage_count = len(evidence)

        return f"""
**Analysis of Media Coverage**

The published material about {beneficiary} demonstrates extraordinary ability through:

1. **Volume and Consistency:** {coverage_count} independent publications provide \
sustained documentation of {possessive} acclaim and recognition in {field}.

2. **Publication Prominence:** The materials appeared in professional journals, major \
trade publications, and widely-circulated media outlets with national and international \
readership.

3. **Independent Third-Party Recognition:** Each article was written by independent \
journalists and experts, not by {beneficiary.split()[-1]}, establishing objective \
third-party validation of {possessive} achievements.

4. **Focus on Achievements:** The publications specifically focus on {possessive} \
contributions, innovations, and impact in {field}, demonstrating that {beneficiary.split()[-1]} \
is recognized as a leader in the field.
"""
