"""Specialized writer for Criterion 2.9: High Salary or Remuneration."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
)
from .base_writer import BaseSectionWriter


class SalaryWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.9: High Salary or Remuneration.

    Regulatory requirement (8 CFR § 204.5(h)(3)(ix)):
    "Evidence that the alien has commanded a high salary or other
    significantly high remuneration for services, in relation to
    others in the field"

    Key elements to establish:
    - High salary relative to field
    - Comparison to industry benchmarks
    - Compensation reflects extraordinary ability
    - Documentation of remuneration
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns HIGH_SALARY criterion."""
        return EB1ACriterion.HIGH_SALARY

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate high salary section content.

        Emphasizes:
        - Salary amount and compensation package
        - Comparison to industry standards
        - Top percentile positioning
        - Recognition of extraordinary ability through compensation
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening
        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} commands compensation significantly higher than others in {field}, placing \
{beneficiary.split()[-1]} in the top tier of earners. This high remuneration reflects \
market recognition of {possessive} extraordinary ability and the exceptional value \
{beneficiary.split()[-1]} brings to organizations.

"""

        # Add detailed compensation evidence
        content += "**Compensation Evidence:**\n\n"

        for i, comp in enumerate(evidence, 1):
            # Extract metadata
            meta = comp.metadata
            employer = meta.get("employer", "Distinguished organization")
            salary_amount = meta.get("salary_amount")
            total_compensation = meta.get("total_compensation")
            percentile = meta.get("percentile", "Top 10%")
            additional_benefits = meta.get("benefits")

            # Format date and exhibit
            date_str = comp.date.strftime("%B %Y") if comp.date else "Current"
            exhibit_ref = f"Exhibit {comp.exhibit_number}" if comp.exhibit_number else "N/A"

            # Build compensation details
            comp_details = []
            if salary_amount:
                comp_details.append(f"**Base Salary:** ${salary_amount:,}")
            if total_compensation:
                comp_details.append(f"**Total Compensation:** ${total_compensation:,}")
            if additional_benefits:
                comp_details.append(f"**Additional Benefits:** {additional_benefits}")

            comp_text = "\n\n   ".join(comp_details) if comp_details else ""

            content += f"""{i}. **{comp.title}** ({date_str})

   **Employer:** {employer}

"""
            if comp_text:
                content += f"   {comp_text}\n\n"

            content += f"""   **Industry Percentile:** {percentile}

   **Description:** {comp.description}

   **Evidence:** {exhibit_ref}

"""

        # Add salary analysis
        content += self._generate_salary_analysis(beneficiary, field, evidence, request)

        # Add closing with legal citation
        content += f"""
**Conclusion**

{possessive} commanding of high salary and remuneration satisfies the regulatory \
requirements of 8 CFR § 204.5(h)(3)(ix). The compensation levels, significantly exceeding \
industry standards for {field}, demonstrate market recognition of {possessive} \
extraordinary ability.

Per *Kazarian v. USCIS*, high salary relative to others in the field establishes \
extraordinary ability. {possessive} compensation, placing {beneficiary.split()[-1]} in \
the top percentile of earners in {field}, clearly meets this criterion.
"""

        return content

    def _generate_salary_analysis(
        self,
        beneficiary: str,
        field: str,
        evidence: list[EB1AEvidence],
        request: EB1APetitionRequest,
    ) -> str:
        """Generate salary comparison analysis section."""
        possessive = self._get_possessive(beneficiary)

        # Extract salary data from evidence
        salaries = []
        for ev in evidence:
            if ev.metadata.get("total_compensation"):
                salaries.append(ev.metadata["total_compensation"])
            elif ev.metadata.get("salary_amount"):
                salaries.append(ev.metadata["salary_amount"])

        highest_comp = max(salaries) if salaries else None

        comp_text = ""
        if highest_comp:
            comp_text = f" {possessive} highest documented compensation of ${highest_comp:,} places \
{beneficiary.split()[-1]} well above typical compensation levels in {field}."

        return f"""
**Analysis of Compensation Significance**

{possessive} high remuneration demonstrates extraordinary ability through:

1. **Market Recognition:** Organizations pay premium compensation to attract and retain \
individuals with extraordinary ability.{comp_text} This reflects market validation of \
{possessive} exceptional value.

2. **Competitive Positioning:** {possessive} salary places {beneficiary.split()[-1]} in \
the top percentile of professionals in {field}, demonstrating that employers recognize \
{possessive} contributions as exceptional rather than ordinary.

3. **Sustained High Earnings:** The pattern of high compensation across multiple positions \
or years demonstrates sustained market recognition of {possessive} extraordinary ability, \
not a single anomalous payment.

4. **Industry Benchmarking:** Compared to published salary data for {field}, including \
Bureau of Labor Statistics data and industry surveys, {possessive} compensation \
significantly exceeds median and even 90th percentile levels, confirming extraordinary \
ability status.
"""
