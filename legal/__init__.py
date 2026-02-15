"""Legal Intelligence Package for EB-1A Processing.

Provides legal-specific enhancements:
- DocumentIntelligence: Legal document analysis and extraction
- CitationExtractor: Citation parsing and cross-referencing
- ComplianceTracker: Compliance monitoring and tracking

Usage:
    from legal import (
        DocumentIntelligence,
        CitationExtractor,
        ComplianceTracker,
    )

    # Analyze legal document
    intel = create_document_intelligence()
    analysis = await intel.analyze_document(document)

    # Extract citations
    extractor = create_citation_extractor()
    citations = await extractor.extract_citations(text)

    # Track compliance
    tracker = create_compliance_tracker()
    status = await tracker.check_compliance(case_id)
"""

from __future__ import annotations

from .citation_extractor import (
    Citation,
    CitationExtractor,
    CitationType,
    CrossReference,
    create_citation_extractor,
)
from .compliance_tracker import (
    ComplianceItem,
    ComplianceReport,
    ComplianceStatus,
    ComplianceTracker,
    RequirementType,
    create_compliance_tracker,
)
from .document_intelligence import (
    DocumentIntelligence,
    DocumentSection,
    DocumentType,
    ExtractedEntity,
    LegalAnalysis,
    create_document_intelligence,
)

__all__ = [
    "Citation",
    "CitationExtractor",
    # Citation Extraction
    "CitationType",
    "ComplianceItem",
    "ComplianceReport",
    "ComplianceStatus",
    "ComplianceTracker",
    "CrossReference",
    "DocumentIntelligence",
    "DocumentSection",
    # Document Intelligence
    "DocumentType",
    "ExtractedEntity",
    "LegalAnalysis",
    # Compliance Tracking
    "RequirementType",
    "create_citation_extractor",
    "create_compliance_tracker",
    "create_document_intelligence",
]
