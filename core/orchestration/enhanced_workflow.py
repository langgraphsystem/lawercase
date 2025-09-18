"""
Enhanced Workflow System with advanced patterns and features.

Provides:
- Fan-out/Fan-in patterns for parallel processing
- Error recovery mechanisms
- Human-in-the-loop checkpoints
- Workflow interrupts and resuming
- Complex workflow orchestration
- Conditional routing with branching
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent


class WorkflowPattern(str, Enum):
    """Паттерны выполнения workflow"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    PIPELINE = "pipeline"
    SCATTER_GATHER = "scatter_gather"
    CONDITIONAL_BRANCH = "conditional_branch"
    HUMAN_IN_LOOP = "human_in_loop"


class WorkflowStatus(str, Enum):
    """Статусы workflow"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckpointType(str, Enum):
    """Типы контрольных точек"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    ERROR_RECOVERY = "error_recovery"
    HUMAN_APPROVAL = "human_approval"
    CONDITIONAL = "conditional"


class WorkflowNode(BaseModel):
    """Узел workflow"""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название узла")
    node_type: str = Field(..., description="Тип узла")
    agent_type: Optional[str] = Field(None, description="Тип агента")
    execution_function: Optional[str] = Field(None, description="Функция выполнения")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Схема входных данных")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Схема выходных данных")
    retry_config: Dict[str, Any] = Field(default_factory=dict, description="Конфигурация повторов")
    timeout_seconds: Optional[int] = Field(None, description="Таймаут выполнения")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости от других узлов")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные узла")


class WorkflowEdge(BaseModel):
    """Связь между узлами workflow"""
    edge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node: str = Field(..., description="Исходный узел")
    to_node: str = Field(..., description="Целевой узел")
    condition: Optional[str] = Field(None, description="Условие перехода")
    condition_function: Optional[str] = Field(None, description="Функция условия")
    weight: float = Field(default=1.0, description="Вес связи")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные связи")


class WorkflowCheckpoint(BaseModel):
    """Контрольная точка workflow"""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="ID workflow")
    checkpoint_type: CheckpointType = Field(..., description="Тип контрольной точки")
    node_id: str = Field(..., description="ID узла")
    state_snapshot: Dict[str, Any] = Field(..., description="Снимок состояния")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Время истечения")
    human_approver: Optional[str] = Field(None, description="ID одобряющего")
    approval_status: Optional[str] = Field(None, description="Статус одобрения")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")


class WorkflowExecution(BaseModel):
    """Выполнение workflow"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="ID workflow")
    user_id: str = Field(..., description="ID пользователя")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Статус")
    pattern: WorkflowPattern = Field(..., description="Паттерн выполнения")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Входные данные")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Выходные данные")
    current_node: Optional[str] = Field(None, description="Текущий узел")
    completed_nodes: List[str] = Field(default_factory=list, description="Завершенные узлы")
    failed_nodes: List[str] = Field(default_factory=list, description="Неудачные узлы")
    checkpoints: List[str] = Field(default_factory=list, description="ID контрольных точек")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Время завершения")
    execution_time: Optional[float] = Field(None, description="Время выполнения")


class WorkflowDefinition(BaseModel):
    """Определение workflow"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название workflow")
    description: str = Field(..., description="Описание workflow")
    version: str = Field(default="1.0", description="Версия workflow")
    pattern: WorkflowPattern = Field(..., description="Паттерн выполнения")
    nodes: List[WorkflowNode] = Field(..., description="Узлы workflow")
    edges: List[WorkflowEdge] = Field(..., description="Связи между узлами")
    entry_point: str = Field(..., description="Точка входа")
    exit_points: List[str] = Field(..., description="Точки выхода")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Политика повторов")
    timeout_policy: Dict[str, Any] = Field(default_factory=dict, description="Политика таймаутов")
    checkpoint_config: Dict[str, Any] = Field(default_factory=dict, description="Конфигурация чекпоинтов")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Создатель workflow")


class EnhancedWorkflowEngine:
    """
    Расширенный движок workflow с поддержкой сложных паттернов.

    Возможности:
    - Множественные паттерны выполнения
    - Контрольные точки и восстановление
    - Human-in-the-loop интеграция
    - Условная маршрутизация
    - Обработка ошибок и повторы
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Инициализация EnhancedWorkflowEngine.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Хранилища
        self._workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self._workflow_executions: Dict[str, WorkflowExecution] = {}
        self._checkpoints: Dict[str, WorkflowCheckpoint] = {}

        # Регистр функций выполнения
        self._execution_functions: Dict[str, Callable] = {}
        self._condition_functions: Dict[str, Callable] = {}

        # Конфигурация
        self._default_timeout = 300  # 5 минут
        self._max_retries = 3

        # Статистика
        self._execution_stats: Dict[str, Any] = {}

    async def create_workflow(
        self,
        definition: WorkflowDefinition,
        user_id: str
    ) -> WorkflowDefinition:
        """
        Создание нового workflow.

        Args:
            definition: Определение workflow
            user_id: ID пользователя

        Returns:
            WorkflowDefinition: Созданный workflow
        """
        # Валидация определения
        await self._validate_workflow_definition(definition)

        # Сохранение
        self._workflow_definitions[definition.workflow_id] = definition

        # Audit log
        await self._log_workflow_created(definition, user_id)

        return definition

    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        user_id: str,
        pattern_override: Optional[WorkflowPattern] = None
    ) -> WorkflowExecution:
        """
        Выполнение workflow.

        Args:
            workflow_id: ID workflow
            input_data: Входные данные
            user_id: ID пользователя
            pattern_override: Переопределение паттерна выполнения

        Returns:
            WorkflowExecution: Результат выполнения
        """
        # Получение определения workflow
        definition = self._workflow_definitions.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Создание выполнения
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            user_id=user_id,
            pattern=pattern_override or definition.pattern,
            input_data=input_data,
            status=WorkflowStatus.RUNNING
        )

        self._workflow_executions[execution.execution_id] = execution

        try:
            # Выполнение по паттерну
            if execution.pattern == WorkflowPattern.SEQUENTIAL:
                await self._execute_sequential(execution, definition)
            elif execution.pattern == WorkflowPattern.PARALLEL:
                await self._execute_parallel(execution, definition)
            elif execution.pattern == WorkflowPattern.FAN_OUT_FAN_IN:
                await self._execute_fan_out_fan_in(execution, definition)
            elif execution.pattern == WorkflowPattern.PIPELINE:
                await self._execute_pipeline(execution, definition)
            elif execution.pattern == WorkflowPattern.SCATTER_GATHER:
                await self._execute_scatter_gather(execution, definition)
            elif execution.pattern == WorkflowPattern.CONDITIONAL_BRANCH:
                await self._execute_conditional_branch(execution, definition)
            elif execution.pattern == WorkflowPattern.HUMAN_IN_LOOP:
                await self._execute_human_in_loop(execution, definition)
            else:
                raise ValueError(f"Unknown pattern: {execution.pattern}")

            # Завершение успешного выполнения
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()

        except Exception as e:
            # Обработка ошибки
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()

        # Audit log
        await self._log_workflow_execution(execution, user_id)

        return execution

    async def create_checkpoint(
        self,
        execution_id: str,
        checkpoint_type: CheckpointType,
        node_id: str,
        state_data: Dict[str, Any]
    ) -> WorkflowCheckpoint:
        """
        Создание контрольной точки.

        Args:
            execution_id: ID выполнения
            checkpoint_type: Тип контрольной точки
            node_id: ID узла
            state_data: Данные состояния

        Returns:
            WorkflowCheckpoint: Созданная контрольная точка
        """
        execution = self._workflow_executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        checkpoint = WorkflowCheckpoint(
            workflow_id=execution.workflow_id,
            checkpoint_type=checkpoint_type,
            node_id=node_id,
            state_snapshot=state_data
        )

        # Установка времени истечения
        if checkpoint_type == CheckpointType.HUMAN_APPROVAL:
            from datetime import timedelta
            checkpoint.expires_at = checkpoint.created_at + timedelta(hours=24)

        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        execution.checkpoints.append(checkpoint.checkpoint_id)

        return checkpoint

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        user_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Возобновление выполнения с контрольной точки.

        Args:
            checkpoint_id: ID контрольной точки
            user_id: ID пользователя
            additional_data: Дополнительные данные

        Returns:
            WorkflowExecution: Возобновленное выполнение
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Поиск соответствующего выполнения
        execution = None
        for exec_obj in self._workflow_executions.values():
            if checkpoint_id in exec_obj.checkpoints:
                execution = exec_obj
                break

        if not execution:
            raise ValueError("Associated execution not found")

        # Восстановление состояния
        if additional_data:
            execution.input_data.update(additional_data)

        # Обновление статуса
        execution.status = WorkflowStatus.RUNNING

        # Продолжение выполнения с точки останова
        definition = self._workflow_definitions[execution.workflow_id]

        # Поиск узла для продолжения
        resume_node = None
        for node in definition.nodes:
            if node.node_id == checkpoint.node_id:
                resume_node = node
                break

        if resume_node:
            await self._execute_node(execution, definition, resume_node)

        return execution

    async def approve_checkpoint(
        self,
        checkpoint_id: str,
        approver_id: str,
        approved: bool,
        comments: Optional[str] = None
    ) -> WorkflowCheckpoint:
        """
        Одобрение контрольной точки.

        Args:
            checkpoint_id: ID контрольной точки
            approver_id: ID одобряющего
            approved: Результат одобрения
            comments: Комментарии

        Returns:
            WorkflowCheckpoint: Обновленная контрольная точка
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        checkpoint.human_approver = approver_id
        checkpoint.approval_status = "approved" if approved else "rejected"

        if comments:
            checkpoint.metadata["approval_comments"] = comments

        # Если одобрено, продолжаем workflow
        if approved:
            await self.resume_from_checkpoint(checkpoint_id, approver_id)

        return checkpoint

    async def _execute_sequential(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Последовательное выполнение узлов"""
        # Топологическая сортировка узлов
        sorted_nodes = await self._topological_sort(definition)

        for node in sorted_nodes:
            execution.current_node = node.node_id
            await self._execute_node(execution, definition, node)
            execution.completed_nodes.append(node.node_id)

    async def _execute_parallel(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Параллельное выполнение независимых узлов"""
        # Группировка по уровням зависимостей
        levels = await self._group_nodes_by_dependency_levels(definition)

        for level_nodes in levels:
            # Выполнение узлов одного уровня параллельно
            tasks = [
                self._execute_node(execution, definition, node)
                for node in level_nodes
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for node, result in zip(level_nodes, results):
                if isinstance(result, Exception):
                    execution.failed_nodes.append(node.node_id)
                    raise result
                else:
                    execution.completed_nodes.append(node.node_id)

    async def _execute_fan_out_fan_in(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Fan-out/Fan-in выполнение"""
        # Поиск fan-out и fan-in узлов
        entry_node = await self._find_node_by_id(definition, definition.entry_point)
        fan_in_nodes = [node for node in definition.nodes if len(node.dependencies) > 1]

        # Выполнение entry point
        await self._execute_node(execution, definition, entry_node)
        execution.completed_nodes.append(entry_node.node_id)

        # Fan-out: параллельное выполнение ветвей
        middle_nodes = [
            node for node in definition.nodes
            if entry_node.node_id in node.dependencies and node not in fan_in_nodes
        ]

        tasks = [
            self._execute_node(execution, definition, node)
            for node in middle_nodes
        ]

        await asyncio.gather(*tasks)
        execution.completed_nodes.extend(node.node_id for node in middle_nodes)

        # Fan-in: объединение результатов
        for fan_in_node in fan_in_nodes:
            await self._execute_node(execution, definition, fan_in_node)
            execution.completed_nodes.append(fan_in_node.node_id)

    async def _execute_pipeline(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Pipeline выполнение с передачей данных между этапами"""
        sorted_nodes = await self._topological_sort(definition)

        pipeline_data = execution.input_data.copy()

        for node in sorted_nodes:
            execution.current_node = node.node_id

            # Передача данных предыдущего этапа
            node_result = await self._execute_node_with_data(
                execution, definition, node, pipeline_data
            )

            # Обновление данных pipeline
            if isinstance(node_result, dict):
                pipeline_data.update(node_result)

            execution.completed_nodes.append(node.node_id)

        execution.output_data = pipeline_data

    async def _execute_scatter_gather(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Scatter-Gather выполнение"""
        # Разделение входных данных
        scattered_data = await self._scatter_input_data(execution.input_data, definition)

        # Параллельная обработка
        processing_nodes = [
            node for node in definition.nodes
            if node.node_type == "processor"
        ]

        tasks = []
        for i, node in enumerate(processing_nodes):
            if i < len(scattered_data):
                task = self._execute_node_with_data(
                    execution, definition, node, scattered_data[i]
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Сбор результатов
        gathered_result = await self._gather_results(results, definition)
        execution.output_data = gathered_result

        execution.completed_nodes.extend(node.node_id for node in processing_nodes)

    async def _execute_conditional_branch(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Условное ветвление"""
        current_node_id = definition.entry_point

        while current_node_id:
            node = await self._find_node_by_id(definition, current_node_id)
            execution.current_node = current_node_id

            await self._execute_node(execution, definition, node)
            execution.completed_nodes.append(current_node_id)

            # Определение следующего узла на основе условий
            next_node_id = await self._evaluate_next_node(
                execution, definition, current_node_id
            )
            current_node_id = next_node_id

    async def _execute_human_in_loop(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition
    ) -> None:
        """Human-in-the-loop выполнение"""
        for node in definition.nodes:
            execution.current_node = node.node_id

            # Проверка необходимости человеческого вмешательства
            if node.metadata.get("requires_human_approval"):
                # Создание checkpoint для одобрения
                checkpoint = await self.create_checkpoint(
                    execution.execution_id,
                    CheckpointType.HUMAN_APPROVAL,
                    node.node_id,
                    {"node_data": node.model_dump(), "execution_data": execution.input_data}
                )

                # Установка статуса ожидания
                execution.status = WorkflowStatus.WAITING_HUMAN

                # Прерывание выполнения до получения одобрения
                return

            await self._execute_node(execution, definition, node)
            execution.completed_nodes.append(node.node_id)

    async def _execute_node(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition,
        node: WorkflowNode
    ) -> Any:
        """Выполнение одного узла workflow"""
        try:
            # Выполнение с retry logic
            max_retries = node.retry_config.get("max_retries", self._max_retries)

            for attempt in range(max_retries + 1):
                try:
                    # Получение функции выполнения
                    exec_function = self._execution_functions.get(node.execution_function)

                    if exec_function:
                        result = await exec_function(execution.input_data, node.metadata)
                    else:
                        # Заглушка выполнения
                        result = {"node_id": node.node_id, "status": "completed"}

                    return result

                except Exception:
                    if attempt == max_retries:
                        raise

                    # Ожидание перед повтором
                    retry_delay = node.retry_config.get("retry_delay", 1.0)
                    await asyncio.sleep(retry_delay * (attempt + 1))

        except Exception:
            execution.failed_nodes.append(node.node_id)
            raise

    async def _execute_node_with_data(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition,
        node: WorkflowNode,
        data: Dict[str, Any]
    ) -> Any:
        """Выполнение узла с конкретными данными"""
        # Временно заменяем входные данные
        original_data = execution.input_data
        execution.input_data = data

        try:
            result = await self._execute_node(execution, definition, node)
            return result
        finally:
            execution.input_data = original_data

    async def _validate_workflow_definition(self, definition: WorkflowDefinition) -> None:
        """Валидация определения workflow"""
        # Проверка наличия entry point
        if not any(node.node_id == definition.entry_point for node in definition.nodes):
            raise ValueError("Entry point node not found")

        # Проверка зависимостей
        node_ids = {node.node_id for node in definition.nodes}
        for node in definition.nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    raise ValueError(f"Dependency {dep} not found for node {node.node_id}")

    async def _topological_sort(self, definition: WorkflowDefinition) -> List[WorkflowNode]:
        """Топологическая сортировка узлов"""
        # Упрощенная реализация
        sorted_nodes = []
        remaining_nodes = definition.nodes.copy()

        while remaining_nodes:
            ready_nodes = [
                node for node in remaining_nodes
                if all(dep in [n.node_id for n in sorted_nodes] for dep in node.dependencies)
            ]

            if not ready_nodes:
                # Циклические зависимости
                ready_nodes = [remaining_nodes[0]]

            sorted_nodes.extend(ready_nodes)
            for node in ready_nodes:
                remaining_nodes.remove(node)

        return sorted_nodes

    async def _group_nodes_by_dependency_levels(
        self,
        definition: WorkflowDefinition
    ) -> List[List[WorkflowNode]]:
        """Группировка узлов по уровням зависимостей"""
        levels = []
        remaining_nodes = definition.nodes.copy()
        completed_node_ids = set()

        while remaining_nodes:
            current_level = [
                node for node in remaining_nodes
                if all(dep in completed_node_ids for dep in node.dependencies)
            ]

            if not current_level:
                current_level = [remaining_nodes[0]]

            levels.append(current_level)
            completed_node_ids.update(node.node_id for node in current_level)

            for node in current_level:
                remaining_nodes.remove(node)

        return levels

    async def _find_node_by_id(
        self,
        definition: WorkflowDefinition,
        node_id: str
    ) -> WorkflowNode:
        """Поиск узла по ID"""
        for node in definition.nodes:
            if node.node_id == node_id:
                return node
        raise ValueError(f"Node {node_id} not found")

    async def _evaluate_next_node(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition,
        current_node_id: str
    ) -> Optional[str]:
        """Определение следующего узла для условного ветвления"""
        # Поиск исходящих связей
        outgoing_edges = [
            edge for edge in definition.edges
            if edge.from_node == current_node_id
        ]

        for edge in outgoing_edges:
            # Оценка условия
            if edge.condition_function:
                condition_func = self._condition_functions.get(edge.condition_function)
                if condition_func and await condition_func(execution.input_data):
                    return edge.to_node
            elif not edge.condition:  # Безусловный переход
                return edge.to_node

        return None

    async def _scatter_input_data(
        self,
        input_data: Dict[str, Any],
        definition: WorkflowDefinition
    ) -> List[Dict[str, Any]]:
        """Разделение входных данных для scatter-gather"""
        # Простая реализация - дублирование данных
        scatter_count = len([n for n in definition.nodes if n.node_type == "processor"])
        return [input_data.copy() for _ in range(scatter_count)]

    async def _gather_results(
        self,
        results: List[Any],
        definition: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Сбор результатов для scatter-gather"""
        return {
            "gathered_results": results,
            "count": len(results),
            "status": "completed"
        }

    def register_execution_function(self, name: str, function: Callable) -> None:
        """Регистрация функции выполнения"""
        self._execution_functions[name] = function

    def register_condition_function(self, name: str, function: Callable) -> None:
        """Регистрация функции условия"""
        self._condition_functions[name] = function

    async def _log_workflow_created(
        self,
        definition: WorkflowDefinition,
        user_id: str
    ) -> None:
        """Логирование создания workflow"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"workflow_{definition.workflow_id}",
            source="enhanced_workflow",
            action="workflow_created",
            payload={
                "workflow_id": definition.workflow_id,
                "workflow_name": definition.name,
                "pattern": definition.pattern.value,
                "nodes_count": len(definition.nodes)
            },
            tags=["workflow", "creation"]
        )
        await self.memory.alog_audit(event)

    async def _log_workflow_execution(
        self,
        execution: WorkflowExecution,
        user_id: str
    ) -> None:
        """Логирование выполнения workflow"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            thread_id=f"workflow_{execution.workflow_id}",
            source="enhanced_workflow",
            action="workflow_executed",
            payload={
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "pattern": execution.pattern.value,
                "execution_time": execution.execution_time,
                "completed_nodes": len(execution.completed_nodes),
                "failed_nodes": len(execution.failed_nodes)
            },
            tags=["workflow", "execution"]
        )
        await self.memory.alog_audit(event)

    async def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Получение статуса выполнения"""
        return self._workflow_executions.get(execution_id)

    async def get_pending_checkpoints(self, user_id: Optional[str] = None) -> List[WorkflowCheckpoint]:
        """Получение ожидающих контрольных точек"""
        checkpoints = []
        for checkpoint in self._checkpoints.values():
            if checkpoint.checkpoint_type == CheckpointType.HUMAN_APPROVAL:
                if checkpoint.approval_status is None:
                    if user_id is None or checkpoint.human_approver == user_id:
                        checkpoints.append(checkpoint)
        return checkpoints

    async def get_workflow_stats(self) -> Dict[str, Any]:
        """Получение статистики workflow"""
        return {
            "total_workflows": len(self._workflow_definitions),
            "total_executions": len(self._workflow_executions),
            "active_executions": len([
                e for e in self._workflow_executions.values()
                if e.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED, WorkflowStatus.WAITING_HUMAN]
            ]),
            "pending_checkpoints": len(await self.get_pending_checkpoints()),
            "execution_stats": self._execution_stats
        }