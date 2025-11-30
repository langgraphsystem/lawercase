"""Enhanced Case Management API endpoints.

Provides full CRUD operations for immigration cases:
- Create, Read, Update, Delete
- Status transitions
- Soft delete and recovery
- Search and filtering
- Versioning
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.logging_utils import get_logger
from core.services.case_service import (CaseListFilter, CaseStatus, CaseType,
                                        get_case_service)

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateCaseRequest(BaseModel):
    """Request to create a new case."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    case_type: str = Field(default="eb1a")
    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateCaseRequest(BaseModel):
    """Request to update a case."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    data: dict[str, Any] | None = None
    status: str | None = None
    change_reason: str = Field(default="", max_length=500)


class UpdateStatusRequest(BaseModel):
    """Request to update case status."""

    status: str = Field(..., description="New status")
    reason: str = Field(default="", max_length=500)


class CaseResponse(BaseModel):
    """Case response model."""

    case_id: str
    user_id: str
    title: str
    description: str
    case_type: str
    status: str
    data: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class CaseListResponse(BaseModel):
    """Response for case listing."""

    cases: list[CaseResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_case_type(case_type_str: str) -> CaseType:
    """Parse case type string to enum."""
    try:
        return CaseType(case_type_str.lower())
    except ValueError:
        return CaseType.OTHER


def _parse_status(status_str: str) -> CaseStatus:
    """Parse status string to enum."""
    try:
        return CaseStatus(status_str.lower())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_str}",
        ) from e


def _case_to_response(case: Any) -> CaseResponse:
    """Convert Case object to response model."""
    return CaseResponse(
        case_id=str(case.case_id),
        user_id=case.user_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type.value,
        status=case.status.value,
        data=case.data,
        version=case.version,
        created_at=case.created_at,
        updated_at=case.updated_at,
        deleted_at=case.deleted_at,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    request: CreateCaseRequest,
    user_id: str = Query(..., description="User ID"),
) -> CaseResponse:
    """Create a new immigration case.

    Args:
        request: Case creation request
        user_id: Owner user ID

    Returns:
        Created case

    Example:
        POST /api/v1/cases?user_id=user123
        {
            "title": "John Doe EB-1A Application",
            "case_type": "eb1a",
            "data": {"applicant_name": "John Doe"}
        }
    """
    service = get_case_service()

    case = await service.create_case(
        user_id=user_id,
        title=request.title,
        description=request.description,
        case_type=_parse_case_type(request.case_type),
        data=request.data,
        metadata=request.metadata,
    )

    return _case_to_response(case)


@router.get("/statuses", tags=["Cases"])
async def get_available_statuses() -> dict[str, Any]:
    """Get available case statuses and valid transitions."""
    return {
        "statuses": [s.value for s in CaseStatus],
        "case_types": [t.value for t in CaseType],
        "valid_transitions": {
            "draft": ["open", "archived"],
            "open": ["in_progress", "closed", "archived"],
            "in_progress": ["pending_review", "open", "closed"],
            "pending_review": ["in_progress", "closed"],
            "closed": ["archived", "open"],
            "archived": ["draft"],
        },
    }


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    user_id: str = Query(..., description="User ID"),
    include_deleted: bool = Query(default=False),
) -> CaseResponse:
    """Get case by ID.

    Args:
        case_id: Case UUID
        user_id: User ID for ownership check
        include_deleted: Include soft-deleted cases

    Returns:
        Case details
    """
    service = get_case_service()

    case = await service.get_case(
        case_id=case_id,
        user_id=user_id,
        include_deleted=include_deleted,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return _case_to_response(case)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    request: UpdateCaseRequest,
    user_id: str = Query(..., description="User ID"),
) -> CaseResponse:
    """Update case.

    Args:
        case_id: Case UUID
        request: Update request
        user_id: User ID

    Returns:
        Updated case
    """
    service = get_case_service()

    case = await service.update_case(
        case_id=case_id,
        user_id=user_id,
        title=request.title,
        description=request.description,
        data=request.data,
        status=_parse_status(request.status) if request.status else None,
        change_reason=request.change_reason,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return _case_to_response(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: UUID,
    user_id: str = Query(..., description="User ID"),
    hard_delete: bool = Query(default=False, description="Permanently delete"),
) -> None:
    """Delete case.

    Args:
        case_id: Case UUID
        user_id: User ID
        hard_delete: If True, permanently delete
    """
    service = get_case_service()

    deleted = await service.delete_case(
        case_id=case_id,
        user_id=user_id,
        hard_delete=hard_delete,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )


@router.post("/{case_id}/restore", response_model=CaseResponse)
async def restore_case(
    case_id: UUID,
    user_id: str = Query(..., description="User ID"),
) -> CaseResponse:
    """Restore soft-deleted case.

    Args:
        case_id: Case UUID
        user_id: User ID

    Returns:
        Restored case
    """
    service = get_case_service()

    case = await service.restore_case(case_id=case_id, user_id=user_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or not deleted",
        )

    return _case_to_response(case)


@router.patch("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    case_id: UUID,
    request: UpdateStatusRequest,
    user_id: str = Query(..., description="User ID"),
) -> CaseResponse:
    """Update case status.

    Args:
        case_id: Case UUID
        request: Status update request
        user_id: User ID

    Returns:
        Updated case
    """
    service = get_case_service()

    case = await service.update_status(
        case_id=case_id,
        user_id=user_id,
        new_status=_parse_status(request.status),
        reason=request.reason,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case not found or invalid status transition",
        )

    return _case_to_response(case)


@router.get("", response_model=CaseListResponse)
async def list_cases(
    user_id: str = Query(..., description="User ID"),
    status_filter: str | None = Query(default=None, alias="status"),
    case_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CaseListResponse:
    """List cases with filtering.

    Args:
        user_id: User ID
        status_filter: Filter by status
        case_type: Filter by case type
        search: Search in title/description
        include_deleted: Include soft-deleted
        limit: Max results
        offset: Pagination offset

    Returns:
        List of cases
    """
    service = get_case_service()

    filter_criteria = CaseListFilter(
        user_id=user_id,
        status=_parse_status(status_filter) if status_filter else None,
        case_type=_parse_case_type(case_type) if case_type else None,
        search_query=search,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )

    result = await service.list_cases(filter_criteria)

    return CaseListResponse(
        cases=[_case_to_response(c) for c in result.cases],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
        has_more=result.has_more,
    )
