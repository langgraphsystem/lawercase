"""Specialized writer for Criterion 2.6: Authorship of Scholarly Articles."""

from __future__ import annotations

from typing import Any

from .....memory.memory_manager import MemoryManager
from ...eb1a_coordinator import (EB1ACriterion, EB1AEvidence,
                                 EB1APetitionRequest)
from .base_writer import BaseSectionWriter


class AuthorshipWriter(BaseSectionWriter):
    """
    Writer for EB-1A Criterion 2.6: Authorship of Scholarly Articles.

    Regulatory requirement (8 CFR § 204.5(h)(3)(vi)):
    "Evidence of the alien's authorship of scholarly articles in the
    field, in professional or major trade publications or other major media"

    Key elements to establish:
    - Scholarly articles (peer-reviewed, technical depth)
    - In professional/major trade publications
    - Demonstrates expertise and contribution
    - Citation impact and influence
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        super().__init__(memory_manager)

    def get_criterion(self) -> EB1ACriterion:
        """Returns SCHOLARLY_ARTICLES criterion."""
        return EB1ACriterion.SCHOLARLY_ARTICLES

    async def generate_content(
        self,
        request: EB1APetitionRequest,
        evidence: list[EB1AEvidence],
        template: Any,
    ) -> str:
        """
        Generate scholarly articles section content.

        Emphasizes:
        - Publication quality and prestige
        - Peer review process
        - Citation impact
        - Contribution to field knowledge
        """
        beneficiary = request.beneficiary_name
        field = request.field_of_expertise
        possessive = self._get_possessive(beneficiary)

        # Build opening with citation metrics
        citation_text = ""
        if request.citations_count:
            citation_text = f" These publications have been cited {request.citations_count:,} times by \
researchers worldwide"
            if request.h_index:
                citation_text += f", with an h-index of {request.h_index}"
            citation_text += ", demonstrating significant impact and influence."

        content = f"""**{template.criterion_name}**

{template.regulatory_text}

{beneficiary} has authored {len(evidence)} scholarly articles published in prestigious \
peer-reviewed journals and professional publications in {field}.{citation_text} This body of \
work establishes {possessive} expertise and sustained contributions to advancing knowledge \
in the field.

"""

        # Add detailed publications
        content += "**Scholarly Publications:**\n\n"

        for i, article in enumerate(evidence, 1):
            # Extract metadata
            meta = article.metadata
            journal = meta.get("journal", "Peer-reviewed journal")
            impact_factor = meta.get("impact_factor")
            citations = meta.get("citations")
            authors = meta.get("authors", beneficiary)
            peer_reviewed = meta.get("peer_reviewed", True)

            # Format date and exhibit
            date_str = article.date.strftime("%B %Y") if article.date else "N/A"
            exhibit_ref = f"Exhibit {article.exhibit_number}" if article.exhibit_number else "N/A"

            # Build citation info
            citation_info = f"**Citations:** {citations:,}" if citations else ""
            impact_info = f"**Impact Factor:** {impact_factor}" if impact_factor else ""

            content += f"""{i}. **{article.title}** ({date_str})

   **Authors:** {authors}

   **Published In:** {journal}

   **Peer Reviewed:** {"Yes" if peer_reviewed else "No"}

"""
            if impact_info:
                content += f"   {impact_info}\n\n"
            if citation_info:
                content += f"   {citation_info}\n\n"

            content += f"""   **Description:** {article.description}

   **Evidence:** {exhibit_ref}

"""

        # Add publications impact analysis
        content += self._generate_publications_analysis(beneficiary, field, evidence, request)

        # Add closing with legal citation
        content += f"""
**Conclusion**

{possessive} authorship of {len(evidence)} scholarly articles in peer-reviewed professional \
publications satisfies the regulatory requirements of 8 CFR § 204.5(h)(3)(vi). The quality \
of publications, citation impact, and peer review process demonstrate {possessive} \
extraordinary ability in {field}.

Per *Matter of Price* and *Kazarian v. USCIS*, scholarly articles in professional \
publications establish expertise and contribution to the field. {possessive} publication \
record, particularly the significant citation impact, clearly meets this criterion.
"""

        return content

    def _generate_publications_analysis(
        self,
        beneficiary: str,
        field: str,
        evidence: list[EB1AEvidence],
        request: EB1APetitionRequest,
    ) -> str:
        """Generate publications impact analysis section."""
        possessive = self._get_possessive(beneficiary)
        article_count = len(evidence)

        # Calculate total citations from evidence if available
        total_evidence_citations = sum(
            ev.metadata.get("citations", 0) for ev in evidence if ev.metadata.get("citations")
        )

        citation_analysis = ""
        if request.citations_count or total_evidence_citations:
            citations = request.citations_count or total_evidence_citations
            citation_analysis = f"""

**Citation Impact Analysis:**

{possessive} work has been cited {citations:,} times, placing {beneficiary.split()[-1]} \
among the most influential researchers in {field}. This citation count reflects the \
significance and impact of {possessive} contributions, as other researchers build upon \
{possessive} work in their own investigations."""

            if request.h_index:
                citation_analysis += f"""

The h-index of {request.h_index} indicates that {beneficiary.split()[-1]} has published \
{request.h_index} papers that have each been cited at least {request.h_index} times, \
demonstrating both productivity and sustained impact."""

        return f"""
**Analysis of Scholarly Publications**

{possessive} scholarly publications demonstrate extraordinary ability through:

1. **Publication Quality:** The {article_count} articles appeared in peer-reviewed \
professional journals, ensuring rigorous evaluation by expert reviewers in {field}.

2. **Knowledge Contribution:** Each publication contributes original research, analysis, \
or insights that advance the collective knowledge base in {field}.

3. **Peer Recognition:** Publication in competitive peer-reviewed venues demonstrates \
recognition by expert editors and reviewers that {possessive} work meets the highest \
standards of scholarship.{citation_analysis}

4. **Sustained Scholarship:** The body of publications demonstrates sustained engagement \
in advancing {field} through rigorous scholarly work, not isolated or occasional contributions.
"""
