"""Language patterns and phrases for persuasive EB-1A petition writing.

This module provides reusable language patterns that create strong,
legally-sound arguments for EB-1A petitions.
"""

from __future__ import annotations

from typing import Any


class LanguagePatterns:
    """
    Collection of persuasive language patterns for EB-1A petitions.

    Includes:
    - Transition phrases
    - Impact statements
    - Comparative language
    - Evidence framing
    - Legal language
    """

    # Opening phrases for different evidence types
    EVIDENCE_OPENERS = {
        "award": [
            "The beneficiary received",
            "In recognition of outstanding achievement,",
            "As a testament to excellence,",
            "Demonstrating extraordinary ability,",
        ],
        "membership": [
            "The beneficiary was admitted to",
            "Following rigorous peer review,",
            "In recognition of outstanding contributions,",
            "Upon evaluation by experts,",
        ],
        "press": [
            "The beneficiary's work was featured in",
            "Major media coverage includes",
            "Widespread recognition is evidenced by",
            "Public acclaim is demonstrated through",
        ],
        "publication": [
            "The beneficiary authored",
            "Research contributions include",
            "Scholarly impact is demonstrated by",
            "Published work includes",
        ],
    }

    # Phrases emphasizing impact and significance
    IMPACT_PHRASES = [
        "has had significant impact on {field}",
        "has fundamentally advanced {field}",
        "has been widely adopted by practitioners in {field}",
        "represents a major breakthrough in {field}",
        "has influenced the direction of research in {field}",
        "has set new standards for {field}",
        "has been recognized as transformative by experts in {field}",
        "has generated substantial interest in the {field} community",
    ]

    # Comparative language for establishing extraordinary ability
    COMPARATIVE_PHRASES = [
        "significantly exceeds the accomplishments of peers",
        "places {beneficiary} among the top tier of {field} professionals",
        "demonstrates achievement beyond that typically seen in {field}",
        "surpasses the standard measures of success in {field}",
        "represents a level of accomplishment rarely achieved in {field}",
        "distinguishes {beneficiary} from the vast majority of {field} practitioners",
    ]

    # Transition phrases between sections
    TRANSITIONS = {
        "evidence_to_analysis": [
            "This evidence demonstrates that",
            "As shown by the foregoing,",
            "The significance of this achievement lies in",
            "This accomplishment is particularly noteworthy because",
        ],
        "section_to_section": [
            "In addition to the foregoing,",
            "Further demonstrating extraordinary ability,",
            "Complementing the evidence above,",
            "Building upon these achievements,",
        ],
        "to_conclusion": [
            "In sum,",
            "Taken together,",
            "The totality of evidence establishes that",
            "Based on the foregoing,",
        ],
    }

    # Legal language patterns
    LEGAL_PHRASES = {
        "regulatory_compliance": [
            "satisfies the requirements of 8 CFR § 204.5(h)(3)",
            "meets the regulatory standard set forth in",
            "fulfills the criterion under",
            "establishes eligibility under INA § 203(b)(1)(A)",
        ],
        "precedent_citation": [
            "Consistent with the precedent established in {case_name},",
            "As recognized in {case_name},",
            "Following the reasoning of {case_name},",
            "In accordance with the holding in {case_name},",
        ],
        "burden_of_proof": [
            "The preponderance of evidence establishes that",
            "The record clearly demonstrates that",
            "The evidence overwhelmingly supports that",
            "It is evident from the documentation that",
        ],
    }

    # Quality/prestige descriptors
    PRESTIGE_DESCRIPTORS = {
        "award": [
            "prestigious",
            "highly competitive",
            "internationally recognized",
            "nationally acclaimed",
            "elite",
            "distinguished",
        ],
        "organization": [
            "leading",
            "premier",
            "foremost",
            "preeminent",
            "distinguished",
            "renowned",
        ],
        "publication": [
            "peer-reviewed",
            "high-impact",
            "leading",
            "prestigious",
            "widely-read",
            "influential",
        ],
    }

    # Quantitative achievement phrases
    QUANTITATIVE_PHRASES = {
        "citations": [
            "has been cited {count} times",
            "received {count} citations from peer researchers",
            "has accumulated {count} citations in {years} years",
            "demonstrates significant influence with {count} citations",
        ],
        "publications": [
            "has authored {count} peer-reviewed articles",
            "published {count} scholarly works",
            "contributed {count} publications to the field",
        ],
        "h_index": [
            "has an h-index of {h_index}",
            "demonstrates sustained impact with an h-index of {h_index}",
            "achieved an h-index of {h_index} in {years} years",
        ],
    }

    @staticmethod
    def format_impact_statement(
        field: str, specific_impact: str, evidence: str | None = None
    ) -> str:
        """
        Create strong impact statement.

        Args:
            field: Field of expertise
            specific_impact: Specific description of impact
            evidence: Optional reference to supporting evidence

        Returns:
            Formatted impact statement

        Example:
            >>> LanguagePatterns.format_impact_statement(
            ...     "machine learning",
            ...     "developed novel attention mechanism",
            ...     "Exhibit A-1"
            ... )
            'This contribution has had significant impact on machine learning, as the developed
            novel attention mechanism has been widely adopted by practitioners. (See Exhibit A-1)'
        """
        statement = (
            f"This contribution has had significant impact on {field}, as the {specific_impact} "
            f"has been widely adopted by practitioners."
        )

        if evidence:
            statement += f" (See {evidence})"

        return statement

    @staticmethod
    def format_comparative_statement(
        beneficiary_name: str, field: str, metric: str, value: Any, context: str | None = None
    ) -> str:
        """
        Create comparative statement establishing extraordinary ability.

        Args:
            beneficiary_name: Name of beneficiary
            field: Field of expertise
            metric: What is being measured
            value: The value achieved
            context: Optional context for comparison

        Returns:
            Formatted comparative statement

        Example:
            >>> LanguagePatterns.format_comparative_statement(
            ...     "Dr. Smith",
            ...     "computer science",
            ...     "h-index",
            ...     45,
            ...     "top 5% of researchers"
            ... )
            'Dr. Smith's h-index of 45 places them among the top tier of computer science
            professionals, specifically in the top 5% of researchers.'
        """
        statement = (
            f"{beneficiary_name}'s {metric} of {value} places them among the top tier of "
            f"{field} professionals"
        )

        if context:
            statement += f", specifically {context}"

        statement += "."
        return statement

    @staticmethod
    def format_evidence_introduction(evidence_type: str, count: int, criterion_name: str) -> str:
        """
        Create evidence introduction sentence.

        Args:
            evidence_type: Type of evidence (e.g., "awards", "publications")
            count: Number of evidence items
            criterion_name: Name of criterion being satisfied

        Returns:
            Formatted introduction

        Example:
            >>> LanguagePatterns.format_evidence_introduction(
            ...     "scholarly articles",
            ...     15,
            ...     "Scholarly Articles"
            ... )
            'The beneficiary satisfies the Scholarly Articles criterion through 15 scholarly
            articles published in peer-reviewed journals and major publications.'
        """
        return (
            f"The beneficiary satisfies the {criterion_name} criterion through {count} "
            f"{evidence_type} published in peer-reviewed journals and major publications."
        )

    @staticmethod
    def format_legal_citation(case_name: str, citation: str, principle: str) -> str:
        """
        Format legal precedent citation.

        Args:
            case_name: Name of legal case
            citation: Legal citation
            principle: Legal principle established

        Returns:
            Formatted citation

        Example:
            >>> LanguagePatterns.format_legal_citation(
            ...     "Kazarian v. USCIS",
            ...     "596 F.3d 1115 (9th Cir. 2010)",
            ...     "two-step analysis for evaluating EB-1A evidence"
            ... )
            'Consistent with the precedent established in Kazarian v. USCIS, 596 F.3d 1115
            (9th Cir. 2010), which established the two-step analysis for evaluating EB-1A
            evidence, this petition demonstrates...'
        """
        return (
            f"Consistent with the precedent established in {case_name}, {citation}, which "
            f"established the {principle}, this petition demonstrates"
        )

    @staticmethod
    def format_prestige_description(
        entity_type: str, entity_name: str, indicators: list[str]
    ) -> str:
        """
        Describe prestige/distinction of an organization or publication.

        Args:
            entity_type: Type (e.g., "organization", "journal")
            entity_name: Name of entity
            indicators: List of prestige indicators

        Returns:
            Formatted description

        Example:
            >>> LanguagePatterns.format_prestige_description(
            ...     "journal",
            ...     "Nature",
            ...     ["impact factor of 69.5", "top 1% of scientific journals", "rejection rate >90%"]
            ... )
            'Nature is a prestigious journal, distinguished by: (1) impact factor of 69.5;
            (2) top 1% of scientific journals; (3) rejection rate >90%.'
        """
        indicators_formatted = "; ".join(f"({i+1}) {ind}" for i, ind in enumerate(indicators))
        return f"{entity_name} is a prestigious {entity_type}, distinguished by: {indicators_formatted}."

    @staticmethod
    def format_conclusion_statement(
        beneficiary_name: str, field: str, criteria_count: int, key_achievements: list[str]
    ) -> str:
        """
        Create strong conclusion statement.

        Args:
            beneficiary_name: Name of beneficiary
            field: Field of expertise
            criteria_count: Number of criteria satisfied
            key_achievements: List of key achievements to highlight

        Returns:
            Formatted conclusion

        Example:
            >>> LanguagePatterns.format_conclusion_statement(
            ...     "Dr. Smith",
            ...     "artificial intelligence",
            ...     5,
            ...     ["50+ publications", "h-index of 45", "3 major awards"]
            ... )
        """
        achievements_text = ", ".join(key_achievements)

        return f"""The totality of evidence establishes that {beneficiary_name} possesses extraordinary \
ability in {field}. The beneficiary has satisfied {criteria_count} of the ten regulatory criteria, \
exceeding the minimum requirement of three. Specifically, {beneficiary_name} has demonstrated: \
{achievements_text}. Based on the preponderance of evidence, {beneficiary_name} clearly qualifies \
for classification as an individual of extraordinary ability under INA § 203(b)(1)(A) and \
8 CFR § 204.5(h)(3)."""

    # Common legal cases for EB-1A citations
    PRECEDENT_CASES = {
        "kazarian": {
            "full_name": "Kazarian v. USCIS",
            "citation": "596 F.3d 1115 (9th Cir. 2010)",
            "principle": "Two-step analysis: (1) whether evidence meets regulatory criteria, "
            "(2) whether totality demonstrates extraordinary ability",
        },
        "visinscaia": {
            "full_name": "Visinscaia v. Beers",
            "citation": "4 F. Supp. 3d 126 (D.D.C. 2013)",
            "principle": "USCIS must consider evidence in totality, not isolation",
        },
        "buletini": {
            "full_name": "Buletini v. INS",
            "citation": "860 F. Supp. 1222 (E.D. Mich. 1994)",
            "principle": "Extraordinary ability requires national or international acclaim",
        },
    }

    @classmethod
    def get_precedent_citation(cls, case_key: str) -> dict[str, str]:
        """
        Get formatted precedent case information.

        Args:
            case_key: Key for precedent case (e.g., "kazarian")

        Returns:
            Dictionary with full_name, citation, and principle

        Raises:
            KeyError: If case_key not found
        """
        return cls.PRECEDENT_CASES[case_key]
