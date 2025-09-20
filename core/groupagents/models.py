"""
Pydantic модели для Core Group Agents.

Содержит модели данных для всех агентов системы:
- Case-related модели
- Document-related модели
- Validation модели
- Workflow состояния
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseStatus(str, Enum):
    """Статусы дела"""

    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CasePriority(str, Enum):
    """Приоритет дела"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CaseType(str, Enum):
    """Типы дел"""

    IMMIGRATION = "immigration"
    CORPORATE = "corporate"
    FAMILY = "family"
    CRIMINAL = "criminal"
    CIVIL = "civil"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    OTHER = "other"


class _AgentBaseModel(BaseModel):
    """Base class with consistent serialization for agent models."""

    model_config = ConfigDict(use_enum_values=True)

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        if "mode" not in kwargs:
            kwargs["mode"] = "json"
        return super().model_dump(*args, **kwargs)


class CaseExhibit(_AgentBaseModel):
    """Приложение к делу"""

    exhibit_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Название приложения")
    description: str | None = Field(None, description="Описание приложения")
    file_path: str | None = Field(None, description="Путь к файлу")
    file_type: str | None = Field(None, description="Тип файла")
    file_size: int | None = Field(None, description="Размер файла в байтах")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: str = Field(..., description="ID пользователя, загрузившего файл")


class CaseRecord(_AgentBaseModel):
    """Основная модель дела"""

    case_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1, max_length=200, description="Название дела")
    description: str = Field(..., description="Описание дела")
    case_type: CaseType = Field(..., description="Тип дела")
    status: CaseStatus = Field(default=CaseStatus.DRAFT, description="Текущий статус")
    priority: CasePriority = Field(default=CasePriority.MEDIUM, description="Приоритет")

    # Участники дела
    client_id: str = Field(..., description="ID клиента")
    assigned_lawyer: str | None = Field(None, description="ID назначенного юриста")
    team_members: list[str] = Field(default_factory=list, description="ID участников команды")

    # Метаданные
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="ID создателя дела")

    # Приложения и документы
    exhibits: list[CaseExhibit] = Field(default_factory=list)

    # Дополнительные данные
    tags: list[str] = Field(default_factory=list, description="Теги для поиска")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")

    # Версионирование
    version: int = Field(default=1, description="Версия записи")

    @field_validator("updated_at", mode="before")
    @classmethod
    def set_updated_at(cls, value: datetime | None) -> datetime:  # pragma: no cover - simple setter
        return datetime.utcnow()


class CaseVersion(_AgentBaseModel):
    """Версия дела для отслеживания изменений"""

    version_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str = Field(..., description="ID связанного дела")
    version_number: int = Field(..., description="Номер версии")
    changes: dict[str, Any] = Field(..., description="Словарь изменений")
    changed_by: str = Field(..., description="ID пользователя, внесшего изменения")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: str | None = Field(None, description="Причина изменения")


class CaseQuery(_AgentBaseModel):
    """Модель для поисковых запросов по делам"""

    query: str | None = Field(None, description="Текстовый запрос")
    case_type: CaseType | None = Field(None, description="Фильтр по типу дела")
    status: CaseStatus | None = Field(None, description="Фильтр по статусу")
    priority: CasePriority | None = Field(None, description="Фильтр по приоритету")
    client_id: str | None = Field(None, description="Фильтр по клиенту")
    assigned_lawyer: str | None = Field(None, description="Фильтр по юристу")
    created_after: datetime | None = Field(None, description="Созданы после даты")
    created_before: datetime | None = Field(None, description="Созданы до даты")
    tags: list[str] | None = Field(None, description="Фильтр по тегам")
    limit: int = Field(default=50, ge=1, le=1000, description="Лимит результатов")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")


class CaseWorkflowState(_AgentBaseModel):
    """Состояние дела в workflow"""

    case_id: str = Field(..., description="ID дела")
    current_step: str = Field(..., description="Текущий шаг workflow")
    step_data: dict[str, Any] = Field(default_factory=dict, description="Данные текущего шага")
    history: list[dict[str, Any]] = Field(default_factory=list, description="История шагов")
    error_state: str | None = Field(None, description="Состояние ошибки")


class CaseOperationResult(_AgentBaseModel):
    """Результат операции с делом"""

    success: bool = Field(..., description="Успешность операции")
    case_id: str | None = Field(None, description="ID дела")
    operation: str = Field(..., description="Тип операции")
    message: str | None = Field(None, description="Сообщение о результате")
    data: dict[str, Any] | None = Field(None, description="Дополнительные данные")
    errors: list[str] | None = Field(None, description="Список ошибок")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(_AgentBaseModel):
    """Результат валидации"""

    is_valid: bool = Field(..., description="Результат валидации")
    errors: list[str] = Field(default_factory=list, description="Список ошибок")
    warnings: list[str] = Field(default_factory=list, description="Список предупреждений")
    score: float | None = Field(None, ge=0.0, le=1.0, description="Оценка качества")
    details: dict[str, Any] = Field(default_factory=dict, description="Детали валидации")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
