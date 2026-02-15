"""Compliance Tracker for EB-1A Case Management.

Provides compliance monitoring and tracking:
- Requirement tracking
- Deadline management
- Compliance status monitoring
- Gap analysis
- Report generation
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RequirementType(str, Enum):
    """Types of compliance requirements."""

    DOCUMENTATION = "documentation"  # Required documents
    EVIDENCE = "evidence"  # Evidence for criteria
    FORM = "form"  # Forms to complete
    DEADLINE = "deadline"  # Time-based requirements
    PROCEDURAL = "procedural"  # Procedural requirements
    REGULATORY = "regulatory"  # Regulatory compliance


class ComplianceStatus(str, Enum):
    """Status of compliance items."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WAIVED = "waived"
    EXPIRED = "expired"


class Priority(str, Enum):
    """Priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplianceItem:
    """A compliance requirement item."""

    id: str
    name: str
    description: str
    requirement_type: RequirementType
    status: ComplianceStatus = ComplianceStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    deadline: datetime | None = None
    assigned_to: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    completion_percentage: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description[:200],
            "requirement_type": self.requirement_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completion_percentage": self.completion_percentage,
            "evidence_count": len(self.evidence_ids),
        }

    @property
    def is_overdue(self) -> bool:
        """Check if item is past deadline."""
        if not self.deadline:
            return False
        if self.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WAIVED]:
            return False
        return datetime.now(UTC) > self.deadline

    @property
    def days_until_deadline(self) -> int | None:
        """Get days until deadline."""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.now(UTC)
        return delta.days


@dataclass
class ComplianceReport:
    """Compliance status report."""

    case_id: str
    report_date: datetime = field(default_factory=datetime.utcnow)
    total_items: int = 0
    compliant_items: int = 0
    non_compliant_items: int = 0
    in_progress_items: int = 0
    overdue_items: int = 0
    compliance_percentage: float = 0.0
    items_by_type: dict[str, int] = field(default_factory=dict)
    items_by_priority: dict[str, int] = field(default_factory=dict)
    upcoming_deadlines: list[dict[str, Any]] = field(default_factory=list)
    critical_gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "report_date": self.report_date.isoformat(),
            "total_items": self.total_items,
            "compliant_items": self.compliant_items,
            "non_compliant_items": self.non_compliant_items,
            "in_progress_items": self.in_progress_items,
            "overdue_items": self.overdue_items,
            "compliance_percentage": self.compliance_percentage,
            "items_by_type": self.items_by_type,
            "critical_gaps": self.critical_gaps[:5],
            "recommendations": self.recommendations[:5],
        }


# EB-1A Standard Requirements
EB1A_REQUIREMENTS = [
    {
        "id": "req_form_i140",
        "name": "Form I-140",
        "description": "Immigrant Petition for Alien Workers",
        "type": RequirementType.FORM,
        "priority": Priority.CRITICAL,
    },
    {
        "id": "req_evidence_criteria",
        "name": "Evidence of 3+ Criteria",
        "description": "Documentation supporting at least 3 of 10 EB-1A criteria",
        "type": RequirementType.EVIDENCE,
        "priority": Priority.CRITICAL,
    },
    {
        "id": "req_sustained_acclaim",
        "name": "Sustained National/International Acclaim",
        "description": "Evidence of sustained acclaim in field of expertise",
        "type": RequirementType.EVIDENCE,
        "priority": Priority.CRITICAL,
    },
    {
        "id": "req_petition_letter",
        "name": "Petition Letter",
        "description": "Comprehensive petition letter explaining qualifications",
        "type": RequirementType.DOCUMENTATION,
        "priority": Priority.HIGH,
    },
    {
        "id": "req_recommendation_letters",
        "name": "Recommendation Letters",
        "description": "Expert recommendation letters (typically 5-8)",
        "type": RequirementType.DOCUMENTATION,
        "priority": Priority.HIGH,
    },
    {
        "id": "req_cv_resume",
        "name": "CV/Resume",
        "description": "Comprehensive curriculum vitae",
        "type": RequirementType.DOCUMENTATION,
        "priority": Priority.MEDIUM,
    },
    {
        "id": "req_passport_copy",
        "name": "Passport Copy",
        "description": "Copy of valid passport",
        "type": RequirementType.DOCUMENTATION,
        "priority": Priority.HIGH,
    },
    {
        "id": "req_filing_fee",
        "name": "Filing Fee",
        "description": "I-140 filing fee payment",
        "type": RequirementType.PROCEDURAL,
        "priority": Priority.CRITICAL,
    },
]

# EB-1A Criteria Requirements
EB1A_CRITERIA_REQUIREMENTS = {
    "awards": {
        "name": "Awards/Prizes Criterion",
        "description": "Evidence of nationally/internationally recognized awards",
        "evidence_examples": [
            "Award certificates",
            "Nomination letters",
            "Media coverage of award",
            "Description of award significance",
        ],
    },
    "membership": {
        "name": "Membership Criterion",
        "description": "Evidence of membership in associations requiring outstanding achievement",
        "evidence_examples": [
            "Membership certificate",
            "Association bylaws showing requirements",
            "Letter from association",
        ],
    },
    "press": {
        "name": "Published Material Criterion",
        "description": "Evidence of published material about the applicant",
        "evidence_examples": [
            "Articles/interviews about applicant",
            "Media circulation data",
            "Translations if needed",
        ],
    },
    "judging": {
        "name": "Judging Criterion",
        "description": "Evidence of judging the work of others",
        "evidence_examples": [
            "Invitation letters to judge",
            "Panel participation evidence",
            "Peer review records",
        ],
    },
    "contributions": {
        "name": "Original Contributions Criterion",
        "description": "Evidence of original contributions of major significance",
        "evidence_examples": [
            "Patents",
            "Expert letters explaining significance",
            "Evidence of field adoption",
        ],
    },
    "authorship": {
        "name": "Scholarly Articles Criterion",
        "description": "Evidence of authorship of scholarly articles",
        "evidence_examples": [
            "Published articles",
            "Citation counts",
            "Journal impact factors",
        ],
    },
    "exhibitions": {
        "name": "Artistic Exhibitions Criterion",
        "description": "Evidence of artistic exhibitions or showcases",
        "evidence_examples": [
            "Exhibition catalogs",
            "Gallery/museum letters",
            "Photos of displayed work",
        ],
    },
    "leading_role": {
        "name": "Leading/Critical Role Criterion",
        "description": "Evidence of leading or critical role",
        "evidence_examples": [
            "Organizational charts",
            "Letters from organization",
            "Evidence of organization's distinction",
        ],
    },
    "high_salary": {
        "name": "High Salary Criterion",
        "description": "Evidence of high salary or remuneration",
        "evidence_examples": [
            "Pay stubs/tax returns",
            "Wage surveys for comparison",
            "Employment contract",
        ],
    },
    "commercial_success": {
        "name": "Commercial Success Criterion",
        "description": "Evidence of commercial success in performing arts",
        "evidence_examples": [
            "Box office records",
            "Sales figures",
            "Industry rankings",
        ],
    },
}


class ComplianceTracker:
    """Track and manage compliance for EB-1A cases."""

    def __init__(
        self,
        llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        storage_callback: Callable[[str, dict], Coroutine[Any, Any, None]] | None = None,
    ):
        self.llm_call = llm_call
        self.storage_callback = storage_callback
        self._items: dict[str, dict[str, ComplianceItem]] = {}  # case_id -> items

    def initialize_case(self, case_id: str) -> list[ComplianceItem]:
        """Initialize compliance tracking for a new case."""
        items = []
        self._items[case_id] = {}

        # Add standard requirements
        for req in EB1A_REQUIREMENTS:
            item = ComplianceItem(
                id=req["id"],
                name=req["name"],
                description=req["description"],
                requirement_type=req["type"],
                priority=req["priority"],
            )
            items.append(item)
            self._items[case_id][item.id] = item

        return items

    def add_criterion_requirements(
        self,
        case_id: str,
        criteria: list[str],
    ) -> list[ComplianceItem]:
        """Add requirements for selected EB-1A criteria."""
        if case_id not in self._items:
            self.initialize_case(case_id)

        items = []
        for criterion in criteria:
            if criterion in EB1A_CRITERIA_REQUIREMENTS:
                req = EB1A_CRITERIA_REQUIREMENTS[criterion]
                item = ComplianceItem(
                    id=f"req_{criterion}",
                    name=req["name"],
                    description=req["description"],
                    requirement_type=RequirementType.EVIDENCE,
                    priority=Priority.HIGH,
                    metadata={"evidence_examples": req["evidence_examples"]},
                )
                items.append(item)
                self._items[case_id][item.id] = item

        return items

    def update_item(
        self,
        case_id: str,
        item_id: str,
        status: ComplianceStatus | None = None,
        completion_percentage: float | None = None,
        notes: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> ComplianceItem | None:
        """Update a compliance item."""
        if case_id not in self._items:
            return None
        if item_id not in self._items[case_id]:
            return None

        item = self._items[case_id][item_id]

        if status is not None:
            item.status = status
            if status == ComplianceStatus.COMPLIANT:
                item.completed_at = datetime.now(UTC)
                item.completion_percentage = 100.0

        if completion_percentage is not None:
            item.completion_percentage = min(max(completion_percentage, 0), 100)

        if notes:
            item.notes.append(f"[{datetime.now(UTC).isoformat()}] {notes}")

        if evidence_ids:
            item.evidence_ids.extend(evidence_ids)

        item.updated_at = datetime.now(UTC)

        return item

    def set_deadline(
        self,
        case_id: str,
        item_id: str,
        deadline: datetime,
    ) -> ComplianceItem | None:
        """Set deadline for a compliance item."""
        if case_id not in self._items:
            return None
        if item_id not in self._items[case_id]:
            return None

        item = self._items[case_id][item_id]
        item.deadline = deadline
        item.updated_at = datetime.now(UTC)

        return item

    def get_status(self, case_id: str) -> dict[str, Any]:
        """Get compliance status for a case."""
        if case_id not in self._items:
            return {"error": "Case not found"}

        items = list(self._items[case_id].values())
        compliant = sum(1 for i in items if i.status == ComplianceStatus.COMPLIANT)
        non_compliant = sum(1 for i in items if i.status == ComplianceStatus.NON_COMPLIANT)
        in_progress = sum(1 for i in items if i.status == ComplianceStatus.IN_PROGRESS)
        overdue = sum(1 for i in items if i.is_overdue)

        return {
            "case_id": case_id,
            "total_items": len(items),
            "compliant": compliant,
            "non_compliant": non_compliant,
            "in_progress": in_progress,
            "overdue": overdue,
            "compliance_percentage": (compliant / len(items) * 100) if items else 0,
        }

    async def generate_report(self, case_id: str) -> ComplianceReport:
        """Generate comprehensive compliance report."""
        if case_id not in self._items:
            return ComplianceReport(case_id=case_id)

        items = list(self._items[case_id].values())

        report = ComplianceReport(
            case_id=case_id,
            total_items=len(items),
            compliant_items=sum(1 for i in items if i.status == ComplianceStatus.COMPLIANT),
            non_compliant_items=sum(1 for i in items if i.status == ComplianceStatus.NON_COMPLIANT),
            in_progress_items=sum(1 for i in items if i.status == ComplianceStatus.IN_PROGRESS),
            overdue_items=sum(1 for i in items if i.is_overdue),
        )

        # Calculate compliance percentage
        if items:
            report.compliance_percentage = (report.compliant_items / len(items)) * 100

        # Count by type
        for item in items:
            type_name = item.requirement_type.value
            report.items_by_type[type_name] = report.items_by_type.get(type_name, 0) + 1

        # Count by priority
        for item in items:
            priority_name = item.priority.value
            report.items_by_priority[priority_name] = (
                report.items_by_priority.get(priority_name, 0) + 1
            )

        # Get upcoming deadlines
        upcoming = [
            item
            for item in items
            if item.deadline
            and item.days_until_deadline is not None
            and 0 <= item.days_until_deadline <= 30
            and item.status not in [ComplianceStatus.COMPLIANT, ComplianceStatus.WAIVED]
        ]
        upcoming.sort(key=lambda x: x.deadline)
        report.upcoming_deadlines = [
            {
                "item_id": item.id,
                "name": item.name,
                "deadline": item.deadline.isoformat(),
                "days_remaining": item.days_until_deadline,
            }
            for item in upcoming[:10]
        ]

        # Identify critical gaps
        critical_incomplete = [
            item
            for item in items
            if item.priority == Priority.CRITICAL
            and item.status not in [ComplianceStatus.COMPLIANT, ComplianceStatus.WAIVED]
        ]
        report.critical_gaps = [f"{item.name}: {item.status.value}" for item in critical_incomplete]

        # Generate recommendations
        report.recommendations = await self._generate_recommendations(items)

        return report

    async def _generate_recommendations(
        self,
        items: list[ComplianceItem],
    ) -> list[str]:
        """Generate recommendations based on compliance status."""
        recommendations = []

        # Check for critical overdue items
        critical_overdue = [i for i in items if i.priority == Priority.CRITICAL and i.is_overdue]
        if critical_overdue:
            recommendations.append(
                f"URGENT: {len(critical_overdue)} critical items are overdue. "
                "Address immediately to avoid case delays."
            )

        # Check for incomplete evidence
        evidence_items = [
            i
            for i in items
            if i.requirement_type == RequirementType.EVIDENCE
            and i.status != ComplianceStatus.COMPLIANT
        ]
        if evidence_items:
            recommendations.append(
                f"{len(evidence_items)} evidence requirements need attention. "
                "Ensure strong documentation for each criterion."
            )

        # Check criteria coverage
        criteria_items = [
            i for i in items if i.id.startswith("req_") and "criterion" in i.name.lower()
        ]
        compliant_criteria = sum(
            1 for i in criteria_items if i.status == ComplianceStatus.COMPLIANT
        )
        if compliant_criteria < 3:
            recommendations.append(
                f"Only {compliant_criteria} criteria documented. "
                "EB-1A requires evidence for at least 3 criteria."
            )

        # LLM-enhanced recommendations
        if self.llm_call and len(items) > 0:
            status_summary = "\n".join(
                f"- {item.name}: {item.status.value} ({item.completion_percentage}%)"
                for item in items[:15]
            )
            prompt = f"""Based on this EB-1A compliance status, provide 2-3 specific recommendations:

{status_summary}

Focus on:
1. What's most urgent
2. What would strengthen the petition
3. Common pitfalls to avoid"""

            try:
                result = await self.llm_call(prompt)
                for raw_line in result.split("\n"):
                    line = raw_line.strip()
                    if line and (line[0].isdigit() or line.startswith("-")):
                        clean = line.lstrip("0123456789.-) ")
                        if clean and len(clean) > 20:
                            recommendations.append(clean)
            except Exception as e:
                logger.warning(f"LLM recommendations failed: {e}")

        return recommendations[:5]

    async def check_compliance(
        self,
        case_id: str,
        criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        """Check overall compliance and return gaps."""
        if case_id not in self._items:
            self.initialize_case(case_id)
            if criteria:
                self.add_criterion_requirements(case_id, criteria)

        status = self.get_status(case_id)
        report = await self.generate_report(case_id)

        return {
            "status": status,
            "report": report.to_dict(),
            "is_ready_to_file": (
                status.get("compliance_percentage", 0) >= 90
                and status.get("overdue", 0) == 0
                and len(report.critical_gaps) == 0
            ),
            "blocking_issues": report.critical_gaps,
            "recommendations": report.recommendations,
        }

    def get_item(self, case_id: str, item_id: str) -> ComplianceItem | None:
        """Get a specific compliance item."""
        if case_id not in self._items:
            return None
        return self._items[case_id].get(item_id)

    def list_items(
        self,
        case_id: str,
        status_filter: ComplianceStatus | None = None,
        type_filter: RequirementType | None = None,
    ) -> list[ComplianceItem]:
        """List compliance items with optional filters."""
        if case_id not in self._items:
            return []

        items = list(self._items[case_id].values())

        if status_filter:
            items = [i for i in items if i.status == status_filter]

        if type_filter:
            items = [i for i in items if i.requirement_type == type_filter]

        return items


def create_compliance_tracker(
    llm_call: Callable[[str], Coroutine[Any, Any, str]] | None = None,
    storage_callback: Callable[[str, dict], Coroutine[Any, Any, None]] | None = None,
) -> ComplianceTracker:
    """Factory function to create ComplianceTracker instance."""
    return ComplianceTracker(
        llm_call=llm_call,
        storage_callback=storage_callback,
    )
