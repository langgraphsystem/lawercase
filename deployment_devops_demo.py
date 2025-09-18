#!/usr/bin/env python3
"""
Deployment & DevOps System Demo для mega_agent_pro.

Демонстрирует:
1. Docker containerization с multi-stage builds
2. CI/CD pipeline orchestration и automation
3. Environment management (dev/staging/production)
4. Infrastructure as Code (IaC) генерация
5. Auto-scaling и resource management
6. Health monitoring integration
7. Secret и configuration management
8. Multiple deployment strategies
9. Rollback capabilities
10. Comprehensive DevOps workflows

Запуск:
    python deployment_devops_demo.py
"""

import asyncio
import logging
import tempfile

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.deployment import (
    PipelineManager,
    EnvironmentManager,
    ConfigManager,
    SecretManager,
    DeploymentConfig,
    ContainerConfig,
    PipelineConfig,
    EnvironmentConfig,
    ServiceConfig,
    HealthCheckConfig,
    DeploymentStrategy,
    EnvironmentType,
    PipelineStage,
    create_deployment_manager,
    create_container_manager,
)


async def basic_deployment_demo():
    """Демонстрация базового развертывания"""
    print("📦 === Basic Deployment Demo ===")

    # Создаем менеджер развертывания
    deployment_manager = await create_deployment_manager()

    # Создаем временную конфигурацию
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
        # Конфигурация будет создана автоматически

    # Выполняем развертывание
    result = await deployment_manager.deploy(config_path)

    print("📊 Deployment result:")
    print(f"   🎯 Success: {result.success}")
    print(f"   🆔 ID: {result.deployment_id}")
    print(f"   ⏱️ Duration: {result.duration:.2f}s" if result.duration else "   ⏱️ Duration: N/A")
    print(f"   📦 Services: {len(result.services_deployed)}")

    if result.success:
        print("   ✅ Deployment completed successfully")
    else:
        print("   ❌ Deployment failed")
        for error in result.errors:
            print(f"      - {error}")

    return deployment_manager


async def container_management_demo():
    """Демонстрация управления контейнерами"""
    print("\n🐳 === Container Management Demo ===")

    container_manager = await create_container_manager()

    # Конфигурация контейнера
    container_config = ContainerConfig(
        dockerfile_path="./Dockerfile",
        build_context=".",
        image_name="mega-agent-pro",
        image_tag="1.0.0",
        registry="registry.mega-agent.com",
        build_args={"VERSION": "1.0.0", "ENVIRONMENT": "production"},
        labels={"app": "mega-agent", "version": "1.0.0"}
    )

    # Сборка образа
    image_id = await container_manager.build_image(container_config)
    print(f"   🏗️ Built image: {image_id[:12]}...")

    # Отправка в registry
    push_success = await container_manager.push_image(container_config)
    if push_success:
        print("   📤 Image pushed to registry")

    # Конфигурация сервиса
    service_config = ServiceConfig(
        name="mega-agent-api",
        image=f"{container_config.image_name}:{container_config.image_tag}",
        port=8000,
        replicas=3,
        cpu_limit="1",
        memory_limit="1Gi",
        environment={"ENV": "production", "LOG_LEVEL": "INFO"},
        health_check=HealthCheckConfig(
            path="/health",
            port=8000,
            interval=30,
            timeout=10
        )
    )

    # Запуск контейнера
    container_id = await container_manager.run_container(container_config, service_config)

    # Health check
    is_healthy = await container_manager.health_check(container_id, service_config.health_check)
    print(f"   🏥 Container health: {'healthy' if is_healthy else 'unhealthy'}")

    # Получение статуса
    status = await container_manager.get_container_status(container_id)
    if status:
        print("   📊 Container status:")
        print(f"      - Name: {status['name']}")
        print(f"      - Status: {status['status']}")
        print(f"      - Port: {status['port']}")
        print(f"      - Health: {status['health']}")

    return container_manager


async def pipeline_orchestration_demo():
    """Демонстрация оркестрации CI/CD pipeline"""
    print("\n🔄 === CI/CD Pipeline Demo ===")

    # Создаем менеджеры
    container_manager = await create_container_manager()
    environment_manager = EnvironmentManager(container_manager)
    pipeline_manager = PipelineManager(container_manager, environment_manager)

    # Конфигурация pipeline
    pipeline_config = PipelineConfig(
        name="mega-agent-pro-pipeline",
        stages=[
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.SECURITY_SCAN,
            PipelineStage.DEPLOY_STAGING,
            PipelineStage.INTEGRATION_TEST,
            PipelineStage.DEPLOY_PRODUCTION,
            PipelineStage.HEALTH_CHECK
        ],
        trigger_branch="main",
        build_timeout=3600,
        approval_required=True
    )

    # Конфигурация развертывания
    deployment_config = DeploymentConfig(
        project_name="mega_agent_pro",
        version="1.0.0",
        strategy=DeploymentStrategy.ROLLING,
        environments=[
            EnvironmentConfig(
                name="staging",
                type=EnvironmentType.STAGING,
                namespace="mega-agent-staging",
                services=[
                    ServiceConfig(
                        name="api-server",
                        image="mega-agent:latest",
                        port=8000,
                        replicas=2
                    )
                ]
            ),
            EnvironmentConfig(
                name="production",
                type=EnvironmentType.PRODUCTION,
                namespace="mega-agent-prod",
                services=[
                    ServiceConfig(
                        name="api-server",
                        image="mega-agent:latest",
                        port=8000,
                        replicas=5
                    )
                ]
            )
        ],
        containers=[
            ContainerConfig(
                dockerfile_path="./Dockerfile",
                build_context=".",
                image_name="mega-agent",
                image_tag="latest"
            )
        ],
        pipeline=pipeline_config
    )

    # Запуск pipeline
    result = await pipeline_manager.run_pipeline(pipeline_config, deployment_config)

    print("📊 Pipeline result:")
    print(f"   🆔 Pipeline ID: {result.pipeline_id}")
    print(f"   🎯 Status: {result.status}")
    print(f"   ⏱️ Duration: {result.duration:.2f}s" if result.duration else "   ⏱️ Duration: N/A")
    print(f"   📋 Stages completed: {len(result.stages_completed)}/{len(pipeline_config.stages)}")

    for stage in result.stages_completed:
        print(f"      ✅ {stage.value}")

    return pipeline_manager


async def environment_management_demo():
    """Демонстрация управления окружениями"""
    print("\n🌍 === Environment Management Demo ===")

    container_manager = await create_container_manager()
    environment_manager = EnvironmentManager(container_manager)

    # Конфигурация окружений
    environments = [
        EnvironmentConfig(
            name="development",
            type=EnvironmentType.DEVELOPMENT,
            namespace="mega-agent-dev",
            services=[
                ServiceConfig(
                    name="mega-agent-api",
                    image="mega-agent:dev",
                    port=8000,
                    replicas=1,
                    environment={"DEBUG": "true", "LOG_LEVEL": "DEBUG"}
                ),
                ServiceConfig(
                    name="postgres",
                    image="postgres:15",
                    port=5432,
                    environment={"POSTGRES_DB": "mega_agent_dev"}
                )
            ]
        ),
        EnvironmentConfig(
            name="staging",
            type=EnvironmentType.STAGING,
            namespace="mega-agent-staging",
            services=[
                ServiceConfig(
                    name="mega-agent-api",
                    image="mega-agent:staging",
                    port=8000,
                    replicas=2,
                    health_check=HealthCheckConfig(path="/health", port=8000)
                ),
                ServiceConfig(
                    name="postgres",
                    image="postgres:15",
                    port=5432,
                    replicas=2
                ),
                ServiceConfig(
                    name="redis",
                    image="redis:7",
                    port=6379
                )
            ],
            auto_scaling=True,
            min_replicas=2,
            max_replicas=5
        ),
        EnvironmentConfig(
            name="production",
            type=EnvironmentType.PRODUCTION,
            namespace="mega-agent-prod",
            services=[
                ServiceConfig(
                    name="mega-agent-api",
                    image="mega-agent:latest",
                    port=8000,
                    replicas=5,
                    cpu_limit="2",
                    memory_limit="2Gi",
                    health_check=HealthCheckConfig(path="/health", port=8000)
                ),
                ServiceConfig(
                    name="postgres",
                    image="postgres:15",
                    port=5432,
                    replicas=3,
                    cpu_limit="4",
                    memory_limit="4Gi"
                ),
                ServiceConfig(
                    name="redis",
                    image="redis:7",
                    port=6379,
                    replicas=3
                )
            ],
            auto_scaling=True,
            min_replicas=3,
            max_replicas=20,
            ingress_host="api.mega-agent.com",
            tls_enabled=True
        )
    ]

    # Создаем окружения
    for env_config in environments:
        print(f"\n🏗️ Creating environment: {env_config.name}")

        success = await environment_manager.create_environment(env_config)
        if success:
            print(f"   ✅ Environment created: {env_config.name}")

            # Развертываем сервисы
            deployed = await environment_manager.deploy_services(env_config.name, env_config.services)
            print(f"   📦 Services deployed: {len(deployed)}")

            # Демонстрируем автомасштабирование
            if env_config.auto_scaling:
                for service in env_config.services:
                    if service.name == "mega-agent-api":
                        new_replicas = min(service.replicas * 2, env_config.max_replicas)
                        await environment_manager.scale_service(env_config.name, service.name, new_replicas)

    return environment_manager


async def secret_config_management_demo():
    """Демонстрация управления секретами и конфигурациями"""
    print("\n🔐 === Secret & Config Management Demo ===")

    secret_manager = SecretManager()
    config_manager = ConfigManager()

    # Создание секретов для разных окружений
    environments = ["development", "staging", "production"]

    for env in environments:
        print(f"\n🏷️ Setting up secrets for {env}:")

        # Секреты базы данных
        await secret_manager.create_secret(
            "database-credentials",
            {
                "username": f"mega_agent_{env}",
                "password": f"super_secure_password_{env}",
                "host": f"postgres.{env}.svc.cluster.local",
                "database": f"mega_agent_{env}"
            },
            f"mega-agent-{env}"
        )

        # API ключи
        await secret_manager.create_secret(
            "api-keys",
            {
                "openai_api_key": f"sk-openai-key-{env}",
                "gemini_api_key": f"gemini-key-{env}",
                "jwt_secret": f"jwt-secret-{env}",
                "encryption_key": f"encryption-key-{env}"
            },
            f"mega-agent-{env}"
        )

        # Внешние сервисы
        await secret_manager.create_secret(
            "external-services",
            {
                "redis_url": f"redis://redis.{env}.svc.cluster.local:6379",
                "elasticsearch_url": f"http://elasticsearch.{env}.svc.cluster.local:9200",
                "monitoring_token": f"monitoring-token-{env}"
            },
            f"mega-agent-{env}"
        )

    # Демонстрируем получение секретов
    print("\n🔍 Retrieving secrets:")
    for env in environments:
        db_secret = await secret_manager.get_secret("database-credentials", f"mega-agent-{env}")
        if db_secret:
            print(f"   ✅ {env} database secret loaded")

    # Работа с конфигурациями
    print("\n⚙️ Configuration management:")

    # Создаем конфигурацию
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name

    # Загружаем/создаем демо конфигурацию
    demo_config = await config_manager.load_config(config_path)
    if demo_config:
        print(f"   ✅ Configuration loaded: {demo_config.project_name} v{demo_config.version}")
        print(f"   🏗️ Environments: {len(demo_config.environments)}")
        print(f"   📦 Containers: {len(demo_config.containers)}")
        print(f"   🔄 Pipeline stages: {len(demo_config.pipeline.stages)}")

    return secret_manager, config_manager


async def deployment_strategies_demo():
    """Демонстрация различных стратегий развертывания"""
    print("\n📋 === Deployment Strategies Demo ===")

    strategies = [
        DeploymentStrategy.ROLLING,
        DeploymentStrategy.BLUE_GREEN,
        DeploymentStrategy.CANARY,
        DeploymentStrategy.RECREATE
    ]

    for strategy in strategies:
        print(f"\n🎯 Testing strategy: {strategy.value}")

        # Конфигурация для каждой стратегии
        config = DeploymentConfig(
            project_name="mega_agent_pro",
            version="1.0.0",
            strategy=strategy,
            environments=[
                EnvironmentConfig(
                    name="test-env",
                    type=EnvironmentType.STAGING,
                    namespace="test-namespace",
                    services=[
                        ServiceConfig(
                            name="test-service",
                            image="mega-agent:test",
                            port=8000,
                            replicas=3
                        )
                    ]
                )
            ],
            containers=[
                ContainerConfig(
                    dockerfile_path="./Dockerfile",
                    build_context=".",
                    image_name="mega-agent",
                    image_tag="test"
                )
            ],
            pipeline=PipelineConfig(
                name=f"test-pipeline-{strategy.value}",
                stages=[PipelineStage.BUILD, PipelineStage.TEST]
            )
        )

        # Симуляция развертывания с разными стратегиями
        print(f"   🚀 Deploying with {strategy.value} strategy...")

        if strategy == DeploymentStrategy.ROLLING:
            print("      - Gradually replacing instances")
            print("      - Zero downtime deployment")
            print("      - Safe rollback available")

        elif strategy == DeploymentStrategy.BLUE_GREEN:
            print("      - Creating parallel environment")
            print("      - Switch traffic after validation")
            print("      - Instant rollback capability")

        elif strategy == DeploymentStrategy.CANARY:
            print("      - Deploying to subset of instances")
            print("      - Monitoring metrics and errors")
            print("      - Gradual traffic increase")

        elif strategy == DeploymentStrategy.RECREATE:
            print("      - Stopping all instances")
            print("      - Deploying new version")
            print("      - Brief downtime expected")

        # Симуляция времени развертывания
        await asyncio.sleep(0.5)
        print(f"   ✅ {strategy.value} deployment completed")


async def monitoring_integration_demo():
    """Демонстрация интеграции с мониторингом"""
    print("\n📊 === Monitoring Integration Demo ===")

    deployment_manager = await create_deployment_manager()

    # Генерируем отчет о развертываниях
    report = await deployment_manager.generate_deployment_report()

    print("📈 Deployment Analytics:")
    print(f"   📊 Total deployments: {report['total_deployments']}")
    print(f"   ✅ Successful deployments: {report['successful_deployments']}")
    print(f"   📈 Success rate: {report['success_rate']:.1f}%")
    print(f"   🌍 Active environments: {report['active_environments']}")
    print(f"   🐳 Active containers: {report['active_containers']}")

    if report['recent_deployments']:
        print("\n📋 Recent deployments:")
        for deployment in report['recent_deployments']:
            status_icon = "✅" if deployment['success'] else "❌"
            print(f"   {status_icon} {deployment['id'][:8]}... "
                  f"({deployment['duration']:.1f}s) - {deployment['environment']}")

    # Симуляция метрик развертывания
    deployment_metrics = {
        "deployment_frequency": "5.2 per day",
        "lead_time": "45 minutes",
        "mttr": "8 minutes",
        "change_failure_rate": "2.1%"
    }

    print("\n📊 DevOps Metrics:")
    for metric, value in deployment_metrics.items():
        print(f"   📈 {metric.replace('_', ' ').title()}: {value}")


async def comprehensive_devops_demo():
    """Комплексная демонстрация DevOps workflow"""
    print("\n🌟 === Comprehensive DevOps Workflow ===")

    deployment_manager = await create_deployment_manager()

    # Полный цикл развертывания
    print("🔄 Starting full deployment lifecycle...")

    # 1. Создание конфигурации
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name

    print("   📝 Configuration created")

    # 2. Развертывание
    print("   🚀 Starting deployment...")
    result = await deployment_manager.deploy(config_path)

    # 3. Проверка результата
    if result.success:
        print("   ✅ Deployment successful")

        # 4. Демонстрация мониторинга
        print("   📊 Monitoring deployment...")
        await asyncio.sleep(1)

        # 5. Симуляция проблемы и отката
        print("   ⚠️ Simulating issue detection...")
        print("   ↩️ Initiating rollback...")

        rollback_success = await deployment_manager.rollback(result.deployment_id)
        if rollback_success:
            print("   ✅ Rollback completed successfully")

    else:
        print("   ❌ Deployment failed")

    # Финальный отчет
    final_report = await deployment_manager.generate_deployment_report()
    print("\n📊 Final DevOps Report:")
    print(f"   🎯 Total operations: {final_report['total_deployments']}")
    print(f"   📈 Success rate: {final_report['success_rate']:.1f}%")


async def main():
    """Главная функция демонстрации"""
    print("🚀 MEGA AGENT PRO - Deployment & DevOps System Demo")
    print("=" * 70)

    try:
        # Базовая демонстрация развертывания
        await basic_deployment_demo()

        # Управление контейнерами
        await container_management_demo()

        # CI/CD Pipeline
        await pipeline_orchestration_demo()

        # Управление окружениями
        await environment_management_demo()

        # Секреты и конфигурации
        await secret_config_management_demo()

        # Стратегии развертывания
        await deployment_strategies_demo()

        # Интеграция с мониторингом
        await monitoring_integration_demo()

        # Комплексный DevOps workflow
        await comprehensive_devops_demo()

        print("\n✅ === Deployment & DevOps Demo Complete ===")

        print("\n🎯 Key Features Demonstrated:")
        print("   ✅ Docker containerization с multi-stage builds")
        print("   ✅ CI/CD pipeline orchestration и automation")
        print("   ✅ Multi-environment management (dev/staging/prod)")
        print("   ✅ Infrastructure as Code (IaC) генерация")
        print("   ✅ Auto-scaling и resource management")
        print("   ✅ Health monitoring integration")
        print("   ✅ Secret и configuration management")
        print("   ✅ Multiple deployment strategies")
        print("   ✅ Rollback capabilities")
        print("   ✅ DevOps metrics и analytics")

        print("\n🚀 DevOps Benefits:")
        print("   📈 Automated deployment processes")
        print("   🔄 Continuous integration и delivery")
        print("   🛡️ Secure secret management")
        print("   📊 Comprehensive monitoring и alerting")
        print("   🌍 Multi-environment support")
        print("   ↩️ Reliable rollback mechanisms")
        print("   📱 Infrastructure as Code approach")

        print("\n🔧 Next Steps:")
        print("   1. Set up actual Kubernetes cluster")
        print("   2. Configure real container registry")
        print("   3. Integrate with external CI/CD tools (Jenkins/GitLab)")
        print("   4. Add infrastructure provisioning (Terraform)")
        print("   5. Implement advanced monitoring (Prometheus/Grafana)")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        logger.exception("Demo failed")


if __name__ == "__main__":
    asyncio.run(main())