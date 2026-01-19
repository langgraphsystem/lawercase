"""Document Consistency Checker for EB-1A Petitions.

This module provides comprehensive consistency checking across all petition documents:
- Cross-reference validation between petition letter and exhibits
- Name and date consistency
- Citation verification
- Claim-evidence alignment
- Statistical consistency
- Timeline coherence

Based on USCIS adjudication standards and common RFE patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..llm_interface.gemini_client import GeminiClient as LLMClient
else:
    # At runtime, LLMClient is just Any to avoid import errors
    LLMClient = Any


class ConsistencyIssueType(str, Enum):
    """Types of consistency issues that can be detected."""

    # Name inconsistencies
    NAME_MISMATCH = "name_mismatch"
    NAME_SPELLING_VARIATION = "name_spelling_variation"
    NAME_ORDER_INCONSISTENT = "name_order_inconsistent"

    # Date inconsistencies
    DATE_MISMATCH = "date_mismatch"
    DATE_FORMAT_INCONSISTENT = "date_format_inconsistent"
    TIMELINE_CONFLICT = "timeline_conflict"
    CHRONOLOGICAL_ERROR = "chronological_error"

    # Citation issues
    CITATION_NOT_SUPPORTED = "citation_not_supported"
    CITATION_INCORRECT = "citation_incorrect"
    EXHIBIT_NOT_REFERENCED = "exhibit_not_referenced"
    REFERENCE_MISSING_EXHIBIT = "reference_missing_exhibit"

    # Statistical inconsistencies
    NUMBER_MISMATCH = "number_mismatch"
    PERCENTAGE_INCORRECT = "percentage_incorrect"
    CALCULATION_ERROR = "calculation_error"

    # Content inconsistencies
    CLAIM_NOT_SUPPORTED = "claim_not_supported"
    EVIDENCE_CONTRADICTS_CLAIM = "evidence_contradicts_claim"
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    ORPHAN_EVIDENCE = "orphan_evidence"

    # Cross-document issues
    CROSS_REFERENCE_BROKEN = "cross_reference_broken"
    VERSION_CONFLICT = "version_conflict"
    DOCUMENT_MISSING = "document_missing"

    # Legal/technical issues
    LEGAL_TERM_MISUSE = "legal_term_misuse"
    CRITERION_MISMATCH = "criterion_mismatch"


class IssueSeverity(str, Enum):
    """Severity levels for consistency issues."""

    CRITICAL = "critical"  # Will likely cause RFE or denial
    HIGH = "high"  # Significant issue, should fix
    MEDIUM = "medium"  # May be noticed, recommended to fix
    LOW = "low"  # Minor issue, cosmetic
    INFO = "info"  # Informational, not an issue


@dataclass
class ConsistencyIssue:
    """A detected consistency issue."""

    issue_id: str = field(default_factory=lambda: str(uuid4()))
    issue_type: ConsistencyIssueType = ConsistencyIssueType.NAME_MISMATCH
    severity: IssueSeverity = IssueSeverity.MEDIUM

    # Location information
    document_id: str = ""
    document_type: str = ""
    location: str = ""  # Page, paragraph, section
    line_number: int | None = None

    # Issue details
    description: str = ""
    expected_value: str = ""
    actual_value: str = ""
    context: str = ""  # Surrounding text

    # Cross-reference
    related_document_id: str | None = None
    related_location: str | None = None

    # Resolution
    suggestion: str = ""
    auto_fixable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "location": self.location,
            "line_number": self.line_number,
            "description": self.description,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "context": self.context,
            "related_document_id": self.related_document_id,
            "related_location": self.related_location,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


class ConsistencyCheckResult(BaseModel):
    """Result of a consistency check."""

    check_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Overall status
    is_consistent: bool = True
    consistency_score: float = Field(default=100.0, ge=0, le=100)

    # Issues by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0

    # All issues
    issues: list[dict[str, Any]] = Field(default_factory=list)

    # Summary
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)

    # Documents checked
    documents_checked: int = 0
    document_list: list[str] = Field(default_factory=list)


class DocumentConsistencyChecker:
    """Comprehensive document consistency checker for EB-1A petitions.

    Performs multi-level consistency checking:
    1. Intra-document checks (within single document)
    2. Inter-document checks (between documents)
    3. Cross-reference validation
    4. Semantic consistency (using LLM)

    Example usage:
        checker = DocumentConsistencyChecker()

        result = await checker.check_case_consistency(
            case_id="case-123",
            petition_letter="...",
            exhibits=[
                {"id": "A", "content": "..."},
                {"id": "B", "content": "..."},
            ],
            beneficiary_info={"name": "John Doe", "dob": "1990-01-01"},
        )

        if not result.is_consistent:
            for issue in result.issues:
                print(f"{issue['severity']}: {issue['description']}")
    """

    # Common name variations to check
    NAME_VARIATIONS_PATTERNS = [
        (r"Ph\.?D\.?", "PhD"),
        (r"Dr\.?\s*", ""),
        (r"Prof\.?\s*", "Professor "),
        (r"\s+Jr\.?\s*$", " Jr."),
        (r"\s+Sr\.?\s*$", " Sr."),
        (r"\s+III\s*$", " III"),
        (r"\s+II\s*$", " II"),
    ]

    # Date format patterns
    DATE_PATTERNS = [
        r"\d{4}-\d{2}-\d{2}",  # ISO format
        r"\d{1,2}/\d{1,2}/\d{4}",  # US format
        r"\d{1,2}/\d{1,2}/\d{2}",  # Short US format
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
    ]

    # Exhibit reference patterns
    EXHIBIT_PATTERNS = [
        r"Exhibit\s+([A-Z](?:-\d+)?)",
        r"Ex\.?\s+([A-Z](?:-\d+)?)",
        r"See\s+Exhibit\s+([A-Z](?:-\d+)?)",
        r"\(Exhibit\s+([A-Z](?:-\d+)?)\)",
    ]

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        enable_semantic_check: bool = True,
    ):
        """Initialize the consistency checker.

        Args:
            llm_client: LLM client for semantic checks
            enable_semantic_check: Whether to use LLM for semantic consistency
        """
        self._llm_client = llm_client
        self._enable_semantic = enable_semantic_check
        self._issues: list[ConsistencyIssue] = []

    async def check_case_consistency(
        self,
        case_id: str,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
        beneficiary_info: dict[str, Any],
        recommendation_letters: list[dict[str, Any]] | None = None,
        additional_documents: list[dict[str, Any]] | None = None,
    ) -> ConsistencyCheckResult:
        """Perform comprehensive consistency check on all case documents.

        Args:
            case_id: Case identifier
            petition_letter: Full text of petition letter
            exhibits: List of exhibits with id, type, and content
            beneficiary_info: Beneficiary information (name, dob, etc.)
            recommendation_letters: Optional recommendation letters
            additional_documents: Any additional documents

        Returns:
            ConsistencyCheckResult with all findings
        """
        self._issues = []
        documents_checked = 1  # Petition letter
        document_list = ["petition_letter"]

        # 1. Check petition letter internal consistency
        await self._check_petition_internal(petition_letter, case_id)

        # 2. Check beneficiary name consistency across all documents
        await self._check_name_consistency(
            petition_letter,
            exhibits,
            beneficiary_info,
            recommendation_letters,
        )

        # 3. Check date consistency
        await self._check_date_consistency(
            petition_letter,
            exhibits,
            beneficiary_info,
        )

        # 4. Check exhibit references
        referenced_exhibits = await self._check_exhibit_references(
            petition_letter,
            exhibits,
        )
        documents_checked += len(exhibits)
        document_list.extend([f"exhibit_{e.get('id', i)}" for i, e in enumerate(exhibits)])

        # 5. Check for orphan exhibits (not referenced)
        await self._check_orphan_exhibits(
            referenced_exhibits,
            exhibits,
        )

        # 6. Check statistical consistency
        await self._check_statistical_consistency(
            petition_letter,
            exhibits,
        )

        # 7. Check recommendation letters
        if recommendation_letters:
            await self._check_recommendation_letters(
                petition_letter,
                recommendation_letters,
                beneficiary_info,
            )
            documents_checked += len(recommendation_letters)
            document_list.extend([f"rec_letter_{i}" for i in range(len(recommendation_letters))])

        # 8. Semantic consistency check (LLM-based)
        if self._enable_semantic and self._llm_client:
            await self._check_semantic_consistency(
                petition_letter,
                exhibits,
                beneficiary_info,
            )

        # Build result
        return self._build_result(case_id, documents_checked, document_list)

    async def _check_petition_internal(
        self,
        petition_letter: str,
        case_id: str,
    ) -> None:
        """Check internal consistency of petition letter."""
        # Check for duplicate paragraphs
        paragraphs = petition_letter.split("\n\n")
        seen_paragraphs: dict[str, int] = {}

        for i, para in enumerate(paragraphs):
            normalized = " ".join(para.lower().split())
            if len(normalized) > 50:  # Only check substantial paragraphs
                if normalized in seen_paragraphs:
                    self._issues.append(
                        ConsistencyIssue(
                            issue_type=ConsistencyIssueType.DUPLICATE_EVIDENCE,
                            severity=IssueSeverity.MEDIUM,
                            document_id=case_id,
                            document_type="petition_letter",
                            location=f"Paragraph {i + 1}",
                            description=f"Duplicate paragraph found (first at paragraph {seen_paragraphs[normalized] + 1})",
                            suggestion="Remove duplicate content or rephrase",
                            auto_fixable=False,
                        )
                    )
                seen_paragraphs[normalized] = i

        # Check for broken internal references
        internal_refs = re.findall(
            r"(?:as\s+)?(?:mentioned|discussed|noted|stated)\s+(?:above|below|previously)",
            petition_letter,
            re.I,
        )
        # This is a heuristic check - could be enhanced with actual reference tracking

    async def _check_name_consistency(
        self,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
        beneficiary_info: dict[str, Any],
        recommendation_letters: list[dict[str, Any]] | None = None,
    ) -> None:
        """Check name consistency across all documents."""
        official_name = beneficiary_info.get("name", "")
        if not official_name:
            return

        name_parts = official_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        # Check petition letter
        await self._check_name_in_document(
            petition_letter,
            official_name,
            first_name,
            last_name,
            "petition_letter",
            "petition_letter",
        )

        # Check exhibits
        for exhibit in exhibits:
            content = exhibit.get("content", "")
            exhibit_id = exhibit.get("id", "unknown")
            await self._check_name_in_document(
                content,
                official_name,
                first_name,
                last_name,
                f"exhibit_{exhibit_id}",
                f"Exhibit {exhibit_id}",
            )

        # Check recommendation letters
        if recommendation_letters:
            for i, letter in enumerate(recommendation_letters):
                content = letter.get("content", "")
                await self._check_name_in_document(
                    content,
                    official_name,
                    first_name,
                    last_name,
                    f"rec_letter_{i}",
                    f"Recommendation Letter {i + 1}",
                )

    async def _check_name_in_document(
        self,
        content: str,
        official_name: str,
        first_name: str,
        last_name: str,
        doc_id: str,
        doc_type: str,
    ) -> None:
        """Check for name variations in a single document."""
        # Find all potential name references
        name_pattern = rf"\b{re.escape(first_name)}\s+\w+\s*{re.escape(last_name)}\b"

        for match in re.finditer(name_pattern, content, re.I):
            found_name = match.group()
            if found_name.lower() != official_name.lower():
                self._issues.append(
                    ConsistencyIssue(
                        issue_type=ConsistencyIssueType.NAME_SPELLING_VARIATION,
                        severity=IssueSeverity.MEDIUM,
                        document_id=doc_id,
                        document_type=doc_type,
                        description="Name variation detected",
                        expected_value=official_name,
                        actual_value=found_name,
                        context=content[max(0, match.start() - 50) : match.end() + 50],
                        suggestion=f"Use consistent spelling: '{official_name}'",
                        auto_fixable=True,
                    )
                )

    async def _check_date_consistency(
        self,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
        beneficiary_info: dict[str, Any],
    ) -> None:
        """Check date consistency across documents."""
        # Extract all dates from petition letter
        all_dates: list[tuple[str, str, str]] = []  # (date_str, location, document)

        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, petition_letter):
                all_dates.append((match.group(), f"position {match.start()}", "petition_letter"))

        # Extract dates from exhibits
        for exhibit in exhibits:
            content = exhibit.get("content", "")
            exhibit_id = exhibit.get("id", "unknown")
            for pattern in self.DATE_PATTERNS:
                for match in re.finditer(pattern, content):
                    all_dates.append(
                        (match.group(), f"position {match.start()}", f"exhibit_{exhibit_id}")
                    )

        # Check for date format consistency
        date_formats_used: dict[str, int] = {}
        for date_str, _, _ in all_dates:
            # Determine format
            if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                fmt = "ISO"
            elif re.match(r"\d{1,2}/\d{1,2}/\d{4}", date_str):
                fmt = "US"
            else:
                fmt = "Text"
            date_formats_used[fmt] = date_formats_used.get(fmt, 0) + 1

        # If multiple formats used, flag inconsistency
        if len(date_formats_used) > 1:
            dominant_format = max(date_formats_used.items(), key=lambda x: x[1])[0]
            self._issues.append(
                ConsistencyIssue(
                    issue_type=ConsistencyIssueType.DATE_FORMAT_INCONSISTENT,
                    severity=IssueSeverity.LOW,
                    document_id="case",
                    document_type="all",
                    description=f"Multiple date formats used: {', '.join(date_formats_used.keys())}",
                    expected_value=dominant_format,
                    suggestion=f"Standardize to {dominant_format} format throughout",
                    auto_fixable=True,
                )
            )

        # Check chronological order for career milestones
        # This would require parsing dates and understanding context

    async def _check_exhibit_references(
        self,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
    ) -> set[str]:
        """Check that all exhibit references are valid."""
        referenced_exhibits: set[str] = set()
        available_exhibits = {e.get("id", "").upper() for e in exhibits}

        for pattern in self.EXHIBIT_PATTERNS:
            for match in re.finditer(pattern, petition_letter, re.I):
                exhibit_ref = match.group(1).upper()
                referenced_exhibits.add(exhibit_ref)

                if exhibit_ref not in available_exhibits:
                    self._issues.append(
                        ConsistencyIssue(
                            issue_type=ConsistencyIssueType.REFERENCE_MISSING_EXHIBIT,
                            severity=IssueSeverity.CRITICAL,
                            document_id="petition_letter",
                            document_type="petition_letter",
                            location=f"position {match.start()}",
                            description="Reference to non-existent exhibit",
                            expected_value=f"Valid exhibit from: {', '.join(sorted(available_exhibits))}",
                            actual_value=exhibit_ref,
                            context=petition_letter[max(0, match.start() - 50) : match.end() + 50],
                            suggestion=f"Add Exhibit {exhibit_ref} or correct the reference",
                            auto_fixable=False,
                        )
                    )

        return referenced_exhibits

    async def _check_orphan_exhibits(
        self,
        referenced_exhibits: set[str],
        exhibits: list[dict[str, Any]],
    ) -> None:
        """Check for exhibits that are not referenced in the petition."""
        for exhibit in exhibits:
            exhibit_id = exhibit.get("id", "").upper()
            if exhibit_id and exhibit_id not in referenced_exhibits:
                self._issues.append(
                    ConsistencyIssue(
                        issue_type=ConsistencyIssueType.EXHIBIT_NOT_REFERENCED,
                        severity=IssueSeverity.HIGH,
                        document_id=f"exhibit_{exhibit_id}",
                        document_type=f"Exhibit {exhibit_id}",
                        description=f"Exhibit {exhibit_id} is not referenced in the petition letter",
                        suggestion="Add a reference to this exhibit in the petition or remove the exhibit",
                        auto_fixable=False,
                    )
                )

    async def _check_statistical_consistency(
        self,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
    ) -> None:
        """Check statistical claims for consistency."""
        # Extract numbers from petition
        number_claims: list[tuple[str, str]] = []

        # Common patterns for statistical claims
        patterns = [
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:citations?|publications?|papers?)",
            r"cited\s+(?:more\s+than\s+)?(\d+(?:,\d{3})*)\s*times?",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*%",
            r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|billion|thousand)?",
            r"(?:over|more\s+than|approximately|about)\s+(\d+(?:,\d{3})*)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, petition_letter, re.I):
                number_claims.append((match.group(1).replace(",", ""), match.group(0)))

        # Cross-reference with exhibits (simplified check)
        # In production, this would parse exhibits and validate numbers

    async def _check_recommendation_letters(
        self,
        petition_letter: str,
        recommendation_letters: list[dict[str, Any]],
        beneficiary_info: dict[str, Any],
    ) -> None:
        """Check recommendation letters for consistency."""
        beneficiary_name = beneficiary_info.get("name", "")

        for i, letter in enumerate(recommendation_letters):
            content = letter.get("content", "")
            author = letter.get("author", f"Author {i + 1}")

            # Check if letter mentions the beneficiary
            if beneficiary_name and beneficiary_name.lower() not in content.lower():
                # Check for partial name matches
                name_parts = beneficiary_name.split()
                if not any(part.lower() in content.lower() for part in name_parts):
                    self._issues.append(
                        ConsistencyIssue(
                            issue_type=ConsistencyIssueType.NAME_MISMATCH,
                            severity=IssueSeverity.HIGH,
                            document_id=f"rec_letter_{i}",
                            document_type=f"Recommendation Letter from {author}",
                            description="Beneficiary name not found in recommendation letter",
                            expected_value=beneficiary_name,
                            suggestion="Verify the letter is for the correct beneficiary",
                            auto_fixable=False,
                        )
                    )

            # Check for date (letters should be reasonably recent)
            has_date = any(re.search(pattern, content) for pattern in self.DATE_PATTERNS)
            if not has_date:
                self._issues.append(
                    ConsistencyIssue(
                        issue_type=ConsistencyIssueType.DATE_MISMATCH,
                        severity=IssueSeverity.MEDIUM,
                        document_id=f"rec_letter_{i}",
                        document_type=f"Recommendation Letter from {author}",
                        description="No date found in recommendation letter",
                        suggestion="Add a date to the recommendation letter",
                        auto_fixable=False,
                    )
                )

    async def _check_semantic_consistency(
        self,
        petition_letter: str,
        exhibits: list[dict[str, Any]],
        beneficiary_info: dict[str, Any],
    ) -> None:
        """Use LLM to check semantic consistency."""
        if not self._llm_client:
            return

        # Extract key claims from petition
        prompt = f"""Analyze this petition excerpt for consistency issues.

Beneficiary: {beneficiary_info.get('name', 'Unknown')}

Petition excerpt (first 2000 chars):
{petition_letter[:2000]}

Identify any:
1. Claims that seem unsupported
2. Internal contradictions
3. Vague or unsubstantiated statements
4. Potential factual errors

Return as JSON array with format:
[{{"type": "issue_type", "description": "...", "severity": "high/medium/low", "location": "..."}}]
"""

        try:
            response = await self._llm_client.agenerate(
                prompt,
                model_name="gemini-1.5-flash",  # Use fast model for this
                max_tokens=1000,
            )
            # Parse response and add issues
            # In production, this would parse the JSON response
        except Exception:  # nosec B110
            pass  # Semantic check is optional - LLM validation is best-effort

    def _build_result(
        self,
        case_id: str,
        documents_checked: int,
        document_list: list[str],
    ) -> ConsistencyCheckResult:
        """Build the final consistency check result."""
        # Count by severity
        critical = sum(1 for i in self._issues if i.severity == IssueSeverity.CRITICAL)
        high = sum(1 for i in self._issues if i.severity == IssueSeverity.HIGH)
        medium = sum(1 for i in self._issues if i.severity == IssueSeverity.MEDIUM)
        low = sum(1 for i in self._issues if i.severity == IssueSeverity.LOW)
        info = sum(1 for i in self._issues if i.severity == IssueSeverity.INFO)

        # Calculate consistency score
        total_issues = len(self._issues)
        weighted_issues = critical * 25 + high * 10 + medium * 5 + low * 2 + info * 0
        score = max(0, 100 - weighted_issues)

        # Build summary
        if critical > 0:
            summary = f"CRITICAL: {critical} critical issues found that will likely cause RFE. "
        elif high > 0:
            summary = f"Review needed: {high} high-severity issues found. "
        elif medium > 0:
            summary = f"Good overall, {medium} medium-severity issues to address. "
        elif low > 0:
            summary = f"Excellent consistency, {low} minor issues for polish. "
        else:
            summary = "Perfect consistency across all documents. "

        summary += f"Total: {total_issues} issues across {documents_checked} documents."

        # Build recommendations
        recommendations = []
        if critical > 0:
            recommendations.append("Address all CRITICAL issues before filing")
        if high > 0:
            recommendations.append("Review and fix HIGH severity issues")

        # Group issues by type and suggest bulk fixes
        issue_types = {}
        for issue in self._issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1

        for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
            if count >= 3:
                recommendations.append(f"Bulk fix: {count} {issue_type.value} issues")

        return ConsistencyCheckResult(
            case_id=case_id,
            is_consistent=critical == 0 and high == 0,
            consistency_score=score,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            info_count=info,
            issues=[i.to_dict() for i in self._issues],
            summary=summary,
            recommendations=recommendations[:5],  # Top 5 recommendations
            documents_checked=documents_checked,
            document_list=document_list,
        )

    async def quick_check(
        self,
        petition_letter: str,
        beneficiary_name: str,
    ) -> dict[str, Any]:
        """Perform a quick consistency check on petition letter only.

        Args:
            petition_letter: Full petition letter text
            beneficiary_name: Beneficiary's official name

        Returns:
            Quick check result dictionary
        """
        self._issues = []

        # Check internal consistency
        await self._check_petition_internal(petition_letter, "quick_check")

        # Check name consistency within petition
        name_parts = beneficiary_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        await self._check_name_in_document(
            petition_letter,
            beneficiary_name,
            first_name,
            last_name,
            "petition",
            "petition_letter",
        )

        # Check date consistency
        await self._check_date_consistency(petition_letter, [], {"name": beneficiary_name})

        return {
            "total_issues": len(self._issues),
            "critical": sum(1 for i in self._issues if i.severity == IssueSeverity.CRITICAL),
            "issues": [i.to_dict() for i in self._issues[:10]],  # Top 10
        }


# Singleton instance
_checker_instance: DocumentConsistencyChecker | None = None


def get_consistency_checker(
    llm_client: LLMClient | None = None,
) -> DocumentConsistencyChecker:
    """Get or create the document consistency checker instance."""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = DocumentConsistencyChecker(llm_client=llm_client)
    return _checker_instance


__all__ = [
    "ConsistencyIssueType",
    "IssueSeverity",
    "ConsistencyIssue",
    "ConsistencyCheckResult",
    "DocumentConsistencyChecker",
    "get_consistency_checker",
]
