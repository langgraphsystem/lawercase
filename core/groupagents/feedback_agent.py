"""
FeedbackAgent - Система обратной связи и обзора документов.

Обеспечивает:
- Peer review система
- Сбор и анализ обратной связи
- Рейтинговая система
- Трекинг изменений и улучшений
- Интеграция с approval workflow
- Collaborative editing поддержка
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent


class _FeedbackBaseModel(BaseModel):
    """Base class to keep dumps JSON-friendly for enums/datetimes."""

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        return super().model_dump(*args, **kwargs)


class FeedbackType(str, Enum):
    """Типы обратной связи"""

    REVIEW = "review"  # Экспертный обзор
    COMMENT = "comment"  # Комментарий
    SUGGESTION = "suggestion"  # Предложение
    CORRECTION = "correction"  # Исправление
    APPROVAL = "approval"  # Одобрение
    REJECTION = "rejection"  # Отклонение


class FeedbackStatus(str, Enum):
    """Статусы обратной связи"""

    PENDING = "pending"  # Ожидает рассмотрения
    REVIEWED = "reviewed"  # Рассмотрено
    ACCEPTED = "accepted"  # Принято
    REJECTED = "rejected"  # Отклонено
    IMPLEMENTED = "implemented"  # Реализовано


class FeedbackPriority(str, Enum):
    """Приоритет обратной связи"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewerRole(str, Enum):
    """Роли рецензентов"""

    SENIOR_LAWYER = "senior_lawyer"
    JUNIOR_LAWYER = "junior_lawyer"
    PARALEGAL = "paralegal"
    EXPERT = "expert"
    CLIENT = "client"
    PEER = "peer"


class FeedbackComment(_FeedbackBaseModel):
    """Комментарий обратной связи"""

    comment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = Field(None, description="ID родительского комментария")
    author_id: str = Field(..., description="ID автора")
    author_role: ReviewerRole = Field(..., description="Роль автора")
    content: str = Field(..., description="Содержание комментария")
    selection_range: dict[str, int] | None = Field(None, description="Диапазон выделенного текста")
    suggested_change: str | None = Field(None, description="Предлагаемое изменение")
    feedback_type: FeedbackType = Field(..., description="Тип обратной связи")
    priority: FeedbackPriority = Field(default=FeedbackPriority.MEDIUM)
    tags: list[str] = Field(default_factory=list, description="Теги")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackSession(_FeedbackBaseModel):
    """Сессия обратной связи"""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    case_id: str | None = Field(None, description="ID дела")
    reviewer_id: str = Field(..., description="ID рецензента")
    reviewer_role: ReviewerRole = Field(..., description="Роль рецензента")
    session_type: str = Field(default="standard", description="Тип сессии")
    comments: list[FeedbackComment] = Field(default_factory=list)
    overall_rating: float | None = Field(None, description="Общая оценка (1-5)")
    recommendations: list[str] = Field(default_factory=list)
    status: FeedbackStatus = Field(default=FeedbackStatus.PENDING)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(None)
    estimated_effort: int | None = Field(None, description="Оценка трудозатрат (минуты)")


class FeedbackRequest(_FeedbackBaseModel):
    """Запрос на обратную связь"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    requester_id: str = Field(..., description="ID запрашивающего")
    reviewer_ids: list[str] = Field(..., description="ID рецензентов")
    review_type: str = Field(default="standard", description="Тип обзора")
    deadline: datetime | None = Field(None, description="Крайний срок")
    instructions: str | None = Field(None, description="Инструкции для рецензентов")
    focus_areas: list[str] = Field(default_factory=list, description="Области фокуса")
    priority: FeedbackPriority = Field(default=FeedbackPriority.MEDIUM)
    case_id: str | None = Field(None, description="Связанное дело")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackAnalysis(_FeedbackBaseModel):
    """Анализ обратной связи"""

    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    total_comments: int = Field(default=0)
    comments_by_type: dict[str, int] = Field(default_factory=dict)
    comments_by_priority: dict[str, int] = Field(default_factory=dict)
    average_rating: float | None = Field(None)
    consensus_score: float = Field(default=0.0, description="Уровень консенсуса")
    implementation_rate: float = Field(default=0.0, description="Процент реализации")
    common_themes: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class CollaborativeEdit(_FeedbackBaseModel):
    """Совместное редактирование"""

    edit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(..., description="ID документа")
    editor_id: str = Field(..., description="ID редактора")
    edit_type: str = Field(..., description="Тип редактирования")
    content_before: str = Field(..., description="Содержание до изменения")
    content_after: str = Field(..., description="Содержание после изменения")
    change_position: dict[str, int] = Field(..., description="Позиция изменения")
    feedback_comment_id: str | None = Field(None, description="Связанный комментарий")
    approved_by: list[str] = Field(default_factory=list)
    rejected_by: list[str] = Field(default_factory=list)
    status: FeedbackStatus = Field(default=FeedbackStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackError(Exception):
    """Исключение для ошибок FeedbackAgent"""


class ReviewError(Exception):
    """Исключение для ошибок рецензирования"""


class FeedbackAgent:
    """
    Агент для управления обратной связью и рецензированием.

    Основные функции:
    - Peer review система
    - Collaborative editing
    - Анализ и агрегация обратной связи
    - Трекинг изменений
    - Рейтинговая система
    - Интеграция с workflow
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        Инициализация FeedbackAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилища
        self._feedback_sessions: dict[str, FeedbackSession] = {}
        self._feedback_requests: dict[str, FeedbackRequest] = {}
        self._collaborative_edits: dict[str, CollaborativeEdit] = {}
        self._analyses: dict[str, FeedbackAnalysis] = {}

        # Статистика
        self._feedback_stats: dict[str, int] = {}

    async def arequest_feedback(
        self, request: FeedbackRequest, requester_id: str
    ) -> FeedbackRequest:
        """
        Создание запроса на обратную связь.

        Args:
            request: Запрос на обратную связь
            requester_id: ID запрашивающего

        Returns:
            FeedbackRequest: Созданный запрос
        """
        try:
            # Валидация запроса
            await self._validate_feedback_request(request)

            # Сохранение запроса
            self._feedback_requests[request.request_id] = request

            # Создание сессий для рецензентов
            for reviewer_id in request.reviewer_ids:
                session = FeedbackSession(
                    document_id=request.document_id,
                    case_id=request.case_id,
                    reviewer_id=reviewer_id,
                    reviewer_role=await self._get_reviewer_role(reviewer_id),
                    session_type=request.review_type,
                )
                self._feedback_sessions[session.session_id] = session

            # Audit log
            await self._log_feedback_requested(request, requester_id)

            # Обновление статистики
            self._update_stats("requests_created")

            return request

        except Exception as e:
            await self._log_feedback_error("request_feedback", requester_id, e)
            raise FeedbackError(f"Failed to create feedback request: {e!s}")

    async def asubmit_feedback(
        self,
        session_id: str,
        comments: list[dict[str, Any]],
        overall_rating: float | None = None,
        reviewer_id: str | None = None,
    ) -> FeedbackSession:
        """
        Подача обратной связи в рамках сессии.

        Args:
            session_id: ID сессии
            comments: Список комментариев
            overall_rating: Общая оценка
            reviewer_id: ID рецензента

        Returns:
            FeedbackSession: Обновленная сессия
        """
        try:
            session = self._feedback_sessions.get(session_id)
            if not session:
                raise FeedbackError(f"Feedback session {session_id} not found")

            # Валидация прав доступа
            if reviewer_id and session.reviewer_id != reviewer_id:
                raise FeedbackError("Access denied: reviewer mismatch")

            # Создание комментариев
            feedback_comments = []
            for comment_data in comments:
                comment = FeedbackComment(
                    author_id=session.reviewer_id, author_role=session.reviewer_role, **comment_data
                )
                feedback_comments.append(comment)

            # Обновление сессии
            session.comments.extend(feedback_comments)
            session.overall_rating = overall_rating
            session.status = FeedbackStatus.REVIEWED
            session.completed_at = datetime.utcnow()

            # Автоматический анализ
            await self._analyze_session_feedback(session)

            # Audit log
            await self._log_feedback_submitted(session)

            # Обновление статистики
            self._update_stats("feedback_submitted")
            self._update_stats("comments_total", len(feedback_comments))

            return session

        except Exception as e:
            await self._log_feedback_error("submit_feedback", session.reviewer_id, e)
            raise FeedbackError(f"Failed to submit feedback: {e!s}")

    async def aanalyze_feedback(self, document_id: str, user_id: str) -> FeedbackAnalysis:
        """
        Анализ всей обратной связи по документу.

        Args:
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            FeedbackAnalysis: Результат анализа
        """
        try:
            # Получение всех сессий по документу
            sessions = [s for s in self._feedback_sessions.values() if s.document_id == document_id]

            if not sessions:
                raise FeedbackError(f"No feedback sessions found for document {document_id}")

            # Сбор всех комментариев
            all_comments = []
            ratings = []

            for session in sessions:
                all_comments.extend(session.comments)
                if session.overall_rating:
                    ratings.append(session.overall_rating)

            # Анализ комментариев
            analysis = await self._perform_feedback_analysis(document_id, all_comments, ratings)

            # Сохранение анализа
            self._analyses[analysis.analysis_id] = analysis

            # Audit log
            await self._log_analysis_completed(analysis, user_id)

            return analysis

        except Exception as e:
            await self._log_feedback_error("analyze_feedback", user_id, e)
            raise FeedbackError(f"Failed to analyze feedback: {e!s}")

    async def acreate_collaborative_edit(
        self, edit_data: dict[str, Any], editor_id: str
    ) -> CollaborativeEdit:
        """
        Создание совместного редактирования.

        Args:
            edit_data: Данные редактирования
            editor_id: ID редактора

        Returns:
            CollaborativeEdit: Созданное редактирование
        """
        try:
            edit = CollaborativeEdit(editor_id=editor_id, **edit_data)

            # Валидация редактирования
            await self._validate_collaborative_edit(edit)

            # Сохранение редактирования
            self._collaborative_edits[edit.edit_id] = edit

            # Уведомления заинтересованным сторонам
            await self._notify_stakeholders(edit)

            # Audit log
            await self._log_collaborative_edit_created(edit)

            return edit

        except Exception as e:
            await self._log_feedback_error("create_collaborative_edit", editor_id, e)
            raise FeedbackError(f"Failed to create collaborative edit: {e!s}")

    async def aapprove_edit(
        self, edit_id: str, approver_id: str, comments: str | None = None
    ) -> CollaborativeEdit:
        """
        Одобрение совместного редактирования.

        Args:
            edit_id: ID редактирования
            approver_id: ID одобряющего
            comments: Комментарии

        Returns:
            CollaborativeEdit: Обновленное редактирование
        """
        edit = self._collaborative_edits.get(edit_id)
        if not edit:
            raise FeedbackError(f"Collaborative edit {edit_id} not found")

        if approver_id not in edit.approved_by:
            edit.approved_by.append(approver_id)

        # Проверка порога одобрения
        if len(edit.approved_by) >= self._get_approval_threshold(edit):
            edit.status = FeedbackStatus.ACCEPTED

        # Audit log
        await self._log_edit_approved(edit, approver_id, comments)

        return edit

    async def aget_feedback_sessions(self, document_id: str, user_id: str) -> list[FeedbackSession]:
        """
        Получение сессий обратной связи по документу.

        Args:
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            List[FeedbackSession]: Список сессий
        """
        sessions = [s for s in self._feedback_sessions.values() if s.document_id == document_id]

        # Сортировка по дате создания
        sessions.sort(key=lambda x: x.started_at, reverse=True)

        # Audit log
        await self._log_sessions_accessed(document_id, len(sessions), user_id)

        return sessions

    async def asearch_feedback(
        self, filters: dict[str, Any], user_id: str
    ) -> list[FeedbackSession]:
        """
        Поиск обратной связи по фильтрам.

        Args:
            filters: Фильтры поиска
            user_id: ID пользователя

        Returns:
            List[FeedbackSession]: Найденные сессии
        """
        results = []

        for session in self._feedback_sessions.values():
            if self._matches_session_filters(session, filters):
                results.append(session)

        # Сортировка по дате
        results.sort(key=lambda x: x.started_at, reverse=True)

        # Audit log
        await self._log_feedback_searched(filters, len(results), user_id)

        return results

    async def aget_improvement_suggestions(self, document_id: str, user_id: str) -> list[str]:
        """
        Получение рекомендаций по улучшению документа.

        Args:
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            List[str]: Список рекомендаций
        """
        # Получение анализа
        analysis = None
        for a in self._analyses.values():
            if a.document_id == document_id:
                analysis = a
                break

        if not analysis:
            # Создание анализа если его нет
            analysis = await self.aanalyze_feedback(document_id, user_id)

        suggestions = analysis.improvement_suggestions.copy()

        # Добавление дополнительных рекомендаций на основе комментариев
        sessions = await self.aget_feedback_sessions(document_id, user_id)
        for session in sessions:
            suggestions.extend(session.recommendations)

        # Удаление дубликатов
        unique_suggestions = list(set(suggestions))

        return unique_suggestions

    async def _validate_feedback_request(self, request: FeedbackRequest) -> None:
        """Валидация запроса на обратную связь"""
        if not request.reviewer_ids:
            raise FeedbackError("At least one reviewer must be specified")

        if request.deadline and request.deadline <= datetime.utcnow():
            raise FeedbackError("Deadline must be in the future")

    async def _validate_collaborative_edit(self, edit: CollaborativeEdit) -> None:
        """Валидация совместного редактирования"""
        if not edit.content_before or not edit.content_after:
            raise FeedbackError("Both before and after content must be provided")

        if edit.content_before == edit.content_after:
            raise FeedbackError("No actual changes detected")

    async def _get_reviewer_role(self, reviewer_id: str) -> ReviewerRole:
        """Получение роли рецензента"""
        # Заглушка - в реальности получать из системы пользователей
        return ReviewerRole.PEER

    async def _analyze_session_feedback(self, session: FeedbackSession) -> None:
        """Анализ обратной связи в рамках сессии"""
        # Подсчет комментариев по типам
        type_counts = {}
        priority_counts = {}

        for comment in session.comments:
            type_key = comment.feedback_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

            priority_key = comment.priority.value
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1

        # Генерация рекомендаций на основе анализа
        recommendations = []

        if type_counts.get("correction", 0) > 3:
            recommendations.append("Multiple corrections needed - consider thorough revision")

        if priority_counts.get("critical", 0) > 0:
            recommendations.append("Critical issues identified - immediate attention required")

        session.recommendations = recommendations

    async def _perform_feedback_analysis(
        self, document_id: str, comments: list[FeedbackComment], ratings: list[float]
    ) -> FeedbackAnalysis:
        """Выполнение полного анализа обратной связи"""

        # Подсчет комментариев по типам и приоритетам
        comments_by_type = {}
        comments_by_priority = {}

        for comment in comments:
            type_key = comment.feedback_type.value
            comments_by_type[type_key] = comments_by_type.get(type_key, 0) + 1

            priority_key = comment.priority.value
            comments_by_priority[priority_key] = comments_by_priority.get(priority_key, 0) + 1

        # Расчет средней оценки
        average_rating = sum(ratings) / len(ratings) if ratings else None

        # Расчет консенсуса (разброс оценок)
        consensus_score = 1.0
        if ratings and len(ratings) > 1:
            import statistics

            stdev = statistics.stdev(ratings)
            consensus_score = max(0.0, 1.0 - (stdev / 2.0))  # Нормализация к [0, 1]

        # Выявление общих тем
        common_themes = self._extract_common_themes(comments)

        # Генерация рекомендаций
        improvement_suggestions = self._generate_improvement_suggestions(
            comments_by_type, comments_by_priority, average_rating
        )

        return FeedbackAnalysis(
            document_id=document_id,
            total_comments=len(comments),
            comments_by_type=comments_by_type,
            comments_by_priority=comments_by_priority,
            average_rating=average_rating,
            consensus_score=consensus_score,
            common_themes=common_themes,
            improvement_suggestions=improvement_suggestions,
        )

    def _extract_common_themes(self, comments: list[FeedbackComment]) -> list[str]:
        """Извлечение общих тем из комментариев"""
        themes = []

        # Простой анализ по ключевым словам
        keywords = {}
        for comment in comments:
            words = comment.content.lower().split()
            for word in words:
                if len(word) > 4:  # Игнорировать короткие слова
                    keywords[word] = keywords.get(word, 0) + 1

        # Топ-5 наиболее упоминаемых слов
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        themes = [word for word, count in sorted_keywords[:5] if count > 1]

        return themes

    def _generate_improvement_suggestions(
        self,
        comments_by_type: dict[str, int],
        comments_by_priority: dict[str, int],
        average_rating: float | None,
    ) -> list[str]:
        """Генерация рекомендаций по улучшению"""
        suggestions = []

        # На основе типов комментариев
        if comments_by_type.get("correction", 0) > 0:
            suggestions.append("Address identified corrections to improve accuracy")

        if comments_by_type.get("suggestion", 0) > 2:
            suggestions.append("Consider implementing multiple improvement suggestions")

        # На основе приоритетов
        if comments_by_priority.get("critical", 0) > 0:
            suggestions.append("Immediately address critical priority issues")

        if comments_by_priority.get("high", 0) > 1:
            suggestions.append("Focus on resolving high-priority concerns")

        # На основе оценок
        if average_rating and average_rating < 3.0:
            suggestions.append("Document requires significant revision based on ratings")
        elif average_rating and average_rating < 4.0:
            suggestions.append("Consider minor improvements to enhance quality")

        return suggestions

    async def _notify_stakeholders(self, edit: CollaborativeEdit) -> None:
        """Уведомление заинтересованных сторон о редактировании"""
        # Заглушка для системы уведомлений

    def _get_approval_threshold(self, edit: CollaborativeEdit) -> int:
        """Получение порога одобрения для редактирования"""
        # Простая логика - требуется 2 одобрения
        return 2

    def _matches_session_filters(self, session: FeedbackSession, filters: dict[str, Any]) -> bool:
        """Проверка соответствия сессии фильтрам"""
        for key, value in filters.items():
            if (key == "document_id" and session.document_id != value) or (
                key == "reviewer_id" and session.reviewer_id != value
            ):
                return False
            if (key == "status" and session.status != value) or (
                key == "reviewer_role" and session.reviewer_role != value
            ):
                return False

        return True

    def _update_stats(self, key: str, increment: int = 1) -> None:
        """Обновление статистики"""
        self._feedback_stats[key] = self._feedback_stats.get(key, 0) + increment

    async def _log_feedback_requested(self, request: FeedbackRequest, requester_id: str) -> None:
        """Логирование запроса обратной связи"""
        await self._log_audit_event(
            user_id=requester_id,
            action="feedback_requested",
            payload={
                "request_id": request.request_id,
                "document_id": request.document_id,
                "reviewers_count": len(request.reviewer_ids),
                "priority": request.priority.value,
                "deadline": request.deadline.isoformat() if request.deadline else None,
            },
        )

    async def _log_feedback_submitted(self, session: FeedbackSession) -> None:
        """Логирование подачи обратной связи"""
        await self._log_audit_event(
            user_id=session.reviewer_id,
            action="feedback_submitted",
            payload={
                "session_id": session.session_id,
                "document_id": session.document_id,
                "comments_count": len(session.comments),
                "overall_rating": session.overall_rating,
                "reviewer_role": session.reviewer_role.value,
            },
        )

    async def _log_analysis_completed(self, analysis: FeedbackAnalysis, user_id: str) -> None:
        """Логирование завершенного анализа"""
        await self._log_audit_event(
            user_id=user_id,
            action="feedback_analysis_completed",
            payload={
                "analysis_id": analysis.analysis_id,
                "document_id": analysis.document_id,
                "total_comments": analysis.total_comments,
                "average_rating": analysis.average_rating,
                "consensus_score": analysis.consensus_score,
            },
        )

    async def _log_collaborative_edit_created(self, edit: CollaborativeEdit) -> None:
        """Логирование создания совместного редактирования"""
        await self._log_audit_event(
            user_id=edit.editor_id,
            action="collaborative_edit_created",
            payload={
                "edit_id": edit.edit_id,
                "document_id": edit.document_id,
                "edit_type": edit.edit_type,
                "change_size": len(edit.content_after) - len(edit.content_before),
            },
        )

    async def _log_edit_approved(
        self, edit: CollaborativeEdit, approver_id: str, comments: str | None
    ) -> None:
        """Логирование одобрения редактирования"""
        await self._log_audit_event(
            user_id=approver_id,
            action="collaborative_edit_approved",
            payload={
                "edit_id": edit.edit_id,
                "document_id": edit.document_id,
                "editor_id": edit.editor_id,
                "status": edit.status.value,
                "comments": comments,
            },
        )

    async def _log_sessions_accessed(self, document_id: str, count: int, user_id: str) -> None:
        """Логирование доступа к сессиям"""
        await self._log_audit_event(
            user_id=user_id,
            action="feedback_sessions_accessed",
            payload={"document_id": document_id, "sessions_count": count},
        )

    async def _log_feedback_searched(
        self, filters: dict[str, Any], count: int, user_id: str
    ) -> None:
        """Логирование поиска обратной связи"""
        await self._log_audit_event(
            user_id=user_id,
            action="feedback_searched",
            payload={"filters": filters, "results_count": count},
        )

    async def _log_feedback_error(self, operation: str, user_id: str, error: Exception) -> None:
        """Логирование ошибки обратной связи"""
        await self._log_audit_event(
            user_id=user_id,
            action="feedback_error",
            payload={
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    async def _log_audit_event(self, user_id: str, action: str, payload: dict[str, Any]) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"feedback_agent_{user_id}",
            source="feedback_agent",
            action=action,
            payload=payload,
            tags=["feedback_agent", "peer_review"],
        )

        await self.memory.alog_audit(event)

    async def get_stats(self) -> dict[str, Any]:
        """Получение статистики FeedbackAgent"""
        return {
            "feedback_stats": self._feedback_stats.copy(),
            "total_sessions": len(self._feedback_sessions),
            "active_sessions": len(
                [s for s in self._feedback_sessions.values() if s.status == FeedbackStatus.PENDING]
            ),
            "total_requests": len(self._feedback_requests),
            "total_edits": len(self._collaborative_edits),
            "pending_edits": len(
                [
                    e
                    for e in self._collaborative_edits.values()
                    if e.status == FeedbackStatus.PENDING
                ]
            ),
        }
