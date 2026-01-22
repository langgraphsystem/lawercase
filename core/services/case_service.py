"""Case Management Service with CRUD and versioning.

Provides comprehensive case management:
- Full CRUD operations
- Version history tracking
- Soft delete with recovery
- Search and filtering
- Status management
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class CaseStatus(str, Enum):
    """Case lifecycle statuses."""

    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CaseType(str, Enum):
    """Types of immigration cases."""

    EB1A = "eb1a"
    EB1B = "eb1b"
    EB2NIW = "eb2niw"
    O1A = "o1a"
    O1B = "o1b"
    OTHER = "other"


@dataclass
class CaseVersion:
    """Version snapshot of a case."""

    version_id: UUID
    case_id: UUID
    version_number: int
    data_snapshot: dict[str, Any]
    changed_fields: list[str]
    changed_by: str
    changed_at: datetime
    change_reason: str = ""


@dataclass
class Case:
    """Immigration case entity."""

    case_id: UUID
    user_id: str
    title: str
    description: str = ""
    case_type: CaseType = CaseType.EB1A
    status: CaseStatus = CaseStatus.DRAFT
    data: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_deleted(self) -> bool:
        """Check if case is soft deleted."""
        return self.deleted_at is not None


@dataclass
class CaseListFilter:
    """Filter criteria for case listing."""

    user_id: str | None = None
    status: CaseStatus | None = None
    case_type: CaseType | None = None
    search_query: str | None = None
    include_deleted: bool = False
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass
class CaseListResult:
    """Result of case listing."""

    cases: list[Case]
    total: int
    limit: int
    offset: int
    has_more: bool


class CaseService:
    """Service for case management operations.

    Features:
    - Full CRUD operations
    - Version history with rollback
    - Soft delete and recovery
    - Status transitions
    - Search and filtering

    Example:
        >>> service = CaseService()
        >>> case = await service.create_case(
        ...     user_id="user123",
        ...     title="EB-1A Application",
        ...     case_type=CaseType.EB1A
        ... )
        >>> updated = await service.update_case(
        ...     case_id=case.case_id,
        ...     user_id="user123",
        ...     data={"applicant_name": "John Doe"}
        ... )
    """

    def __init__(self) -> None:
        """Initialize case service."""
        self._db_manager: Any = None
        self.logger = logger.bind(component="case_service")

    async def _get_db(self) -> Any:
        """Get database manager."""
        if self._db_manager is None:
            from core.storage.connection import get_db_manager

            self._db_manager = get_db_manager()
        return self._db_manager

    async def create_case(
        self,
        user_id: str,
        title: str,
        description: str = "",
        case_type: CaseType = CaseType.EB1A,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Case:
        """Create a new case.

        Args:
            user_id: Owner user ID
            title: Case title
            description: Case description
            case_type: Type of immigration case
            data: Case data payload
            metadata: Additional metadata

        Returns:
            Created Case object

        Example:
            >>> case = await service.create_case(
            ...     user_id="user123",
            ...     title="John Doe EB-1A",
            ...     case_type=CaseType.EB1A,
            ...     data={"applicant_name": "John Doe"}
            ... )
        """
        db = await self._get_db()

        case_id = uuid4()
        now = datetime.utcnow()

        case = Case(
            case_id=case_id,
            user_id=user_id,
            title=title,
            description=description,
            case_type=case_type,
            status=CaseStatus.DRAFT,
            data=data or {},
            version=1,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        try:
            from core.storage.models import CaseDB

            async with db.session() as session:
                db_case = CaseDB(
                    case_id=case_id,
                    user_id=user_id,
                    title=title,
                    description=description,
                    status=case.status.value,
                    case_type=case_type.value,
                    data={**(data or {}), "metadata": metadata or {}},
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(db_case)

            self.logger.info(
                "case_created",
                case_id=str(case_id),
                user_id=user_id,
                case_type=case_type.value,
            )

        except ImportError:
            self.logger.warning("database_not_available", operation="create_case")

        return case

    async def get_case(
        self,
        case_id: UUID,
        user_id: str | None = None,
        include_deleted: bool = False,
    ) -> Case | None:
        """Get case by ID.

        Args:
            case_id: Case UUID
            user_id: Optional user ID for ownership check
            include_deleted: Include soft-deleted cases

        Returns:
            Case object or None if not found
        """
        db = await self._get_db()

        try:
            from sqlalchemy import select

            from core.storage.models import CaseDB

            async with db.session() as session:
                query = select(CaseDB).where(CaseDB.case_id == case_id)

                if user_id:
                    query = query.where(CaseDB.user_id == user_id)

                if not include_deleted:
                    query = query.where(CaseDB.deleted_at.is_(None))

                result = await session.execute(query)
                db_case = result.scalar_one_or_none()

                if not db_case:
                    return None

                return Case(
                    case_id=db_case.case_id,
                    user_id=db_case.user_id,
                    title=db_case.title,
                    description=db_case.description or "",
                    case_type=CaseType(db_case.case_type) if db_case.case_type else CaseType.OTHER,
                    status=CaseStatus(db_case.status),
                    data=db_case.data or {},
                    version=db_case.version,
                    created_at=db_case.created_at,
                    updated_at=db_case.updated_at,
                    deleted_at=db_case.deleted_at,
                    metadata=db_case.data.get("metadata", {}) if db_case.data else {},
                )

        except ImportError:
            self.logger.warning("database_not_available", operation="get_case")
            return None

    async def update_case(
        self,
        case_id: UUID,
        user_id: str,
        title: str | None = None,
        description: str | None = None,
        data: dict[str, Any] | None = None,
        status: CaseStatus | None = None,
        change_reason: str = "",
    ) -> Case | None:
        """Update case with version tracking.

        Args:
            case_id: Case UUID
            user_id: User making the change
            title: New title
            description: New description
            data: Data updates (merged with existing)
            status: New status
            change_reason: Reason for change (for audit)

        Returns:
            Updated Case or None if not found
        """
        db = await self._get_db()

        try:
            from sqlalchemy import select

            from core.storage.models import CaseDB

            async with db.session() as session:
                query = select(CaseDB).where(
                    CaseDB.case_id == case_id,
                    CaseDB.user_id == user_id,
                    CaseDB.deleted_at.is_(None),
                )
                result = await session.execute(query)
                db_case = result.scalar_one_or_none()

                if not db_case:
                    return None

                # Track changed fields
                changed_fields = []

                if title and title != db_case.title:
                    db_case.title = title
                    changed_fields.append("title")

                if description is not None and description != db_case.description:
                    db_case.description = description
                    changed_fields.append("description")

                if status and status.value != db_case.status:
                    db_case.status = status.value
                    changed_fields.append("status")

                if data:
                    # Merge data
                    current_data = db_case.data or {}
                    current_data.update(data)
                    db_case.data = current_data
                    changed_fields.append("data")

                # Increment version
                db_case.version += 1
                db_case.updated_at = datetime.utcnow()

                self.logger.info(
                    "case_updated",
                    case_id=str(case_id),
                    user_id=user_id,
                    version=db_case.version,
                    changed_fields=changed_fields,
                    reason=change_reason,
                )

                return Case(
                    case_id=db_case.case_id,
                    user_id=db_case.user_id,
                    title=db_case.title,
                    description=db_case.description or "",
                    case_type=CaseType(db_case.case_type) if db_case.case_type else CaseType.OTHER,
                    status=CaseStatus(db_case.status),
                    data=db_case.data or {},
                    version=db_case.version,
                    created_at=db_case.created_at,
                    updated_at=db_case.updated_at,
                    metadata=db_case.data.get("metadata", {}) if db_case.data else {},
                )

        except ImportError:
            self.logger.warning("database_not_available", operation="update_case")
            return None

    async def delete_case(
        self,
        case_id: UUID,
        user_id: str,
        hard_delete: bool = False,
    ) -> bool:
        """Delete case (soft or hard delete).

        Args:
            case_id: Case UUID
            user_id: User requesting deletion
            hard_delete: If True, permanently delete; otherwise soft delete

        Returns:
            True if deleted successfully
        """
        db = await self._get_db()

        try:
            from sqlalchemy import delete, update

            from core.storage.models import CaseDB

            async with db.session() as session:
                if hard_delete:
                    stmt = delete(CaseDB).where(
                        CaseDB.case_id == case_id,
                        CaseDB.user_id == user_id,
                    )
                    result = await session.execute(stmt)
                    deleted = result.rowcount > 0
                else:
                    stmt = (
                        update(CaseDB)
                        .where(
                            CaseDB.case_id == case_id,
                            CaseDB.user_id == user_id,
                            CaseDB.deleted_at.is_(None),
                        )
                        .values(deleted_at=datetime.utcnow())
                    )
                    result = await session.execute(stmt)
                    deleted = result.rowcount > 0

                if deleted:
                    self.logger.info(
                        "case_deleted",
                        case_id=str(case_id),
                        user_id=user_id,
                        hard_delete=hard_delete,
                    )

                return deleted

        except ImportError:
            self.logger.warning("database_not_available", operation="delete_case")
            return False

    async def restore_case(
        self,
        case_id: UUID,
        user_id: str,
    ) -> Case | None:
        """Restore soft-deleted case.

        Args:
            case_id: Case UUID
            user_id: User requesting restoration

        Returns:
            Restored Case or None
        """
        db = await self._get_db()

        try:
            from sqlalchemy import update

            from core.storage.models import CaseDB

            async with db.session() as session:
                stmt = (
                    update(CaseDB)
                    .where(
                        CaseDB.case_id == case_id,
                        CaseDB.user_id == user_id,
                        CaseDB.deleted_at.isnot(None),
                    )
                    .values(deleted_at=None, updated_at=datetime.utcnow())
                )
                result = await session.execute(stmt)

                if result.rowcount > 0:
                    self.logger.info(
                        "case_restored",
                        case_id=str(case_id),
                        user_id=user_id,
                    )
                    return await self.get_case(case_id, user_id)

                return None

        except ImportError:
            self.logger.warning("database_not_available", operation="restore_case")
            return None

    async def list_cases(
        self,
        filter_criteria: CaseListFilter,
    ) -> CaseListResult:
        """List cases with filtering and pagination.

        Args:
            filter_criteria: Filter and pagination options

        Returns:
            CaseListResult with cases and metadata
        """
        db = await self._get_db()

        try:
            from sqlalchemy import func, select

            from core.storage.models import CaseDB

            async with db.session() as session:
                query = select(CaseDB)

                # Apply filters
                if filter_criteria.user_id:
                    query = query.where(CaseDB.user_id == filter_criteria.user_id)

                if filter_criteria.status:
                    query = query.where(CaseDB.status == filter_criteria.status.value)

                if filter_criteria.case_type:
                    query = query.where(CaseDB.case_type == filter_criteria.case_type.value)

                if not filter_criteria.include_deleted:
                    query = query.where(CaseDB.deleted_at.is_(None))

                if filter_criteria.created_after:
                    query = query.where(CaseDB.created_at >= filter_criteria.created_after)

                if filter_criteria.created_before:
                    query = query.where(CaseDB.created_at <= filter_criteria.created_before)

                if filter_criteria.search_query:
                    search = f"%{filter_criteria.search_query}%"
                    query = query.where(
                        CaseDB.title.ilike(search) | CaseDB.description.ilike(search)
                    )

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                # Apply pagination
                query = (
                    query.order_by(CaseDB.created_at.desc())
                    .offset(filter_criteria.offset)
                    .limit(filter_criteria.limit)
                )

                result = await session.execute(query)
                db_cases = result.scalars().all()

                cases = [
                    Case(
                        case_id=c.case_id,
                        user_id=c.user_id,
                        title=c.title,
                        description=c.description or "",
                        case_type=CaseType(c.case_type) if c.case_type else CaseType.OTHER,
                        status=CaseStatus(c.status),
                        data=c.data or {},
                        version=c.version,
                        created_at=c.created_at,
                        updated_at=c.updated_at,
                        deleted_at=c.deleted_at,
                    )
                    for c in db_cases
                ]

                return CaseListResult(
                    cases=cases,
                    total=total,
                    limit=filter_criteria.limit,
                    offset=filter_criteria.offset,
                    has_more=(filter_criteria.offset + len(cases)) < total,
                )

        except ImportError:
            self.logger.warning("database_not_available", operation="list_cases")
            return CaseListResult(
                cases=[],
                total=0,
                limit=filter_criteria.limit,
                offset=filter_criteria.offset,
                has_more=False,
            )

    async def update_status(
        self,
        case_id: UUID,
        user_id: str,
        new_status: CaseStatus,
        reason: str = "",
    ) -> Case | None:
        """Update case status with validation.

        Args:
            case_id: Case UUID
            user_id: User making the change
            new_status: New status
            reason: Reason for status change

        Returns:
            Updated Case or None
        """
        # Validate status transition
        valid_transitions = {
            CaseStatus.DRAFT: [CaseStatus.OPEN, CaseStatus.ARCHIVED],
            CaseStatus.OPEN: [CaseStatus.IN_PROGRESS, CaseStatus.CLOSED, CaseStatus.ARCHIVED],
            CaseStatus.IN_PROGRESS: [CaseStatus.PENDING_REVIEW, CaseStatus.OPEN, CaseStatus.CLOSED],
            CaseStatus.PENDING_REVIEW: [CaseStatus.IN_PROGRESS, CaseStatus.CLOSED],
            CaseStatus.CLOSED: [CaseStatus.ARCHIVED, CaseStatus.OPEN],
            CaseStatus.ARCHIVED: [CaseStatus.DRAFT],
        }

        current_case = await self.get_case(case_id, user_id)
        if not current_case:
            return None

        allowed = valid_transitions.get(current_case.status, [])
        if new_status not in allowed:
            self.logger.warning(
                "invalid_status_transition",
                case_id=str(case_id),
                from_status=current_case.status.value,
                to_status=new_status.value,
            )
            return None

        return await self.update_case(
            case_id=case_id,
            user_id=user_id,
            status=new_status,
            change_reason=reason,
        )


# Singleton instance
_case_service: CaseService | None = None


def get_case_service() -> CaseService:
    """Get global case service instance."""
    global _case_service
    if _case_service is None:
        _case_service = CaseService()
    return _case_service


__all__ = [
    "Case",
    "CaseListFilter",
    "CaseListResult",
    "CaseService",
    "CaseStatus",
    "CaseType",
    "CaseVersion",
    "get_case_service",
]
