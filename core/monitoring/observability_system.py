"""
Comprehensive Monitoring & Observability System для mega_agent_pro.

Обеспечивает:
- Real-time monitoring всех агентов и компонентов
- Distributed tracing для multi-agent workflows
- Metrics collection и aggregation
- Health checks и availability monitoring
- Performance analytics и anomaly detection
- Alerting и notification system
- Log aggregation и structured logging
- Dashboard data для visualization
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Типы метрик."""
    COUNTER = "counter"           # Возрастающий счетчик
    GAUGE = "gauge"              # Текущее значение
    HISTOGRAM = "histogram"       # Распределение значений
    TIMER = "timer"              # Измерение времени
    RATE = "rate"                # Скорость изменения


class AlertSeverity(str, Enum):
    """Уровни серьезности алертов."""
    CRITICAL = "critical"        # Критическая проблема
    HIGH = "high"               # Высокий приоритет
    MEDIUM = "medium"           # Средний приоритет
    LOW = "low"                 # Низкий приоритет
    INFO = "info"               # Информационный


class HealthStatus(str, Enum):
    """Статусы здоровья компонентов."""
    HEALTHY = "healthy"         # Все в порядке
    DEGRADED = "degraded"       # Частичные проблемы
    UNHEALTHY = "unhealthy"     # Серьезные проблемы
    UNKNOWN = "unknown"         # Неизвестный статус


class ComponentType(str, Enum):
    """Типы компонентов для мониторинга."""
    AGENT = "agent"             # Агенты
    SERVICE = "service"         # Сервисы
    DATABASE = "database"       # Базы данных
    CACHE = "cache"             # Системы кэширования
    WORKFLOW = "workflow"       # Workflow engine
    API = "api"                 # API endpoints
    SECURITY = "security"       # Security components


class Metric(BaseModel):
    """Метрика системы."""
    name: str = Field(..., description="Название метрики")
    value: Union[int, float] = Field(..., description="Значение метрики")
    metric_type: MetricType = Field(..., description="Тип метрики")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict, description="Теги метрики")
    component: Optional[str] = Field(None, description="Компонент")
    component_type: Optional[ComponentType] = Field(None, description="Тип компонента")


class Trace(BaseModel):
    """Трейс для distributed tracing."""
    trace_id: str = Field(..., description="ID трейса")
    span_id: str = Field(..., description="ID спана")
    parent_span_id: Optional[str] = Field(None, description="ID родительского спана")
    operation_name: str = Field(..., description="Название операции")
    service_name: str = Field(..., description="Название сервиса")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="Время завершения")
    duration_ms: Optional[float] = Field(None, description="Длительность в мс")
    status: str = Field("pending", description="Статус операции")
    tags: Dict[str, str] = Field(default_factory=dict, description="Теги трейса")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="Логи спана")
    error: Optional[str] = Field(None, description="Ошибка если есть")

    def finish(self, status: str = "success", error: Optional[str] = None) -> None:
        """Завершить трейс."""
        self.end_time = datetime.utcnow()
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        if error:
            self.error = error

    def add_log(self, message: str, level: str = "info", **kwargs) -> None:
        """Добавить лог к трейсу."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": level,
            **kwargs
        }
        self.logs.append(log_entry)


class HealthCheck(BaseModel):
    """Результат health check."""
    component: str = Field(..., description="Компонент")
    component_type: ComponentType = Field(..., description="Тип компонента")
    status: HealthStatus = Field(..., description="Статус здоровья")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: float = Field(..., description="Время ответа в мс")
    details: Dict[str, Any] = Field(default_factory=dict, description="Детали проверки")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class Alert(BaseModel):
    """Алерт системы."""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Название алерта")
    description: str = Field(..., description="Описание проблемы")
    severity: AlertSeverity = Field(..., description="Серьезность")
    component: str = Field(..., description="Компонент")
    component_type: ComponentType = Field(..., description="Тип компонента")
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None, description="Время решения")
    is_active: bool = Field(True, description="Активен ли алерт")
    metric_value: Optional[Union[int, float]] = Field(None, description="Значение метрики")
    threshold: Optional[Union[int, float]] = Field(None, description="Пороговое значение")
    tags: Dict[str, str] = Field(default_factory=dict, description="Теги алерта")

    def resolve(self) -> None:
        """Разрешить алерт."""
        self.resolved_at = datetime.utcnow()
        self.is_active = False


class MetricsCollector:
    """Коллектор метрик."""

    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.metric_aggregates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def record_metric(self, metric: Metric) -> None:
        """Записать метрику."""
        async with self._lock:
            self.metrics.append(metric)
            await self._update_aggregates(metric)

    async def record_counter(self, name: str, value: Union[int, float] = 1,
                           tags: Optional[Dict[str, str]] = None,
                           component: Optional[str] = None) -> None:
        """Записать counter метрику."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            tags=tags or {},
            component=component
        )
        await self.record_metric(metric)

    async def record_gauge(self, name: str, value: Union[int, float],
                          tags: Optional[Dict[str, str]] = None,
                          component: Optional[str] = None) -> None:
        """Записать gauge метрику."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags or {},
            component=component
        )
        await self.record_metric(metric)

    async def record_timer(self, name: str, duration_ms: float,
                          tags: Optional[Dict[str, str]] = None,
                          component: Optional[str] = None) -> None:
        """Записать timer метрику."""
        metric = Metric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            tags=tags or {},
            component=component
        )
        await self.record_metric(metric)

    async def _update_aggregates(self, metric: Metric) -> None:
        """Обновить агрегированные метрики."""
        key = f"{metric.name}:{metric.component or 'global'}"

        if key not in self.metric_aggregates:
            self.metric_aggregates[key] = {
                "count": 0,
                "sum": 0,
                "min": float('inf'),
                "max": float('-inf'),
                "avg": 0,
                "last_value": None,
                "last_update": None
            }

        agg = self.metric_aggregates[key]
        agg["count"] += 1
        agg["sum"] += metric.value
        agg["min"] = min(agg["min"], metric.value)
        agg["max"] = max(agg["max"], metric.value)
        agg["avg"] = agg["sum"] / agg["count"]
        agg["last_value"] = metric.value
        agg["last_update"] = metric.timestamp

    async def get_metrics(self, component: Optional[str] = None,
                         metric_type: Optional[MetricType] = None,
                         since: Optional[datetime] = None,
                         limit: int = 1000) -> List[Metric]:
        """Получить метрики с фильтрацией."""
        async with self._lock:
            filtered_metrics = []

            for metric in reversed(self.metrics):
                if len(filtered_metrics) >= limit:
                    break

                if component and metric.component != component:
                    continue

                if metric_type and metric.metric_type != metric_type:
                    continue

                if since and metric.timestamp < since:
                    continue

                filtered_metrics.append(metric)

            return list(reversed(filtered_metrics))

    async def get_aggregates(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Получить агрегированные метрики."""
        async with self._lock:
            if component:
                return {k: v for k, v in self.metric_aggregates.items()
                       if component in k}
            return dict(self.metric_aggregates)


class TracingCollector:
    """Коллектор трейсов для distributed tracing."""

    def __init__(self, max_traces: int = 5000):
        self.traces: Dict[str, Trace] = {}
        self.completed_traces: deque = deque(maxlen=max_traces)
        self._lock = asyncio.Lock()

    async def start_trace(self, operation_name: str, service_name: str,
                         parent_span_id: Optional[str] = None,
                         trace_id: Optional[str] = None) -> Trace:
        """Начать новый трейс."""
        async with self._lock:
            if not trace_id:
                trace_id = str(uuid.uuid4())

            span_id = str(uuid.uuid4())

            trace = Trace(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                operation_name=operation_name,
                service_name=service_name
            )

            self.traces[span_id] = trace
            return trace

    async def finish_trace(self, span_id: str, status: str = "success",
                          error: Optional[str] = None) -> None:
        """Завершить трейс."""
        async with self._lock:
            if span_id in self.traces:
                trace = self.traces[span_id]
                trace.finish(status, error)
                self.completed_traces.append(trace)
                del self.traces[span_id]

    async def add_trace_log(self, span_id: str, message: str,
                           level: str = "info", **kwargs) -> None:
        """Добавить лог к трейсу."""
        async with self._lock:
            if span_id in self.traces:
                self.traces[span_id].add_log(message, level, **kwargs)

    async def get_traces(self, trace_id: Optional[str] = None,
                        service_name: Optional[str] = None,
                        since: Optional[datetime] = None,
                        limit: int = 100) -> List[Trace]:
        """Получить трейсы с фильтрацией."""
        async with self._lock:
            all_traces = list(self.completed_traces) + list(self.traces.values())
            filtered_traces = []

            for trace in reversed(all_traces):
                if len(filtered_traces) >= limit:
                    break

                if trace_id and trace.trace_id != trace_id:
                    continue

                if service_name and trace.service_name != service_name:
                    continue

                if since and trace.start_time < since:
                    continue

                filtered_traces.append(trace)

            return filtered_traces


class HealthMonitor:
    """Монитор здоровья компонентов."""

    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_history: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()

    async def register_health_check(self, component: str,
                                   component_type: ComponentType,
                                   check_func: Callable[[], bool]) -> None:
        """Зарегистрировать health check."""
        # В реальной реализации здесь была бы регистрация функции проверки
        pass

    async def check_component_health(self, component: str,
                                   component_type: ComponentType,
                                   check_func: Optional[Callable] = None) -> HealthCheck:
        """Проверить здоровье компонента."""
        start_time = time.time()

        try:
            if check_func:
                is_healthy = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            else:
                # Базовая проверка - компонент считается здоровым
                is_healthy = True

            response_time = (time.time() - start_time) * 1000

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

            health_check = HealthCheck(
                component=component,
                component_type=component_type,
                status=status,
                response_time_ms=response_time,
                details={"check_time": datetime.utcnow().isoformat()}
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                component=component,
                component_type=component_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e)
            )

        async with self._lock:
            self.health_checks[component] = health_check
            self.health_history.append(health_check)

        return health_check

    async def get_system_health(self) -> Dict[str, Any]:
        """Получить общее здоровье системы."""
        async with self._lock:
            if not self.health_checks:
                return {
                    "overall_status": HealthStatus.UNKNOWN,
                    "healthy_components": 0,
                    "total_components": 0,
                    "components": {}
                }

            healthy_count = sum(1 for hc in self.health_checks.values()
                              if hc.status == HealthStatus.HEALTHY)
            total_count = len(self.health_checks)

            if healthy_count == total_count:
                overall_status = HealthStatus.HEALTHY
            elif healthy_count > total_count / 2:
                overall_status = HealthStatus.DEGRADED
            else:
                overall_status = HealthStatus.UNHEALTHY

            return {
                "overall_status": overall_status,
                "healthy_components": healthy_count,
                "total_components": total_count,
                "health_percentage": (healthy_count / total_count) * 100,
                "components": {name: hc.dict() for name, hc in self.health_checks.items()},
                "last_check": max(hc.timestamp for hc in self.health_checks.values()).isoformat()
            }


class AlertManager:
    """Менеджер алертов."""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_history: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()

    async def add_alert_rule(self, metric_name: str, threshold: Union[int, float],
                           operator: str, severity: AlertSeverity,
                           component: Optional[str] = None) -> None:
        """Добавить правило алерта."""
        rule = {
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,  # "gt", "lt", "eq", "gte", "lte"
            "severity": severity,
            "component": component
        }
        self.alert_rules.append(rule)

    async def check_metric_alerts(self, metric: Metric) -> List[Alert]:
        """Проверить метрику на срабатывание алертов."""
        triggered_alerts = []

        for rule in self.alert_rules:
            if rule["metric_name"] != metric.name:
                continue

            if rule["component"] and rule["component"] != metric.component:
                continue

            should_alert = self._evaluate_rule(metric.value, rule["threshold"], rule["operator"])

            if should_alert:
                alert = Alert(
                    name=f"{metric.name}_threshold",
                    description=f"Metric {metric.name} exceeded threshold",
                    severity=rule["severity"],
                    component=metric.component or "unknown",
                    component_type=metric.component_type or ComponentType.SERVICE,
                    metric_value=metric.value,
                    threshold=rule["threshold"],
                    tags=metric.tags
                )

                triggered_alerts.append(alert)
                await self._trigger_alert(alert)

        return triggered_alerts

    def _evaluate_rule(self, value: Union[int, float], threshold: Union[int, float], operator: str) -> bool:
        """Оценить правило алерта."""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "eq":
            return value == threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        return False

    async def _trigger_alert(self, alert: Alert) -> None:
        """Срабатывание алерта."""
        async with self._lock:
            # Проверяем, не активен ли уже похожий алерт
            existing_key = f"{alert.name}:{alert.component}"

            if existing_key in self.alerts:
                existing_alert = self.alerts[existing_key]
                if existing_alert.is_active:
                    # Обновляем существующий алерт
                    existing_alert.metric_value = alert.metric_value
                    existing_alert.triggered_at = alert.triggered_at
                    return

            self.alerts[existing_key] = alert
            self.alert_history.append(alert)

    async def resolve_alert(self, alert_id: str) -> bool:
        """Разрешить алерт."""
        async with self._lock:
            for alert in self.alerts.values():
                if alert.alert_id == alert_id and alert.is_active:
                    alert.resolve()
                    return True
            return False

    async def get_active_alerts(self, severity: Optional[AlertSeverity] = None,
                               component: Optional[str] = None) -> List[Alert]:
        """Получить активные алерты."""
        async with self._lock:
            active_alerts = [alert for alert in self.alerts.values() if alert.is_active]

            if severity:
                active_alerts = [alert for alert in active_alerts if alert.severity == severity]

            if component:
                active_alerts = [alert for alert in active_alerts if alert.component == component]

            return sorted(active_alerts, key=lambda x: x.triggered_at, reverse=True)


class PerformanceAnalyzer:
    """Анализатор производительности."""

    def __init__(self):
        self.performance_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = asyncio.Lock()

    async def analyze_component_performance(self, component: str,
                                          metrics: List[Metric]) -> Dict[str, Any]:
        """Анализировать производительность компонента."""
        async with self._lock:
            if not metrics:
                return {"component": component, "status": "no_data"}

            # Фильтруем метрики по компоненту
            component_metrics = [m for m in metrics if m.component == component]

            if not component_metrics:
                return {"component": component, "status": "no_component_data"}

            # Анализируем различные типы метрик
            analysis = {
                "component": component,
                "metric_count": len(component_metrics),
                "time_range": {
                    "start": min(m.timestamp for m in component_metrics).isoformat(),
                    "end": max(m.timestamp for m in component_metrics).isoformat()
                }
            }

            # Анализ по типам метрик
            by_type = defaultdict(list)
            for metric in component_metrics:
                by_type[metric.metric_type].append(metric.value)

            for metric_type, values in by_type.items():
                if values:
                    analysis[metric_type.value] = {
                        "count": len(values),
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "latest": values[-1] if values else None
                    }

            # Определяем статус производительности
            analysis["performance_status"] = self._assess_performance(analysis)

            return analysis

    def _assess_performance(self, analysis: Dict[str, Any]) -> str:
        """Оценить статус производительности."""
        # Простая эвристика для оценки производительности
        if "timer" in analysis:
            avg_time = analysis["timer"]["avg"]
            if avg_time > 1000:  # > 1 секунды
                return "poor"
            elif avg_time > 500:  # > 500мс
                return "degraded"
            else:
                return "good"

        if "gauge" in analysis:
            # Можно добавить специфические проверки для gauge метрик
            pass

        return "unknown"

    async def detect_anomalies(self, component: str, metric_name: str,
                              window_minutes: int = 30) -> Dict[str, Any]:
        """Обнаружение аномалий в метриках."""
        # Простой алгоритм обнаружения аномалий
        since = datetime.utcnow() - timedelta(minutes=window_minutes)

        # В реальной реализации здесь были бы более сложные алгоритмы
        # например, статистические методы или ML модели

        return {
            "component": component,
            "metric": metric_name,
            "window_minutes": window_minutes,
            "anomalies_detected": 0,
            "status": "normal"
        }


class ObservabilitySystem:
    """Главная система наблюдаемости."""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.tracing_collector = TracingCollector()
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.performance_analyzer = PerformanceAnalyzer()
        self._monitoring_tasks: Set[asyncio.Task] = set()

    async def initialize(self) -> None:
        """Инициализация системы мониторинга."""
        # Настраиваем базовые алерты
        await self.alert_manager.add_alert_rule(
            "response_time", 1000, "gt", AlertSeverity.HIGH
        )
        await self.alert_manager.add_alert_rule(
            "error_rate", 0.05, "gt", AlertSeverity.CRITICAL
        )
        await self.alert_manager.add_alert_rule(
            "memory_usage", 0.9, "gt", AlertSeverity.HIGH
        )

        # Запускаем фоновые задачи мониторинга
        task = asyncio.create_task(self._background_monitoring())
        self._monitoring_tasks.add(task)
        task.add_done_callback(self._monitoring_tasks.discard)

    async def _background_monitoring(self) -> None:
        """Фоновый мониторинг системы."""
        while True:
            try:
                # Проверяем здоровье компонентов
                await self._check_system_health()

                # Проверяем алерты на метриках
                await self._check_metric_alerts()

                # Ждем следующей итерации
                await asyncio.sleep(30)  # Проверка каждые 30 секунд

            except Exception as e:
                # Логируем ошибку, но продолжаем мониторинг
                await self.record_metric("monitoring_errors", 1, {"error": str(e)})
                await asyncio.sleep(60)  # Увеличиваем интервал при ошибках

    async def _check_system_health(self) -> None:
        """Периодическая проверка здоровья системы."""
        # Проверяем основные компоненты
        components = [
            ("memory_manager", ComponentType.SERVICE),
            ("cache_system", ComponentType.CACHE),
            ("mega_agent", ComponentType.AGENT),
            ("workflow_engine", ComponentType.WORKFLOW)
        ]

        for component, comp_type in components:
            await self.health_monitor.check_component_health(component, comp_type)

    async def _check_metric_alerts(self) -> None:
        """Проверка алертов на основе метрик."""
        # Получаем последние метрики
        recent_metrics = await self.metrics_collector.get_metrics(
            since=datetime.utcnow() - timedelta(minutes=5),
            limit=100
        )

        for metric in recent_metrics:
            await self.alert_manager.check_metric_alerts(metric)

    # Public API для интеграции с другими компонентами

    async def record_metric(self, name: str, value: Union[int, float],
                           tags: Optional[Dict[str, str]] = None,
                           component: Optional[str] = None,
                           metric_type: MetricType = MetricType.GAUGE) -> None:
        """Записать метрику."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            component=component
        )
        await self.metrics_collector.record_metric(metric)

    async def start_trace(self, operation: str, service: str,
                         parent_span_id: Optional[str] = None) -> Trace:
        """Начать трейс операции."""
        return await self.tracing_collector.start_trace(operation, service, parent_span_id)

    async def finish_trace(self, span_id: str, status: str = "success",
                          error: Optional[str] = None) -> None:
        """Завершить трейс операции."""
        await self.tracing_collector.finish_trace(span_id, status, error)

    async def check_health(self, component: str, component_type: ComponentType) -> HealthCheck:
        """Проверить здоровье компонента."""
        return await self.health_monitor.check_component_health(component, component_type)

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Получить данные для dashboard."""
        # Получаем данные за последний час
        since = datetime.utcnow() - timedelta(hours=1)

        metrics = await self.metrics_collector.get_metrics(since=since, limit=500)
        traces = await self.tracing_collector.get_traces(since=since, limit=100)
        system_health = await self.health_monitor.get_system_health()
        active_alerts = await self.alert_manager.get_active_alerts()

        # Агрегируем данные для dashboard
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": system_health,
            "metrics_summary": {
                "total_metrics": len(metrics),
                "unique_components": len(set(m.component for m in metrics if m.component)),
                "metric_types": list(set(m.metric_type.value for m in metrics))
            },
            "tracing_summary": {
                "total_traces": len(traces),
                "unique_services": len(set(t.service_name for t in traces)),
                "avg_duration_ms": sum(t.duration_ms for t in traces if t.duration_ms) / len(traces) if traces else 0
            },
            "alerts_summary": {
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "alerts_by_severity": {
                    severity.value: len([a for a in active_alerts if a.severity == severity])
                    for severity in AlertSeverity
                }
            },
            "recent_metrics": [m.dict() for m in metrics[-20:]],  # Последние 20 метрик
            "recent_traces": [t.dict() for t in traces[-10:]],     # Последние 10 трейсов
            "active_alerts": [a.dict() for a in active_alerts[:10]]  # Топ 10 алертов
        }

        return dashboard_data

    async def get_component_analytics(self, component: str) -> Dict[str, Any]:
        """Получить аналитику для компонента."""
        since = datetime.utcnow() - timedelta(hours=24)

        # Получаем метрики компонента
        metrics = await self.metrics_collector.get_metrics(
            component=component, since=since, limit=1000
        )

        # Получаем трейсы компонента
        traces = await self.tracing_collector.get_traces(
            service_name=component, since=since, limit=500
        )

        # Анализируем производительность
        performance = await self.performance_analyzer.analyze_component_performance(
            component, metrics
        )

        # Получаем здоровье компонента
        health = self.health_monitor.health_checks.get(component)

        # Получаем алерты компонента
        alerts = await self.alert_manager.get_active_alerts(component=component)

        return {
            "component": component,
            "timestamp": datetime.utcnow().isoformat(),
            "health": health.dict() if health else None,
            "performance": performance,
            "metrics_count": len(metrics),
            "traces_count": len(traces),
            "active_alerts": len(alerts),
            "recent_activity": {
                "last_metric": metrics[-1].timestamp.isoformat() if metrics else None,
                "last_trace": traces[-1].start_time.isoformat() if traces else None
            }
        }

    async def shutdown(self) -> None:
        """Корректное завершение работы системы мониторинга."""
        # Отменяем все фоновые задачи
        for task in self._monitoring_tasks:
            task.cancel()

        # Ждем завершения задач
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)


# Decorators для автоматического мониторинга

def monitor_performance(component: str, operation: str):
    """Декоратор для мониторинга производительности функций."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Получаем глобальную систему мониторинга (в реальности через DI)
            observability = getattr(wrapper, '_observability', None)

            if observability:
                # Начинаем трейс
                trace = await observability.start_trace(operation, component)
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

                    # Записываем успешную метрику
                    duration = (time.time() - start_time) * 1000
                    await observability.record_metric(
                        f"{operation}_duration",
                        duration,
                        {"component": component},
                        component,
                        MetricType.TIMER
                    )

                    await observability.finish_trace(trace.span_id, "success")
                    return result

                except Exception as e:
                    # Записываем ошибку
                    await observability.record_metric(
                        f"{operation}_errors",
                        1,
                        {"component": component, "error": str(e)},
                        component,
                        MetricType.COUNTER
                    )

                    await observability.finish_trace(trace.span_id, "error", str(e))
                    raise
            else:
                # Мониторинг недоступен, выполняем функцию как обычно
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        return wrapper
    return decorator


# Factory functions

async def create_observability_system() -> ObservabilitySystem:
    """Создать и инициализировать систему наблюдаемости."""
    system = ObservabilitySystem()
    await system.initialize()
    return system