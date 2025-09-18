#!/usr/bin/env python3
"""
Monitoring & Observability System Demo для mega_agent_pro.

Демонстрирует:
1. Real-time monitoring всех агентов и компонентов
2. Distributed tracing для multi-agent workflows
3. Metrics collection и aggregation
4. Health checks и availability monitoring
5. Performance analytics и anomaly detection
6. Alerting и notification system
7. Dashboard data generation
8. Agent integration и automatic instrumentation

Запуск:
    python monitoring_observability_demo.py
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.monitoring import (
    MetricType,
    AlertSeverity,
    ComponentType,
    HealthStatus,
    create_observability_system,
    create_monitoring_integration,
)

# Import agents for monitoring integration
try:
    from core.groupagents.mega_agent import MegaAgent, MegaAgentCommand, UserRole, CommandType
    from core.groupagents.rag_pipeline_agent import RAGPipelineAgent, SearchQuery
    from core.memory.memory_manager import MemoryManager
    AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import agents for monitoring: {e}")
    AGENTS_AVAILABLE = False


async def demo_basic_monitoring():
    """Демонстрация базового мониторинга."""
    print("📊 === Basic Monitoring Demo ===\n")

    observability = await create_observability_system()

    # Записываем различные типы метрик
    print("📈 Recording various metrics...")

    # Counter метрики
    await observability.record_metric("requests_total", 1, {"endpoint": "/api/status"}, "api_server", MetricType.COUNTER)
    await observability.record_metric("requests_total", 1, {"endpoint": "/api/health"}, "api_server", MetricType.COUNTER)

    # Gauge метрики
    await observability.record_metric("memory_usage_percent", 75.5, {"server": "main"}, "system", MetricType.GAUGE)
    await observability.record_metric("cpu_usage_percent", 45.2, {"server": "main"}, "system", MetricType.GAUGE)

    # Timer метрики
    await observability.record_metric("response_time", 150.5, {"endpoint": "/api/search"}, "api_server", MetricType.TIMER)
    await observability.record_metric("response_time", 89.3, {"endpoint": "/api/health"}, "api_server", MetricType.TIMER)

    print("   ✅ Recorded 6 different metrics")

    # Получаем агрегированные метрики
    print("\n📊 Retrieving aggregated metrics...")
    aggregates = await observability.metrics_collector.get_aggregates()

    for key, agg in aggregates.items():
        print(f"   📈 {key}:")
        print(f"      Count: {agg['count']}, Avg: {agg['avg']:.2f}")
        print(f"      Min: {agg['min']:.2f}, Max: {agg['max']:.2f}")
        print(f"      Last: {agg['last_value']:.2f}")

    print()


async def demo_distributed_tracing():
    """Демонстрация distributed tracing."""
    print("🔍 === Distributed Tracing Demo ===\n")

    observability = await create_observability_system()

    print("🔄 Simulating multi-service workflow...")

    # Симулируем сложный workflow с несколькими сервисами
    # 1. Главный трейс
    main_trace = await observability.start_trace("process_legal_request", "api_gateway")
    main_trace.tags["user_id"] = "user_123"
    main_trace.tags["request_type"] = "contract_review"

    await asyncio.sleep(0.01)  # Симуляция работы

    # 2. Дочерний трейс - валидация
    validation_trace = await observability.start_trace(
        "validate_request", "validation_service",
        parent_span_id=main_trace.span_id
    )
    validation_trace.tags["validation_type"] = "security"

    await asyncio.sleep(0.005)  # Симуляция валидации
    await observability.finish_trace(validation_trace.span_id, "success")

    # 3. Дочерний трейс - обработка документа
    document_trace = await observability.start_trace(
        "process_document", "document_service",
        parent_span_id=main_trace.span_id
    )
    document_trace.tags["document_type"] = "contract"

    await asyncio.sleep(0.015)  # Симуляция обработки документа
    await observability.finish_trace(document_trace.span_id, "success")

    # 4. Дочерний трейс - поиск в базе знаний
    search_trace = await observability.start_trace(
        "knowledge_search", "search_service",
        parent_span_id=main_trace.span_id
    )
    search_trace.tags["query_type"] = "semantic_search"

    await asyncio.sleep(0.008)  # Симуляция поиска
    await observability.finish_trace(search_trace.span_id, "success")

    # 5. Завершаем главный трейс
    await observability.finish_trace(main_trace.span_id, "success")

    print(f"   ✅ Main trace: {main_trace.trace_id}")
    print(f"      🔄 Validation: {validation_trace.span_id}")
    print(f"      📄 Document processing: {document_trace.span_id}")
    print(f"      🔍 Knowledge search: {search_trace.span_id}")

    # Получаем трейсы
    print("\n📋 Retrieving trace information...")
    traces = await observability.tracing_collector.get_traces(
        trace_id=main_trace.trace_id, limit=10
    )

    for trace in traces:
        duration = f"{trace.duration_ms:.2f}ms" if trace.duration_ms else "in progress"
        print(f"   🔍 {trace.operation_name} ({trace.service_name}): {duration}")

    print()


async def demo_health_monitoring():
    """Демонстрация мониторинга здоровья."""
    print("🏥 === Health Monitoring Demo ===\n")

    observability = await create_observability_system()

    # Проверяем здоровье различных компонентов
    components = [
        ("database", ComponentType.DATABASE),
        ("cache_redis", ComponentType.CACHE),
        ("mega_agent", ComponentType.AGENT),
        ("api_server", ComponentType.API),
        ("workflow_engine", ComponentType.WORKFLOW)
    ]

    print("🔍 Checking component health...")

    health_results = []
    for component, comp_type in components:
        # Симулируем разное здоровье компонентов
        def mock_health_check():
            # Случайно определяем здоровье для демонстрации
            return random.choice([True, True, True, False])  # 75% здоровых

        health = await observability.health_monitor.check_component_health(
            component, comp_type, mock_health_check
        )
        health_results.append(health)

        status_icon = "✅" if health.status == HealthStatus.HEALTHY else "❌"
        print(f"   {status_icon} {component} ({comp_type.value}): {health.status.value}")
        print(f"      Response time: {health.response_time_ms:.2f}ms")

    # Получаем общее здоровье системы
    print("\n🏥 System health summary:")
    system_health = await observability.health_monitor.get_system_health()

    print(f"   🎯 Overall status: {system_health['overall_status'].upper()}")
    print(f"   📊 Health percentage: {system_health['health_percentage']:.1f}%")
    print(f"   ✅ Healthy components: {system_health['healthy_components']}/{system_health['total_components']}")

    print()


async def demo_alerting_system():
    """Демонстрация системы алертов."""
    print("🚨 === Alerting System Demo ===\n")

    observability = await create_observability_system()

    # Настраиваем правила алертов
    print("⚙️ Setting up alert rules...")
    await observability.alert_manager.add_alert_rule(
        "response_time", 100, "gt", AlertSeverity.HIGH
    )
    await observability.alert_manager.add_alert_rule(
        "error_rate", 5, "gt", AlertSeverity.CRITICAL
    )
    await observability.alert_manager.add_alert_rule(
        "memory_usage", 80, "gt", AlertSeverity.MEDIUM
    )

    print("   ✅ Configured 3 alert rules")

    # Генерируем метрики, которые должны срабатывать алерты
    print("\n🔥 Generating metrics that trigger alerts...")

    # Медленный response time
    await observability.record_metric(
        "response_time", 150, {"endpoint": "/api/slow"}, "api_server", MetricType.TIMER
    )

    # Высокий error rate
    await observability.record_metric(
        "error_rate", 8, {"service": "payment"}, "payment_service", MetricType.GAUGE
    )

    # Высокое использование памяти
    await observability.record_metric(
        "memory_usage", 85, {"server": "worker-1"}, "worker_service", MetricType.GAUGE
    )

    # Нормальная метрика (не должна срабатывать)
    await observability.record_metric(
        "response_time", 50, {"endpoint": "/api/fast"}, "api_server", MetricType.TIMER
    )

    # Ждем немного для обработки алертов
    await asyncio.sleep(0.1)

    # Получаем активные алерты
    print("\n🚨 Active alerts:")
    active_alerts = await observability.alert_manager.get_active_alerts()

    if active_alerts:
        for alert in active_alerts:
            severity_icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.HIGH else "🟠"
            print(f"   {severity_icon} {alert.name} ({alert.severity.value})")
            print(f"      Component: {alert.component}")
            print(f"      Value: {alert.metric_value} > {alert.threshold}")
            print(f"      Triggered: {alert.triggered_at.strftime('%H:%M:%S')}")
    else:
        print("   ✅ No active alerts")

    print()


async def demo_agent_monitoring():
    """Демонстрация мониторинга агентов."""
    print("🤖 === Agent Monitoring Demo ===\n")

    if not AGENTS_AVAILABLE:
        print("❌ Agents not available, skipping agent monitoring demo")
        return

    observability = await create_observability_system()
    integration = await create_monitoring_integration(observability)

    # Создаем агентов
    memory_manager = MemoryManager()
    mega_agent = MegaAgent(memory_manager=memory_manager)
    rag_agent = RAGPipelineAgent(memory_manager=memory_manager)

    # Оборачиваем агентов мониторингом
    print("🔧 Setting up agent monitoring...")
    monitored_mega = await integration.wrap_mega_agent(mega_agent)
    monitored_rag = await integration.wrap_rag_agent(rag_agent)

    print("   ✅ Wrapped MegaAgent with monitoring")
    print("   ✅ Wrapped RAGPipelineAgent with monitoring")

    # Демонстрируем мониторимые операции
    print("\n🎯 Executing monitored operations...")

    # Команда MegaAgent
    command = MegaAgentCommand(
        user_id="demo_user",
        command_type=CommandType.ADMIN,
        action="status_check",
        payload={"status": "check"}
    )
    await monitored_mega.handle_command(command, UserRole.ADMIN)
    print("   ✅ Executed monitored MegaAgent command")

    # Поиск RAGAgent
    search_query = SearchQuery(query_text="legal documents", limit=5)
    await monitored_rag.asearch(search_query, "demo_user")
    print("   ✅ Executed monitored RAG search")

    # Получаем отчет о здоровье агентов
    print("\n🏥 Agent health report:")
    health_report = await integration.get_agents_health_report()

    print(f"   🎯 Overall status: {health_report['overall_status'].upper()}")
    print(f"   📊 Healthy agents: {health_report['healthy_agents']}/{health_report['total_agents']}")

    for agent_name, agent_health in health_report['agents'].items():
        status_icon = "✅" if agent_health['status'] == 'healthy' else "❌"
        print(f"   {status_icon} {agent_name}: {agent_health['status']}")

    print()


async def demo_performance_analytics():
    """Демонстрация аналитики производительности."""
    print("📊 === Performance Analytics Demo ===\n")

    observability = await create_observability_system()

    # Генерируем данные производительности для анализа
    print("📈 Generating performance data...")

    components = ["web_server", "database", "cache", "search_engine"]
    operations = ["read", "write", "search", "update"]

    # Генерируем метрики производительности
    for _ in range(50):
        component = random.choice(components)
        operation = random.choice(operations)

        # Симулируем разные времена ответа
        if component == "database":
            response_time = random.uniform(50, 200)  # База данных медленнее
        elif component == "cache":
            response_time = random.uniform(1, 10)    # Кэш быстрый
        else:
            response_time = random.uniform(20, 100)  # Средние значения

        await observability.record_metric(
            f"{operation}_time", response_time,
            {"component": component, "operation": operation},
            component, MetricType.TIMER
        )

    print("   ✅ Generated 50 performance metrics")

    # Анализируем производительность по компонентам
    print("\n🔍 Analyzing component performance...")

    for component in components:
        # Получаем метрики компонента
        since = datetime.utcnow() - timedelta(minutes=5)
        metrics = await observability.metrics_collector.get_metrics(
            component=component, since=since, limit=100
        )

        if metrics:
            times = [m.value for m in metrics if "time" in m.name]
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)

                # Определяем статус производительности
                if avg_time > 150:
                    status = "🔴 POOR"
                elif avg_time > 75:
                    status = "🟡 DEGRADED"
                else:
                    status = "✅ GOOD"

                print(f"   📊 {component}: {status}")
                print(f"      Avg: {avg_time:.1f}ms, Max: {max_time:.1f}ms, Min: {min_time:.1f}ms")
                print(f"      Samples: {len(times)}")

    print()


async def demo_dashboard_data():
    """Демонстрация генерации данных для dashboard."""
    print("📱 === Dashboard Data Demo ===\n")

    observability = await create_observability_system()

    # Генерируем разнообразные данные для dashboard
    print("📊 Generating dashboard data...")

    # Симулируем активность системы
    for i in range(30):
        # Различные метрики
        await observability.record_metric("page_views", random.randint(1, 10), {"page": f"page_{i%5}"}, "web_server")
        await observability.record_metric("api_requests", random.randint(1, 20), {"endpoint": f"/api/v{i%3}"}, "api_server")
        await observability.record_metric("db_queries", random.randint(1, 15), {"table": f"table_{i%4}"}, "database")

        # Трейсы операций
        trace = await observability.start_trace(f"operation_{i%3}", f"service_{i%2}")
        await asyncio.sleep(0.001)  # Короткая задержка
        await observability.finish_trace(trace.span_id, "success")

        # Случайные ошибки
        if random.random() < 0.1:  # 10% вероятность ошибки
            await observability.record_metric("errors", 1, {"type": "timeout"}, "api_server", MetricType.COUNTER)

    print("   ✅ Generated comprehensive system activity data")

    # Получаем данные для dashboard
    print("\n📱 Generating dashboard data...")
    dashboard_data = await observability.get_dashboard_data()

    print("📊 Dashboard Summary:")
    print(f"   🎯 System Health: {dashboard_data['system_health']['overall_status'].upper()}")
    print(f"   📈 Total Metrics: {dashboard_data['metrics_summary']['total_metrics']}")
    print(f"   🔍 Total Traces: {dashboard_data['tracing_summary']['total_traces']}")
    print(f"   🚨 Active Alerts: {dashboard_data['alerts_summary']['active_alerts']}")

    print("\n📊 Metrics Summary:")
    print(f"   🏢 Components: {dashboard_data['metrics_summary']['unique_components']}")
    print(f"   📊 Metric Types: {', '.join(dashboard_data['metrics_summary']['metric_types'])}")

    print("\n🔍 Tracing Summary:")
    print(f"   🏢 Services: {dashboard_data['tracing_summary']['unique_services']}")
    print(f"   ⏱️ Avg Duration: {dashboard_data['tracing_summary']['avg_duration_ms']:.2f}ms")

    if dashboard_data['alerts_summary']['active_alerts'] > 0:
        print("\n🚨 Alerts by Severity:")
        for severity, count in dashboard_data['alerts_summary']['alerts_by_severity'].items():
            if count > 0:
                print(f"   {severity}: {count}")

    print()


async def demo_workflow_monitoring():
    """Демонстрация мониторинга workflow."""
    print("🔄 === Workflow Monitoring Demo ===\n")

    observability = await create_observability_system()
    integration = await create_monitoring_integration(observability)

    workflow_monitor = integration.workflow_monitor

    # Симулируем workflow
    print("🚀 Starting workflow monitoring...")

    workflow_id = "legal_case_workflow_123"
    await workflow_monitor.start_workflow_monitoring(workflow_id, "case_processing")

    print(f"   ✅ Started monitoring workflow: {workflow_id}")

    # Симулируем выполнение шагов workflow
    steps = [
        "document_validation",
        "legal_analysis",
        "compliance_check",
        "approval_process",
        "finalization"
    ]

    for i, step in enumerate(steps, 1):
        await asyncio.sleep(0.1)  # Симуляция времени выполнения

        await workflow_monitor.update_workflow_progress(workflow_id, i, len(steps))
        print(f"   🔄 Step {i}/{len(steps)}: {step} completed")

    # Завершаем workflow
    await workflow_monitor.finish_workflow_monitoring(workflow_id, "success")
    print("   ✅ Workflow completed successfully")

    # Получаем статус активных workflow
    print("\n📊 Active workflows status:")
    status = await workflow_monitor.get_active_workflows_status()

    print(f"   🔄 Active workflows: {status['active_workflows']}")
    print(f"   ⏰ Long running: {status['long_running_workflows']}")
    print(f"   ⏱️ Average duration: {status['average_duration_seconds']:.2f}s")

    print()


async def demo_comprehensive_monitoring():
    """Комплексная демонстрация всей системы мониторинга."""
    print("🌟 === Comprehensive Monitoring Demo ===\n")

    observability = await create_observability_system()
    integration = await create_monitoring_integration(observability)

    print("🔧 Setting up comprehensive monitoring...")

    # Симулируем реальную активность системы
    print("\n🎭 Simulating real system activity...")

    # Параллельно выполняем различные операции
    tasks = []

    # Задача 1: Генерация метрик
    async def generate_metrics():
        for _ in range(20):
            await observability.record_metric(
                "cpu_usage", random.uniform(20, 90),
                {"server": f"server_{random.randint(1,3)}"}, "system"
            )
            await asyncio.sleep(0.05)

    # Задача 2: Создание трейсов
    async def generate_traces():
        for i in range(10):
            trace = await observability.start_trace(f"api_call_{i}", "api_gateway")
            await asyncio.sleep(random.uniform(0.01, 0.05))
            await observability.finish_trace(trace.span_id, "success")

    # Задача 3: Health checks
    async def health_checks():
        components = ["database", "cache", "api", "worker"]
        for component in components:
            await observability.check_health(component, ComponentType.SERVICE)
            await asyncio.sleep(0.02)

    # Запускаем все задачи параллельно
    tasks = [
        generate_metrics(),
        generate_traces(),
        health_checks()
    ]

    await asyncio.gather(*tasks)
    print("   ✅ Generated comprehensive system activity")

    # Получаем полную аналитику
    print("\n📊 Comprehensive system analytics:")

    # Dashboard данные
    dashboard = await observability.get_dashboard_data()

    print(f"   🎯 System Health: {dashboard['system_health']['overall_status'].upper()}")
    print(f"   📊 Health Percentage: {dashboard['system_health']['health_percentage']:.1f}%")
    print(f"   📈 Total Metrics: {dashboard['metrics_summary']['total_metrics']}")
    print(f"   🔍 Total Traces: {dashboard['tracing_summary']['total_traces']}")

    # Получаем агрегированные метрики
    aggregates = await observability.metrics_collector.get_aggregates()
    print("\n📊 Top performing components:")

    # Сортируем по количеству метрик
    sorted_components = sorted(
        [(k, v) for k, v in aggregates.items()],
        key=lambda x: x[1]['count'],
        reverse=True
    )[:5]

    for component, metrics in sorted_components:
        print(f"   📈 {component}: {metrics['count']} metrics, avg: {metrics['avg']:.2f}")

    print()


async def main():
    """Главная функция демонстрации."""
    print("📊 MEGA AGENT PRO - Monitoring & Observability System Demo")
    print("=" * 75)
    print()

    try:
        # Демонстрируем различные аспекты системы мониторинга
        await demo_basic_monitoring()
        await demo_distributed_tracing()
        await demo_health_monitoring()
        await demo_alerting_system()
        await demo_agent_monitoring()
        await demo_performance_analytics()
        await demo_dashboard_data()
        await demo_workflow_monitoring()
        await demo_comprehensive_monitoring()

        print("✅ === Monitoring & Observability Demo Complete ===")
        print()
        print("🎯 Key Features Demonstrated:")
        print("   ✅ Real-time metrics collection and aggregation")
        print("   ✅ Distributed tracing for multi-service workflows")
        print("   ✅ Component health monitoring and checks")
        print("   ✅ Intelligent alerting with threshold rules")
        print("   ✅ Agent integration with automatic instrumentation")
        print("   ✅ Performance analytics and anomaly detection")
        print("   ✅ Dashboard data generation for visualization")
        print("   ✅ Workflow monitoring with progress tracking")
        print("   ✅ Comprehensive system observability")
        print()
        print("🚀 Observability Benefits:")
        print("   📈 Complete visibility into system performance")
        print("   🔍 End-to-end tracing for complex workflows")
        print("   🚨 Proactive alerting for issue prevention")
        print("   📊 Rich analytics for capacity planning")
        print("   🏥 Automated health monitoring")
        print("   🎯 Agent-level performance insights")
        print()
        print("🔧 Next Steps:")
        print("   1. Deploy with real-time dashboard (Grafana/Kibana)")
        print("   2. Integrate with external alerting (PagerDuty/Slack)")
        print("   3. Add machine learning for anomaly detection")
        print("   4. Implement log aggregation (ELK stack)")
        print("   5. Create custom business metrics")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())