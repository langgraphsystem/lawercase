"""
MegaAgent - Центральный оркестратор системы mega_agent_pro.

Обеспечивает:
- Централизованную маршрутизацию команд между агентами
- RBAC проверки и контроль доступа
- Audit trail для всех операций
- Интеграцию с workflow system
- Retry logic и error handling
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from ..orchestration.workflow_graph import WorkflowState, build_case_workflow
from ..orchestration.pipeline_manager import run
from core.llm.router import LLMRouter
from core.rag.retrieve import HybridRetriever, _default_retriever
from .case_agent import CaseAgent
from .writer_agent import WriterAgent
from .validator_agent import ValidationType, ValidatorAgent


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    ADMIN = "admin"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    CLIENT = "client"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Разрешения в системе"""
    CREATE_CASE = "create_case"
    READ_CASE = "read_case"
    UPDATE_CASE = "update_case"
    DELETE_CASE = "delete_case"
    GENERATE_DOCUMENT = "generate_document"
    VALIDATE_DOCUMENT = "validate_document"
    ADMIN_ACCESS = "admin_access"
    VIEW_AUDIT = "view_audit"


class CommandType(str, Enum):
    """Типы команд системы"""
    ASK = "ask"
    TRAIN = "train"
    VALIDATE = "validate"
    GENERATE = "generate"
    CASE = "case"
    SEARCH = "search"
    WORKFLOW = "workflow"
    ADMIN = "admin"


class MegaAgentCommand(BaseModel):
    """Модель команды для MegaAgent"""
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID пользователя")
    command_type: CommandType = Field(..., description="Тип команды")
    action: str = Field(..., description="Действие для выполнения")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Данные команды")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Контекст команды")
    priority: int = Field(default=5, ge=1, le=10, description="Приоритет (1-10)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MegaAgentResponse(BaseModel):
    """Модель ответа MegaAgent"""
    command_id: str = Field(..., description="ID команды")
    success: bool = Field(..., description="Успешность выполнения")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Результат")
    error: Optional[str] = Field(default=None, description="Ошибка")
    agent_used: Optional[str] = Field(default=None, description="Использованный агент")
    execution_time: Optional[float] = Field(default=None, description="Время выполнения")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SecurityError(Exception):
    """Исключение для ошибок безопасности"""
    pass


class CommandError(Exception):
    """Исключение для ошибок команд"""
    pass


class MegaAgent:
    """
    Центральный агент-оркестратор системы mega_agent_pro.

    Основные функции:
    - Маршрутизация команд между специализированными агентами
    - Контроль доступа и RBAC
    - Centralized audit logging
    - Retry logic и error handling
    - Интеграция с workflow system
    """

    # RBAC матрица разрешений
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: [
            Permission.CREATE_CASE, Permission.READ_CASE, Permission.UPDATE_CASE,
            Permission.DELETE_CASE, Permission.GENERATE_DOCUMENT, Permission.VALIDATE_DOCUMENT,
            Permission.ADMIN_ACCESS, Permission.VIEW_AUDIT
        ],
        UserRole.LAWYER: [
            Permission.CREATE_CASE, Permission.READ_CASE, Permission.UPDATE_CASE,
            Permission.GENERATE_DOCUMENT, Permission.VALIDATE_DOCUMENT
        ],
        UserRole.PARALEGAL: [
            Permission.READ_CASE, Permission.UPDATE_CASE, Permission.GENERATE_DOCUMENT
        ],
        UserRole.CLIENT: [
            Permission.READ_CASE
        ],
        UserRole.VIEWER: [
            Permission.READ_CASE
        ]
    }

    # Маппинг команд к агентам
    COMMAND_AGENT_MAPPING = {
        CommandType.CASE: "case_agent",
        CommandType.GENERATE: "writer_agent",
        CommandType.VALIDATE: "validator_agent",
        CommandType.SEARCH: "rag_pipeline_agent",
        CommandType.ASK: "supervisor_agent",
        CommandType.WORKFLOW: "workflow_system"
    }

    def __init__(
        self,
        *,
        router: Optional[LLMRouter] = None,
        retriever: Optional[HybridRetriever] = None,
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        """
        Инициализация MegaAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()
        self._router = router or LLMRouter()
        self._retriever = retriever or _default_retriever

        # Инициализация агентов
        self.case_agent = CaseAgent(router=self._router, retriever=self._retriever)
        self.writer_agent = WriterAgent(router=self._router, retriever=self._retriever)
        self.validator_agent = ValidatorAgent(router=self._router, retriever=self._retriever)

        # Кэш пользователей и их ролей (в реальности из базы данных)
        self._user_roles: Dict[str, UserRole] = {}

        # Статистика команд
        self._command_stats: Dict[str, int] = {}

    async def handle_command(
        self,
        command: MegaAgentCommand,
        user_role: Optional[UserRole] = None
    ) -> MegaAgentResponse:
        """
        Центральный обработчик команд с RBAC проверкой.

        Args:
            command: Команда для выполнения
            user_role: Роль пользователя (если не указана, получается из кэша)

        Returns:
            MegaAgentResponse: Результат выполнения команды

        Raises:
            SecurityError: При нарушении безопасности
            CommandError: При ошибках команды
        """
        start_time = datetime.utcnow()

        try:
            # Получение роли пользователя
            if user_role is None:
                user_role = await self._get_user_role(command.user_id)

            # RBAC проверка
            if not await self._check_permission(command, user_role):
                raise SecurityError(
                    f"User {command.user_id} with role {user_role} "
                    f"does not have permission for {command.command_type}:{command.action}"
                )

            # Audit log начала команды
            await self._log_command_start(command, user_role)

            # Маршрутизация к соответствующему агенту
            result = await self._dispatch_to_agent(command)

            # Расчет времени выполнения
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Создание успешного ответа
            response = MegaAgentResponse(
                command_id=command.command_id,
                success=True,
                result=result,
                agent_used=self.COMMAND_AGENT_MAPPING.get(command.command_type),
                execution_time=execution_time
            )

            # Audit log завершения
            await self._log_command_completion(command, response)

            # Обновление статистики
            self._update_stats(command.command_type)

            return response

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Создание ответа с ошибкой
            response = MegaAgentResponse(
                command_id=command.command_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

            # Audit log ошибки
            await self._log_command_error(command, response, e)

            return response

    async def _dispatch_to_agent(self, command: MegaAgentCommand) -> Dict[str, Any]:
        """
        Маршрутизация команды к соответствующему агенту.

        Args:
            command: Команда для выполнения

        Returns:
            Dict[str, Any]: Результат выполнения

        Raises:
            CommandError: При ошибках маршрутизации
        """
        agent_name = self.COMMAND_AGENT_MAPPING.get(command.command_type)

        if not agent_name:
            raise CommandError(f"Unknown command type: {command.command_type}")

        # Маршрутизация к case_agent через LangGraph workflow
        if agent_name == "case_agent":
            return await self._handle_case_command(command)

        elif agent_name == "writer_agent":
            return await self._handle_writer_command(command)

        elif agent_name == "validator_agent":
            return await self._handle_validator_command(command)

        # Маршрутизация к workflow_system (использует тот же workflow)
        elif agent_name == "workflow_system":
            return await self._handle_workflow_command(command)

        # Placeholder для других агентов
        else:
            return {
                "message": f"Agent {agent_name} not yet implemented",
                "command": command.action,
                "agent": agent_name
            }

    async def _handle_case_command(self, command: MegaAgentCommand) -> Dict[str, Any]:
        """Обработка команд case_agent"""
        state = await self._run_case_workflow(
            operation=command.action,
            payload=command.payload,
            user_id=command.user_id,
        )
        return self._format_case_response(state)

    async def _handle_workflow_command(self, command: MegaAgentCommand) -> Dict[str, Any]:
        """Обработка команд workflow system"""
        state = await self._run_case_workflow(
            operation=command.action,
            payload=command.payload,
            user_id=command.user_id,
        )
        response = self._format_case_response(state)
        response["operation"] = command.action
        response["workflow"] = "case"
        return response

    async def _handle_writer_command(self, command: MegaAgentCommand) -> Dict[str, Any]:
        payload = command.payload
        action = (command.action or 'letter').lower()
        if action in {'letter', 'generate_letter'}:
            draft = await self.writer_agent.agenerate_letter(
                author_id=command.user_id,
                recipient=payload['recipient'],
                subject=payload['subject'],
                outline=payload.get('outline', ''),
                case_reference=payload.get('case_reference'),
            )
            return {'document': draft.model_dump(), 'operation': 'generate_letter'}
        if action == 'get':
            document = await self.writer_agent.aget_document(payload['document_id'])
            return {'document': document.model_dump(), 'operation': 'get_document'}
        raise CommandError(f"Unknown writer action {command.action}")

    async def _handle_validator_command(self, command: MegaAgentCommand) -> Dict[str, Any]:
        payload = command.payload
        action = (command.action or 'document').lower()
        if action in {'document', 'case'}:
            vtype = ValidationType.DOCUMENT if action == 'document' else ValidationType.CASE_DATA
            result = await self.validator_agent.avalidate(data=payload['data'], validation_type=vtype)
            return {'validation': result.model_dump(), 'operation': action}
        if action == 'compare':
            result = await self.validator_agent.acompare_versions(left=payload['left'], right=payload['right'])
            return {'comparison': result.model_dump(), 'operation': 'compare'}
        raise CommandError(f"Unknown validator action {command.action}")

    async def _check_permission(
        self,
        command: MegaAgentCommand,
        user_role: UserRole
    ) -> bool:
        """
        Проверка разрешений RBAC.

        Args:
            command: Команда для проверки
            user_role: Роль пользователя

        Returns:
            bool: True если разрешение есть
        """
        required_permissions = []

        # Определение требуемых разрешений по команде
        if command.command_type == CommandType.CASE:
            if command.action in ["create"]:
                required_permissions.append(Permission.CREATE_CASE)
            elif command.action in ["get", "search"]:
                required_permissions.append(Permission.READ_CASE)
            elif command.action in ["update"]:
                required_permissions.append(Permission.UPDATE_CASE)
            elif command.action in ["delete"]:
                required_permissions.append(Permission.DELETE_CASE)

        elif command.command_type == CommandType.GENERATE:
            required_permissions.append(Permission.GENERATE_DOCUMENT)

        elif command.command_type == CommandType.VALIDATE:
            required_permissions.append(Permission.VALIDATE_DOCUMENT)

        elif command.command_type == CommandType.ADMIN:
            required_permissions.append(Permission.ADMIN_ACCESS)

        # Проверка наличия разрешений у роли
        user_permissions = self.ROLE_PERMISSIONS.get(user_role, [])

        return all(perm in user_permissions for perm in required_permissions)

    async def _get_user_role(self, user_id: str) -> UserRole:
        """
        Получение роли пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            UserRole: Роль пользователя
        """
        # В реальной системе - запрос к базе данных
        # Пока используем кэш с дефолтной ролью
        if user_id not in self._user_roles:
            # Дефолтная роль для демо
            self._user_roles[user_id] = UserRole.LAWYER

        return self._user_roles[user_id]

    async def set_user_role(self, user_id: str, role: UserRole) -> None:
        """
        Установка роли пользователя (для админов).

        Args:
            user_id: ID пользователя
            role: Новая роль
        """
        self._user_roles[user_id] = role

        # Audit log изменения роли
        await self._log_audit_event(
            user_id="system",
            action="set_user_role",
            payload={
                "target_user": user_id,
                "new_role": role.value
            }
        )

    async def _log_command_start(
        self,
        command: MegaAgentCommand,
        user_role: UserRole
    ) -> None:
        """Логирование начала выполнения команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_start",
            payload={
                "command_id": command.command_id,
                "command_type": command.command_type.value,
                "action": command.action,
                "user_role": user_role.value,
                "priority": command.priority
            }
        )

    async def _log_command_completion(
        self,
        command: MegaAgentCommand,
        response: MegaAgentResponse
    ) -> None:
        """Логирование успешного завершения команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_completed",
            payload={
                "command_id": command.command_id,
                "agent_used": response.agent_used,
                "execution_time": response.execution_time,
                "success": response.success
            }
        )

    async def _log_command_error(
        self,
        command: MegaAgentCommand,
        response: MegaAgentResponse,
        error: Exception
    ) -> None:
        """Логирование ошибки команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_error",
            payload={
                "command_id": command.command_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "execution_time": response.execution_time
            }
        )

    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"mega_agent_{user_id}",
            source="mega_agent",
            action=action,
            payload=payload,
            tags=["mega_agent", "orchestration"]
        )

        await self.memory.alog_audit(event)

    def _update_stats(self, command_type: CommandType) -> None:
        """Обновление статистики команд"""
        key = command_type.value
        self._command_stats[key] = self._command_stats.get(key, 0) + 1

    async def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики работы MegaAgent.

        Returns:
            Dict[str, Any]: Статистика
        """
        return {
            "command_stats": self._command_stats.copy(),
            "total_commands": sum(self._command_stats.values()),
            "registered_users": len(self._user_roles),
            "available_agents": list(self.COMMAND_AGENT_MAPPING.values())
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка состояния системы.

        Returns:
            Dict[str, Any]: Состояние системы
        """
        try:
            # Проверка памяти
            memory_ok = self.memory is not None

            # Проверка агентов
            case_agent_ok = self.case_agent is not None

            return {
                "status": "healthy",
                "memory_system": memory_ok,
                "case_agent": case_agent_ok,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }




