"""
CaseAgent - Агент для управления делами и случаями.

Обеспечивает полный CRUD функционал для работы с делами,
включая создание, получение, обновление, удаление и поиск.
Интегрирован с MemoryManager для persistence и audit trail.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..exceptions import AgentError, NotFoundError, ValidationError as MegaValidationError
from ..logging_config import StructuredLogger
from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from .models import (
    CaseExhibit,
    CaseOperationResult,
    CaseQuery,
    CaseRecord,
    CaseStatus,
    CaseVersion,
    CaseWorkflowState,
    ValidationResult,
)


class CaseNotFoundError(NotFoundError):
    """Case not found error."""

    def __init__(self, case_id: str, **kwargs):
        super().__init__(
            message=f"Case with ID {case_id} not found",
            resource_type="Case",
            resource_id=case_id,
            **kwargs,
        )


class CaseValidationError(MegaValidationError):
    """Case validation error."""

    def __init__(self, message: str, errors: list[str] | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if errors:
            details["validation_errors"] = errors
        super().__init__(message=message, details=details, **kwargs)


class CaseVersionConflictError(AgentError):
    """Case version conflict error."""

    def __init__(
        self,
        case_id: str,
        expected_version: int,
        current_version: int,
        **kwargs,
    ):
        super().__init__(
            message=f"Version conflict for case {case_id}: expected {expected_version}, current {current_version}",
            agent_name="CaseAgent",
            details={
                "case_id": case_id,
                "expected_version": expected_version,
                "current_version": current_version,
            },
            user_message="The case has been modified by someone else. Please refresh and try again.",
            recoverable=True,
            **kwargs,
        )


class CaseAgent:
    """
    Агент для управления делами с полным CRUD функционалом.

    Основные возможности:
    - Создание и управление делами
    - Optimistic locking для concurrent updates
    - Интеграция с MemoryManager для persistence
    - Audit trail для всех операций
    - Поиск и фильтрация дел
    - Управление версиями и изменениями
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Инициализация CaseAgent.

        Args:
            memory_manager: Экземпляр MemoryManager для persistence
        """
        self.logger = StructuredLogger("core.groupagents.case_agent")
        self.memory = memory_manager or MemoryManager()
        self._cases_store: dict[str, CaseRecord] = {}
        self._versions_store: dict[str, list[CaseVersion]] = {}

    # ---- Core CRUD Operations ----

    async def acreate_case(
        self, user_id: str, case_data: dict[str, Any], *, created_by: str | None = None
    ) -> CaseRecord:
        """
        Создание нового дела.

        Args:
            user_id: ID пользователя
            case_data: Данные дела
            created_by: ID создателя (если отличается от user_id)

        Returns:
            CaseRecord: Созданное дело

        Raises:
            CaseValidationError: При ошибках валидации
        """
        self.logger.info(
            "Creating case",
            user_id=user_id,
            case_type=case_data.get("case_type"),
            created_by=created_by or user_id,
        )

        try:
            # Создание записи дела
            case_data["created_by"] = created_by or user_id
            case_record = CaseRecord(**case_data)

            # Валидация
            validation = await self._validate_case_data(case_record)
            if not validation.is_valid:
                raise CaseValidationError(
                    message="Case validation failed",
                    errors=validation.errors,
                    details={"user_id": user_id, "case_data": case_data},
                )

            # Сохранение в локальное хранилище
            self._cases_store[case_record.case_id] = case_record

            # Создание первой версии
            initial_version = CaseVersion(
                case_id=case_record.case_id,
                version_number=1,
                changes={"action": "created", "data": case_record.model_dump()},
                changed_by=case_record.created_by,
                change_reason="Initial case creation",
            )
            self._versions_store[case_record.case_id] = [initial_version]

            # Audit log
            await self._log_audit_event(
                user_id=user_id,
                action="create_case",
                case_id=case_record.case_id,
                payload={"case_title": case_record.title, "case_type": case_record.case_type},
            )

            # Сохранение в семантическую память
            await self._store_case_memory(case_record, user_id)

            self.logger.info(
                "Case created successfully",
                user_id=user_id,
                case_id=case_record.case_id,
                case_type=case_record.case_type,
            )

            return case_record

        except (CaseValidationError, AgentError):
            raise  # Re-raise known errors
        except Exception as e:
            await self._log_audit_event(
                user_id=user_id,
                action="create_case_failed",
                case_id=None,
                payload={"error": str(e), "case_data": case_data},
            )
            raise AgentError(
                message=f"Failed to create case: {e!s}",
                agent_name="CaseAgent",
                details={"user_id": user_id, "error_type": type(e).__name__},
                cause=e,
            ) from e

    async def aget_case(self, case_id: str, user_id: str | None = None) -> CaseRecord:
        """
        Получение дела по ID.

        Args:
            case_id: ID дела
            user_id: ID пользователя (для audit)

        Returns:
            CaseRecord: Найденное дело

        Raises:
            CaseNotFoundError: Если дело не найдено
        """
        if case_id not in self._cases_store:
            if user_id:
                await self._log_audit_event(
                    user_id=user_id,
                    action="get_case_not_found",
                    case_id=case_id,
                    payload={"error": "Case not found"},
                )
            raise CaseNotFoundError(case_id=case_id)

        case_record = self._cases_store[case_id]

        if user_id:
            await self._log_audit_event(
                user_id=user_id,
                action="get_case",
                case_id=case_id,
                payload={"case_title": case_record.title},
            )

        return case_record

    async def aupdate_case(
        self,
        case_id: str,
        updates: dict[str, Any],
        user_id: str,
        *,
        expected_version: int | None = None,
    ) -> CaseRecord:
        """
        Обновление дела с optimistic locking.

        Args:
            case_id: ID дела
            updates: Словарь обновлений
            user_id: ID пользователя
            expected_version: Ожидаемая версия для optimistic locking

        Returns:
            CaseRecord: Обновленное дело

        Raises:
            CaseNotFoundError: Если дело не найдено
            CaseVersionConflictError: При конфликте версий
        """
        # Получение текущего дела
        current_case = await self.aget_case(case_id, user_id)

        # Проверка версии для optimistic locking
        if expected_version is not None and current_case.version != expected_version:
            raise CaseVersionConflictError(
                case_id=case_id,
                expected_version=expected_version,
                current_version=current_case.version,
            )

        # Создание обновленной копии
        case_data = current_case.model_dump()
        case_data.update(updates)
        case_data["version"] = current_case.version + 1
        case_data["updated_at"] = datetime.utcnow()

        updated_case = CaseRecord(**case_data)

        # Валидация
        validation = await self._validate_case_data(updated_case)
        if not validation.is_valid:
            raise CaseValidationError(f"Validation failed: {validation.errors}")

        # Сохранение
        self._cases_store[case_id] = updated_case

        # Создание версии изменений
        version = CaseVersion(
            case_id=case_id,
            version_number=updated_case.version,
            changes={"action": "updated", "updates": updates},
            changed_by=user_id,
            change_reason=updates.get("change_reason", "Case update"),
        )
        self._versions_store[case_id].append(version)

        # Audit log
        await self._log_audit_event(
            user_id=user_id,
            action="update_case",
            case_id=case_id,
            payload={"updates": updates, "new_version": updated_case.version},
        )

        # Обновление семантической памяти
        await self._store_case_memory(updated_case, user_id)

        return updated_case

    async def adelete_case(self, case_id: str, user_id: str) -> CaseOperationResult:
        """
        Удаление дела (soft delete).

        Args:
            case_id: ID дела
            user_id: ID пользователя

        Returns:
            CaseOperationResult: Результат операции

        Raises:
            CaseNotFoundError: Если дело не найдено
        """
        # Проверка существования дела
        case_record = await self.aget_case(case_id, user_id)

        # Soft delete - обновление статуса
        await self.aupdate_case(
            case_id=case_id,
            updates={"status": CaseStatus.ARCHIVED, "change_reason": f"Deleted by user {user_id}"},
            user_id=user_id,
        )

        # Audit log
        await self._log_audit_event(
            user_id=user_id,
            action="delete_case",
            case_id=case_id,
            payload={"case_title": case_record.title},
        )

        return CaseOperationResult(
            success=True,
            case_id=case_id,
            operation="delete",
            message=f"Case {case_id} successfully archived",
        )

    async def asearch_cases(self, query: CaseQuery, user_id: str | None = None) -> list[CaseRecord]:
        """
        Поиск дел по запросу.

        Args:
            query: Параметры поиска
            user_id: ID пользователя (для audit)

        Returns:
            List[CaseRecord]: Найденные дела
        """
        results = []

        for case_record in self._cases_store.values():
            if self._matches_query(case_record, query):
                results.append(case_record)

        # Сортировка по дате создания (новые первыми)
        results.sort(key=lambda x: x.created_at, reverse=True)

        # Применение offset и limit
        start_idx = query.offset
        end_idx = start_idx + query.limit
        results = results[start_idx:end_idx]

        if user_id:
            await self._log_audit_event(
                user_id=user_id,
                action="search_cases",
                case_id=None,
                payload={"query": query.model_dump(), "results_count": len(results)},
            )

        return results

    # ---- Case Workflow Integration ----

    async def to_graph_state(self, case_id: str) -> CaseWorkflowState:
        """
        Конвертация дела в состояние для LangGraph workflow.

        Args:
            case_id: ID дела

        Returns:
            CaseWorkflowState: Состояние для workflow
        """
        case_record = await self.aget_case(case_id)

        return CaseWorkflowState(
            case_id=case_id,
            current_step="case_loaded",
            step_data={
                "case_title": case_record.title,
                "case_type": case_record.case_type,
                "status": case_record.status,
                "priority": case_record.priority,
            },
        )

    async def astart_workflow(self, case_id: str, user_id: str) -> dict[str, Any]:
        """
        Запуск workflow для дела.

        Args:
            case_id: ID дела
            user_id: ID пользователя

        Returns:
            Dict: Данные для запуска workflow
        """
        case_record = await self.aget_case(case_id, user_id)
        workflow_state = await self.to_graph_state(case_id)

        await self._log_audit_event(
            user_id=user_id,
            action="start_workflow",
            case_id=case_id,
            payload={"workflow_step": workflow_state.current_step},
        )

        return {"case_record": case_record, "workflow_state": workflow_state, "user_id": user_id}

    # ---- Exhibit Management ----

    async def aadd_exhibit(self, case_id: str, exhibit: CaseExhibit, user_id: str) -> CaseRecord:
        """
        Добавление приложения к делу.

        Args:
            case_id: ID дела
            exhibit: Приложение
            user_id: ID пользователя

        Returns:
            CaseRecord: Обновленное дело
        """
        case_record = await self.aget_case(case_id, user_id)

        # Добавление приложения
        exhibits = case_record.exhibits.copy()
        exhibits.append(exhibit)

        return await self.aupdate_case(
            case_id=case_id,
            updates={"exhibits": exhibits, "change_reason": f"Added exhibit: {exhibit.name}"},
            user_id=user_id,
        )

    # ---- Version Management ----

    async def aget_case_versions(self, case_id: str) -> list[CaseVersion]:
        """
        Получение истории версий дела.

        Args:
            case_id: ID дела

        Returns:
            List[CaseVersion]: Список версий
        """
        return self._versions_store.get(case_id, [])

    # ---- Helper Methods ----

    async def _validate_case_data(self, case_record: CaseRecord) -> ValidationResult:
        """Валидация данных дела"""
        errors = []
        warnings = []

        # Базовая валидация уже выполнена Pydantic
        # Дополнительная бизнес-логика валидации

        if len(case_record.title.strip()) < 3:
            errors.append("Case title must be at least 3 characters long")

        if len(case_record.description.strip()) < 10:
            warnings.append("Case description is quite short")

        if not case_record.client_id:
            errors.append("Client ID is required")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=1.0 if len(errors) == 0 else 0.5,
        )

    def _matches_query(self, case_record: CaseRecord, query: CaseQuery) -> bool:
        """Проверка соответствия дела поисковому запросу"""
        # Текстовый поиск
        if query.query:
            text_fields = [case_record.title, case_record.description, " ".join(case_record.tags)]
            query_lower = query.query.lower()
            if not any(query_lower in field.lower() for field in text_fields):
                return False

        # Фильтры
        if query.case_type and case_record.case_type != query.case_type:
            return False

        if query.status and case_record.status != query.status:
            return False

        if query.priority and case_record.priority != query.priority:
            return False

        if query.client_id and case_record.client_id != query.client_id:
            return False

        if query.assigned_lawyer and case_record.assigned_lawyer != query.assigned_lawyer:
            return False

        # Фильтры по датам
        if query.created_after and case_record.created_at < query.created_after:
            return False

        if query.created_before and case_record.created_at > query.created_before:
            return False

        # Фильтр по тегам
        if query.tags:
            if not any(tag in case_record.tags for tag in query.tags):
                return False

        return True

    async def _log_audit_event(
        self, user_id: str, action: str, case_id: str | None, payload: dict[str, Any]
    ) -> None:
        """Логирование audit события"""
        import uuid

        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"case_agent_{case_id or 'unknown'}",
            source="case_agent",
            action=action,
            payload=payload,
            tags=["case_management"],
        )

        await self.memory.alog_audit(event)

    async def _store_case_memory(self, case_record: CaseRecord, user_id: str) -> None:
        """Сохранение дела в семантическую память"""
        # Создание записи для семантической памяти
        memory_text = f"Case: {case_record.title} - {case_record.description}"
        memory_record = MemoryRecord(
            text=memory_text,
            user_id=user_id,
            type="semantic",
            metadata={
                "case_id": case_record.case_id,
                "case_type": case_record.case_type,
                "status": case_record.status,
                "priority": case_record.priority,
                "tags": case_record.tags,
            },
        )

        await self.memory.awrite([memory_record])
