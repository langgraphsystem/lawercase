"""Services module for business logic.

Provides service layer implementations:
- Case management
- Document management
- Workflow orchestration
- Evidence classification (EB-1A)
- RFE pattern analysis
- Document consistency checking
"""

from __future__ import annotations

from .case_service import (
    Case,
    CaseListFilter,
    CaseListResult,
    CaseService,
    CaseStatus,
    CaseType,
    CaseVersion,
    get_case_service,
)
from .document_consistency_checker import (
    ConsistencyCheckResult,
    ConsistencyIssue,
    ConsistencyIssueType,
    DocumentConsistencyChecker,
    IssueSeverity,
    get_consistency_checker,
)
from .evidence_classifier import (
    CaseEvidenceAssessment,
    ClassificationResult,
    CriterionEvidence,
    DocumentType,
    EB1ACriterion,
    EvidenceClassifier,
    RFERiskLevel,
)
from .rfe_analyzer import (
    RFEAnalyzer,
    RFECategory,
    RFEIssueType,
    RFEPattern,
    RFERiskAssessment,
    SuccessPattern,
)

__all__ = [
    # Case Service
    "Case",
    # Evidence Classifier
    "CaseEvidenceAssessment",
    "CaseListFilter",
    "CaseListResult",
    "CaseService",
    "CaseStatus",
    "CaseType",
    "CaseVersion",
    "ClassificationResult",
    # Document Consistency Checker
    "ConsistencyCheckResult",
    "ConsistencyIssue",
    "ConsistencyIssueType",
    "CriterionEvidence",
    "DocumentConsistencyChecker",
    "DocumentType",
    "EB1ACriterion",
    "EvidenceClassifier",
    "IssueSeverity",
    # RFE Analyzer
    "RFEAnalyzer",
    "RFECategory",
    "RFEIssueType",
    "RFEPattern",
    "RFERiskAssessment",
    "RFERiskLevel",
    "SuccessPattern",
    "get_case_service",
    "get_consistency_checker",
]
