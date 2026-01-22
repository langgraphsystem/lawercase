"""
EB-1A Criteria Module.

Contains individual criterion classes for all 10 EB-1A criteria
plus comparable evidence and supporting documentation sections,
each with full USCIS prompts and evaluation/writing/validation methods.
"""

from __future__ import annotations

from .awards import AwardsCriterion
from .commercial_success import CommercialSuccessCriterion
from .comparable_evidence import ComparableEvidenceCriterion
from .exhibitions import ExhibitionsCriterion
from .future_work import FutureWorkDocumentation
from .high_salary import HighSalaryCriterion
from .judging import JudgingCriterion
from .leading_role import LeadingRoleCriterion
from .membership import MembershipCriterion
from .national_benefit import NationalBenefitDocumentation
from .original_contributions import OriginalContributionsCriterion
from .published_material import PublishedMaterialCriterion
from .scholarly_articles import ScholarlyArticlesCriterion

__all__ = [
    # 10 EB-1A Criteria
    "AwardsCriterion",
    "MembershipCriterion",
    "PublishedMaterialCriterion",
    "JudgingCriterion",
    "OriginalContributionsCriterion",
    "ScholarlyArticlesCriterion",
    "ExhibitionsCriterion",
    "LeadingRoleCriterion",
    "HighSalaryCriterion",
    "CommercialSuccessCriterion",
    # Comparable Evidence
    "ComparableEvidenceCriterion",
    # Supporting Documentation
    "FutureWorkDocumentation",
    "NationalBenefitDocumentation",
]

# Mapping from CriterionType to Criterion class
CRITERION_CLASSES = {
    # 10 EB-1A Criteria (8 CFR 204.5(h)(3))
    "awards": AwardsCriterion,
    "membership": MembershipCriterion,
    "published_material": PublishedMaterialCriterion,
    "judging": JudgingCriterion,
    "original_contributions": OriginalContributionsCriterion,
    "scholarly_articles": ScholarlyArticlesCriterion,
    "exhibitions": ExhibitionsCriterion,
    "leading_role": LeadingRoleCriterion,
    "high_salary": HighSalaryCriterion,
    "commercial_success": CommercialSuccessCriterion,
    # Comparable Evidence (8 CFR 204.5(h)(4))
    "comparable_evidence": ComparableEvidenceCriterion,
}

# Supporting Documentation Classes (not criteria, but required sections)
SUPPORTING_DOC_CLASSES = {
    "future_work": FutureWorkDocumentation,
    "national_benefit": NationalBenefitDocumentation,
}


def get_criterion_class(criterion_type: str):
    """
    Get the criterion class for a given type.

    Args:
        criterion_type: One of the 10 criteria types or 'comparable_evidence'

    Returns:
        The corresponding criterion class

    Raises:
        ValueError: If criterion_type is not recognized
    """
    criterion_class = CRITERION_CLASSES.get(criterion_type.lower())
    if criterion_class is None:
        valid_types = ", ".join(CRITERION_CLASSES.keys())
        raise ValueError(
            f"Unknown criterion type: {criterion_type}. " f"Valid types are: {valid_types}"
        )
    return criterion_class


def create_criterion(criterion_type: str, llm_router=None, memory_manager=None):
    """
    Create an instance of a criterion class.

    Args:
        criterion_type: One of the 10 criteria types or 'comparable_evidence'
        llm_router: Optional LLM router for API calls
        memory_manager: Optional memory manager for context

    Returns:
        An instance of the corresponding criterion class
    """
    criterion_class = get_criterion_class(criterion_type)
    return criterion_class(llm_router=llm_router, memory_manager=memory_manager)


def get_supporting_doc_class(doc_type: str):
    """
    Get the supporting documentation class for a given type.

    Args:
        doc_type: One of 'future_work' or 'national_benefit'

    Returns:
        The corresponding documentation class

    Raises:
        ValueError: If doc_type is not recognized
    """
    doc_class = SUPPORTING_DOC_CLASSES.get(doc_type.lower())
    if doc_class is None:
        valid_types = ", ".join(SUPPORTING_DOC_CLASSES.keys())
        raise ValueError(
            f"Unknown supporting doc type: {doc_type}. " f"Valid types are: {valid_types}"
        )
    return doc_class


def create_supporting_doc(doc_type: str, llm_router=None, memory_manager=None):
    """
    Create an instance of a supporting documentation class.

    Args:
        doc_type: One of 'future_work' or 'national_benefit'
        llm_router: Optional LLM router for API calls
        memory_manager: Optional memory manager for context

    Returns:
        An instance of the corresponding documentation class
    """
    doc_class = get_supporting_doc_class(doc_type)
    return doc_class(llm_router=llm_router, memory_manager=memory_manager)
