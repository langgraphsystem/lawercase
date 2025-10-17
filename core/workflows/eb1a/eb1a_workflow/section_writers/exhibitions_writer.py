"""Specialized writer for Criterion 2.7: Artistic Exhibitions or Showcases."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
)
from .base_writer import BaseSectionWriter


class ExhibitionsWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.7: Artistic Exhibitions or Showcases.

    Regulatory requirement (8 CFR § 204.5(h)(3)(vii)):
    "Evidence of the display of the alien's work in the field at
    artistic exhibitions or showcases"

    Key elements to establish:
    - Work displayed at artistic exhibitions/showcases
    - Prestige and selectivity of venues
    - Geographic reach and audience
    - Recognition in artistic field
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns ARTISTIC_EXHIBITION criterion."""
        return EB1ACriterion.ARTISTIC_EXHIBITION

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate exhibitions section content.

        Emphasizes:
        - Prestige of exhibition venues
        - Selectivity and curatorial process
        - Geographic reach and audience size
        - Critical reception and reviews
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{possessive} work has been displayed at {len(evidence)} prestigious artistic exhibitions \
and showcases, demonstrating widespread recognition and acclaim in {field}. These venues \
represent some of the most selective and prominent platforms for artistic display, with \
national and international audiences.

"""

        # Add detailed exhibitions
        content += "**Exhibitions and Showcases:**\n\n"

        for i, exhibition in enumerate(evidence, 1):
            # Extract metadata
            meta = exhibition.metadata
            venue = meta.get("venue", "Prestigious gallery/museum")
            location = meta.get("location", "Major city")
            type_of_show = meta.get("type", "Featured exhibition")
            attendance = meta.get("attendance", "Thousands of visitors")
            selection_process = meta.get("selection_process", "Curated selection")

            # Format date and exhibit
            date_str = exhibition.date.strftime("%B %Y") if exhibition.date else "N/A"
            exhibit_ref = (
                f"Exhibit {exhibition.exhibit_number}" if exhibition.exhibit_number else "N/A"
            )

            content += f"""{i}. **{exhibition.title}** ({date_str})

   **Venue:** {venue}

   **Location:** {location}

   **Type of Show:** {type_of_show}

   **Selection Process:** {selection_process}

   **Attendance:** {attendance}

   **Description:** {exhibition.description}

   **Evidence:** {exhibit_ref}

"""

        # Add exhibitions significance analysis
        content += self._generate_exhibitions_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

The display of {possessive} work at {len(evidence)} prestigious artistic exhibitions and \
showcases satisfies the regulatory requirements of 8 CFR § 204.5(h)(3)(vii). The prestige \
of venues, selectivity of curatorial processes, and audience reach demonstrate {possessive} \
extraordinary ability in {field}.

Per *Kazarian v. USCIS*, display at artistic exhibitions establishes recognition and \
acclaim in the artistic field. {possessive} exhibition record at major venues with \
selective curatorial processes clearly meets this criterion.
"""

        return content

    def _generate_exhibitions_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate exhibitions significance analysis section."""
        possessive = self._get_possessive(beneficiary)
        exhibition_count = len(evidence)

        return f"""
**Analysis of Exhibition Significance**

{possessive} exhibition record demonstrates extraordinary ability through:

1. **Venue Prestige:** The {exhibition_count} exhibitions took place at renowned galleries, \
museums, and cultural institutions known for their selective curatorial standards and \
influence in {field}.

2. **Curatorial Selection:** Each exhibition involved a competitive selection process where \
curators and artistic directors chose {possessive} work based on artistic merit, innovation, \
and significance to the field.

3. **Geographic Reach:** The exhibitions spanned multiple cities and regions, reaching \
national and international audiences and establishing {possessive} acclaim beyond local \
or regional recognition.

4. **Professional Validation:** Display at these prestigious venues represents validation \
by expert curators, gallery directors, and institutions that {possessive} work meets the \
highest artistic standards and merits presentation to sophisticated audiences.
"""
