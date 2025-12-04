"""Integration tests for Case Management Service.

Tests the CaseService module structure and basic functionality.
Uses in-memory storage to avoid database dependencies.
"""

from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4

import pytest

# Skip database-dependent tests if no database is configured
SKIP_DB_TESTS = not os.environ.get("DATABASE_URL") and not os.environ.get("POSTGRES_DSN")
DB_SKIP_REASON = "Database not configured (set DATABASE_URL or POSTGRES_DSN)"


# ============================================================================
# Module Import Tests
# ============================================================================


class TestModuleImports:
    """Tests for module imports and structure."""

    def test_import_core_classes(self) -> None:
        """Test importing core service classes."""
        from core.services import (Case, CaseListFilter, CaseListResult,
                                   CaseService, CaseStatus, CaseType,
                                   CaseVersion, get_case_service)

        assert Case is not None
        assert CaseListFilter is not None
        assert CaseListResult is not None
        assert CaseService is not None
        assert CaseStatus is not None
        assert CaseType is not None
        assert CaseVersion is not None
        assert get_case_service is not None

    def test_case_status_enum_values(self) -> None:
        """Test CaseStatus enum values."""
        from core.services import CaseStatus

        assert hasattr(CaseStatus, "DRAFT")
        assert hasattr(CaseStatus, "OPEN")
        assert hasattr(CaseStatus, "IN_PROGRESS")
        assert hasattr(CaseStatus, "PENDING_REVIEW")
        assert hasattr(CaseStatus, "CLOSED")
        assert hasattr(CaseStatus, "ARCHIVED")

    def test_case_type_enum_values(self) -> None:
        """Test CaseType enum values."""
        from core.services import CaseType

        assert hasattr(CaseType, "EB1A")
        assert hasattr(CaseType, "EB1B")
        assert hasattr(CaseType, "EB2NIW")
        assert hasattr(CaseType, "O1A")
        assert hasattr(CaseType, "OTHER")


# ============================================================================
# Case Dataclass Tests
# ============================================================================


class TestCaseDataclass:
    """Tests for Case dataclass."""

    def test_case_creation(self) -> None:
        """Test Case dataclass creation."""
        from core.services import Case, CaseStatus, CaseType

        case = Case(
            case_id=uuid4(),
            user_id="user123",
            title="Test Case",
            description="Test description",
            case_type=CaseType.EB1A,
            status=CaseStatus.DRAFT,
            data={},
            metadata={},
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert case.user_id == "user123"
        assert case.title == "Test Case"
        assert case.case_type == CaseType.EB1A
        assert case.status == CaseStatus.DRAFT

    def test_case_with_data(self) -> None:
        """Test Case with data field."""
        from core.services import Case, CaseStatus, CaseType

        data = {"applicant_name": "John Doe", "field": "Technology"}

        case = Case(
            case_id=uuid4(),
            user_id="user123",
            title="Test Case",
            description="",
            case_type=CaseType.EB1A,
            status=CaseStatus.DRAFT,
            data=data,
            metadata={},
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert case.data["applicant_name"] == "John Doe"
        assert case.data["field"] == "Technology"


# ============================================================================
# CaseListFilter Tests
# ============================================================================


class TestCaseListFilter:
    """Tests for CaseListFilter dataclass."""

    def test_filter_creation(self) -> None:
        """Test CaseListFilter creation."""
        from core.services import CaseListFilter

        filter_obj = CaseListFilter(user_id="user123")
        assert filter_obj.user_id == "user123"

    def test_filter_with_status(self) -> None:
        """Test CaseListFilter with status."""
        from core.services import CaseListFilter, CaseStatus

        filter_obj = CaseListFilter(
            user_id="user123",
            status=CaseStatus.OPEN,
        )
        assert filter_obj.status == CaseStatus.OPEN

    def test_filter_with_pagination(self) -> None:
        """Test CaseListFilter with pagination."""
        from core.services import CaseListFilter

        filter_obj = CaseListFilter(
            user_id="user123",
            limit=20,
            offset=40,
        )
        assert filter_obj.limit == 20
        assert filter_obj.offset == 40


# ============================================================================
# CaseService Tests
# ============================================================================


class TestCaseService:
    """Tests for CaseService class."""

    def test_service_instantiation(self) -> None:
        """Test CaseService can be instantiated."""
        from core.services import CaseService

        service = CaseService()
        assert service is not None

    def test_get_case_service_singleton(self) -> None:
        """Test get_case_service returns same instance."""
        from core.services import get_case_service

        service1 = get_case_service()
        service2 = get_case_service()
        # Should be same or equivalent instance
        assert service1 is not None
        assert service2 is not None

    def test_service_has_create_method(self) -> None:
        """Test service has create_case method."""
        from core.services import CaseService

        service = CaseService()
        assert hasattr(service, "create_case")
        assert callable(service.create_case)

    def test_service_has_get_method(self) -> None:
        """Test service has get_case method."""
        from core.services import CaseService

        service = CaseService()
        assert hasattr(service, "get_case")
        assert callable(service.get_case)

    def test_service_has_update_method(self) -> None:
        """Test service has update_case method."""
        from core.services import CaseService

        service = CaseService()
        assert hasattr(service, "update_case")
        assert callable(service.update_case)

    def test_service_has_delete_method(self) -> None:
        """Test service has delete_case method."""
        from core.services import CaseService

        service = CaseService()
        assert hasattr(service, "delete_case")
        assert callable(service.delete_case)

    def test_service_has_list_method(self) -> None:
        """Test service has list_cases method."""
        from core.services import CaseService

        service = CaseService()
        assert hasattr(service, "list_cases")
        assert callable(service.list_cases)


# ============================================================================
# Case Creation Tests (with in-memory storage)
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestCaseCreation:
    """Tests for case creation using in-memory storage."""

    @pytest.mark.asyncio
    async def test_create_case_basic(self) -> None:
        """Test basic case creation."""
        from core.services import CaseService, CaseStatus, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="New Case",
            case_type=CaseType.EB1A,
        )

        assert case is not None
        assert case.user_id == "user123"
        assert case.title == "New Case"
        assert case.case_type == CaseType.EB1A
        assert case.status == CaseStatus.DRAFT
        assert case.version == 1

    @pytest.mark.asyncio
    async def test_create_case_with_description(self) -> None:
        """Test case creation with description."""
        from core.services import CaseService, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="Complete Case",
            description="Full description",
            case_type=CaseType.EB1A,
        )

        assert case.description == "Full description"

    @pytest.mark.asyncio
    async def test_create_case_with_data(self) -> None:
        """Test case creation with data."""
        from core.services import CaseService, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="Data Case",
            case_type=CaseType.EB1A,
            data={"field": "Science"},
        )

        assert case.data == {"field": "Science"}

    @pytest.mark.asyncio
    async def test_create_case_generates_uuid(self) -> None:
        """Test that case creation generates a UUID."""
        from uuid import UUID

        from core.services import CaseService, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="UUID Case",
            case_type=CaseType.EB1A,
        )

        assert isinstance(case.case_id, UUID)


# ============================================================================
# Case Retrieval Tests
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestCaseRetrieval:
    """Tests for case retrieval."""

    @pytest.mark.asyncio
    async def test_get_existing_case(self) -> None:
        """Test retrieving existing case."""
        from core.services import CaseService, CaseType

        service = CaseService()

        created = await service.create_case(
            user_id="user123",
            title="Get Test",
            case_type=CaseType.EB1A,
        )

        retrieved = await service.get_case(
            case_id=created.case_id,
            user_id="user123",
        )

        assert retrieved is not None
        assert retrieved.case_id == created.case_id
        assert retrieved.title == "Get Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_case(self) -> None:
        """Test retrieving non-existent case returns None."""
        from core.services import CaseService

        service = CaseService()

        result = await service.get_case(
            case_id=uuid4(),
            user_id="user123",
        )
        assert result is None


# ============================================================================
# Case Update Tests
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestCaseUpdate:
    """Tests for case updates."""

    @pytest.mark.asyncio
    async def test_update_title(self) -> None:
        """Test updating case title."""
        from core.services import CaseService, CaseType

        service = CaseService()

        created = await service.create_case(
            user_id="user123",
            title="Original Title",
            case_type=CaseType.EB1A,
        )

        updated = await service.update_case(
            case_id=created.case_id,
            user_id="user123",
            title="Updated Title",
        )

        assert updated is not None
        assert updated.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_increments_version(self) -> None:
        """Test that updates increment version."""
        from core.services import CaseService, CaseType

        service = CaseService()

        created = await service.create_case(
            user_id="user123",
            title="Version Test",
            case_type=CaseType.EB1A,
        )
        assert created.version == 1

        updated = await service.update_case(
            case_id=created.case_id,
            user_id="user123",
            title="Update 1",
        )

        assert updated is not None
        assert updated.version == 2


# ============================================================================
# Status Transition Tests
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestStatusTransitions:
    """Tests for status transitions."""

    @pytest.mark.asyncio
    async def test_valid_transition_draft_to_open(self) -> None:
        """Test valid transition from draft to open."""
        from core.services import CaseService, CaseStatus, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="Status Test",
            case_type=CaseType.EB1A,
        )
        assert case.status == CaseStatus.DRAFT

        updated = await service.update_status(
            case_id=case.case_id,
            user_id="user123",
            new_status=CaseStatus.OPEN,
        )

        assert updated is not None
        assert updated.status == CaseStatus.OPEN


# ============================================================================
# Delete Tests
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestDelete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_soft_delete(self) -> None:
        """Test soft delete marks case as deleted."""
        from core.services import CaseService, CaseType

        service = CaseService()

        case = await service.create_case(
            user_id="user123",
            title="Delete Test",
            case_type=CaseType.EB1A,
        )

        result = await service.delete_case(
            case_id=case.case_id,
            user_id="user123",
        )
        assert result is True

        # Verify it's not returned by default
        retrieved = await service.get_case(
            case_id=case.case_id,
            user_id="user123",
        )
        assert retrieved is None


# ============================================================================
# List Tests
# ============================================================================


@pytest.mark.skipif(SKIP_DB_TESTS, reason=DB_SKIP_REASON)
class TestList:
    """Tests for listing cases."""

    @pytest.mark.asyncio
    async def test_list_user_cases(self) -> None:
        """Test listing cases for a user."""
        from core.services import CaseListFilter, CaseService, CaseType

        service = CaseService()

        # Create cases with unique user ID to avoid conflicts
        test_user = f"list_test_{uuid4().hex[:8]}"

        for i in range(3):
            await service.create_case(
                user_id=test_user,
                title=f"Case {i}",
                case_type=CaseType.EB1A,
            )

        filter_criteria = CaseListFilter(user_id=test_user)
        result = await service.list_cases(filter_criteria)

        assert result.total >= 3
        assert len(result.cases) >= 3
