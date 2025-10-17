"""Supervisor Agent for orchestrating complex document generation workflows.

This module provides the SupervisorAgent class which coordinates multi-agent workflows
for generating complex legal documents like EB-1A petitions, I-140 forms, etc.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any

from ..memory.memory_manager import MemoryManager
from ..workflows.eb1a.eb1a_coordinator import (
    EB1ACriterion,
    EB1AEvidence,
    EB1APetitionRequest,
    SectionContent,
)
from ..workflows.eb1a.eb1a_workflow.evidence_researcher import EvidenceResearcher
from ..workflows.eb1a.eb1a_workflow.section_writers import (
    AuthorshipWriter,
    AwardsWriter,
    BaseSectionWriter,
    CommercialSuccessWriter,
    ContributionsWriter,
    ExhibitionsWriter,
    JudgingWriter,
    LeadingRoleWriter,
    MembershipWriter,
    PressWriter,
    SalaryWriter,
)


class DocumentType(str, Enum):
    """Supported document types for generation."""

    EB1A = "EB-1A"
    I140 = "I-140"
    EB2_NIW = "EB-2 NIW"
    O1_VISA = "O-1"


class ValidationStatus(str, Enum):
    """Document validation status."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ComplexDocumentResult:
    """Result of complex document generation process."""

    def __init__(
        self,
        document: dict[str, Any],
        validation: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ):
        self.document = document
        self.validation = validation
        self.metadata = metadata or {}
        self.generated_at = datetime.utcnow()


class SupervisorAgent:
    """
    Supervisor agent for orchestrating complex multi-agent workflows.

    This agent coordinates specialized sub-agents to generate complex legal documents
    following a structured multi-phase approach:

    1. Data Collection: Extract and validate client data
    2. Evidence Research: Use RAG to find supporting evidence
    3. Criteria Mapping: Map evidence to legal criteria
    4. Parallel Section Writing: Generate sections concurrently
    5. Assembly: Combine sections into final document
    6. Quality Check: Validate and score document quality

    Example:
        >>> supervisor = SupervisorAgent(memory_manager)
        >>> result = await supervisor.orchestrate_complex_document(
        ...     document_type=DocumentType.EB1A,
        ...     client_data={...},
        ...     user_id="user123"
        ... )
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Initialize supervisor agent.

        Args:
            memory_manager: Memory manager for RAG and context
        """
        self.memory = memory_manager or MemoryManager()

        # Initialize EB-1A workflow components
        self.evidence_researcher = EvidenceResearcher(self.memory)

        # Initialize section writers for all 10 EB-1A criteria
        self.section_writers: dict[EB1ACriterion, BaseSectionWriter] = {
            EB1ACriterion.AWARDS: AwardsWriter(self.memory),
            EB1ACriterion.MEMBERSHIP: MembershipWriter(self.memory),
            EB1ACriterion.PRESS: PressWriter(self.memory),
            EB1ACriterion.JUDGING: JudgingWriter(self.memory),
            EB1ACriterion.ORIGINAL_CONTRIBUTION: ContributionsWriter(self.memory),
            EB1ACriterion.SCHOLARLY_ARTICLES: AuthorshipWriter(self.memory),
            EB1ACriterion.ARTISTIC_EXHIBITION: ExhibitionsWriter(self.memory),
            EB1ACriterion.LEADING_ROLE: LeadingRoleWriter(self.memory),
            EB1ACriterion.HIGH_SALARY: SalaryWriter(self.memory),
            EB1ACriterion.COMMERCIAL_SUCCESS: CommercialSuccessWriter(self.memory),
        }

    async def orchestrate_complex_document(
        self,
        document_type: DocumentType,
        client_data: dict[str, Any],
        user_id: str,
    ) -> ComplexDocumentResult:
        """
        Orchestrate creation of complex legal document.

        This is the main entry point for document generation, coordinating all phases
        of the workflow.

        Args:
            document_type: Type of document to generate (EB-1A, I-140, etc.)
            client_data: Raw client data and evidence
            user_id: User identifier for tracking

        Returns:
            ComplexDocumentResult with generated document and validation

        Example:
            >>> client_data = {
            ...     "beneficiary_name": "Dr. Jane Smith",
            ...     "field": "Artificial Intelligence",
            ...     "evidence": [...],
            ... }
            >>> result = await supervisor.orchestrate_complex_document(
            ...     DocumentType.EB1A, client_data, "user123"
            ... )
        """
        print(f"🚀 Starting orchestration for {document_type.value} for user '{user_id}'...")

        # Route to appropriate workflow based on document type
        if document_type == DocumentType.EB1A:
            return await self._orchestrate_eb1a(client_data, user_id)
        if document_type == DocumentType.I140:
            return await self._orchestrate_i140(client_data, user_id)
        raise NotImplementedError(f"Document type {document_type.value} not yet implemented")

    async def _orchestrate_eb1a(
        self, client_data: dict[str, Any], user_id: str
    ) -> ComplexDocumentResult:
        """
        Orchestrate EB-1A petition generation using the complete workflow.

        Phases:
        1. Data Collection: Parse client data into EB1APetitionRequest
        2. Evidence Research: Use RAG to find additional supporting evidence
        3. Criteria Mapping: Organize evidence by EB-1A criteria
        4. Parallel Section Writing: Generate all criterion sections concurrently
        5. Assembly: Combine sections into complete petition
        6. Quality Check: Validate and score the petition

        Args:
            client_data: Client information and evidence
            user_id: User identifier

        Returns:
            ComplexDocumentResult with EB-1A petition
        """
        # Phase 1: Data Collection
        print("📋 Phase 1: Collecting and validating client data...")
        petition_request = await self._collect_eb1a_data(client_data, user_id)

        # Phase 2: Evidence Research
        print("🔍 Phase 2: Researching additional evidence using RAG...")
        additional_evidence = await self._research_eb1a_evidence(petition_request)

        # Phase 3: Criteria Mapping
        print("🗺️  Phase 3: Mapping evidence to EB-1A criteria...")
        evidence_by_criterion = await self._map_eb1a_criteria(petition_request, additional_evidence)

        # Phase 4: Parallel Section Writing
        print("✍️  Phase 4: Generating criterion sections in parallel...")
        sections = await self._generate_eb1a_sections_parallel(
            petition_request, evidence_by_criterion
        )

        # Phase 5: Assembly
        print("🔨 Phase 5: Assembling complete EB-1A petition...")
        document = await self._assemble_eb1a_document(petition_request, sections)

        # Phase 6: Quality Check
        print("✅ Phase 6: Performing quality validation...")
        validation = await self._validate_eb1a_document(document, sections)

        print("✨ EB-1A orchestration complete!")
        return ComplexDocumentResult(
            document=document,
            validation=validation,
            metadata={
                "document_type": "EB-1A",
                "beneficiary": petition_request.beneficiary_name,
                "criteria_count": len(petition_request.primary_criteria),
                "section_count": len(sections),
            },
        )

    async def _collect_eb1a_data(
        self, client_data: dict[str, Any], user_id: str
    ) -> EB1APetitionRequest:
        """
        Phase 1: Collect and validate EB-1A client data.

        Args:
            client_data: Raw client data
            user_id: User identifier

        Returns:
            Validated EB1APetitionRequest
        """
        # Extract required fields with defaults
        beneficiary_name = client_data.get("beneficiary_name", "Beneficiary")
        country_of_birth = client_data.get("country_of_birth", "Unknown")
        field_of_expertise = client_data.get("field_of_expertise", client_data.get("field", ""))
        current_position = client_data.get("current_position", "Professional")
        current_employer = client_data.get("current_employer", "")

        # Parse criteria
        primary_criteria_raw = client_data.get("primary_criteria", [])
        primary_criteria = self._parse_criteria(primary_criteria_raw)

        supporting_criteria_raw = client_data.get("supporting_criteria", [])
        supporting_criteria = self._parse_criteria(supporting_criteria_raw)

        # Parse evidence
        evidence_list = self._parse_evidence(client_data.get("evidence", []))

        # Create petition request
        petition_request = EB1APetitionRequest(
            beneficiary_name=beneficiary_name,
            country_of_birth=country_of_birth,
            field_of_expertise=field_of_expertise,
            current_position=current_position,
            current_employer=current_employer,
            primary_criteria=primary_criteria,
            supporting_criteria=supporting_criteria,
            evidence=evidence_list,
            citations_count=client_data.get("citations_count"),
            h_index=client_data.get("h_index"),
            include_comparative_analysis=client_data.get("include_comparative_analysis", True),
        )

        return petition_request

    async def _research_eb1a_evidence(self, request: EB1APetitionRequest) -> list[EB1AEvidence]:
        """
        Phase 2: Research additional evidence using RAG.

        Args:
            request: EB-1A petition request

        Returns:
            List of additional evidence found through research
        """
        additional_evidence = await self.evidence_researcher.research(request)
        print(f"   Found {len(additional_evidence)} additional evidence items")
        return additional_evidence

    async def _map_eb1a_criteria(
        self, request: EB1APetitionRequest, additional_evidence: list[EB1AEvidence]
    ) -> dict[EB1ACriterion, list[EB1AEvidence]]:
        """
        Phase 3: Map evidence to EB-1A criteria.

        Args:
            request: Petition request with existing evidence
            additional_evidence: Additional evidence from research

        Returns:
            Dictionary mapping criteria to evidence lists
        """
        # Combine all evidence
        all_evidence = request.evidence + additional_evidence

        # Group by criterion
        evidence_by_criterion: dict[EB1ACriterion, list[EB1AEvidence]] = {}

        for criterion in request.primary_criteria + request.supporting_criteria:
            criterion_evidence = [ev for ev in all_evidence if ev.criterion == criterion]
            evidence_by_criterion[criterion] = criterion_evidence
            print(f"   {criterion.value}: {len(criterion_evidence)} evidence items")

        return evidence_by_criterion

    async def _generate_eb1a_sections_parallel(
        self,
        request: EB1APetitionRequest,
        evidence_by_criterion: dict[EB1ACriterion, list[EB1AEvidence]],
    ) -> list[SectionContent]:
        """
        Phase 4: Generate criterion sections in parallel.

        Uses asyncio.gather to generate all sections concurrently for maximum speed.

        Args:
            request: Petition request
            evidence_by_criterion: Evidence grouped by criterion

        Returns:
            List of generated section content
        """
        # Create tasks for all criteria
        tasks = []
        for criterion, evidence_list in evidence_by_criterion.items():
            if criterion in self.section_writers:
                writer = self.section_writers[criterion]
                task = writer.write_section(request, evidence_list)
                tasks.append(task)

        # Execute all section writing tasks in parallel
        sections = await asyncio.gather(*tasks)

        print(f"   Generated {len(sections)} sections")
        return sections

    async def _assemble_eb1a_document(
        self, request: EB1APetitionRequest, sections: list[SectionContent]
    ) -> dict[str, Any]:
        """
        Phase 5: Assemble complete EB-1A petition document.

        Args:
            request: Petition request
            sections: Generated section content

        Returns:
            Complete assembled document
        """
        # Sort sections by criterion order
        criterion_order = {
            EB1ACriterion.AWARDS: 1,
            EB1ACriterion.MEMBERSHIP: 2,
            EB1ACriterion.PRESS: 3,
            EB1ACriterion.JUDGING: 4,
            EB1ACriterion.ORIGINAL_CONTRIBUTION: 5,
            EB1ACriterion.SCHOLARLY_ARTICLES: 6,
            EB1ACriterion.ARTISTIC_EXHIBITION: 7,
            EB1ACriterion.LEADING_ROLE: 8,
            EB1ACriterion.HIGH_SALARY: 9,
            EB1ACriterion.COMMERCIAL_SUCCESS: 10,
        }
        sorted_sections = sorted(sections, key=lambda s: criterion_order.get(s.criterion, 99))

        # Build document structure
        document = {
            "title": f"EB-1A Petition: {request.beneficiary_name}",
            "beneficiary": {
                "name": request.beneficiary_name,
                "country_of_birth": request.country_of_birth,
                "field": request.field_of_expertise,
                "position": request.current_position,
                "employer": request.current_employer,
            },
            "introduction": self._generate_introduction(request),
            "sections": [
                {
                    "criterion": section.criterion.value,
                    "title": section.title,
                    "content": section.content,
                    "evidence_references": section.evidence_references,
                    "legal_citations": section.legal_citations,
                    "word_count": section.word_count,
                    "confidence_score": section.confidence_score,
                }
                for section in sorted_sections
            ],
            "conclusion": self._generate_conclusion(request),
            "metadata": {
                "total_sections": len(sections),
                "total_word_count": sum(s.word_count for s in sections),
                "average_confidence": (
                    sum(s.confidence_score for s in sections) / len(sections) if sections else 0.0
                ),
            },
        }

        return document

    async def _validate_eb1a_document(
        self, document: dict[str, Any], sections: list[SectionContent]
    ) -> dict[str, Any]:
        """
        Phase 6: Validate EB-1A petition quality.

        Args:
            document: Assembled document
            sections: Section content for analysis

        Returns:
            Validation results
        """
        issues = []
        warnings = []

        # Check section count (need at least 3 criteria)
        if len(sections) < 3:
            issues.append(
                f"Petition must satisfy at least 3 criteria (currently has {len(sections)})"
            )

        # Check average confidence score
        avg_confidence = document["metadata"]["average_confidence"]
        if avg_confidence < 0.6:
            warnings.append(f"Average confidence score is low ({avg_confidence:.2f})")

        # Collect all suggestions from sections
        all_suggestions = []
        for section in sections:
            all_suggestions.extend(section.suggestions)

        # Determine overall status
        if issues:
            status = ValidationStatus.FAILED
        elif warnings or all_suggestions:
            status = ValidationStatus.NEEDS_REVIEW
        else:
            status = ValidationStatus.PASSED

        validation = {
            "status": status.value,
            "issues": issues,
            "warnings": warnings,
            "suggestions": all_suggestions[:10],  # Limit to top 10
            "section_scores": {
                section.criterion.value: section.confidence_score for section in sections
            },
            "overall_score": avg_confidence,
        }

        return validation

    async def _orchestrate_i140(
        self, client_data: dict[str, Any], user_id: str
    ) -> ComplexDocumentResult:
        """
        Orchestrate I-140 form generation (placeholder).

        Args:
            client_data: Client data
            user_id: User identifier

        Returns:
            ComplexDocumentResult with I-140 form
        """
        # Placeholder implementation
        print("I-140 workflow not yet implemented")
        return ComplexDocumentResult(
            document={"title": "I-140 Form", "status": "Not implemented"},
            validation={"status": "pending"},
        )

    def _parse_criteria(self, criteria_raw: list[str] | list[EB1ACriterion]) -> list[EB1ACriterion]:
        """Parse criteria from strings or enum values."""
        criteria = []
        for item in criteria_raw:
            if isinstance(item, EB1ACriterion):
                criteria.append(item)
            elif isinstance(item, str):
                # Try to match by value or name
                for criterion in EB1ACriterion:
                    if item.lower() in criterion.value.lower() or item.upper() == criterion.name:
                        criteria.append(criterion)
                        break
        return criteria

    def _parse_evidence(self, evidence_raw: list[dict[str, Any]]) -> list[EB1AEvidence]:
        """Parse evidence from raw dictionaries."""
        evidence_list = []
        for ev_dict in evidence_raw:
            try:
                # Try to create EB1AEvidence from dict
                evidence = EB1AEvidence(**ev_dict)
                evidence_list.append(evidence)
            except Exception as e:
                print(f"   Warning: Could not parse evidence: {e}")
        return evidence_list

    def _generate_introduction(self, request: EB1APetitionRequest) -> str:
        """Generate petition introduction."""
        return f"""
# Introduction

This petition is submitted on behalf of {request.beneficiary_name}, a distinguished \
professional in the field of {request.field_of_expertise}. {request.beneficiary_name} \
currently serves as {request.current_position} at {request.current_employer}.

This EB-1A petition demonstrates that {request.beneficiary_name} possesses extraordinary \
ability in {request.field_of_expertise} through sustained national and international acclaim. \
The evidence presented satisfies {len(request.primary_criteria)} of the regulatory criteria \
set forth in 8 CFR § 204.5(h)(3), clearly establishing eligibility for this classification.
"""

    def _generate_conclusion(self, request: EB1APetitionRequest) -> str:
        """Generate petition conclusion."""
        return f"""
# Conclusion

The evidence presented in this petition conclusively demonstrates that {request.beneficiary_name} \
has achieved sustained national and international acclaim in {request.field_of_expertise} and meets \
the requirements for classification as an alien of extraordinary ability under INA § 203(b)(1)(A).

The petition satisfies {len(request.primary_criteria)} regulatory criteria, exceeding the \
minimum requirement of three. Each criterion is supported by substantial documentary evidence \
and establishes {request.beneficiary_name}'s extraordinary ability through peer recognition, \
expert validation, and measurable impact on the field.

We respectfully request approval of this EB-1A petition.
"""
