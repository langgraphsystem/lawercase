"""EB-1A Criteria Skill Module.

Comprehensive skill for evaluating and documenting all 10 EB-1A extraordinary ability criteria
plus comparable evidence. Works with intake, researcher, writer, and reviewer agents.

Prompts are defined directly in criterion classes (criteria/*.py).
"""

from __future__ import annotations

from .criteria import CRITERION_CLASSES, SUPPORTING_DOC_CLASSES
from .criteria_skill import (
    CriteriaAnalysisResult,
    CriterionType,
    EB1ACriteriaSkill,
    Evidence,
    EvidenceEvaluation,
    EvidenceStrength,
)
from .evaluators import (
    AwardsEvaluator,
    CommercialSuccessEvaluator,
    ComparableEvidenceEvaluator,
    ExhibitionsEvaluator,
    HighSalaryEvaluator,
    JudgingEvaluator,
    LeadingRoleEvaluator,
    MembershipEvaluator,
    OriginalContributionsEvaluator,
    PublishedMaterialEvaluator,
    ScholarlyArticlesEvaluator,
)
from .rag_examples import (
    EB1A_EXAMPLES_NAMESPACE,
    enrich_prompt_with_examples,
    format_examples_for_prompt,
    get_examples_for_criterion,
    get_relevant_examples,
)

__all__ = [
    "CRITERION_CLASSES",
    "EB1A_EXAMPLES_NAMESPACE",
    "SUPPORTING_DOC_CLASSES",
    # Core classes
    "AwardsEvaluator",
    "CommercialSuccessEvaluator",
    "ComparableEvidenceEvaluator",
    "CriteriaAnalysisResult",
    "CriterionType",
    "EB1ACriteriaSkill",
    "Evidence",
    "EvidenceEvaluation",
    "EvidenceStrength",
    "ExhibitionsEvaluator",
    "HighSalaryEvaluator",
    "JudgingEvaluator",
    "LeadingRoleEvaluator",
    "MembershipEvaluator",
    "OriginalContributionsEvaluator",
    "PublishedMaterialEvaluator",
    "ScholarlyArticlesEvaluator",
    # RAG functions
    "enrich_prompt_with_examples",
    "format_examples_for_prompt",
    "get_examples_for_criterion",
    "get_relevant_examples",
]
