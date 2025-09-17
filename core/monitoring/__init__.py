"""
Monitoring & Observability module для mega_agent_pro.

Provides comprehensive monitoring and observability:
- Real-time monitoring всех агентов и компонентов
- Distributed tracing для multi-agent workflows
- Metrics collection и aggregation
- Health checks и availability monitoring
- Performance analytics и anomaly detection
- Alerting и notification system
- Agent integration и automatic instrumentation
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Observability System
    "ObservabilitySystem",
    "MetricsCollector",
    "TracingCollector",
    "HealthMonitor",
    "AlertManager",
    "PerformanceAnalyzer",

    # Models
    "Metric",
    "Trace",
    "HealthCheck",
    "Alert",
    "MetricType",
    "AlertSeverity",
    "HealthStatus",
    "ComponentType",

    # Agent Monitoring
    "MonitoringIntegrationManager",
    "MonitoredMegaAgent",
    "MonitoredRAGAgent",
    "WorkflowMonitor",
    "AgentMonitoringMixin",

    # Decorators
    "monitor_performance",

    # Factory Functions
    "create_observability_system",
    "create_monitoring_integration",
]

# Import core observability system
from .observability_system import (
    ObservabilitySystem,
    MetricsCollector,
    TracingCollector,
    HealthMonitor,
    AlertManager,
    PerformanceAnalyzer,
    Metric,
    Trace,
    HealthCheck,
    Alert,
    MetricType,
    AlertSeverity,
    HealthStatus,
    ComponentType,
    monitor_performance,
    create_observability_system,
)

# Import agent monitoring
from .agent_monitoring import (
    MonitoringIntegrationManager,
    MonitoredMegaAgent,
    MonitoredRAGAgent,
    WorkflowMonitor,
    AgentMonitoringMixin,
    create_monitoring_integration,
)