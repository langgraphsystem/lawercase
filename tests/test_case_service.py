"""Tests for CaseService (core/services/case_service.py).

Tests cover:
- CaseStatus and CaseType enum values and membership
- Case, CaseVersion, CaseListFilter, CaseListResult dataclass construction
- get_case_service() singleton behavior
- CaseService async methods with a fully mocked DB layer
- Status transition validation in update_status()
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from core.services.case_service import (
    Case,
    CaseListFilter,
    CaseListResult,
    CaseService,
    CaseStatus,
    CaseType,
    CaseVersion,
    get_case_service,
)

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestCaseStatus:
    """CaseStatus enum values and behaviour."""

    def test_all_members_present(self):
        names = {m.name for m in CaseStatus}
        assert names == {
            "DRAFT", "OPEN", "IN_PROGRESS",
            "PENDING_REVIEW", "CLOSED", "ARCHIVED",
        }

    def test_string_values(self):
        assert CaseStatus.DRAFT.value == "draft"
        assert CaseStatus.OPEN.value == "open"
        assert CaseStatus.IN_PROGRESS.value == "in_progress"
        assert CaseStatus.PENDING_REVIEW.value == "pending_review"
        assert CaseStatus.CLOSED.value == "closed"
        assert CaseStatus.ARCHIVED.value == "archived"

    def test_is_str_subclass(self):
        assert isinstance(CaseStatus.DRAFT, str)

    def test_lookup_by_value(self):
        assert CaseStatus("draft") is CaseStatus.DRAFT
        assert CaseStatus("archived") is CaseStatus.ARCHIVED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            CaseStatus("nonexistent")


class TestCaseType:
    """CaseType enum values and behaviour."""

    def test_all_members_present(self):
        names = {m.name for m in CaseType}
        assert names == {"EB1A", "EB1B", "EB2NIW", "O1A", "O1B", "OTHER"}

    def test_string_values(self):
        assert CaseType.EB1A.value == "eb1a"
        assert CaseType.EB1B.value == "eb1b"
        assert CaseType.EB2NIW.value == "eb2niw"
        assert CaseType.O1A.value == "o1a"
        assert CaseType.O1B.value == "o1b"
        assert CaseType.OTHER.value == "other"

    def test_is_str_subclass(self):
        assert isinstance(CaseType.EB1A, str)

    def test_lookup_by_value(self):
        assert CaseType("eb1a") is CaseType.EB1A
        assert CaseType("other") is CaseType.OTHER

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            CaseType("invalid")


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestCaseDataclass:
    """Case dataclass construction and helpers."""

    def test_minimal_construction(self):
        cid = uuid4()
        case = Case(case_id=cid, user_id="u1", title="Test")
        assert case.case_id == cid
        assert case.user_id == "u1"
        assert case.title == "Test"
        assert case.description == ""
        assert case.case_type is CaseType.EB1A
        assert case.status is CaseStatus.DRAFT
        assert case.data == {}
        assert case.version == 1
        assert case.deleted_at is None
        assert case.metadata == {}

    def test_full_construction(self):
        cid = uuid4()
        now = datetime.now(UTC)
        case = Case(
            case_id=cid,
            user_id="u2",
            title="Full",
            description="desc",
            case_type=CaseType.O1A,
            status=CaseStatus.IN_PROGRESS,
            data={"key": "value"},
            version=3,
            created_at=now,
            updated_at=now,
            deleted_at=now,
            metadata={"m": 1},
        )
        assert case.case_type is CaseType.O1A
        assert case.status is CaseStatus.IN_PROGRESS
        assert case.data == {"key": "value"}
        assert case.version == 3
        assert case.deleted_at == now
        assert case.metadata == {"m": 1}

    def test_is_deleted_false_when_none(self):
        case = Case(case_id=uuid4(), user_id="u", title="t")
        assert case.is_deleted() is False

    def test_is_deleted_true_when_set(self):
        case = Case(
            case_id=uuid4(),
            user_id="u",
            title="t",
            deleted_at=datetime.now(UTC),
        )
        assert case.is_deleted() is True

    def test_data_default_is_independent(self):
        """Each instance gets its own default dict."""
        a = Case(case_id=uuid4(), user_id="u", title="a")
        b = Case(case_id=uuid4(), user_id="u", title="b")
        a.data["x"] = 1
        assert "x" not in b.data


class TestCaseVersion:
    """CaseVersion dataclass construction."""

    def test_construction(self):
        vid = uuid4()
        cid = uuid4()
        now = datetime.now(UTC)
        v = CaseVersion(
            version_id=vid,
            case_id=cid,
            version_number=2,
            data_snapshot={"title": "old"},
            changed_fields=["title"],
            changed_by="user1",
            changed_at=now,
            change_reason="renamed",
        )
        assert v.version_id == vid
        assert v.case_id == cid
        assert v.version_number == 2
        assert v.data_snapshot == {"title": "old"}
        assert v.changed_fields == ["title"]
        assert v.changed_by == "user1"
        assert v.changed_at == now
        assert v.change_reason == "renamed"

    def test_default_change_reason(self):
        v = CaseVersion(
            version_id=uuid4(),
            case_id=uuid4(),
            version_number=1,
            data_snapshot={},
            changed_fields=[],
            changed_by="sys",
            changed_at=datetime.now(UTC),
        )
        assert v.change_reason == ""


class TestCaseListFilter:
    """CaseListFilter defaults and construction."""

    def test_all_defaults(self):
        f = CaseListFilter()
        assert f.user_id is None
        assert f.status is None
        assert f.case_type is None
        assert f.search_query is None
        assert f.include_deleted is False
        assert f.created_after is None
        assert f.created_before is None
        assert f.limit == 50
        assert f.offset == 0

    def test_custom_values(self):
        now = datetime.now(UTC)
        f = CaseListFilter(
            user_id="u1",
            status=CaseStatus.OPEN,
            case_type=CaseType.EB2NIW,
            search_query="test",
            include_deleted=True,
            created_after=now,
            created_before=now,
            limit=10,
            offset=20,
        )
        assert f.user_id == "u1"
        assert f.status is CaseStatus.OPEN
        assert f.case_type is CaseType.EB2NIW
        assert f.search_query == "test"
        assert f.include_deleted is True
        assert f.limit == 10
        assert f.offset == 20


class TestCaseListResult:
    """CaseListResult dataclass construction."""

    def test_empty_result(self):
        r = CaseListResult(cases=[], total=0, limit=50, offset=0, has_more=False)
        assert r.cases == []
        assert r.total == 0
        assert r.has_more is False

    def test_result_with_cases(self):
        c1 = Case(case_id=uuid4(), user_id="u", title="a")
        c2 = Case(case_id=uuid4(), user_id="u", title="b")
        r = CaseListResult(cases=[c1, c2], total=5, limit=2, offset=0, has_more=True)
        assert len(r.cases) == 2
        assert r.total == 5
        assert r.has_more is True
        assert r.limit == 2
        assert r.offset == 0


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------

class TestGetCaseService:
    """get_case_service() singleton."""

    def setup_method(self):
        # Reset the module-level singleton before each test
        import core.services.case_service as mod
        mod._case_service = None

    def test_returns_case_service(self):
        svc = get_case_service()
        assert isinstance(svc, CaseService)

    def test_returns_same_instance(self):
        s1 = get_case_service()
        s2 = get_case_service()
        assert s1 is s2

    def test_new_instance_after_reset(self):
        import core.services.case_service as mod
        s1 = get_case_service()
        mod._case_service = None
        s2 = get_case_service()
        assert s1 is not s2


# ---------------------------------------------------------------------------
# CaseService async method tests (mocked DB layer)
# ---------------------------------------------------------------------------

def _make_mock_db():
    """Build a mock db manager whose .session() is an async context manager."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()

    mock_db = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_db.session.return_value = ctx

    return mock_db, mock_session


class TestCaseServiceCreateCase:
    """CaseService.create_case with mocked DB."""

    @pytest.mark.asyncio
    async def test_create_case_returns_case(self):
        mock_db, _ = _make_mock_db()
        svc = CaseService()
        svc._db_manager = mock_db

        case = await svc.create_case(
            user_id="user1",
            title="My Case",
            description="desc",
            case_type=CaseType.EB1A,
            data={"foo": "bar"},
            metadata={"source": "test"},
        )

        assert isinstance(case, Case)
        assert isinstance(case.case_id, UUID)
        assert case.user_id == "user1"
        assert case.title == "My Case"
        assert case.description == "desc"
        assert case.case_type is CaseType.EB1A
        assert case.status is CaseStatus.DRAFT
        assert case.data == {"foo": "bar"}
        assert case.version == 1
        assert case.metadata == {"source": "test"}

    @pytest.mark.asyncio
    async def test_create_case_defaults(self):
        mock_db, _ = _make_mock_db()
        svc = CaseService()
        svc._db_manager = mock_db

        case = await svc.create_case(user_id="u", title="T")

        assert case.description == ""
        assert case.case_type is CaseType.EB1A
        assert case.data == {}
        assert case.metadata == {}

    @pytest.mark.asyncio
    async def test_create_case_none_data_becomes_empty_dict(self):
        mock_db, _ = _make_mock_db()
        svc = CaseService()
        svc._db_manager = mock_db

        case = await svc.create_case(user_id="u", title="T", data=None, metadata=None)
        assert case.data == {}
        assert case.metadata == {}

    @pytest.mark.asyncio
    async def test_create_case_import_error_still_returns_case(self):
        """When core.storage.models is not importable the service still returns a Case."""
        svc = CaseService()
        svc._db_manager = MagicMock()

        with patch.dict("sys.modules", {"core.storage.models": None}):
            case = await svc.create_case(user_id="u", title="T")

        assert isinstance(case, Case)


class TestCaseServiceGetCase:
    """CaseService.get_case with mocked DB."""

    @pytest.mark.asyncio
    async def test_get_case_returns_none_on_import_error(self):
        """When DB models are not available, get_case returns None."""
        svc = CaseService()
        svc._db_manager = MagicMock()

        with patch.dict("sys.modules", {"core.storage.models": None}):
            result = await svc.get_case(uuid4(), user_id="u1")

        assert result is None


class TestCaseServiceUpdateCase:
    """CaseService.update_case with mocked DB."""

    @pytest.mark.asyncio
    async def test_update_case_returns_none_on_import_error(self):
        svc = CaseService()
        svc._db_manager = MagicMock()

        with patch.dict("sys.modules", {"core.storage.models": None}):
            result = await svc.update_case(uuid4(), "u1", title="New")

        assert result is None


class TestCaseServiceDeleteCase:
    """CaseService.delete_case with mocked DB."""

    @pytest.mark.asyncio
    async def test_delete_case_returns_false_on_import_error(self):
        svc = CaseService()
        svc._db_manager = MagicMock()

        with patch.dict("sys.modules", {"core.storage.models": None}):
            result = await svc.delete_case(uuid4(), "u1")

        assert result is False


class TestCaseServiceRestoreCase:
    """CaseService.restore_case with mocked DB."""

    @pytest.mark.asyncio
    async def test_restore_case_returns_none_on_import_error(self):
        svc = CaseService()
        svc._db_manager = MagicMock()

        with patch.dict("sys.modules", {"core.storage.models": None}):
            result = await svc.restore_case(uuid4(), "u1")

        assert result is None


class TestCaseServiceListCases:
    """CaseService.list_cases with mocked DB."""

    @pytest.mark.asyncio
    async def test_list_cases_returns_empty_on_import_error(self):
        svc = CaseService()
        svc._db_manager = MagicMock()

        criteria = CaseListFilter(user_id="u1", limit=25, offset=5)

        with patch.dict("sys.modules", {"core.storage.models": None}):
            result = await svc.list_cases(criteria)

        assert isinstance(result, CaseListResult)
        assert result.cases == []
        assert result.total == 0
        assert result.limit == 25
        assert result.offset == 5
        assert result.has_more is False


class TestCaseServiceUpdateStatus:
    """CaseService.update_status – status-transition validation."""

    @pytest.mark.asyncio
    async def test_returns_none_when_case_not_found(self):
        svc = CaseService()
        svc.get_case = AsyncMock(return_value=None)

        result = await svc.update_status(uuid4(), "u1", CaseStatus.OPEN)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_transition_draft_to_open(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.DRAFT)
        updated = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.OPEN)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock(return_value=updated)

        result = await svc.update_status(cid, "u1", CaseStatus.OPEN, reason="start")
        assert result is updated
        svc.update_case.assert_awaited_once_with(
            case_id=cid,
            user_id="u1",
            status=CaseStatus.OPEN,
            change_reason="start",
        )

    @pytest.mark.asyncio
    async def test_valid_transition_open_to_in_progress(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.OPEN)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock(return_value=existing)

        result = await svc.update_status(cid, "u1", CaseStatus.IN_PROGRESS)
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_transition_draft_to_closed_returns_none(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.DRAFT)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock()

        result = await svc.update_status(cid, "u1", CaseStatus.CLOSED)
        assert result is None
        svc.update_case.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_transition_draft_to_in_progress_returns_none(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.DRAFT)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock()

        result = await svc.update_status(cid, "u1", CaseStatus.IN_PROGRESS)
        assert result is None
        svc.update_case.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_valid_transition_closed_to_archived(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.CLOSED)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock(return_value=existing)

        result = await svc.update_status(cid, "u1", CaseStatus.ARCHIVED)
        assert result is not None

    @pytest.mark.asyncio
    async def test_valid_transition_archived_to_draft(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.ARCHIVED)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock(return_value=existing)

        result = await svc.update_status(cid, "u1", CaseStatus.DRAFT)
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_transition_archived_to_open_returns_none(self):
        cid = uuid4()
        existing = Case(case_id=cid, user_id="u1", title="T", status=CaseStatus.ARCHIVED)

        svc = CaseService()
        svc.get_case = AsyncMock(return_value=existing)
        svc.update_case = AsyncMock()

        result = await svc.update_status(cid, "u1", CaseStatus.OPEN)
        assert result is None
        svc.update_case.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_all_valid_transitions(self):
        """Exhaustive check of every allowed status transition."""
        valid_transitions = {
            CaseStatus.DRAFT: [CaseStatus.OPEN, CaseStatus.ARCHIVED],
            CaseStatus.OPEN: [CaseStatus.IN_PROGRESS, CaseStatus.CLOSED, CaseStatus.ARCHIVED],
            CaseStatus.IN_PROGRESS: [CaseStatus.PENDING_REVIEW, CaseStatus.OPEN, CaseStatus.CLOSED],
            CaseStatus.PENDING_REVIEW: [CaseStatus.IN_PROGRESS, CaseStatus.CLOSED],
            CaseStatus.CLOSED: [CaseStatus.ARCHIVED, CaseStatus.OPEN],
            CaseStatus.ARCHIVED: [CaseStatus.DRAFT],
        }

        for from_status, allowed_targets in valid_transitions.items():
            for to_status in allowed_targets:
                cid = uuid4()
                existing = Case(
                    case_id=cid, user_id="u", title="T", status=from_status,
                )
                svc = CaseService()
                svc.get_case = AsyncMock(return_value=existing)
                svc.update_case = AsyncMock(return_value=existing)

                result = await svc.update_status(cid, "u", to_status)
                assert result is not None, (
                    f"Transition {from_status.value} -> {to_status.value} should be valid"
                )

    @pytest.mark.asyncio
    async def test_all_invalid_transitions(self):
        """Exhaustive check that disallowed transitions return None."""
        valid_transitions = {
            CaseStatus.DRAFT: {CaseStatus.OPEN, CaseStatus.ARCHIVED},
            CaseStatus.OPEN: {CaseStatus.IN_PROGRESS, CaseStatus.CLOSED, CaseStatus.ARCHIVED},
            CaseStatus.IN_PROGRESS: {CaseStatus.PENDING_REVIEW, CaseStatus.OPEN, CaseStatus.CLOSED},
            CaseStatus.PENDING_REVIEW: {CaseStatus.IN_PROGRESS, CaseStatus.CLOSED},
            CaseStatus.CLOSED: {CaseStatus.ARCHIVED, CaseStatus.OPEN},
            CaseStatus.ARCHIVED: {CaseStatus.DRAFT},
        }
        all_statuses = set(CaseStatus)

        for from_status in CaseStatus:
            disallowed = all_statuses - valid_transitions[from_status] - {from_status}
            for to_status in disallowed:
                cid = uuid4()
                existing = Case(
                    case_id=cid, user_id="u", title="T", status=from_status,
                )
                svc = CaseService()
                svc.get_case = AsyncMock(return_value=existing)
                svc.update_case = AsyncMock()

                result = await svc.update_status(cid, "u", to_status)
                assert result is None, (
                    f"Transition {from_status.value} -> {to_status.value} should be invalid"
                )
                svc.update_case.assert_not_awaited()


class TestCaseServiceGetDb:
    """CaseService._get_db lazy initialisation."""

    @pytest.mark.asyncio
    async def test_get_db_calls_get_db_manager_once(self):
        svc = CaseService()
        mock_manager = MagicMock()

        with patch(
            "core.services.case_service.get_db_manager",
            return_value=mock_manager,
            create=True,
        ), patch(
            "core.storage.connection.get_db_manager",
            return_value=mock_manager,
        ):
            db1 = await svc._get_db()
            db2 = await svc._get_db()

        assert db1 is mock_manager
        assert db2 is mock_manager

    @pytest.mark.asyncio
    async def test_get_db_reuses_cached_manager(self):
        svc = CaseService()
        mock_manager = MagicMock()
        svc._db_manager = mock_manager

        db = await svc._get_db()
        assert db is mock_manager


class TestCaseServiceInit:
    """CaseService.__init__ sets expected attributes."""

    def test_init_db_manager_none(self):
        svc = CaseService()
        assert svc._db_manager is None

    def test_init_has_logger(self):
        svc = CaseService()
        assert svc.logger is not None
