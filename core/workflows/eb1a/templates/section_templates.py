"""Section templates for EB-1A petition criteria (2.1-2.10).

This module provides structured templates for each of the 10 EB-1A criteria,
including opening statements, evidence presentation formats, and conclusion patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CriterionTemplate:
    """Template for a specific EB-1A criterion section."""

    criterion_code: str  # e.g., "2.1"
    criterion_name: str
    regulatory_text: str  # Exact text from 8 CFR § 204.5(h)(3)
    opening_template: str
    evidence_intro: str
    evidence_format: str
    closing_template: str
    key_elements: list[str]  # What must be demonstrated
    common_pitfalls: list[str]  # What to avoid


class SectionTemplates:
    """
    Library of templates for all 10 EB-1A criteria.

    Each template includes:
    - Regulatory language
    - Opening/closing patterns
    - Evidence presentation formats
    - Key elements to emphasize
    - Common mistakes to avoid
    """

    AWARDS = CriterionTemplate(
        criterion_code="2.1",
        criterion_name="Awards and Prizes",
        regulatory_text=(
            "Documentation of the alien's receipt of lesser nationally or internationally "
            "recognized prizes or awards for excellence in the field of endeavor"
        ),
        opening_template=(
            "{beneficiary_name} has received {award_count} nationally and internationally "
            "recognized {award_type} for outstanding achievements in {field}. These awards "
            "demonstrate sustained excellence and recognition by peers and experts."
        ),
        evidence_intro=("The following awards establish {possessive} extraordinary ability:"),
        evidence_format=(
            "**{award_name}** ({award_date})\n"
            "- Awarded by: {awarding_body}\n"
            "- Selection criteria: {criteria}\n"
            "- Recognition scope: {scope}\n"
            "- Significance: {significance}\n"
            "- Evidence: Exhibit {exhibit_number}"
        ),
        closing_template=(
            "The quality, prestige, and competitive nature of these awards clearly establish "
            "{beneficiary_name}'s sustained national and international acclaim in {field}."
        ),
        key_elements=[
            "National or international scope",
            "Excellence in the field (not just participation)",
            "Recognition by peers/experts",
            "Competitive selection process",
            "Significance to the field",
        ],
        common_pitfalls=[
            "Don't include purely local awards",
            "Avoid awards that are not competitive",
            "Don't claim awards for participation only",
            "Avoid awards in unrelated fields",
        ],
    )

    MEMBERSHIP = CriterionTemplate(
        criterion_code="2.2",
        criterion_name="Membership in Associations",
        regulatory_text=(
            "Documentation of the alien's membership in associations in the field for which "
            "classification is sought, which require outstanding achievements of their members, "
            "as judged by recognized national or international experts in their disciplines or fields"
        ),
        opening_template=(
            "{beneficiary_name} holds {membership_count} prestigious memberships in professional "
            "associations that require outstanding achievements as a prerequisite for membership. "
            "These memberships were granted based on rigorous evaluation by recognized experts."
        ),
        evidence_intro=("The following memberships demonstrate {possessive} standing in {field}:"),
        evidence_format=(
            "**{association_name}**\n"
            "- Member since: {member_since}\n"
            "- Membership type: {membership_type}\n"
            "- Selection criteria: {selection_criteria}\n"
            "- Acceptance rate: {acceptance_rate}\n"
            "- Notable members: {notable_members}\n"
            "- Evidence: Exhibit {exhibit_number}"
        ),
        closing_template=(
            "These selective memberships, each requiring demonstration of outstanding achievements "
            "and expert peer review, collectively establish {beneficiary_name}'s extraordinary "
            "ability in {field}."
        ),
        key_elements=[
            "Membership requires outstanding achievements (not just payment)",
            "Judged by recognized experts",
            "Selective/competitive admission",
            "National or international scope",
            "Field-specific relevance",
        ],
        common_pitfalls=[
            "Don't include memberships that only require fee payment",
            "Avoid non-selective professional associations",
            "Don't claim student memberships",
            "Avoid memberships in unrelated fields",
        ],
    )

    PRESS = CriterionTemplate(
        criterion_code="2.3",
        criterion_name="Published Material About the Beneficiary",
        regulatory_text=(
            "Published material about the alien in professional or major trade publications or "
            "other major media, relating to the alien's work in the field for which classification "
            "is sought. Such evidence shall include the title, date, and author of the material, "
            "and any necessary translation"
        ),
        opening_template=(
            "{beneficiary_name}'s work has been featured in {press_count} major {media_type} "
            "publications, demonstrating widespread recognition and public interest in "
            "{possessive} contributions to {field}."
        ),
        evidence_intro=(
            "The following publications document {possessive} recognition in major media:"
        ),
        evidence_format=(
            '**"{article_title}"**\n'
            "- Publication: {publication_name}\n"
            "- Date: {publication_date}\n"
            "- Author: {author}\n"
            "- Circulation/Reach: {circulation}\n"
            "- Topic: {topic_summary}\n"
            "- Evidence: Exhibit {exhibit_number}"
        ),
        closing_template=(
            "The breadth and quality of media coverage establishes that {beneficiary_name}'s work "
            "has garnered significant public attention and recognition from major media outlets."
        ),
        key_elements=[
            "Major trade publications or major media",
            "About the beneficiary (not just mentioning)",
            "Related to work in the field",
            "Professional or mainstream media",
            "Demonstrable circulation/reach",
        ],
        common_pitfalls=[
            "Don't include self-published material",
            "Avoid minor blogs or personal websites",
            "Don't claim articles where beneficiary is just mentioned in passing",
            "Avoid non-major publications without circulation data",
        ],
    )

    JUDGING = CriterionTemplate(
        criterion_code="2.4",
        criterion_name="Participation as a Judge",
        regulatory_text=(
            "Evidence of the alien's participation, either individually or on a panel, as a judge "
            "of the work of others in the same or an allied field of specification for which "
            "classification is sought"
        ),
        opening_template=(
            "{beneficiary_name} has served as a judge of the work of others in {field} on "
            "{judging_count} occasions, demonstrating recognition of {possessive} expertise "
            "by peers and organizations."
        ),
        evidence_intro=(
            "The following judging activities establish {possessive} standing as an expert:"
        ),
        evidence_format=(
            "**{judging_activity}**\n"
            "- Organization: {organization}\n"
            "- Date: {date}\n"
            "- Role: {role}\n"
            "- Scope: {scope}\n"
            "- Number reviewed: {number_reviewed}\n"
            "- Selection basis: {selection_basis}\n"
            "- Evidence: Exhibit {exhibit_number}"
        ),
        closing_template=(
            "These judging activities demonstrate that {beneficiary_name} is recognized as an "
            "expert capable of evaluating the work of others in {field}."
        ),
        key_elements=[
            "Judging of others' work (not just collaboration)",
            "In the same or allied field",
            "Individual or panel participation",
            "Peer review, grant review, competition judging, etc.",
            "Documentation of selection as judge",
        ],
        common_pitfalls=[
            "Don't confuse collaboration with judging",
            "Avoid informal peer reviews",
            "Don't claim activities in unrelated fields",
            "Avoid judging activities without documentation",
        ],
    )

    ORIGINAL_CONTRIBUTION = CriterionTemplate(
        criterion_code="2.5",
        criterion_name="Original Contributions of Major Significance",
        regulatory_text=(
            "Evidence of the alien's original scientific, scholarly, artistic, athletic, or "
            "business-related contributions of major significance in the field"
        ),
        opening_template=(
            "{beneficiary_name} has made {contribution_count} original contributions of major "
            "significance to {field}. These contributions have fundamentally advanced the field "
            "and have been widely adopted and cited by peers."
        ),
        evidence_intro=("The following contributions demonstrate {possessive} impact on {field}:"),
        evidence_format=(
            "**{contribution_title}**\n"
            "- Description: {description}\n"
            "- Innovation: {innovation}\n"
            "- Impact: {impact}\n"
            "- Adoption: {adoption}\n"
            "- Recognition: {recognition}\n"
            "- Supporting evidence: Exhibits {exhibit_numbers}\n"
        ),
        closing_template=(
            "These original contributions have had demonstrable major significance in {field}, "
            "as evidenced by widespread adoption, recognition, and impact on the field's development."
        ),
        key_elements=[
            "Original (not derivative)",
            "Major significance (not incremental)",
            "In the field of endeavor",
            "Demonstrable impact",
            "Recognition by peers",
        ],
        common_pitfalls=[
            "Don't claim routine work as major contributions",
            "Avoid contributions without demonstrated impact",
            "Don't conflate publications with contributions",
            "Avoid claims without third-party validation",
        ],
    )

    SCHOLARLY_ARTICLES = CriterionTemplate(
        criterion_code="2.6",
        criterion_name="Scholarly Articles",
        regulatory_text=(
            "Evidence of the alien's authorship of scholarly articles in the field, in "
            "professional or major trade publications or other major media"
        ),
        opening_template=(
            "{beneficiary_name} has authored {article_count} scholarly articles published in "
            "peer-reviewed journals and major trade publications. These articles have received "
            "{citation_count} citations and have an h-index of {h_index}."
        ),
        evidence_intro=(
            "The following scholarly articles demonstrate {possessive} research contributions:"
        ),
        evidence_format=(
            '**"{article_title}"**\n'
            "- Authors: {authors}\n"
            "- Journal: {journal}\n"
            "- Date: {publication_date}\n"
            "- Impact Factor: {impact_factor}\n"
            "- Citations: {citation_count}\n"
            "- Evidence: Exhibit {exhibit_number}\n"
        ),
        closing_template=(
            "The quantity, quality, and impact of these scholarly publications establish "
            "{beneficiary_name} as a leading researcher in {field}."
        ),
        key_elements=[
            "Scholarly (peer-reviewed or equivalent)",
            "Authored by beneficiary",
            "In the field",
            "Professional/major publications",
            "Demonstrable impact (citations)",
        ],
        common_pitfalls=[
            "Don't include non-peer-reviewed articles without justification",
            "Avoid counting abstracts as full articles",
            "Don't claim articles in unrelated fields",
            "Avoid unpublished or self-published works",
        ],
    )

    ARTISTIC_EXHIBITION = CriterionTemplate(
        criterion_code="2.7",
        criterion_name="Artistic Exhibitions or Showcases",
        regulatory_text=(
            "Evidence of the display of the alien's work in the field at artistic exhibitions "
            "or showcases"
        ),
        opening_template=(
            "{beneficiary_name}'s work has been displayed at {exhibition_count} major exhibitions "
            "and showcases, demonstrating widespread recognition of {possessive} artistic "
            "contributions."
        ),
        evidence_intro=("The following exhibitions showcase {possessive} work:"),
        evidence_format=(
            "**{exhibition_name}**\n"
            "- Venue: {venue}\n"
            "- Location: {location}\n"
            "- Date: {date}\n"
            "- Type: {type}\n"
            "- Selection process: {selection}\n"
            "- Attendance: {attendance}\n"
            "- Evidence: Exhibit {exhibit_number}\n"
        ),
        closing_template=(
            "These exhibitions at prestigious venues demonstrate the recognition of "
            "{beneficiary_name}'s artistic work by curators, critics, and the public."
        ),
        key_elements=[
            "Artistic exhibitions or showcases",
            "Display of beneficiary's work",
            "In the field",
            "Major or prestigious venues",
            "Evidence of selection/invitation",
        ],
        common_pitfalls=[
            "Don't include minor or local exhibitions only",
            "Avoid exhibitions without selective process",
            "Don't claim group shows without individual recognition",
            "Avoid exhibitions in unrelated fields",
        ],
    )

    LEADING_ROLE = CriterionTemplate(
        criterion_code="2.8",
        criterion_name="Leading or Critical Role",
        regulatory_text=(
            "Evidence that the alien has performed in a leading or critical role for organizations "
            "or establishments that have a distinguished reputation"
        ),
        opening_template=(
            "{beneficiary_name} has served in {role_count} leading and critical roles for "
            "organizations with distinguished reputations in {field}."
        ),
        evidence_intro=("The following positions demonstrate {possessive} leadership:"),
        evidence_format=(
            "**{position_title}** at **{organization}**\n"
            "- Period: {start_date} - {end_date}\n"
            "- Organization reputation: {reputation}\n"
            "- Role: {role_description}\n"
            "- Responsibilities: {responsibilities}\n"
            "- Impact: {impact}\n"
            "- Evidence: Exhibit {exhibit_number}\n"
        ),
        closing_template=(
            "These leadership positions in distinguished organizations demonstrate that "
            "{beneficiary_name} plays a critical role in advancing {field}."
        ),
        key_elements=[
            "Leading or critical role",
            "For organizations/establishments",
            "With distinguished reputation",
            "Demonstrable impact",
            "Documentation of role and reputation",
        ],
        common_pitfalls=[
            "Don't claim routine employment as critical role",
            "Avoid organizations without distinguished reputation",
            "Don't conflate junior positions with leadership",
            "Avoid positions in unrelated organizations",
        ],
    )

    HIGH_SALARY = CriterionTemplate(
        criterion_code="2.9",
        criterion_name="High Salary or Remuneration",
        regulatory_text=(
            "Evidence that the alien has commanded a high salary or other significantly high "
            "remuneration for services, in relation to others in the field"
        ),
        opening_template=(
            "{beneficiary_name} commands a salary in the top {percentile}th percentile of "
            "{field} professionals, demonstrating {possessive} extraordinary value to employers."
        ),
        evidence_intro=("The following evidence establishes {possessive} high remuneration:"),
        evidence_format=(
            "**Compensation Package**\n"
            "- Base salary: ${salary:,}\n"
            "- Total compensation: ${total_comp:,}\n"
            "- Comparison: {comparison_data}\n"
            "- Industry percentile: {percentile}th\n"
            "- Source: {source}\n"
            "- Evidence: Exhibit {exhibit_number}\n"
        ),
        closing_template=(
            "This high remuneration, significantly exceeding industry averages, demonstrates the "
            "extraordinary value that employers place on {beneficiary_name}'s services."
        ),
        key_elements=[
            "High salary/remuneration",
            "Relative to others in field",
            "Documented comparison",
            "For services (employment)",
            "Significantly above average",
        ],
        common_pitfalls=[
            "Don't claim high salary without comparative data",
            "Avoid comparisons to wrong peer group",
            "Don't include non-salary benefits without documentation",
            "Avoid claiming high salary for entry-level positions",
        ],
    )

    COMMERCIAL_SUCCESS = CriterionTemplate(
        criterion_code="2.10",
        criterion_name="Commercial Successes in Performing Arts",
        regulatory_text=(
            "Evidence of commercial successes in the performing arts, as shown by box office "
            "receipts or record, cassette, compact disk, or video sales"
        ),
        opening_template=(
            "{beneficiary_name} has achieved significant commercial success in {performing_art}, "
            "with ${revenue:,} in box office receipts and sales."
        ),
        evidence_intro=("The following demonstrates {possessive} commercial success:"),
        evidence_format=(
            "**{work_title}**\n"
            "- Type: {type}\n"
            "- Release date: {release_date}\n"
            "- Box office/Sales: ${revenue:,}\n"
            "- Rankings: {rankings}\n"
            "- Awards: {awards}\n"
            "- Evidence: Exhibit {exhibit_number}\n"
        ),
        closing_template=(
            "These commercial successes demonstrate widespread public recognition and appreciation "
            "of {beneficiary_name}'s work in {performing_art}."
        ),
        key_elements=[
            "Commercial success",
            "In performing arts",
            "Measurable (box office, sales)",
            "Documented revenue/sales",
            "Significant success (not marginal)",
        ],
        common_pitfalls=[
            "Only applies to performing arts",
            "Don't claim success without revenue documentation",
            "Avoid minor or local performances",
            "Don't conflate critical acclaim with commercial success",
        ],
    )

    @classmethod
    def get_template(cls, criterion_code: str) -> CriterionTemplate:
        """
        Get template for a specific criterion.

        Args:
            criterion_code: Criterion code (e.g., "2.1", "2.5")

        Returns:
            CriterionTemplate for the specified criterion

        Raises:
            ValueError: If criterion_code is invalid
        """
        template_map = {
            "2.1": cls.AWARDS,
            "2.2": cls.MEMBERSHIP,
            "2.3": cls.PRESS,
            "2.4": cls.JUDGING,
            "2.5": cls.ORIGINAL_CONTRIBUTION,
            "2.6": cls.SCHOLARLY_ARTICLES,
            "2.7": cls.ARTISTIC_EXHIBITION,
            "2.8": cls.LEADING_ROLE,
            "2.9": cls.HIGH_SALARY,
            "2.10": cls.COMMERCIAL_SUCCESS,
        }

        if criterion_code not in template_map:
            raise ValueError(f"Invalid criterion code: {criterion_code}")

        return template_map[criterion_code]

    @classmethod
    def format_section(
        cls,
        criterion_code: str,
        beneficiary_name: str,
        field: str,
        evidence_list: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """
        Format a complete section using template.

        Args:
            criterion_code: Criterion code
            beneficiary_name: Full name of beneficiary
            field: Field of expertise
            evidence_list: List of evidence dictionaries
            **kwargs: Additional template variables

        Returns:
            Formatted section text
        """
        template = cls.get_template(criterion_code)

        # Prepare template variables
        possessive = beneficiary_name.split()[-1] + "'s"
        variables = {
            "beneficiary_name": beneficiary_name,
            "possessive": possessive,
            "field": field,
            **kwargs,
        }

        # Format opening
        section = template.opening_template.format(**variables) + "\n\n"

        # Format evidence intro
        section += template.evidence_intro.format(**variables) + "\n\n"

        # Format each evidence item
        for evidence in evidence_list:
            section += template.evidence_format.format(**evidence) + "\n\n"

        # Format closing
        section += template.closing_template.format(**variables)

        return section
