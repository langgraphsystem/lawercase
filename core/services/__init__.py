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
    DocumentType,
    EB1ACriterion,
    EvidenceClassifier,
    EvidenceStrength,
)
from .rfe_analyzer import (
    RFEAnalyzer,
    RFEIssueType,
    RFEPattern,
    RFERiskAssessment,
    RiskLevel,
    SuccessPattern,
)

__all__ = [
    # Case Service
    "Case",
    "CaseListFilter",
    "CaseListResult",
    "CaseService",
    "CaseStatus",
    "CaseType",
    "CaseVersion",
    "get_case_service",
    # Document Consistency Checker
    "ConsistencyCheckResult",
    "ConsistencyIssue",
    "ConsistencyIssueType",
    "DocumentConsistencyChecker",
    "IssueSeverity",
    "get_consistency_checker",
    # Evidence Classifier
    "CaseEvidenceAssessment",
    "ClassificationResult",
    "DocumentType",
    "EB1ACriterion",
    "EvidenceClassifier",
    "EvidenceStrength",
    # RFE Analyzer
    "RFEAnalyzer",
    "RFEIssueType",
    "RFEPattern",
    "RFERiskAssessment",
    "RiskLevel",
    "SuccessPattern",
]
