"""
SupervisorAgent - Динамическая маршрутизация и оркестрация задач.

Обеспечивает:
- LLM-driven анализ задач и выбор агентов
- Intelligent decomposition сложных задач
- Orchestration workflow с планированием
- Conditional routing logic
- Parallel execution и result fusion
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..memory.memory_manager import MemoryManager
from ..memory.models import AuditEvent, MemoryRecord
from ..orchestration.workflow_graph import WorkflowState, build_case_workflow
from ..orchestration.pipeline_manager import run


class TaskComplexity(str, Enum):
    """Уровни сложности задач"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class ExecutionStrategy(str, Enum):
    """Стратегии выполнения задач"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    FAN_OUT_FAN_IN = "fan_out_fan_in"


class AgentType(str, Enum):
    """Типы доступных агентов"""
    CASE_AGENT = "case_agent"
    WRITER_AGENT = "writer_agent"
    VALIDATOR_AGENT = "validator_agent"
    RAG_PIPELINE_AGENT = "rag_pipeline_agent"
    LEGAL_RESEARCH_AGENT = "legal_research_agent"


class TaskAnalysis(BaseModel):
    """Результат анализа задачи"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complexity: TaskComplexity = Field(..., description="Сложность задачи")
    estimated_duration: int = Field(..., description="Оценка времени в секундах")
    required_agents: List[AgentType] = Field(..., description="Необходимые агенты")
    execution_strategy: ExecutionStrategy = Field(..., description="Стратегия выполнения")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости между подзадачами")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Уверенность в анализе")
    reasoning: str = Field(..., description="Объяснение выбора стратегии")


class SubTask(BaseModel):
    """Подзадача для декомпозиции"""
    subtask_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str = Field(..., description="Описание подзадачи")
    agent_type: AgentType = Field(..., description="Тип агента для выполнения")
    priority: int = Field(default=5, ge=1, le=10, description="Приоритет")
    dependencies: List[str] = Field(default_factory=list, description="ID зависимых подзадач")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Входные данные")
    expected_output: str = Field(..., description="Ожидаемый результат")


class WorkflowPlan(BaseModel):
    """План выполнения workflow"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_task: str = Field(..., description="Исходная задача")
    subtasks: List[SubTask] = Field(..., description="Список подзадач")
    execution_strategy: ExecutionStrategy = Field(..., description="Стратегия выполнения")
    estimated_total_time: int = Field(..., description="Общее время выполнения")
    critical_path: List[str] = Field(default_factory=list, description="Критический путь")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    """Результат выполнения workflow"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = Field(..., description="ID плана")
    success: bool = Field(..., description="Успешность выполнения")
    results: Dict[str, Any] = Field(default_factory=dict, description="Результаты подзадач")
    execution_time: float = Field(..., description="Время выполнения")
    errors: List[str] = Field(default_factory=list, description="Ошибки")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Итоговый результат")
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class SupervisorAgent:
    """
    Агент-супервизор для динамической маршрутизации и оркестрации задач.

    Основные функции:
    - LLM-driven анализ задач и выбор оптимальной стратегии
    - Decomposition сложных задач на подзадачи
    - Orchestration workflow с учетом зависимостей
    - Parallel execution и result fusion
    - Adaptive routing на основе контекста
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Инициализация SupervisorAgent.

        Args:
            memory_manager: Менеджер памяти для persistence
        """
        self.memory = memory_manager or MemoryManager()

        # Кэш планов и результатов
        self._workflow_plans: Dict[str, WorkflowPlan] = {}
        self._execution_results: Dict[str, ExecutionResult] = {}

        # Статистика производительности агентов
        self._agent_performance: Dict[AgentType, Dict[str, float]] = {}

    async def analyze_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> TaskAnalysis:
        """
        LLM-driven анализ задачи для определения оптимальной стратегии.

        Args:
            task_description: Описание задачи
            context: Дополнительный контекст

        Returns:
            TaskAnalysis: Результат анализа задачи
        """
        # Создание prompt для LLM анализа
        analysis_prompt = self._build_analysis_prompt(task_description, context)

        # В реальной реализации здесь будет вызов LLM
        # Пока используем rule-based анализ
        analysis = await self._rule_based_analysis(task_description, context)

        # Логирование анализа
        await self._log_task_analysis(task_description, analysis)

        return analysis

    async def decompose_task(self, task_description: str, analysis: TaskAnalysis) -> List[SubTask]:
        """
        Intelligent decomposition сложной задачи на подзадачи.

        Args:
            task_description: Описание задачи
            analysis: Результат анализа задачи

        Returns:
            List[SubTask]: Список подзадач
        """
        subtasks = []

        if analysis.complexity == TaskComplexity.SIMPLE:
            # Простая задача - одна подзадача
            subtask = SubTask(
                description=task_description,
                agent_type=analysis.required_agents[0] if analysis.required_agents else AgentType.CASE_AGENT,
                expected_output="Direct task completion"
            )
            subtasks.append(subtask)

        elif analysis.complexity == TaskComplexity.MODERATE:
            # Средняя сложность - 2-3 подзадачи
            subtasks = await self._decompose_moderate_task(task_description, analysis)

        elif analysis.complexity == TaskComplexity.COMPLEX:
            # Сложная задача - множественная декомпозиция
            subtasks = await self._decompose_complex_task(task_description, analysis)

        elif analysis.complexity == TaskComplexity.ENTERPRISE:
            # Энтерпрайз задача - полная декомпозиция с workflow
            subtasks = await self._decompose_enterprise_task(task_description, analysis)

        # Логирование декомпозиции
        await self._log_task_decomposition(task_description, subtasks)

        return subtasks

    async def orchestrate_workflow(
        self,
        task_description: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Orchestration workflow с планированием и выполнением.

        Args:
            task_description: Описание задачи
            user_id: ID пользователя
            context: Контекст выполнения

        Returns:
            ExecutionResult: Результат выполнения
        """
        start_time = datetime.utcnow()

        try:
            # 1. Анализ задачи
            analysis = await self.analyze_task(task_description, context)

            # 2. Декомпозиция на подзадачи
            subtasks = await self.decompose_task(task_description, analysis)

            # 3. Создание плана выполнения
            plan = await self._create_workflow_plan(task_description, subtasks, analysis)

            # 4. Выполнение плана
            results = await self._execute_workflow_plan(plan, user_id, context)

            # 5. Fusion результатов
            final_result = await self._fuse_results(results, analysis.execution_strategy)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            execution_result = ExecutionResult(
                plan_id=plan.plan_id,
                success=True,
                results=results,
                execution_time=execution_time,
                final_result=final_result
            )

            # Сохранение результата
            self._execution_results[execution_result.execution_id] = execution_result

            # Логирование успешного выполнения
            await self._log_workflow_completion(task_description, execution_result)

            return execution_result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            execution_result = ExecutionResult(
                plan_id="error",
                success=False,
                execution_time=execution_time,
                errors=[str(e)]
            )

            # Логирование ошибки
            await self._log_workflow_error(task_description, execution_result, e)

            return execution_result

    async def _rule_based_analysis(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskAnalysis:
        """Rule-based анализ задачи (заглушка для LLM)"""

        # Простейший анализ по ключевым словам
        task_lower = task_description.lower()

        # Определение сложности
        complexity = TaskComplexity.SIMPLE
        if any(word in task_lower for word in ["create", "generate", "analyze"]):
            complexity = TaskComplexity.MODERATE
        if any(word in task_lower for word in ["workflow", "process", "integration"]):
            complexity = TaskComplexity.COMPLEX
        if any(word in task_lower for word in ["enterprise", "system", "architecture"]):
            complexity = TaskComplexity.ENTERPRISE

        # Определение необходимых агентов
        required_agents = []
        if any(word in task_lower for word in ["case", "legal", "client"]):
            required_agents.append(AgentType.CASE_AGENT)
        if any(word in task_lower for word in ["document", "letter", "generate", "write"]):
            required_agents.append(AgentType.WRITER_AGENT)
        if any(word in task_lower for word in ["validate", "check", "verify"]):
            required_agents.append(AgentType.VALIDATOR_AGENT)
        if any(word in task_lower for word in ["search", "find", "research"]):
            required_agents.append(AgentType.RAG_PIPELINE_AGENT)

        if not required_agents:
            required_agents = [AgentType.CASE_AGENT]  # Default

        # Определение стратегии выполнения
        execution_strategy = ExecutionStrategy.SEQUENTIAL
        if len(required_agents) > 1:
            execution_strategy = ExecutionStrategy.PARALLEL
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE]:
            execution_strategy = ExecutionStrategy.PIPELINE

        # Оценка времени
        base_time = {
            TaskComplexity.SIMPLE: 30,
            TaskComplexity.MODERATE: 120,
            TaskComplexity.COMPLEX: 300,
            TaskComplexity.ENTERPRISE: 600
        }

        estimated_duration = base_time[complexity] * len(required_agents)

        return TaskAnalysis(
            complexity=complexity,
            estimated_duration=estimated_duration,
            required_agents=required_agents,
            execution_strategy=execution_strategy,
            confidence_score=0.7,  # Rule-based имеет среднюю уверенность
            reasoning=f"Rule-based analysis: {complexity} task requiring {len(required_agents)} agents"
        )

    async def _decompose_moderate_task(
        self,
        task_description: str,
        analysis: TaskAnalysis
    ) -> List[SubTask]:
        """Декомпозиция задачи средней сложности"""
        subtasks = []

        # Подготовительная подзадача
        prep_task = SubTask(
            description=f"Prepare context and validate input for: {task_description}",
            agent_type=AgentType.VALIDATOR_AGENT,
            priority=8,
            expected_output="Validated input and prepared context"
        )
        subtasks.append(prep_task)

        # Основная подзадача
        main_task = SubTask(
            description=f"Execute main task: {task_description}",
            agent_type=analysis.required_agents[0] if analysis.required_agents else AgentType.CASE_AGENT,
            priority=10,
            dependencies=[prep_task.subtask_id],
            expected_output="Main task result"
        )
        subtasks.append(main_task)

        # Валидация результата
        if len(analysis.required_agents) > 1:
            validation_task = SubTask(
                description=f"Validate result of: {task_description}",
                agent_type=AgentType.VALIDATOR_AGENT,
                priority=6,
                dependencies=[main_task.subtask_id],
                expected_output="Validated final result"
            )
            subtasks.append(validation_task)

        return subtasks

    async def _decompose_complex_task(
        self,
        task_description: str,
        analysis: TaskAnalysis
    ) -> List[SubTask]:
        """Декомпозиция сложной задачи"""
        subtasks = []

        # Research подзадача
        research_task = SubTask(
            description=f"Research and gather information for: {task_description}",
            agent_type=AgentType.RAG_PIPELINE_AGENT,
            priority=9,
            expected_output="Research results and context"
        )
        subtasks.append(research_task)

        # Parallel execution для каждого агента
        for i, agent_type in enumerate(analysis.required_agents):
            agent_task = SubTask(
                description=f"Execute {agent_type} tasks for: {task_description}",
                agent_type=agent_type,
                priority=8 - i,
                dependencies=[research_task.subtask_id],
                expected_output=f"Results from {agent_type}"
            )
            subtasks.append(agent_task)

        # Result fusion
        fusion_task = SubTask(
            description=f"Fuse and validate results for: {task_description}",
            agent_type=AgentType.VALIDATOR_AGENT,
            priority=10,
            dependencies=[task.subtask_id for task in subtasks[1:]],  # All agent tasks
            expected_output="Fused and validated final result"
        )
        subtasks.append(fusion_task)

        return subtasks

    async def _decompose_enterprise_task(
        self,
        task_description: str,
        analysis: TaskAnalysis
    ) -> List[SubTask]:
        """Декомпозиция энтерпрайз задачи"""
        # Enterprise tasks требуют полного workflow pipeline
        return await self._decompose_complex_task(task_description, analysis)

    async def _create_workflow_plan(
        self,
        task_description: str,
        subtasks: List[SubTask],
        analysis: TaskAnalysis
    ) -> WorkflowPlan:
        """Создание плана выполнения workflow"""

        # Расчет критического пути
        critical_path = await self._calculate_critical_path(subtasks)

        # Оценка общего времени
        total_time = analysis.estimated_duration
        if analysis.execution_strategy == ExecutionStrategy.PARALLEL:
            # При параллельном выполнении время сокращается
            total_time = int(total_time * 0.6)

        plan = WorkflowPlan(
            original_task=task_description,
            subtasks=subtasks,
            execution_strategy=analysis.execution_strategy,
            estimated_total_time=total_time,
            critical_path=critical_path
        )

        # Сохранение плана
        self._workflow_plans[plan.plan_id] = plan

        return plan

    async def _execute_workflow_plan(
        self,
        plan: WorkflowPlan,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Выполнение плана workflow"""
        results = {}

        if plan.execution_strategy == ExecutionStrategy.SEQUENTIAL:
            results = await self._execute_sequential(plan, user_id, context)
        elif plan.execution_strategy == ExecutionStrategy.PARALLEL:
            results = await self._execute_parallel(plan, user_id, context)
        elif plan.execution_strategy == ExecutionStrategy.PIPELINE:
            results = await self._execute_pipeline(plan, user_id, context)
        elif plan.execution_strategy == ExecutionStrategy.FAN_OUT_FAN_IN:
            results = await self._execute_fan_out_fan_in(plan, user_id, context)

        return results

    async def _execute_sequential(
        self,
        plan: WorkflowPlan,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Последовательное выполнение подзадач"""
        results = {}

        # Сортировка по зависимостям
        sorted_tasks = await self._topological_sort(plan.subtasks)

        for subtask in sorted_tasks:
            try:
                result = await self._execute_subtask(subtask, user_id, context, results)
                results[subtask.subtask_id] = result
            except Exception as e:
                results[subtask.subtask_id] = {"error": str(e), "success": False}

        return results

    async def _execute_parallel(
        self,
        plan: WorkflowPlan,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Параллельное выполнение подзадач"""
        # Группировка задач по dependency levels
        levels = await self._group_by_dependency_levels(plan.subtasks)
        results = {}

        for level_tasks in levels:
            # Выполнение задач одного уровня параллельно
            tasks = [
                self._execute_subtask(subtask, user_id, context, results)
                for subtask in level_tasks
            ]

            level_results = await asyncio.gather(*tasks, return_exceptions=True)

            for subtask, result in zip(level_tasks, level_results):
                if isinstance(result, Exception):
                    results[subtask.subtask_id] = {"error": str(result), "success": False}
                else:
                    results[subtask.subtask_id] = result

        return results

    async def _execute_pipeline(
        self,
        plan: WorkflowPlan,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Pipeline выполнение подзадач"""
        # Pipeline = sequential с передачей результатов между задачами
        return await self._execute_sequential(plan, user_id, context)

    async def _execute_fan_out_fan_in(
        self,
        plan: WorkflowPlan,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fan-out/Fan-in выполнение"""
        # Первая задача - fan-out point
        # Последняя задача - fan-in point
        # Средние задачи выполняются параллельно
        return await self._execute_parallel(plan, user_id, context)

    async def _execute_subtask(
        self,
        subtask: SubTask,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        previous_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Выполнение одной подзадачи"""

        # Placeholder для выполнения подзадачи через соответствующий агент
        # В реальной реализации здесь будет вызов агента

        # Имитация работы агента
        await asyncio.sleep(0.1)  # Симуляция времени выполнения

        return {
            "success": True,
            "subtask_id": subtask.subtask_id,
            "agent_type": subtask.agent_type.value,
            "result": f"Completed: {subtask.description}",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _fuse_results(
        self,
        results: Dict[str, Any],
        strategy: ExecutionStrategy
    ) -> Dict[str, Any]:
        """Fusion результатов подзадач"""

        successful_results = [
            result for result in results.values()
            if isinstance(result, dict) and result.get("success", False)
        ]

        failed_results = [
            result for result in results.values()
            if isinstance(result, dict) and not result.get("success", True)
        ]

        return {
            "fusion_strategy": strategy.value,
            "total_subtasks": len(results),
            "successful_subtasks": len(successful_results),
            "failed_subtasks": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "combined_results": successful_results,
            "errors": [r.get("error", "Unknown error") for r in failed_results],
            "overall_success": len(failed_results) == 0
        }

    async def _calculate_critical_path(self, subtasks: List[SubTask]) -> List[str]:
        """Расчет критического пути"""
        # Упрощенный алгоритм - самая длинная цепочка зависимостей
        paths = []

        for subtask in subtasks:
            if not subtask.dependencies:  # Начальная задача
                path = await self._find_longest_path(subtask, subtasks)
                paths.append(path)

        return max(paths, key=len) if paths else []

    async def _find_longest_path(self, start_task: SubTask, all_tasks: List[SubTask]) -> List[str]:
        """Поиск самого длинного пути от задачи"""
        path = [start_task.subtask_id]

        # Поиск задач, зависящих от текущей
        dependent_tasks = [
            task for task in all_tasks
            if start_task.subtask_id in task.dependencies
        ]

        if not dependent_tasks:
            return path

        # Рекурсивный поиск самого длинного пути
        longest_subpath = []
        for dep_task in dependent_tasks:
            subpath = await self._find_longest_path(dep_task, all_tasks)
            if len(subpath) > len(longest_subpath):
                longest_subpath = subpath

        return path + longest_subpath

    async def _topological_sort(self, subtasks: List[SubTask]) -> List[SubTask]:
        """Топологическая сортировка подзадач"""
        # Упрощенная реализация
        sorted_tasks = []
        remaining_tasks = subtasks.copy()

        while remaining_tasks:
            # Поиск задач без неразрешенных зависимостей
            ready_tasks = [
                task for task in remaining_tasks
                if all(
                    dep_id in [t.subtask_id for t in sorted_tasks]
                    for dep_id in task.dependencies
                )
            ]

            if not ready_tasks:
                # Циклические зависимости - берем первую задачу
                ready_tasks = [remaining_tasks[0]]

            sorted_tasks.extend(ready_tasks)
            for task in ready_tasks:
                remaining_tasks.remove(task)

        return sorted_tasks

    async def _group_by_dependency_levels(self, subtasks: List[SubTask]) -> List[List[SubTask]]:
        """Группировка задач по уровням зависимостей"""
        levels = []
        remaining_tasks = subtasks.copy()
        completed_task_ids = set()

        while remaining_tasks:
            current_level = [
                task for task in remaining_tasks
                if all(dep_id in completed_task_ids for dep_id in task.dependencies)
            ]

            if not current_level:
                # Циклические зависимости - берем все оставшиеся
                current_level = remaining_tasks.copy()

            levels.append(current_level)
            completed_task_ids.update(task.subtask_id for task in current_level)

            for task in current_level:
                remaining_tasks.remove(task)

        return levels

    def _build_analysis_prompt(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Построение prompt для LLM анализа"""

        base_prompt = f"""
        Analyze the following task and provide a structured analysis:

        Task: {task_description}
        Context: {context or "No additional context"}

        Please analyze:
        1. Task complexity (simple/moderate/complex/enterprise)
        2. Required agents and their roles
        3. Optimal execution strategy
        4. Estimated duration
        5. Dependencies and critical path

        Provide reasoning for your analysis.
        """

        return base_prompt

    async def _log_task_analysis(self, task: str, analysis: TaskAnalysis) -> None:
        """Логирование анализа задачи"""
        await self._log_audit_event(
            user_id="supervisor_agent",
            action="task_analysis",
            payload={
                "task": task,
                "complexity": analysis.complexity.value,
                "agents": [a.value for a in analysis.required_agents],
                "strategy": analysis.execution_strategy.value,
                "confidence": analysis.confidence_score
            }
        )

    async def _log_task_decomposition(self, task: str, subtasks: List[SubTask]) -> None:
        """Логирование декомпозиции задачи"""
        await self._log_audit_event(
            user_id="supervisor_agent",
            action="task_decomposition",
            payload={
                "task": task,
                "subtasks_count": len(subtasks),
                "subtasks": [
                    {
                        "id": st.subtask_id,
                        "agent": st.agent_type.value,
                        "priority": st.priority
                    }
                    for st in subtasks
                ]
            }
        )

    async def _log_workflow_completion(self, task: str, result: ExecutionResult) -> None:
        """Логирование завершения workflow"""
        await self._log_audit_event(
            user_id="supervisor_agent",
            action="workflow_completed",
            payload={
                "task": task,
                "execution_id": result.execution_id,
                "success": result.success,
                "execution_time": result.execution_time,
                "subtasks_count": len(result.results)
            }
        )

    async def _log_workflow_error(self, task: str, result: ExecutionResult, error: Exception) -> None:
        """Логирование ошибки workflow"""
        await self._log_audit_event(
            user_id="supervisor_agent",
            action="workflow_error",
            payload={
                "task": task,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "execution_time": result.execution_time
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
            thread_id=f"supervisor_agent_{user_id}",
            source="supervisor_agent",
            action=action,
            payload=payload,
            tags=["supervisor_agent", "orchestration", "workflow"]
        )

        await self.memory.alog_audit(event)

    async def get_workflow_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Получение статуса выполнения workflow"""
        plan = self._workflow_plans.get(plan_id)
        if not plan:
            return None

        execution = next(
            (result for result in self._execution_results.values()
             if result.plan_id == plan_id),
            None
        )

        return {
            "plan": plan.model_dump(),
            "execution": execution.model_dump() if execution else None,
            "status": "completed" if execution else "planned"
        }

    async def get_agent_performance(self) -> Dict[str, Any]:
        """Получение статистики производительности агентов"""
        return {
            "agent_stats": self._agent_performance,
            "total_workflows": len(self._execution_results),
            "successful_workflows": len([
                r for r in self._execution_results.values() if r.success
            ])
        }