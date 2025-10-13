"""Legal Features package for MegaAgent Pro.

This package provides comprehensive legal document processing capabilities:
- Document parsing and structure extraction
- Contract analysis and clause extraction
- Compliance checking
- Case law search and citation extraction
- Legal entity recognition
- Legal-specific RAG
"""

from __future__ import annotations

from .case_law import CaseLawSearch, CaseLawSearchResult
from .citation_extractor import CitationExtractor, CitationType, LegalCitation
from .compliance_checker import (
    ComplianceChecker,
    ComplianceResult,
    ComplianceRule,
    ComplianceStandard,
    ComplianceStatus,
)
from .contract_analyzer import (
    ClauseType,
    ContractAnalysisResult,
    ContractAnalyzer,
    ContractClause,
    RiskLevel,
)
from .document_parser import DocumentParser, DocumentSection, LegalDocument, LegalDocumentType
from .entity_recognition import LegalEntity, LegalEntityRecognizer, LegalEntityType

__all__ = [
    "CaseLawSearch",
    "CaseLawSearchResult",
    "CitationExtractor",
    "CitationType",
    "ClauseType",
    "ComplianceChecker",
    "ComplianceResult",
    "ComplianceRule",
    "ComplianceStandard",
    "ComplianceStatus",
    "ContractAnalysisResult",
    "ContractAnalyzer",
    "ContractClause",
    "DocumentParser",
    "DocumentSection",
    "LegalCitation",
    "LegalDocument",
    "LegalDocumentType",
    "LegalEntity",
    "LegalEntityRecognizer",
    "LegalEntityType",
    "RiskLevel",
]
