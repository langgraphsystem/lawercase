"""Specialized writer for Criterion 2.10: Commercial Success in Performing Arts."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
)
from .base_writer import BaseSectionWriter


class CommercialSuccessWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.10: Commercial Success in Performing Arts.

    Regulatory requirement (8 CFR § 204.5(h)(3)(x)):
    "Evidence of commercial successes in the performing arts, as shown
    by box office receipts or record, cassette, compact disk, or video sales"

    Key elements to establish:
    - Commercial success (quantifiable sales/revenue)
    - In performing arts field
    - National or international reach
    - Demonstrates market recognition and popularity
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns COMMERCIAL_SUCCESS criterion."""
        return EB1ACriterion.COMMERCIAL_SUCCESS

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate commercial success section content.

        Emphasizes:
        - Quantifiable sales and revenue
        - Market reach and audience size
        - Industry rankings and charts
        - Sustained commercial performance
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has achieved significant commercial success in {field}, as demonstrated by \
{len(evidence)} documented achievements in sales, box office performance, and market \
recognition. These commercial successes reflect widespread public acclaim and market \
validation of {possessive} extraordinary ability.

"""

        # Add detailed commercial successes
        content += "**Commercial Successes:**\n\n"

        for i, success in enumerate(evidence, 1):
            # Extract metadata
            meta = success.metadata
            success_type = meta.get("type", "Sales/Box Office")
            revenue = meta.get("revenue")
            units_sold = meta.get("units_sold")
            chart_position = meta.get("chart_position")
            awards = meta.get("awards")
            market_reach = meta.get("market_reach", "National/International")

            # Format date and exhibit
            date_str = success.date.strftime("%B %Y") if success.date else "N/A"
            exhibit_ref = f"Exhibit {success.exhibit_number}" if success.exhibit_number else "N/A"

            # Build commercial metrics
            metrics = []
            if revenue:
                metrics.append(f"**Revenue:** ${revenue:,}")
            if units_sold:
                metrics.append(f"**Units Sold:** {units_sold:,}")
            if chart_position:
                metrics.append(f"**Chart Performance:** {chart_position}")
            if awards:
                metrics.append(f"**Commercial Awards:** {awards}")

            metrics_text = "\n\n   ".join(metrics) if metrics else ""

            content += f"""{i}. **{success.title}** ({date_str})

   **Type:** {success_type}

   **Market Reach:** {market_reach}

"""
            if metrics_text:
                content += f"   {metrics_text}\n\n"

            content += f"""   **Description:** {success.description}

   **Evidence:** {exhibit_ref}

"""

        # Add commercial success analysis
        content += self._generate_commercial_analysis(beneficiary, field, evidence)

        # Add closing with legal citation
        content += f"""
**Conclusion**

{possessive} commercial successes satisfy the regulatory requirements of 8 CFR § 204.5(h)(3)(x). \
The documented sales, box office receipts, and market performance demonstrate sustained \
commercial success and widespread public recognition of {possessive} extraordinary ability \
in {field}.

Per *Kazarian v. USCIS*, commercial success in the performing arts, evidenced by sales \
and revenue data, establishes extraordinary ability. {possessive} commercial achievements, \
spanning multiple successful releases or performances, clearly meet this criterion.
"""

        return content

    def _generate_commercial_analysis(
        self, beneficiary: str, field: str, evidence: list[EB1AEvidence]
    ) -> str:
        """Generate commercial success analysis section."""
        possessive = self._get_possessive(beneficiary)
        success_count = len(evidence)

        # Calculate total revenue if available
        total_revenue = sum(
            ev.metadata.get("revenue", 0) for ev in evidence if ev.metadata.get("revenue")
        )
        total_units = sum(
            ev.metadata.get("units_sold", 0) for ev in evidence if ev.metadata.get("units_sold")
        )

        financial_text = ""
        if total_revenue:
            financial_text = (
                f" {possessive} work has generated ${total_revenue:,} in documented revenue"
            )
            if total_units:
                financial_text += f", with {total_units:,} units sold"
            financial_text += ", demonstrating exceptional market appeal."

        return f"""
**Analysis of Commercial Success**

{possessive} commercial achievements demonstrate extraordinary ability through:

1. **Market Validation:** The {success_count} commercial successes represent validation \
by the marketplace and public that {possessive} work in {field} has exceptional appeal \
and quality.{financial_text}

2. **Sustained Performance:** Multiple commercial successes demonstrate sustained ability \
to create work that achieves significant market penetration, not a single anomalous hit.

3. **Industry Recognition:** Commercial success at this level places {beneficiary.split()[-1]} \
among the top tier of performing artists in {field}, as the market rewards only those \
with extraordinary ability to connect with and move audiences.

4. **National/International Reach:** The geographic scope of {possessive} commercial \
success demonstrates acclaim beyond local or regional levels, establishing national and \
international recognition through market performance.
"""
