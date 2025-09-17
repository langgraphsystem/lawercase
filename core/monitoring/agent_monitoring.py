"""
Agent Monitoring Integration для mega_agent_pro.

Интегрирует систему мониторинга с агентами:
- Automatic instrumentation для всех агентов
- Agent-specific metrics и health checks
- Workflow monitoring и tracing
- Performance benchmarking
- Error tracking и alerting
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Dict, List, Optional

from .observability_system import (
    ObservabilitySystem,
    ComponentType,
    MetricType,
    AlertSeverity,
    HealthStatus,
    monitor_performance
)


class AgentMonitoringMixin:
    """Mixin для добавления мониторинга к агентам."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._observability: Optional[ObservabilitySystem] = None
        self._agent_metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "avg_response_time": 0.0,
            "last_activity": None
        }

    def set_observability_system(self, observability: ObservabilitySystem) -> None:
        """Установить систему мониторинга."""
        self._observability = observability

    async def _record_agent_metric(self, name: str, value: Any,
                                  tags: Optional[Dict[str, str]] = None,
                                  metric_type: MetricType = MetricType.GAUGE) -> None:
        """Записать метрику агента."""
        if self._observability:
            agent_name = getattr(self, 'agent_id', self.__class__.__name__)
            await self._observability.record_metric(
                name, value, tags or {}, agent_name, metric_type
            )

    async def _start_agent_trace(self, operation: str, **kwargs) -> Optional[str]:
        """Начать трейс операции агента."""
        if self._observability:
            agent_name = getattr(self, 'agent_id', self.__class__.__name__)
            trace = await self._observability.start_trace(operation, agent_name)

            # Добавляем метаданные
            for key, value in kwargs.items():
                trace.tags[key] = str(value)

            return trace.span_id
        return None

    async def _finish_agent_trace(self, span_id: Optional[str],
                                 status: str = "success",
                                 error: Optional[str] = None) -> None:
        """Завершить трейс операции агента."""
        if self._observability and span_id:
            await self._observability.finish_trace(span_id, status, error)

    async def _check_agent_health(self) -> Dict[str, Any]:
        """Проверить здоровье агента."""
        if self._observability:
            agent_name = getattr(self, 'agent_id', self.__class__.__name__)
            health_check = await self._observability.check_health(
                agent_name, ComponentType.AGENT
            )
            return health_check.dict()

        return {
            "status": "unknown",
            "message": "Monitoring not available"
        }

    def _update_agent_metrics(self, success: bool, response_time: float) -> None:
        """Обновить метрики агента."""
        self._agent_metrics["requests_total"] += 1

        if success:
            self._agent_metrics["requests_success"] += 1
        else:
            self._agent_metrics["requests_error"] += 1

        # Обновляем среднее время ответа
        current_avg = self._agent_metrics["avg_response_time"]
        total_requests = self._agent_metrics["requests_total"]

        self._agent_metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )

        self._agent_metrics["last_activity"] = time.time()


class MonitoredMegaAgent:
    """Мониторимая обертка для MegaAgent."""

    def __init__(self, mega_agent, observability: ObservabilitySystem):
        self.mega_agent = mega_agent
        self.observability = observability
        self.agent_name = "mega_agent"

    async def handle_command(self, command, user_role=None):
        """Мониторимая обработка команд."""
        span_id = None
        start_time = time.time()

        try:
            # Начинаем трейс
            span_id = await self._start_trace("handle_command",
                                             command=str(command),
                                             user_role=str(user_role))

            # Записываем метрику запроса
            await self.observability.record_metric(
                "command_requests", 1,
                {"command": str(command), "user_role": str(user_role)},
                self.agent_name, MetricType.COUNTER
            )

            # Выполняем команду
            result = await self.mega_agent.handle_command(command, user_role)

            # Записываем успешную обработку
            response_time = (time.time() - start_time) * 1000
            await self.observability.record_metric(
                "command_duration", response_time,
                {"command": str(command), "status": "success"},
                self.agent_name, MetricType.TIMER
            )

            await self.observability.record_metric(
                "command_success", 1,
                {"command": str(command)},
                self.agent_name, MetricType.COUNTER
            )

            if span_id:
                await self.observability.finish_trace(span_id, "success")

            return result

        except Exception as e:
            # Записываем ошибку
            response_time = (time.time() - start_time) * 1000
            await self.observability.record_metric(
                "command_errors", 1,
                {"command": str(command), "error": str(e)},
                self.agent_name, MetricType.COUNTER
            )

            await self.observability.record_metric(
                "command_duration", response_time,
                {"command": str(command), "status": "error"},
                self.agent_name, MetricType.TIMER
            )

            if span_id:
                await self.observability.finish_trace(span_id, "error", str(e))

            raise

    async def _start_trace(self, operation: str, **kwargs):
        """Начать трейс операции."""
        trace = await self.observability.start_trace(operation, self.agent_name)
        for key, value in kwargs.items():
            trace.tags[key] = str(value)
        return trace.span_id

    def __getattr__(self, name):
        """Проксировать остальные методы."""
        return getattr(self.mega_agent, name)


class MonitoredRAGAgent:
    """Мониторимая обертка для RAGPipelineAgent."""

    def __init__(self, rag_agent, observability: ObservabilitySystem):
        self.rag_agent = rag_agent
        self.observability = observability
        self.agent_name = "rag_pipeline_agent"

    async def asearch(self, search_query, user_id="system"):
        """Мониторимый поиск."""
        span_id = None
        start_time = time.time()

        try:
            # Начинаем трейс
            span_id = await self._start_trace("search",
                                             query=str(search_query),
                                             user_id=user_id)

            # Записываем метрику поискового запроса
            await self.observability.record_metric(
                "search_requests", 1,
                {"user_id": user_id},
                self.agent_name, MetricType.COUNTER
            )

            # Выполняем поиск
            result = await self.rag_agent.asearch(search_query, user_id)

            # Записываем результаты
            response_time = (time.time() - start_time) * 1000
            results_count = len(result.results) if hasattr(result, 'results') else 0

            await self.observability.record_metric(
                "search_duration", response_time,
                {"status": "success"},
                self.agent_name, MetricType.TIMER
            )

            await self.observability.record_metric(
                "search_results_count", results_count,
                {"user_id": user_id},
                self.agent_name, MetricType.GAUGE
            )

            if span_id:
                await self.observability.finish_trace(span_id, "success")

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            await self.observability.record_metric(
                "search_errors", 1,
                {"error": str(e), "user_id": user_id},
                self.agent_name, MetricType.COUNTER
            )

            await self.observability.record_metric(
                "search_duration", response_time,
                {"status": "error"},
                self.agent_name, MetricType.TIMER
            )

            if span_id:
                await self.observability.finish_trace(span_id, "error", str(e))

            raise

    async def _start_trace(self, operation: str, **kwargs):
        """Начать трейс операции."""
        trace = await self.observability.start_trace(operation, self.agent_name)
        for key, value in kwargs.items():
            trace.tags[key] = str(value)
        return trace.span_id

    def __getattr__(self, name):
        """Проксировать остальные методы."""
        return getattr(self.rag_agent, name)


class WorkflowMonitor:
    """Монитор для workflow operations."""

    def __init__(self, observability: ObservabilitySystem):
        self.observability = observability
        self.active_workflows: Dict[str, Dict[str, Any]] = {}

    async def start_workflow_monitoring(self, workflow_id: str, workflow_type: str) -> None:
        """Начать мониторинг workflow."""
        start_time = time.time()

        # Начинаем трейс workflow
        trace = await self.observability.start_trace(
            f"workflow_{workflow_type}", "workflow_engine"
        )

        # Сохраняем информацию об активном workflow
        self.active_workflows[workflow_id] = {
            "type": workflow_type,
            "start_time": start_time,
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "steps_completed": 0,
            "steps_total": 0
        }

        # Записываем метрику начала workflow
        await self.observability.record_metric(
            "workflow_started", 1,
            {"workflow_type": workflow_type},
            "workflow_engine", MetricType.COUNTER
        )

    async def update_workflow_progress(self, workflow_id: str,
                                     steps_completed: int,
                                     steps_total: int) -> None:
        """Обновить прогресс workflow."""
        if workflow_id in self.active_workflows:
            workflow_info = self.active_workflows[workflow_id]
            workflow_info["steps_completed"] = steps_completed
            workflow_info["steps_total"] = steps_total

            progress = (steps_completed / steps_total) * 100 if steps_total > 0 else 0

            await self.observability.record_metric(
                "workflow_progress", progress,
                {"workflow_id": workflow_id, "workflow_type": workflow_info["type"]},
                "workflow_engine", MetricType.GAUGE
            )

    async def finish_workflow_monitoring(self, workflow_id: str,
                                       status: str = "success",
                                       error: Optional[str] = None) -> None:
        """Завершить мониторинг workflow."""
        if workflow_id not in self.active_workflows:
            return

        workflow_info = self.active_workflows[workflow_id]
        duration = (time.time() - workflow_info["start_time"]) * 1000

        # Завершаем трейс
        await self.observability.finish_trace(
            workflow_info["span_id"], status, error
        )

        # Записываем метрики завершения
        await self.observability.record_metric(
            "workflow_duration", duration,
            {"workflow_type": workflow_info["type"], "status": status},
            "workflow_engine", MetricType.TIMER
        )

        if status == "success":
            await self.observability.record_metric(
                "workflow_completed", 1,
                {"workflow_type": workflow_info["type"]},
                "workflow_engine", MetricType.COUNTER
            )
        else:
            await self.observability.record_metric(
                "workflow_failed", 1,
                {"workflow_type": workflow_info["type"], "error": error or "unknown"},
                "workflow_engine", MetricType.COUNTER
            )

        # Удаляем из активных workflow
        del self.active_workflows[workflow_id]

    async def get_active_workflows_status(self) -> Dict[str, Any]:
        """Получить статус активных workflow."""
        current_time = time.time()

        active_count = len(self.active_workflows)
        long_running = 0
        avg_duration = 0

        if self.active_workflows:
            durations = []
            for workflow_info in self.active_workflows.values():
                duration = current_time - workflow_info["start_time"]
                durations.append(duration)

                if duration > 300:  # > 5 минут
                    long_running += 1

            avg_duration = sum(durations) / len(durations)

        return {
            "active_workflows": active_count,
            "long_running_workflows": long_running,
            "average_duration_seconds": avg_duration,
            "workflows_by_type": {}
        }


class MonitoringIntegrationManager:
    """Менеджер интеграции мониторинга с агентами."""

    def __init__(self, observability: ObservabilitySystem):
        self.observability = observability
        self.workflow_monitor = WorkflowMonitor(observability)
        self.monitored_agents: Dict[str, Any] = {}

    async def wrap_mega_agent(self, mega_agent) -> MonitoredMegaAgent:
        """Обернуть MegaAgent мониторингом."""
        monitored = MonitoredMegaAgent(mega_agent, self.observability)
        self.monitored_agents["mega_agent"] = monitored
        return monitored

    async def wrap_rag_agent(self, rag_agent) -> MonitoredRAGAgent:
        """Обернуть RAGPipelineAgent мониторингом."""
        monitored = MonitoredRAGAgent(rag_agent, self.observability)
        self.monitored_agents["rag_agent"] = monitored
        return monitored

    async def setup_system_monitoring(self) -> None:
        """Настроить системный мониторинг."""
        # Настраиваем алерты для агентов
        await self.observability.alert_manager.add_alert_rule(
            "command_duration", 5000, "gt", AlertSeverity.HIGH
        )

        await self.observability.alert_manager.add_alert_rule(
            "search_duration", 3000, "gt", AlertSeverity.MEDIUM
        )

        await self.observability.alert_manager.add_alert_rule(
            "workflow_duration", 300000, "gt", AlertSeverity.HIGH  # 5 минут
        )

        await self.observability.alert_manager.add_alert_rule(
            "command_errors", 5, "gt", AlertSeverity.CRITICAL
        )

    async def get_agents_health_report(self) -> Dict[str, Any]:
        """Получить отчет о здоровье всех агентов."""
        report = {
            "timestamp": time.time(),
            "agents": {},
            "overall_status": "healthy"
        }

        unhealthy_count = 0

        for agent_name, agent in self.monitored_agents.items():
            try:
                # Проверяем здоровье агента
                health = await self.observability.check_health(
                    agent_name, ComponentType.AGENT
                )

                report["agents"][agent_name] = {
                    "status": health.status.value,
                    "response_time_ms": health.response_time_ms,
                    "last_check": health.timestamp.isoformat()
                }

                if health.status != HealthStatus.HEALTHY:
                    unhealthy_count += 1

            except Exception as e:
                report["agents"][agent_name] = {
                    "status": "error",
                    "error": str(e)
                }
                unhealthy_count += 1

        # Определяем общий статус
        total_agents = len(self.monitored_agents)
        if unhealthy_count == 0:
            report["overall_status"] = "healthy"
        elif unhealthy_count < total_agents / 2:
            report["overall_status"] = "degraded"
        else:
            report["overall_status"] = "unhealthy"

        report["healthy_agents"] = total_agents - unhealthy_count
        report["total_agents"] = total_agents

        return report

    async def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Генерировать отчет о производительности."""
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(hours=hours)

        # Получаем метрики за период
        metrics = await self.observability.metrics_collector.get_metrics(
            since=since, limit=5000
        )

        # Получаем трейсы за период
        traces = await self.observability.tracing_collector.get_traces(
            since=since, limit=1000
        )

        # Анализируем производительность по компонентам
        performance_by_component = {}

        for metric in metrics:
            if metric.component and metric.metric_type.value in ["timer", "gauge"]:
                if metric.component not in performance_by_component:
                    performance_by_component[metric.component] = {
                        "response_times": [],
                        "error_count": 0,
                        "request_count": 0
                    }

                if "duration" in metric.name:
                    performance_by_component[metric.component]["response_times"].append(metric.value)
                elif "error" in metric.name:
                    performance_by_component[metric.component]["error_count"] += metric.value
                elif "request" in metric.name:
                    performance_by_component[metric.component]["request_count"] += metric.value

        # Составляем итоговый отчет
        report = {
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_metrics": len(metrics),
                "total_traces": len(traces),
                "components_monitored": len(performance_by_component)
            },
            "performance_by_component": {}
        }

        for component, data in performance_by_component.items():
            response_times = data["response_times"]

            if response_times:
                avg_response = sum(response_times) / len(response_times)
                max_response = max(response_times)
                min_response = min(response_times)
            else:
                avg_response = max_response = min_response = 0

            error_rate = (data["error_count"] / max(data["request_count"], 1)) * 100

            report["performance_by_component"][component] = {
                "avg_response_time_ms": avg_response,
                "max_response_time_ms": max_response,
                "min_response_time_ms": min_response,
                "error_rate_percent": error_rate,
                "total_requests": data["request_count"],
                "total_errors": data["error_count"]
            }

        return report


# Utility functions

async def create_monitoring_integration(observability: ObservabilitySystem) -> MonitoringIntegrationManager:
    """Создать менеджер интеграции мониторинга."""
    integration = MonitoringIntegrationManager(observability)
    await integration.setup_system_monitoring()
    return integration