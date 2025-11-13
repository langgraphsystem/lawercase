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

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
from typing import Any
import uuid

from pydantic import BaseModel, Field, ValidationError
import structlog

from ..agents import ComplexityAnalyzer, ComplexityResult, TaskTier
from ..exceptions import AgentError, MegaAgentError
from ..execution.secure_sandbox import (
    SandboxPolicy,
    SandboxRunner,
    SandboxViolation,
    ensure_tool_allowed,
)
from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent
from ..orchestration.enhanced_workflows import EnhancedWorkflowState
from ..orchestration.pipeline_manager import (
    build_enhanced_pipeline,
    build_pipeline,
    run as run_pipeline,
)
from ..orchestration.workflow_graph import WorkflowState, build_case_workflow
from ..prompts import CoTTemplate, enhance_prompt_with_cot, select_cot_template
from ..retry import with_retry
from ..security import (
    PromptInjectionResult,
    get_audit_trail,
    get_prompt_detector,
    get_rbac_manager,
    security_config,
)
from ..tools.tool_registry import get_tool_registry
from .case_agent import CaseAgent
from .eb1_agent import EB1Agent
from .models import (
    AskPayload,
    BatchTrainPayload,
    FeedbackPayload,
    ImprovePayload,
    LegalPayload,
    MemoryLookupPayload,
    OptimizePayload,
    RecommendPayload,
    SearchPayload,
    ToolCommandPayload,
    TrainPayload,
)
from .supervisor_agent import PlannedSubTask, SupervisorAgent, SupervisorTaskRequest
from .validator_agent import ValidationRequest, ValidatorAgent
from .writer_agent import DocumentRequest, DocumentType, WriterAgent

logger = structlog.get_logger(__name__)


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
    USE_TOOL = "use_tool"


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
    TOOL = "tool"
    EB1 = "eb1"  # EB-1A Immigration petitions


class MegaAgentCommand(BaseModel):
    """Модель команды для MegaAgent"""

    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID пользователя")
    command_type: CommandType = Field(..., description="Тип команды")
    action: str = Field(..., description="Действие для выполнения")
    payload: dict[str, Any] = Field(default_factory=dict, description="Данные команды")
    context: dict[str, Any] | None = Field(default=None, description="Контекст команды")
    requested_agent: str | None = Field(
        default=None, description="Желаемый агент (если указан пользователем)"
    )
    requested_tier: TaskTier | None = Field(
        default=None, description="Принудительное указание уровня исполнения"
    )
    auto_route: bool = Field(
        default=True,
        description="Если False, команде не требуется LLM-анализ маршрутизации",
    )
    priority: int = Field(default=5, ge=1, le=10, description="Приоритет (1-10)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MegaAgentResponse(BaseModel):
    """Модель ответа MegaAgent"""

    command_id: str = Field(..., description="ID команды")
    success: bool = Field(..., description="Успешность выполнения")
    result: dict[str, Any] | None = Field(default=None, description="Результат")
    error: str | None = Field(default=None, description="Ошибка")
    agent_used: str | None = Field(default=None, description="Использованный агент")
    execution_time: float | None = Field(default=None, description="Время выполнения")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tier: TaskTier | None = Field(default=None, description="Использованный уровень маршрутизации")
    routing_metadata: dict[str, Any] | None = Field(
        default=None, description="Диагностика решения роутера"
    )


@dataclass(slots=True)
class RoutingDecision:
    """Decision returned by the complexity analyzer."""

    tier: TaskTier
    score: float
    agent: str
    reason: str
    requires_supervisor: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "score": round(self.score, 3),
            "agent": self.agent,
            "reason": self.reason,
            "requires_supervisor": self.requires_supervisor,
            "metadata": self.metadata,
        }


class SecurityError(MegaAgentError):
    """Security error in MegaAgent."""

    def __init__(self, message: str, **kwargs):
        from ..exceptions import ErrorCategory, ErrorCode

        super().__init__(
            message=message,
            code=ErrorCode.PERMISSION_DENIED,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Access denied due to security policy.",
            **kwargs,
        )


class CommandError(AgentError):
    """Command execution error."""

    def __init__(self, message: str, command_type: str | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if command_type:
            details["command_type"] = command_type
        super().__init__(
            message=message,
            agent_name="MegaAgent",
            details=details,
            user_message="Command execution failed. Please try again.",
            **kwargs,
        )


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
            Permission.CREATE_CASE,
            Permission.READ_CASE,
            Permission.UPDATE_CASE,
            Permission.DELETE_CASE,
            Permission.GENERATE_DOCUMENT,
            Permission.VALIDATE_DOCUMENT,
            Permission.ADMIN_ACCESS,
            Permission.VIEW_AUDIT,
            Permission.USE_TOOL,
        ],
        UserRole.LAWYER: [
            Permission.CREATE_CASE,
            Permission.READ_CASE,
            Permission.UPDATE_CASE,
            Permission.GENERATE_DOCUMENT,
            Permission.VALIDATE_DOCUMENT,
            Permission.USE_TOOL,
        ],
        UserRole.PARALEGAL: [
            Permission.READ_CASE,
            Permission.UPDATE_CASE,
            Permission.GENERATE_DOCUMENT,
            Permission.USE_TOOL,
        ],
        UserRole.CLIENT: [Permission.READ_CASE],
        UserRole.VIEWER: [Permission.READ_CASE],
    }

    # Маппинг команд к агентам
    COMMAND_AGENT_MAPPING = {
        CommandType.CASE: "case_agent",
        CommandType.GENERATE: "writer_agent",
        CommandType.VALIDATE: "validator_agent",
        CommandType.SEARCH: "rag_pipeline_agent",
        CommandType.ASK: "supervisor_agent",
        CommandType.WORKFLOW: "workflow_system",
        CommandType.TOOL: "tool_runner",
        CommandType.EB1: "eb1_agent",
    }

    # Опциональная валидация payload через Pydantic-модели
    # COMMAND_MAP: { (command_type, action) -> (handler_name, PayloadModel) }
    COMMAND_MAP: dict[tuple[CommandType, str], tuple[str, type[BaseModel]]] = {
        (CommandType.GENERATE, "letter"): ("_handle_writer_command", DocumentRequest),
        (CommandType.VALIDATE, "document"): ("_handle_validate_command", ValidationRequest),
        (CommandType.ASK, "*"): ("_handle_ask_command", AskPayload),
        (CommandType.SEARCH, "*"): ("_handle_search_command", SearchPayload),
        (CommandType.TOOL, "*"): ("_handle_tool_command", ToolCommandPayload),
        (CommandType.TRAIN, "*"): ("_handle_train_command", TrainPayload),
        (CommandType.ADMIN, "batch_train"): ("_handle_batch_train_command", BatchTrainPayload),
        (CommandType.ADMIN, "optimize"): ("_handle_optimize_command", OptimizePayload),
        (CommandType.ADMIN, "improve"): ("_handle_improve_command", ImprovePayload),
        (CommandType.ADMIN, "memory_lookup"): (
            "_handle_memory_lookup_command",
            MemoryLookupPayload,
        ),
        (CommandType.ADMIN, "recommend"): ("_handle_recommend_command", RecommendPayload),
        (CommandType.ADMIN, "feedback"): ("_handle_feedback_command", FeedbackPayload),
        (CommandType.WORKFLOW, "*"): ("_handle_workflow_command", WorkflowState),
        (CommandType.ADMIN, "legal"): ("_handle_legal_command", LegalPayload),
    }

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        *,
        complexity_analyzer: ComplexityAnalyzer | None = None,
        supervisor_agent: SupervisorAgent | None = None,
        use_chain_of_thought: bool = True,
    ):
        """
        Инициализация MegaAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
            complexity_analyzer: Анализатор сложности задач
            supervisor_agent: Supervisor agent для планирования
            use_chain_of_thought: Enable Chain-of-Thought prompting for better reasoning (default: True)
        """
        self.memory = memory_manager or MemoryManager()
        self.complexity_analyzer = complexity_analyzer or ComplexityAnalyzer()
        self.use_cot = use_chain_of_thought

        # Инициализация агентов
        self.case_agent = CaseAgent(memory_manager=self.memory)
        self.writer_agent = WriterAgent(memory_manager=self.memory)
        self.eb1_agent = EB1Agent(memory_manager=self.memory)
        self.validator_agent = ValidatorAgent(memory_manager=self.memory)
        self.supervisor_agent = supervisor_agent or SupervisorAgent(memory_manager=self.memory)

        # Кэш пользователей и их ролей (в реальности из базы данных)
        self._user_roles: dict[str, UserRole] = {}

        # Статистика команд
        self._command_stats: dict[str, int] = {}

        # Compiled graph pool для переиспользования (thread-safe optimization)
        self._compiled_graph_pool: dict[str, Any] = {}

        # Log CoT status
        logger.info(
            "megaagent.initialized",
            use_chain_of_thought=self.use_cot,
            agents=["case", "writer", "eb1", "validator", "supervisor"],
        )

        self.rbac_manager = get_rbac_manager()
        self.prompt_detector = (
            get_prompt_detector() if security_config.prompt_detection_enabled else None
        )
        self.audit_trail = get_audit_trail() if security_config.audit_enabled else None

    async def handle_command(
        self, command: MegaAgentCommand, user_role: UserRole | None = None
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

        decision: RoutingDecision | None = None

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

            # Анализ сложности и маршрута
            decision = await self._route_command(command)

            # Маршрутизация к соответствующему агенту
            result = await self._dispatch_to_agent(command, user_role, decision)

            # Расчет времени выполнения
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Создание успешного ответа
            response = MegaAgentResponse(
                command_id=command.command_id,
                success=True,
                result=result,
                agent_used=(
                    decision.agent
                    if decision
                    else self.COMMAND_AGENT_MAPPING.get(command.command_type)
                ),
                execution_time=execution_time,
                tier=decision.tier if decision else None,
                routing_metadata=decision.to_dict() if decision else None,
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
                execution_time=execution_time,
                tier=decision.tier if decision else None,
                routing_metadata=decision.to_dict() if decision else None,
            )

            # Audit log ошибки
            await self._log_command_error(command, response, e)

            return response

    async def _route_command(self, command: MegaAgentCommand) -> RoutingDecision:
        """Определение агента и уровня исполнения для команды."""

        if command.requested_agent:
            reason = "User requested explicit agent"
            tier = command.requested_tier or TaskTier.LANGGRAPH
            return RoutingDecision(
                tier=tier,
                score=0.5,
                agent=command.requested_agent,
                reason=reason,
                requires_supervisor=command.requested_agent == "supervisor_agent",
                metadata={"source": "manual_override"},
            )

        if command.requested_tier:
            agent = self._determine_agent_from_tier(command, command.requested_tier, hint=None)
            return RoutingDecision(
                tier=command.requested_tier,
                score=0.5,
                agent=agent,
                reason="User requested explicit tier",
                requires_supervisor=command.requested_tier is TaskTier.DEEP,
                metadata={"source": "manual_override"},
            )

        if not command.auto_route:
            agent = self.COMMAND_AGENT_MAPPING.get(command.command_type, "workflow_system")
            return RoutingDecision(
                tier=TaskTier.LANGCHAIN,
                score=0.3,
                agent=agent,
                reason="Auto routing disabled",
                metadata={"source": "static_mapping"},
            )

        complexity: ComplexityResult = await self.complexity_analyzer.analyze(command)
        agent = self._determine_agent_from_tier(
            command, complexity.tier, complexity.recommended_agent
        )
        reason = complexity.reasons[-1] if complexity.reasons else "Heuristic routing"
        metadata = {
            "reasons": complexity.reasons,
            "estimated_steps": complexity.estimated_steps,
            "estimated_cost": complexity.estimated_cost,
        }
        return RoutingDecision(
            tier=complexity.tier,
            score=complexity.score,
            agent=agent,
            reason=reason,
            requires_supervisor=complexity.requires_supervisor,
            metadata=metadata,
        )

    def _determine_agent_from_tier(
        self,
        command: MegaAgentCommand,
        tier: TaskTier,
        hint: str | None = None,
    ) -> str:
        if hint:
            return hint
        if tier is TaskTier.DEEP:
            return "supervisor_agent"
        if tier is TaskTier.LANGGRAPH:
            if command.command_type in (
                CommandType.CASE,
                CommandType.GENERATE,
                CommandType.VALIDATE,
            ):
                return self.COMMAND_AGENT_MAPPING.get(command.command_type, "workflow_system")
            return "workflow_system"
        return self.COMMAND_AGENT_MAPPING.get(command.command_type, "tool_runner")

    async def _invoke_supervisor(
        self,
        command: MegaAgentCommand,
        user_role: UserRole,
        decision: RoutingDecision | None,
    ) -> dict[str, Any]:
        request = self._build_supervisor_request(command, decision)

        async def executor(step: PlannedSubTask) -> dict[str, Any]:
            return await self._execute_supervisor_step(step, command, user_role)

        result = await self.supervisor_agent.run_task(request, executor)
        return result.model_dump()

    def _build_supervisor_request(
        self, command: MegaAgentCommand, decision: RoutingDecision | None
    ) -> SupervisorTaskRequest:
        context = command.context.copy() if command.context else {}
        context.setdefault("priority", command.priority)

        # Get task description and enhance with CoT for better planning
        task_description = command.payload.get("task_description") or command.action
        # Use STRUCTURED template for supervisor tasks (complex multi-step planning)
        enhanced_task = self._enhance_with_cot(
            task_description, command, template=CoTTemplate.STRUCTURED
        )

        return SupervisorTaskRequest(
            task=enhanced_task,
            user_id=command.user_id,
            thread_id=context.get("thread_id"),
            context=context,
            constraints=command.payload.get("constraints", []),
            preferred_agents=[command.requested_agent] if command.requested_agent else [],
            metadata={
                "parent_command": command.command_id,
                "decision": decision.to_dict() if decision else None,
            },
        )

    async def _execute_supervisor_step(
        self,
        step: PlannedSubTask,
        parent_command: MegaAgentCommand,
        user_role: UserRole,
    ) -> dict[str, Any]:
        try:
            command_type = CommandType(step.command_type)
        except ValueError:
            command_type = CommandType.ASK

        requested_tier = None
        if step.requested_tier:
            try:
                requested_tier = TaskTier(step.requested_tier)
            except ValueError:
                requested_tier = None

        context = dict(parent_command.context or {})
        trace = list(context.get("supervisor_trace", []))
        trace.append({"step_id": step.id, "description": step.description})
        context["supervisor_trace"] = trace

        sub_command = MegaAgentCommand(
            user_id=parent_command.user_id,
            command_type=command_type,
            action=step.action,
            payload=step.payload,
            context=context,
            priority=parent_command.priority,
            requested_agent=step.expected_agent,
            requested_tier=requested_tier,
            auto_route=step.expected_agent is None,
        )

        return await self._dispatch_to_agent(
            sub_command,
            user_role,
            None,
            preferred_agent=step.expected_agent,
        )

    async def _dispatch_to_agent(
        self,
        command: MegaAgentCommand,
        user_role: UserRole,
        decision: RoutingDecision | None = None,
        *,
        preferred_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        Маршрутизация команды к соответствующему агенту.

        Args:
            command: Команда для выполнения

        Returns:
            Dict[str, Any]: Результат выполнения

        Raises:
            CommandError: При ошибках маршрутизации
        """
        agent_name = preferred_agent
        if not agent_name:
            if decision:
                agent_name = decision.agent
            else:
                agent_name = self.COMMAND_AGENT_MAPPING.get(command.command_type)

        if not agent_name:
            raise CommandError(f"Unknown command type: {command.command_type}")

        self._enforce_permission(user_role, command)

        # Валидируем payload по COMMAND_MAP, если модель указана
        try:
            key = (command.command_type, (command.action or "").lower())
            _handler_name, model_cls = self.COMMAND_MAP.get(key, ("", None))  # type: ignore
            if not model_cls:
                # Fallback to wildcard mapping for this command type
                key_any = (command.command_type, "*")
                _handler_name, model_cls = self.COMMAND_MAP.get(key_any, ("", None))  # type: ignore
            if model_cls is not None:
                # Провалидировать payload и заменить на dict
                model_obj = model_cls.model_validate(command.payload)
                command.payload = model_obj.model_dump()
        except ValidationError as ve:
            raise CommandError(f"Payload validation failed: {ve}")

        # Маршрутизация к case_agent через LangGraph workflow
        if agent_name == "case_agent":
            return await self._handle_case_command(command)

        if agent_name == "writer_agent":
            return await self._handle_writer_command(command)

        # Маршрутизация к workflow_system (использует тот же workflow)
        if agent_name == "workflow_system":
            return await self._handle_workflow_command(command, user_role)

        if agent_name == "tool_runner":
            return await self._handle_tool_command(command, user_role)

        # Базовая интеграция для ASK: memory workflow (log→reflect→retrieve→rmt)
        if agent_name == "supervisor_agent":
            if command.command_type == CommandType.ASK and not (
                decision and decision.requires_supervisor
            ):
                return await self._handle_ask_command(command)
            return await self._invoke_supervisor(command, user_role, decision)

        # Базовый SEARCH: прямой поиск по семантической памяти
        if agent_name == "rag_pipeline_agent":
            return await self._handle_search_command(command)

        # EB-1A Immigration петиции
        if agent_name == "eb1_agent":
            return await self._handle_eb1_command(command)

        # Placeholder для других агентов
        return {
            "message": f"Agent {agent_name} not yet implemented",
            "command": command.action,
            "agent": agent_name,
        }

    def _permission_for_command(self, command: MegaAgentCommand) -> tuple[str, str]:
        action = (command.action or "").lower() or "read"
        ct = command.command_type
        if ct == CommandType.CASE:
            return (f"case:{action}", "case")
        if ct == CommandType.GENERATE:
            return (f"document:{action}", "document")
        if ct == CommandType.VALIDATE:
            return ("document:validate", "document")
        if ct == CommandType.TRAIN:
            return (f"model:{action}", "model")
        if ct == CommandType.SEARCH:
            return ("memory:read", "memory")
        if ct == CommandType.ASK:
            return ("memory:read", "memory")
        if ct == CommandType.WORKFLOW:
            return (f"workflow:{action}", "workflow")
        if ct == CommandType.TOOL:
            return (f"tool:{action or 'use'}", "tool")
        if ct == CommandType.ADMIN:
            return (f"admin:{action}", "admin")
        return ("*", "*")

    def _enforce_permission(self, user_role: UserRole, command: MegaAgentCommand) -> None:
        if not security_config.rbac_strict_mode:
            return
        action, resource = self._permission_for_command(command)
        context = dict(command.context or {})
        payload_tags = command.payload.get("tags") if isinstance(command.payload, dict) else None
        if payload_tags:
            context.setdefault("tags", [])
            context["tags"].extend(
                payload_tags if isinstance(payload_tags, list) else [payload_tags]
            )
        context.setdefault("time", context.get("time") or datetime.utcnow().strftime("%H:%M"))
        context.setdefault("mfa_verified", context.get("mfa_verified", False))
        allowed = self.rbac_manager.check_permission(
            user_role.value,
            action,
            resource,
            context=context,
        )
        if not allowed:
            raise SecurityError(
                f"Role '{user_role.value}' lacks permission for {action} on {resource}"
            )

    def _check_prompt_injection(
        self, text: str, *, context: dict[str, Any] | None = None
    ) -> PromptInjectionResult | None:
        if not text or not self.prompt_detector or not security_config.prompt_detection_enabled:
            return None

        result = self.prompt_detector.analyze(text, context=context)
        if result.is_injection:
            raise CommandError("Prompt blocked due to suspected injection attempt")
        return result

    def _enhance_with_cot(
        self, prompt: str, command: MegaAgentCommand, template: CoTTemplate | None = None
    ) -> str:
        """Enhance prompt with Chain-of-Thought reasoning.

        Automatically applies CoT templates to improve LLM reasoning quality.
        Uses command type and action to select optimal template.

        Args:
            prompt: Original prompt text
            command: Command being executed (for template selection)
            template: Optional specific template to use

        Returns:
            CoT-enhanced prompt

        Example:
            >>> enhanced = self._enhance_with_cot("Analyze this evidence", command)
            >>> # Returns prompt with analytical CoT template
        """
        if not self.use_cot:
            # CoT disabled, return original
            return prompt

        # Select template based on command if not provided
        if template is None:
            template = select_cot_template(
                command_type=command.command_type.value, action=command.action
            )

        # Apply CoT enhancement
        enhanced = enhance_prompt_with_cot(
            prompt, command_type=command.command_type.value, action=command.action
        )

        logger.debug(
            "megaagent.cot.enhanced",
            command_id=command.command_id,
            command_type=command.command_type.value,
            action=command.action,
            template=template.value,
            original_length=len(prompt),
            enhanced_length=len(enhanced),
        )

        return enhanced

    async def _handle_case_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка команд case_agent"""
        state = await self._run_case_workflow(
            operation=command.action,
            payload=command.payload,
            user_id=command.user_id,
        )
        return self._format_case_response(state)

    async def _handle_workflow_command(
        self, command: MegaAgentCommand, user_role: UserRole
    ) -> dict[str, Any]:
        """Обработка команд workflow system"""
        action = (command.action or "").lower()
        if action == "enhanced_memory":
            return await self._handle_enhanced_memory_command(command)

        state = await self._run_case_workflow(
            operation=command.action,
            payload=command.payload,
            user_id=command.user_id,
        )
        response = self._format_case_response(state)
        response["operation"] = command.action
        response["workflow"] = "case"
        return response

    async def _handle_enhanced_memory_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Запуск расширенного workflow с человеческими review и оптимизацией."""
        payload = dict(command.payload or {})
        query = payload.get("query") or command.payload.get("query") if command.payload else None
        if not query:
            raise CommandError("enhanced_memory workflow requires 'query' in payload")

        thread_id = payload.get("thread_id") or command.command_id
        event_payload = payload.get("event") or {}

        detection = self._check_prompt_injection(query, context=command.context)

        event = AuditEvent(
            event_id=event_payload.get("event_id", str(uuid.uuid4())),
            timestamp=event_payload.get("timestamp", datetime.utcnow()),
            user_id=command.user_id,
            thread_id=thread_id,
            source=event_payload.get("source", "mega_agent"),
            action=event_payload.get("action", "enhanced_memory"),
            payload=event_payload.get("payload", {}),
        )

        initial_state = EnhancedWorkflowState(
            thread_id=thread_id,
            user_id=command.user_id,
            query=query,
            event=event,
        )

        pipeline = build_enhanced_pipeline(self.memory)
        final_state = await run_pipeline(pipeline, initial_state, thread_id=thread_id)

        if isinstance(final_state, dict):
            values = list(final_state.values())
            if values and isinstance(values[0], dict):
                final_state = EnhancedWorkflowState.model_validate(values[0])
            else:
                final_state = EnhancedWorkflowState.model_validate(final_state)

        response = {
            "operation": "enhanced_memory",
            "workflow": "enhanced",
            "state": final_state.model_dump(),
        }
        if detection:
            response["prompt_analysis"] = {
                "score": detection.confidence,
                "issues": detection.injection_types,
            }
        return response

    async def _handle_writer_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка команд writer_agent"""
        action = (command.action or "").lower()
        payload: dict[str, Any] = dict(command.payload or {})

        if action in {"letter", "generate_letter"}:
            payload.setdefault("document_type", DocumentType.LETTER)
            try:
                request = DocumentRequest(**payload)
            except ValidationError as exc:
                raise CommandError(f"Invalid document request: {exc}") from exc

            document = await self.writer_agent.agenerate_letter(request, command.user_id)
            return {
                "operation": "generate_letter",
                "document_id": document.document_id,
                "document": document.model_dump(),
            }

        if action in {"generate_pdf", "pdf"}:
            document_id = payload.get("document_id")
            if not document_id:
                raise CommandError("document_id required for generate_pdf action")
            pdf_path = await self.writer_agent.agenerate_document_pdf(document_id, command.user_id)
            return {
                "operation": "generate_pdf",
                "document_id": document_id,
                "pdf_path": pdf_path,
            }

        if action == "get":
            document_id = payload.get("document_id")
            if not document_id:
                raise CommandError("document_id required for get action")
            document = await self.writer_agent.aget_document(document_id, command.user_id)
            return {
                "operation": "get_document",
                "document_id": document_id,
                "document": document.model_dump(),
            }

        raise CommandError(f"Unknown writer action: {command.action}")

    async def _handle_train_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = TrainPayload.model_validate(command.payload)
        # persist samples into semantic memory
        records = []
        for s in payload.samples:
            text = s.get("text") or s.get("content") or ""
            if not text:
                continue
            records.append(
                {
                    "text": text,
                    "user_id": command.user_id,
                    "type": "semantic",
                    "metadata": {"tags": payload.tags},
                }
            )
        if records:
            await self.memory.awrite(records)  # type: ignore[arg-type]
        return {"operation": "train", "ingested": len(records)}

    async def _handle_recommend_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = RecommendPayload.model_validate(command.payload)
        # simple stub: return topk placeholders
        recs = [
            {"id": f"rec_{i + 1}", "text": payload.context[:80], "score": 1 - i * 0.1}
            for i in range(payload.topk or 5)
        ]
        return {"operation": "recommend", "items": recs}

    async def _handle_feedback_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = FeedbackPayload.model_validate(command.payload)
        await self._log_audit_event(
            user_id=command.user_id,
            action="feedback",
            payload={"target_id": payload.target_id, "rating": payload.rating},
        )
        return {"operation": "feedback", "ok": True}

    async def _handle_legal_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        from ..legal.contract_analyzer import ContractAnalyzer
        from ..legal.document_parser import DocumentParser

        payload = LegalPayload.model_validate(command.payload)
        parser = DocumentParser()
        doc = parser.parse(payload.text)

        if payload.action == "parse":
            return {"operation": "legal.parse", "doc_type": doc.doc_type.value, "title": doc.title}
        if payload.action == "analyze":
            analyzer = ContractAnalyzer()
            result = analyzer.analyze(doc)
            return {"operation": "legal.analyze", "risk": result.overall_risk_score}
        return {"operation": "legal", "doc_type": doc.doc_type.value}

    async def _handle_improve_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = ImprovePayload.model_validate(command.payload)
        improved = payload.text.strip()
        return {"operation": "improve", "goal": payload.goal, "text": improved}

    async def _handle_optimize_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = OptimizePayload.model_validate(command.payload)
        optimized = payload.text.strip()
        return {"operation": "optimize", "target": payload.target, "text": optimized}

    async def _handle_memory_lookup_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = MemoryLookupPayload.model_validate(command.payload)
        results = await self.memory.aretrieve(
            query=payload.query,
            user_id=command.user_id,
            topk=payload.topk or 8,
            filters=payload.filters or {},
        )
        return {
            "operation": "memory_lookup",
            "count": len(results),
            "results": [r.model_dump() for r in results],
        }

    async def _handle_batch_train_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        payload = BatchTrainPayload.model_validate(command.payload)
        ingested = 0
        for batch in payload.batches:
            sub_cmd = MegaAgentCommand(
                user_id=command.user_id,
                command_type=CommandType.TRAIN,
                action="ingest",
                payload=batch.model_dump(),
            )
            r = await self._handle_train_command(sub_cmd)
            ingested += int(r.get("ingested", 0))
        return {"operation": "batch_train", "ingested": ingested}

    async def _handle_validate_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка команд валидации через ValidatorAgent."""
        action = (command.action or "").lower()
        payload = dict(command.payload or {})

        if action in {"document", "validate", "avalidate"}:
            # Ожидаем payload, совместимый с ValidationRequest
            try:
                request = ValidationRequest.model_validate(payload)
            except ValidationError as e:
                raise CommandError(f"Invalid validation payload: {e}") from e

            report = await self.validator_agent.avalidate_document(request)
            return {
                "operation": "validate_document",
                "report_id": report.report_id,
                "overall_result": report.overall_result.model_dump(),
                "issues": [i.model_dump() for i in report.issues],
            }

        raise CommandError(f"Unknown validate action: {command.action}")

    @with_retry(max_attempts=3, exceptions=(Exception,), wait_min=0.2, wait_max=2.0)
    async def _handle_tool_command(
        self, command: MegaAgentCommand, user_role: UserRole
    ) -> dict[str, Any]:
        """Execute registered tool within sandbox policy."""

        payload = dict(command.payload or {})
        tool_id = payload.get("tool_id")
        if not tool_id:
            raise CommandError("tool_id is required for TOOL commands")

        arguments = payload.get("arguments") or {}
        timeout = float(payload.get("timeout", 2.0))
        network = bool(payload.get("network", False))
        filesystem = bool(payload.get("filesystem", False))

        registry = get_tool_registry()
        metadata = registry.get_metadata(tool_id)

        policy = SandboxPolicy(
            name=str(payload.get("policy", "default")),
            description=f"Sandbox for tool {tool_id}",
            allowed_tools={tool_id},
            network_access=network,
            filesystem_access=filesystem,
            max_cpu_seconds=timeout,
            max_memory_mb=int(payload.get("memory_mb", 256)),
        )

        ensure_tool_allowed(policy, tool_id)
        runner = SandboxRunner(policy)

        async def _invoke():
            return await registry.invoke(
                tool_id,
                caller_role=user_role.value,
                arguments=arguments,
            )

        try:
            result = await runner.run_async(_invoke, timeout=timeout)
        except SandboxViolation as exc:
            raise CommandError(str(exc)) from exc

        return {
            "operation": "tool",
            "tool_id": tool_id,
            "result": result,
            "metadata": {
                "policy": policy.name,
                "network": policy.network_access,
                "filesystem": policy.filesystem_access,
                "allowed_roles": list(metadata.allowed_roles),
                "tags": list(metadata.tags),
            },
        }

    async def _handle_ask_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка ASK: прогон через memory workflow и возврат контекста.

        Ожидает в payload:
            - query: str — пользовательский вопрос
        """
        query = str((command.payload or {}).get("query", "")).strip()
        if not query:
            raise CommandError("ASK requires 'query' in payload")

        logger.info(
            "mega.ask.start",
            command_id=command.command_id,
            user_id=command.user_id,
            query_length=len(query),
        )

        detection = self._check_prompt_injection(query, context=command.context)
        if detection:
            logger.warning(
                "mega.ask.prompt_injection_detected",
                command_id=command.command_id,
                user_id=command.user_id,
                score=detection.confidence,
                issues=detection.injection_types,
            )

        # Формируем AuditEvent для трассировки
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=command.user_id,
            thread_id=f"ask_{uuid.uuid4().hex[:8]}",
            source="mega_agent",
            action="ask",
            payload={"summary": query},
            tags=["ask", "milestone"],
        )

        # Собираем и запускаем граф памяти
        graph_exec = build_pipeline(self.memory)
        initial = WorkflowState(
            thread_id=event.thread_id or str(uuid.uuid4()),
            user_id=command.user_id,
            event=event,
            query=query,
        )
        final = await run_pipeline(graph_exec, initial)
        logger.info(
            "mega.ask.memory_complete",
            command_id=command.command_id,
            user_id=command.user_id,
            retrieved=len(final.retrieved),
            reflected=len(final.reflected),
            rmt_slots=len(final.rmt_slots or []),
        )

        response: dict[str, Any] = {
            "operation": "ask",
            "thread_id": final.thread_id,
            "rmt_slots": final.rmt_slots,
            "reflected": [r.model_dump() for r in final.reflected],
            "retrieved": [r.model_dump() for r in final.retrieved],
        }
        if detection:
            response["prompt_analysis"] = {
                "score": detection.confidence,
                "issues": detection.injection_types,
            }

        # Optional: generate a natural-language answer using configured LLM
        # Prefer OpenAI, then Anthropic, then Gemini. If no keys configured, skip.
        try:
            import os

            openai_key = os.getenv("OPENAI_API_KEY")
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            try:
                logger.info(
                    "ask.llm.keys",
                    openai=bool(openai_key),
                    anthropic=bool(anthropic_key),
                    gemini=bool(gemini_key),
                )
            except Exception:  # nosec B110 - logging is best-effort
                pass

            provider_used = None
            llm_text: str | None = None

            # Build concise context for the model from retrieved memory
            if final.retrieved:
                top_facts = []
                for rec in final.retrieved[:5]:
                    try:
                        top_facts.append(
                            getattr(rec, "text", "") or rec.model_dump().get("text", "")
                        )
                    except Exception:  # nosec B112 - continue is safe for parsing optional fields
                        continue
                context_blob = "\n".join(f"- {t}" for t in top_facts if t)
            else:
                context_blob = ""

            prompt = (
                "You are MegaAgent Pro assistant. Answer the user question clearly and concisely.\n"
                "If helpful, use the provided context. If context is insufficient, answer generally and state any assumptions.\n\n"
                f"User question: {query}\n\n"
                f"Context (may be empty):\n{context_blob}"
            ).strip()

            # Apply Chain-of-Thought enhancement for better reasoning
            prompt = self._enhance_with_cot(prompt, command)

            logger.info(
                "mega.ask.prompt_built",
                command_id=command.command_id,
                user_id=command.user_id,
                prompt_length=len(prompt),
                context_length=len(context_blob),
            )

            if openai_key:
                # OpenAI via SDK wrapper (core/llm_interface/openai_client.py)
                # Respect environment model/config to match SDK handlers
                try:
                    import os

                    from core.llm_interface.openai_client import OpenAIClient

                    model_env = os.getenv("OPENAI_DEFAULT_MODEL")
                    # Prefer env override; default to gpt-5-mini for cost if unset
                    model_name = model_env or OpenAIClient.GPT_5_MINI
                    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
                    verbosity = os.getenv("OPENAI_VERBOSITY", "medium")
                    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "medium")

                    client = OpenAIClient(
                        model=model_name,
                        api_key=openai_key,
                        temperature=temperature,
                        verbosity=verbosity,
                        reasoning_effort=reasoning_effort,
                    )
                    # Allow max tokens override to align with SDK usage
                    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
                    logger.info(
                        "mega.ask.llm.request",
                        command_id=command.command_id,
                        provider="openai",
                        model=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        verbosity=verbosity,
                        reasoning_effort=reasoning_effort,
                    )
                    result = await client.acomplete(prompt, max_tokens=max_tokens)
                    llm_text = result.get("output") or result.get("response")
                    provider_used = result.get("provider", "openai")
                    response["llm_model"] = result.get("model")
                    # DEBUG: Log OpenAI result to diagnose missing response
                    logger.info(
                        "ask.openai.result",
                        has_output=bool(result.get("output")),
                        output_length=len(result.get("output") or ""),
                        llm_text_length=len(llm_text or ""),
                        finish_reason=result.get("finish_reason"),
                    )
                    response.setdefault("llm_params", {})
                    response["llm_params"].update(
                        {
                            "verbosity": verbosity,
                            "reasoning_effort": reasoning_effort,
                            "max_tokens": max_tokens,
                        }
                    )
                    logger.info(
                        "mega.ask.llm.response",
                        command_id=command.command_id,
                        provider="openai",
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        completion_tokens=((result.get("usage") or {}).get("completion_tokens")),
                        output_length=len(llm_text or ""),
                    )
                except Exception as e:  # pragma: no cover - external dependency branch
                    try:
                        logger.exception("ask.llm.error", provider="openai", error=str(e))
                    except Exception:  # nosec B110 - logging is best-effort
                        pass
                    response.setdefault("llm_error", str(e))
            elif anthropic_key:
                # Anthropic
                try:
                    from core.llm_interface.anthropic_client import AnthropicClient

                    client = AnthropicClient(
                        model=AnthropicClient.CLAUDE_HAIKU_3_5,
                        api_key=anthropic_key,
                        temperature=0.2,
                    )
                    logger.info(
                        "mega.ask.llm.request",
                        command_id=command.command_id,
                        provider="anthropic",
                        model=AnthropicClient.CLAUDE_HAIKU_3_5,
                        max_tokens=800,
                    )
                    result = await client.acomplete(prompt, max_tokens=800)
                    llm_text = result.get("output") or result.get("response")
                    provider_used = result.get("provider", "anthropic")
                    response["llm_model"] = result.get("model")
                    logger.info(
                        "mega.ask.llm.response",
                        command_id=command.command_id,
                        provider="anthropic",
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        completion_tokens=((result.get("usage") or {}).get("completion_tokens")),
                        output_length=len(llm_text or ""),
                    )
                except Exception as e:  # pragma: no cover
                    try:
                        logger.exception("ask.llm.error", provider="anthropic", error=str(e))
                    except Exception:  # nosec B110 - logging is best-effort
                        pass
                    response.setdefault("llm_error", str(e))
            elif gemini_key:
                # Google Gemini
                try:
                    from core.llm_interface.gemini_client import GeminiClient

                    client = GeminiClient(
                        model=GeminiClient.GEMINI_2_5_FLASH, api_key=gemini_key, temperature=0.2
                    )
                    logger.info(
                        "mega.ask.llm.request",
                        command_id=command.command_id,
                        provider="gemini",
                        model=GeminiClient.GEMINI_2_5_FLASH,
                        max_tokens=800,
                    )
                    result = await client.acomplete(prompt, max_output_tokens=800)
                    llm_text = result.get("output") or result.get("response")
                    provider_used = result.get("provider", "gemini")
                    response["llm_model"] = result.get("model")
                    logger.info(
                        "mega.ask.llm.response",
                        command_id=command.command_id,
                        provider="gemini",
                        model=result.get("model"),
                        finish_reason=result.get("finish_reason"),
                        completion_tokens=((result.get("usage") or {}).get("completion_tokens")),
                        output_length=len(llm_text or ""),
                    )
                except Exception as e:  # pragma: no cover
                    try:
                        logger.exception("ask.llm.error", provider="gemini", error=str(e))
                    except Exception:  # nosec B110 - logging is best-effort
                        pass
                    response.setdefault("llm_error", str(e))

            if llm_text:
                # DEBUG: Log exact type and content before setting response
                logger.info(
                    "ask.llm_text.debug",
                    llm_text_type=type(llm_text).__name__,
                    llm_text_repr=repr(
                        llm_text[:200] if isinstance(llm_text, str) else str(llm_text)[:200]
                    ),
                    llm_text_length=(
                        len(llm_text) if isinstance(llm_text, str) else len(str(llm_text))
                    ),
                )
                response["llm_response"] = llm_text
                response["llm_provider"] = provider_used
                logger.info(
                    "mega.ask.llm_result_attached",
                    command_id=command.command_id,
                    provider=provider_used,
                    output_length=len(llm_text) if isinstance(llm_text, str) else None,
                )

        except Exception as e:  # pragma: no cover - defensive guard
            # Don't fail ASK due to LLM errors
            response.setdefault("llm_error", str(e))
            logger.exception(
                "mega.ask.llm_exception",
                command_id=command.command_id,
                user_id=command.user_id,
                error=str(e),
            )
        finally:
            try:
                if not response.get("llm_response"):
                    reason = response.get("llm_error") or (
                        "no_api_keys"
                        if not (
                            os.getenv("OPENAI_API_KEY")
                            or os.getenv("ANTHROPIC_API_KEY")
                            or os.getenv("GEMINI_API_KEY")
                            or os.getenv("GOOGLE_API_KEY")
                        )
                        else "no_llm_output"
                    )
                    logger.info("ask.llm.missing_output", reason=reason)
            except Exception:  # nosec B110 - logging is best-effort
                pass

        logger.info(
            "mega.ask.completed",
            command_id=command.command_id,
            user_id=command.user_id,
            has_llm_response=bool(response.get("llm_response")),
            prompt_analysis=bool(response.get("prompt_analysis")),
        )

        return response

    async def _handle_search_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка SEARCH: упрощенный поиск по памяти.

        Ожидает в payload:
            - query: str
            - topk: int (optional)
            - filters: dict (optional)
        """
        payload = dict(command.payload or {})
        query = str(payload.get("query", "")).strip()
        if not query:
            raise CommandError("SEARCH requires 'query' in payload")
        topk = int(payload.get("topk", 8))
        filters = payload.get("filters") or {}

        detection = self._check_prompt_injection(query, context=command.context)

        results = await self.memory.aretrieve(
            query=query, user_id=command.user_id, topk=topk, filters=filters
        )
        response = {
            "operation": "search",
            "query": query,
            "count": len(results),
            "results": [r.model_dump() for r in results],
        }
        if detection:
            response["prompt_analysis"] = {
                "score": detection.confidence,
                "issues": detection.injection_types,
            }
        return response

    async def _handle_eb1_command(self, command: MegaAgentCommand) -> dict[str, Any]:
        """Обработка EB-1A команд: создание петиций и интерактивный опросник.

        Поддерживаемые действия:
            - create: Создание новой EB-1A петиции
            - message: Обработка сообщения пользователя в контексте петиции
            - status: Получение статуса петиции
            - get: Получение полных данных петиции
        """
        action = (command.action or "").lower()
        payload = dict(command.payload or {})

        if action == "create":
            # Создание новой петиции
            petition, welcome_msg = await self.eb1_agent.create_petition(command.user_id)

            return {
                "operation": "create_eb1_petition",
                "petition_id": petition.petition_id,
                "status": petition.status.value,
                "message": welcome_msg,
                "awaiting_input": True,
            }

        if action == "message":
            # Обработка сообщения пользователя
            petition_id = payload.get("petition_id")
            user_message = payload.get("message", "")

            if not petition_id:
                raise CommandError("petition_id required for message action")

            bot_response = await self.eb1_agent.process_user_message(
                petition_id, user_message, command.user_id
            )

            return {
                "operation": "eb1_message",
                "petition_id": petition_id,
                "bot_response": bot_response,
                "awaiting_input": True,
            }

        if action == "status":
            # Получение статуса
            petition_id = payload.get("petition_id")
            if not petition_id:
                raise CommandError("petition_id required for status action")

            status = await self.eb1_agent.get_petition_status(petition_id)

            return {
                "operation": "eb1_status",
                **status,
            }

        if action == "get":
            # Получение полных данных
            petition_id = payload.get("petition_id")
            if not petition_id:
                raise CommandError("petition_id required for get action")

            petition = await self.eb1_agent.get_petition(petition_id)
            if not petition:
                raise CommandError(f"Petition {petition_id} not found")

            return {
                "operation": "get_eb1_petition",
                "petition": petition.model_dump(),
            }

        raise CommandError(f"Unknown EB1 action: {action}")

    async def _run_case_workflow(
        self,
        *,
        operation: str,
        payload: dict[str, Any],
        user_id: str,
    ) -> WorkflowState:
        # Thread-safe ID generation with timestamp and randomness
        # Format: {user_id}_{microseconds}_{uuid_hex}
        thread_id = f"{user_id}_{int(time.time() * 1000000)}_{uuid.uuid4().hex[:8]}"

        # Use connection pooling for compiled graph (cache by operation type)
        cache_key = f"case_{operation}"
        if cache_key not in self._compiled_graph_pool:
            graph = build_case_workflow(self.memory, case_agent=self.case_agent)
            self._compiled_graph_pool[cache_key] = graph.compile()

        compiled = self._compiled_graph_pool[cache_key]

        initial = WorkflowState(
            thread_id=thread_id,
            user_id=user_id,
            case_operation=operation,
            case_data=payload,
            case_id=payload.get("case_id"),
        )
        final_state = await run_pipeline(compiled, initial, thread_id=thread_id)

        if isinstance(final_state, dict):
            candidate = (
                final_state.get("update_rmt")
                or final_state.get("case_agent")
                or final_state.get("audit")
                or final_state.get("reflect")
                or next(iter(final_state.values()), None)
            )
            if isinstance(candidate, WorkflowState):
                final_state = candidate
            elif isinstance(candidate, dict):
                final_state = WorkflowState.model_validate(candidate)
            else:
                final_state = candidate

        if not isinstance(final_state, WorkflowState):
            raise CommandError("Unexpected workflow result type")

        if final_state.error:
            raise CommandError(final_state.error)

        return final_state

    @staticmethod
    def _format_case_response(state: WorkflowState) -> dict[str, Any]:
        result: dict[str, Any] = {
            "case_result": state.case_result or {},
            "thread_id": state.thread_id,
        }
        if state.case_id:
            result["case_id"] = state.case_id
        if state.rmt_slots:
            result["rmt_slots"] = state.rmt_slots
        if state.reflected:
            result["reflected_count"] = len(state.reflected)
        if state.retrieved:
            result["retrieved_count"] = len(state.retrieved)
        return result

    async def _check_permission(self, command: MegaAgentCommand, user_role: UserRole) -> bool:
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

        elif command.command_type == CommandType.TOOL:
            required_permissions.append(Permission.USE_TOOL)

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
            payload={"target_user": user_id, "new_role": role.value},
            resource="rbac",
            tags=["rbac", "role"],
        )

    async def _log_command_start(self, command: MegaAgentCommand, user_role: UserRole) -> None:
        """Логирование начала выполнения команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_start",
            payload={
                "command_id": command.command_id,
                "command_type": command.command_type.value,
                "action": command.action,
                "user_role": user_role.value,
                "priority": command.priority,
            },
            resource="command",
            tags=["mega_agent", "command"],
        )

    async def _log_command_completion(
        self, command: MegaAgentCommand, response: MegaAgentResponse
    ) -> None:
        """Логирование успешного завершения команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_completed",
            payload={
                "command_id": command.command_id,
                "agent_used": response.agent_used,
                "execution_time": response.execution_time,
                "success": response.success,
            },
            resource="command",
            tags=["mega_agent", "command"],
        )

    async def _log_command_error(
        self, command: MegaAgentCommand, response: MegaAgentResponse, error: Exception
    ) -> None:
        """Логирование ошибки команды"""
        await self._log_audit_event(
            user_id=command.user_id,
            action="command_error",
            payload={
                "command_id": command.command_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "execution_time": response.execution_time,
            },
            resource="command",
            tags=["mega_agent", "command", "error"],
        )

    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        payload: dict[str, Any],
        *,
        resource: str = "mega_agent",
        tags: list[str] | None = None,
    ) -> None:
        """Централизованное логирование audit событий"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"mega_agent_{user_id}",
            source="mega_agent",
            action=action,
            payload=payload,
            tags=tags or ["mega_agent", "orchestration"],
        )

        await self.memory.alog_audit(event)
        # Note: AuditTrail.log_event() requires different parameters than record_event()
        # Structlog already provides comprehensive logging, so we skip AuditTrail for now
        # if self.audit_trail and security_config.audit_enabled:
        #     self.audit_trail.log_event(
        #         event_type=...,
        #         user_id=user_id,
        #         resource_type=resource,
        #         resource_id=None,
        #         action=action,
        #         result="success",
        #         details=payload,
        #     )

    def _update_stats(self, command_type: CommandType) -> None:
        """Обновление статистики команд"""
        key = command_type.value
        self._command_stats[key] = self._command_stats.get(key, 0) + 1

    async def get_stats(self) -> dict[str, Any]:
        """
        Получение статистики работы MegaAgent.

        Returns:
            Dict[str, Any]: Статистика
        """
        return {
            "command_stats": self._command_stats.copy(),
            "total_commands": sum(self._command_stats.values()),
            "registered_users": len(self._user_roles),
            "available_agents": list(self.COMMAND_AGENT_MAPPING.values()),
        }

    async def health_check(self) -> dict[str, Any]:
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
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
