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
from typing import Any, Dict, List, Optional
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
    description: Optional[str] = Field(None, description="Описание приложения")
    file_path: Optional[str] = Field(None, description="Путь к файлу")
    file_type: Optional[str] = Field(None, description="Тип файла")
    file_size: Optional[int] = Field(None, description="Размер файла в байтах")
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
    assigned_lawyer: Optional[str] = Field(None, description="ID назначенного юриста")
    team_members: List[str] = Field(default_factory=list, description="ID участников команды")

    # Метаданные
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="ID создателя дела")

    # Приложения и документы
    exhibits: List[CaseExhibit] = Field(default_factory=list)

    # Дополнительные данные
    tags: List[str] = Field(default_factory=list, description="Теги для поиска")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")

    # Версионирование
    version: int = Field(default=1, description="Версия записи")

    @field_validator("updated_at", mode="before")
    @classmethod
    def set_updated_at(cls, value: Optional[datetime]) -> datetime:  # pragma: no cover - simple setter
        return datetime.utcnow()


class CaseVersion(_AgentBaseModel):
    """Версия дела для отслеживания изменений"""
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str = Field(..., description="ID связанного дела")
    version_number: int = Field(..., description="Номер версии")
    changes: Dict[str, Any] = Field(..., description="Словарь изменений")
    changed_by: str = Field(..., description="ID пользователя, внесшего изменения")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: Optional[str] = Field(None, description="Причина изменения")

class CaseQuery(_AgentBaseModel):
    """Модель для поисковых запросов по делам"""
    query: Optional[str] = Field(None, description="Текстовый запрос")
    case_type: Optional[CaseType] = Field(None, description="Фильтр по типу дела")
    status: Optional[CaseStatus] = Field(None, description="Фильтр по статусу")
    priority: Optional[CasePriority] = Field(None, description="Фильтр по приоритету")
    client_id: Optional[str] = Field(None, description="Фильтр по клиенту")
    assigned_lawyer: Optional[str] = Field(None, description="Фильтр по юристу")
    created_after: Optional[datetime] = Field(None, description="Созданы после даты")
    created_before: Optional[datetime] = Field(None, description="Созданы до даты")
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    limit: int = Field(default=50, ge=1, le=1000, description="Лимит результатов")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")

class CaseWorkflowState(_AgentBaseModel):
    """Состояние дела в workflow"""
    case_id: str = Field(..., description="ID дела")
    current_step: str = Field(..., description="Текущий шаг workflow")
    step_data: Dict[str, Any] = Field(default_factory=dict, description="Данные текущего шага")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="История шагов")
    error_state: Optional[str] = Field(None, description="Состояние ошибки")

class CaseOperationResult(_AgentBaseModel):
    """Результат операции с делом"""
    success: bool = Field(..., description="Успешность операции")
    case_id: Optional[str] = Field(None, description="ID дела")
    operation: str = Field(..., description="Тип операции")
    message: Optional[str] = Field(None, description="Сообщение о результате")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    errors: Optional[List[str]] = Field(None, description="Список ошибок")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationResult(_AgentBaseModel):
    """Результат валидации"""
    is_valid: bool = Field(..., description="Результат валидации")
    errors: List[str] = Field(default_factory=list, description="Список ошибок")
    warnings: List[str] = Field(default_factory=list, description="Список предупреждений")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Оценка качества")
    details: Dict[str, Any] = Field(default_factory=dict, description="Детали валидации")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
