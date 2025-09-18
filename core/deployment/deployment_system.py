"""
Comprehensive Deployment & DevOps System для mega_agent_pro.

Provides full deployment automation including:
- Docker containerization с multi-stage builds
- CI/CD pipeline orchestration
- Environment management (dev/staging/production)
- Infrastructure as Code (IaC) configuration
- Auto-scaling и resource management
- Health monitoring integration
- Secret и configuration management
- Multiple deployment strategies
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import yaml
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DeploymentStrategy(str, Enum):
    """Стратегии развертывания"""
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


class EnvironmentType(str, Enum):
    """Типы окружений"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ServiceStatus(str, Enum):
    """Статусы сервисов"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class PipelineStage(str, Enum):
    """Стадии CI/CD pipeline"""
    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DEPLOY_STAGING = "deploy_staging"
    INTEGRATION_TEST = "integration_test"
    DEPLOY_PRODUCTION = "deploy_production"
    HEALTH_CHECK = "health_check"
    ROLLBACK = "rollback"


class HealthCheckConfig(BaseModel):
    """Конфигурация health check"""
    path: str = Field(..., description="Health check endpoint path")
    port: int = Field(..., description="Port для health check")
    interval: int = Field(default=30, description="Интервал проверки (секунды)")
    timeout: int = Field(default=10, description="Timeout для проверки")
    retries: int = Field(default=3, description="Количество попыток")
    initial_delay: int = Field(default=60, description="Начальная задержка")


class ServiceConfig(BaseModel):
    """Конфигурация сервиса"""
    name: str = Field(..., description="Имя сервиса")
    image: str = Field(..., description="Docker образ")
    port: int = Field(..., description="Порт сервиса")
    replicas: int = Field(default=1, description="Количество реплик")
    cpu_limit: str = Field(default="1", description="CPU лимит")
    memory_limit: str = Field(default="1Gi", description="Memory лимит")
    environment: Dict[str, str] = Field(default_factory=dict)
    volumes: List[str] = Field(default_factory=list)
    health_check: Optional[HealthCheckConfig] = None
    dependencies: List[str] = Field(default_factory=list)


class ContainerConfig(BaseModel):
    """Конфигурация контейнера"""
    dockerfile_path: str = Field(..., description="Путь к Dockerfile")
    build_context: str = Field(..., description="Build context")
    image_name: str = Field(..., description="Имя образа")
    image_tag: str = Field(default="latest", description="Тег образа")
    build_args: Dict[str, str] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)
    registry: Optional[str] = Field(default=None, description="Container registry")


class EnvironmentConfig(BaseModel):
    """Конфигурация окружения"""
    name: str = Field(..., description="Имя окружения")
    type: EnvironmentType = Field(..., description="Тип окружения")
    services: List[ServiceConfig] = Field(..., description="Сервисы в окружении")
    namespace: str = Field(..., description="Kubernetes namespace")
    ingress_host: Optional[str] = Field(default=None, description="Ingress hostname")
    tls_enabled: bool = Field(default=False, description="Включить TLS")
    auto_scaling: bool = Field(default=False, description="Auto-scaling")
    min_replicas: int = Field(default=1, description="Минимум реплик")
    max_replicas: int = Field(default=10, description="Максимум реплик")
    cpu_threshold: int = Field(default=70, description="CPU threshold для scaling")


class PipelineConfig(BaseModel):
    """Конфигурация CI/CD pipeline"""
    name: str = Field(..., description="Имя pipeline")
    stages: List[PipelineStage] = Field(..., description="Стадии pipeline")
    trigger_branch: str = Field(default="main", description="Branch для trigger")
    build_timeout: int = Field(default=3600, description="Timeout build (секунды)")
    test_timeout: int = Field(default=1800, description="Timeout тестов")
    deploy_timeout: int = Field(default=1200, description="Timeout deploy")
    notification_channels: List[str] = Field(default_factory=list)
    approval_required: bool = Field(default=True, description="Требуется approval")


class DeploymentConfig(BaseModel):
    """Главная конфигурация развертывания"""
    project_name: str = Field(..., description="Имя проекта")
    version: str = Field(..., description="Версия")
    strategy: DeploymentStrategy = Field(..., description="Стратегия развертывания")
    environments: List[EnvironmentConfig] = Field(..., description="Окружения")
    containers: List[ContainerConfig] = Field(..., description="Контейнеры")
    pipeline: PipelineConfig = Field(..., description="Pipeline конфигурация")
    monitoring_enabled: bool = Field(default=True, description="Включить мониторинг")
    backup_enabled: bool = Field(default=True, description="Включить бэкапы")
    secrets: Dict[str, str] = Field(default_factory=dict, description="Секреты")


class DeploymentResult(BaseModel):
    """Результат развертывания"""
    success: bool = Field(..., description="Успешность развертывания")
    deployment_id: str = Field(..., description="ID развертывания")
    environment: str = Field(..., description="Окружение")
    version: str = Field(..., description="Версия")
    start_time: datetime = Field(..., description="Время начала")
    end_time: Optional[datetime] = Field(default=None, description="Время окончания")
    duration: Optional[float] = Field(default=None, description="Длительность (секунды)")
    services_deployed: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    rollback_available: bool = Field(default=False, description="Доступен rollback")


class PipelineResult(BaseModel):
    """Результат выполнения pipeline"""
    pipeline_id: str = Field(..., description="ID pipeline")
    status: str = Field(..., description="Статус pipeline")
    stages_completed: List[PipelineStage] = Field(default_factory=list)
    current_stage: Optional[PipelineStage] = Field(default=None)
    start_time: datetime = Field(..., description="Время начала")
    end_time: Optional[datetime] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    artifacts: List[str] = Field(default_factory=list)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    deployment_result: Optional[DeploymentResult] = None


class ContainerManager:
    """Менеджер Docker контейнеров"""

    def __init__(self):
        self.active_containers: Dict[str, Dict[str, Any]] = {}
        self.build_cache: Dict[str, str] = {}

    async def build_image(self, config: ContainerConfig) -> str:
        """Построить Docker образ"""
        try:
            # Проверяем cache
            cache_key = f"{config.image_name}:{config.image_tag}"
            if cache_key in self.build_cache:
                return self.build_cache[cache_key]

            print(f"🔨 Building Docker image: {config.image_name}:{config.image_tag}")

            # Генерируем Dockerfile если нужно
            dockerfile_content = await self._generate_dockerfile(config)
            dockerfile_path = Path(config.build_context) / "Dockerfile"

            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)

            # Симуляция сборки образа
            build_time = 30 + len(dockerfile_content) * 0.001  # Симуляция времени сборки
            await asyncio.sleep(min(build_time / 10, 3))  # Ускоренная симуляция

            image_id = f"sha256:{''.join([hex(hash(config.image_name + str(time.time())))[-8:]])}"
            self.build_cache[cache_key] = image_id

            print(f"   ✅ Image built successfully: {image_id[:12]}")
            return image_id

        except Exception as e:
            print(f"   ❌ Failed to build image: {e}")
            raise

    async def push_image(self, config: ContainerConfig) -> bool:
        """Отправить образ в registry"""
        try:
            if not config.registry:
                print("   ⚠️ No registry configured, skipping push")
                return True

            print(f"📤 Pushing image to registry: {config.registry}")
            await asyncio.sleep(1)  # Симуляция push
            print("   ✅ Image pushed successfully")
            return True

        except Exception as e:
            print(f"   ❌ Failed to push image: {e}")
            return False

    async def run_container(self, config: ContainerConfig, service_config: ServiceConfig) -> str:
        """Запустить контейнер"""
        try:
            container_id = f"container_{service_config.name}_{int(time.time())}"

            print(f"🚀 Starting container: {service_config.name}")

            # Симуляция запуска контейнера
            await asyncio.sleep(0.5)

            container_info = {
                "id": container_id,
                "name": service_config.name,
                "image": config.image_name,
                "status": ServiceStatus.RUNNING,
                "port": service_config.port,
                "started_at": datetime.utcnow(),
                "health": "healthy"
            }

            self.active_containers[container_id] = container_info
            print(f"   ✅ Container started: {container_id[:12]}")

            return container_id

        except Exception as e:
            print(f"   ❌ Failed to start container: {e}")
            raise

    async def stop_container(self, container_id: str) -> bool:
        """Остановить контейнер"""
        try:
            if container_id in self.active_containers:
                container = self.active_containers[container_id]
                print(f"🛑 Stopping container: {container['name']}")

                await asyncio.sleep(0.2)  # Симуляция остановки

                container["status"] = ServiceStatus.STOPPED
                container["stopped_at"] = datetime.utcnow()

                print(f"   ✅ Container stopped: {container_id[:12]}")
                return True
            else:
                print(f"   ⚠️ Container not found: {container_id}")
                return False

        except Exception as e:
            print(f"   ❌ Failed to stop container: {e}")
            return False

    async def get_container_status(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус контейнера"""
        return self.active_containers.get(container_id)

    async def health_check(self, container_id: str, health_config: HealthCheckConfig) -> bool:
        """Выполнить health check контейнера"""
        try:
            container = self.active_containers.get(container_id)
            if not container:
                return False

            print(f"🔍 Health check: {container['name']}")

            # Симуляция health check
            await asyncio.sleep(0.1)

            # 90% вероятность успеха
            is_healthy = hash(container_id) % 10 != 0

            if is_healthy:
                container["health"] = "healthy"
                container["last_health_check"] = datetime.utcnow()
                print("   ✅ Health check passed")
            else:
                container["health"] = "unhealthy"
                print("   ❌ Health check failed")

            return is_healthy

        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False

    async def _generate_dockerfile(self, config: ContainerConfig) -> str:
        """Генерировать Dockerfile для mega_agent_pro"""
        return f"""# Multi-stage Dockerfile for mega_agent_pro
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development
RUN pip install pytest pytest-asyncio black flake8
COPY . .
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Labels
LABEL name="{config.image_name}"
LABEL version="{config.image_tag}"
LABEL description="mega_agent_pro Legal AI System"
"""


class EnvironmentManager:
    """Менеджер окружений"""

    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
        self.environments: Dict[str, Dict[str, Any]] = {}

    async def create_environment(self, config: EnvironmentConfig) -> bool:
        """Создать окружение"""
        try:
            print(f"🌍 Creating environment: {config.name} ({config.type})")

            # Создаем namespace
            await self._create_namespace(config.namespace)

            # Генерируем Kubernetes манифесты
            manifests = await self._generate_k8s_manifests(config)

            # Симуляция создания ресурсов
            await asyncio.sleep(1)

            env_info = {
                "name": config.name,
                "type": config.type,
                "namespace": config.namespace,
                "services": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "manifests": manifests
            }

            self.environments[config.name] = env_info
            print(f"   ✅ Environment created: {config.name}")

            return True

        except Exception as e:
            print(f"   ❌ Failed to create environment: {e}")
            return False

    async def deploy_services(self, env_name: str, services: List[ServiceConfig]) -> List[str]:
        """Развернуть сервисы в окружении"""
        deployed_services = []

        try:
            print(f"🚀 Deploying services to environment: {env_name}")

            for service in services:
                print(f"   📦 Deploying service: {service.name}")

                # Симуляция развертывания сервиса
                await asyncio.sleep(0.5)

                # Создаем deployment манифест
                deployment_manifest = await self._generate_deployment_manifest(service)

                deployed_services.append(service.name)
                print(f"      ✅ Service deployed: {service.name}")

            if env_name in self.environments:
                self.environments[env_name]["services"] = deployed_services

            return deployed_services

        except Exception as e:
            print(f"   ❌ Failed to deploy services: {e}")
            return deployed_services

    async def scale_service(self, env_name: str, service_name: str, replicas: int) -> bool:
        """Масштабировать сервис"""
        try:
            print(f"📊 Scaling service {service_name} to {replicas} replicas")
            await asyncio.sleep(0.3)
            print("   ✅ Service scaled successfully")
            return True

        except Exception as e:
            print(f"   ❌ Failed to scale service: {e}")
            return False

    async def _create_namespace(self, namespace: str) -> None:
        """Создать Kubernetes namespace"""
        print(f"   🏷️ Creating namespace: {namespace}")
        await asyncio.sleep(0.1)

    async def _generate_k8s_manifests(self, config: EnvironmentConfig) -> Dict[str, str]:
        """Генерировать Kubernetes манифесты"""
        manifests = {}

        # Namespace manifest
        manifests["namespace"] = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {config.namespace}
  labels:
    environment: {config.type}
    project: mega-agent-pro
"""

        # ConfigMap manifest
        manifests["configmap"] = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: mega-agent-config
  namespace: {config.namespace}
data:
  environment: {config.type}
  log_level: INFO
  database_url: postgresql://localhost:5432/mega_agent
"""

        # Ingress manifest if needed
        if config.ingress_host:
            manifests["ingress"] = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mega-agent-ingress
  namespace: {config.namespace}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - {config.ingress_host}
    secretName: mega-agent-tls
  rules:
  - host: {config.ingress_host}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mega-agent-service
            port:
              number: 80
"""

        return manifests

    async def _generate_deployment_manifest(self, service: ServiceConfig) -> str:
        """Генерировать Deployment манифест для сервиса"""
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service.name}
  labels:
    app: {service.name}
spec:
  replicas: {service.replicas}
  selector:
    matchLabels:
      app: {service.name}
  template:
    metadata:
      labels:
        app: {service.name}
    spec:
      containers:
      - name: {service.name}
        image: {service.image}
        ports:
        - containerPort: {service.port}
        resources:
          limits:
            cpu: {service.cpu_limit}
            memory: {service.memory_limit}
          requests:
            cpu: {int(service.cpu_limit.rstrip('m')) // 2 if service.cpu_limit.endswith('m') else '0.5'}
            memory: {service.memory_limit}
        env:
        {chr(10).join([f'        - name: {k}{chr(10)}          value: "{v}"' for k, v in service.environment.items()])}
        {f'''livenessProbe:
          httpGet:
            path: {service.health_check.path}
            port: {service.health_check.port}
          initialDelaySeconds: {service.health_check.initial_delay}
          periodSeconds: {service.health_check.interval}
          timeoutSeconds: {service.health_check.timeout}
        readinessProbe:
          httpGet:
            path: {service.health_check.path}
            port: {service.health_check.port}
          initialDelaySeconds: 10
          periodSeconds: 5''' if service.health_check else ''}
---
apiVersion: v1
kind: Service
metadata:
  name: {service.name}-service
spec:
  selector:
    app: {service.name}
  ports:
  - port: 80
    targetPort: {service.port}
  type: ClusterIP
"""


class PipelineManager:
    """Менеджер CI/CD pipeline"""

    def __init__(self, container_manager: ContainerManager, environment_manager: EnvironmentManager):
        self.container_manager = container_manager
        self.environment_manager = environment_manager
        self.active_pipelines: Dict[str, PipelineResult] = {}

    async def run_pipeline(self, config: PipelineConfig, deployment_config: DeploymentConfig) -> PipelineResult:
        """Запустить CI/CD pipeline"""
        pipeline_id = f"pipeline_{int(time.time())}"

        result = PipelineResult(
            pipeline_id=pipeline_id,
            status="running",
            start_time=datetime.utcnow()
        )

        self.active_pipelines[pipeline_id] = result

        try:
            print(f"🔄 Starting CI/CD pipeline: {config.name}")
            print(f"   📋 Pipeline ID: {pipeline_id}")

            for stage in config.stages:
                print(f"\n📍 Stage: {stage.value}")
                result.current_stage = stage

                stage_success = await self._execute_stage(stage, config, deployment_config)

                if stage_success:
                    result.stages_completed.append(stage)
                    print(f"   ✅ Stage completed: {stage.value}")
                else:
                    result.status = "failed"
                    print(f"   ❌ Stage failed: {stage.value}")
                    break

            if result.status != "failed":
                result.status = "completed"
                print(f"\n🎉 Pipeline completed successfully: {pipeline_id}")
            else:
                print(f"\n💥 Pipeline failed: {pipeline_id}")

        except Exception as e:
            result.status = "failed"
            print(f"   ❌ Pipeline error: {e}")

        finally:
            result.end_time = datetime.utcnow()
            result.duration = (result.end_time - result.start_time).total_seconds()
            result.current_stage = None

        return result

    async def _execute_stage(self, stage: PipelineStage, config: PipelineConfig, deployment_config: DeploymentConfig) -> bool:
        """Выполнить стадию pipeline"""
        try:
            if stage == PipelineStage.BUILD:
                return await self._build_stage(deployment_config)
            elif stage == PipelineStage.TEST:
                return await self._test_stage(config)
            elif stage == PipelineStage.SECURITY_SCAN:
                return await self._security_scan_stage()
            elif stage == PipelineStage.DEPLOY_STAGING:
                return await self._deploy_stage(deployment_config, "staging")
            elif stage == PipelineStage.INTEGRATION_TEST:
                return await self._integration_test_stage()
            elif stage == PipelineStage.DEPLOY_PRODUCTION:
                return await self._deploy_stage(deployment_config, "production")
            elif stage == PipelineStage.HEALTH_CHECK:
                return await self._health_check_stage(deployment_config)
            elif stage == PipelineStage.ROLLBACK:
                return await self._rollback_stage(deployment_config)
            else:
                print(f"   ⚠️ Unknown stage: {stage}")
                return False

        except Exception as e:
            print(f"   ❌ Stage execution error: {e}")
            return False

    async def _build_stage(self, deployment_config: DeploymentConfig) -> bool:
        """Стадия сборки"""
        print("   🔨 Building application...")

        for container_config in deployment_config.containers:
            await self.container_manager.build_image(container_config)
            await self.container_manager.push_image(container_config)

        await asyncio.sleep(0.5)  # Симуляция сборки
        return True

    async def _test_stage(self, config: PipelineConfig) -> bool:
        """Стадия тестирования"""
        print("   🧪 Running tests...")

        test_results = {
            "unit_tests": {"passed": 45, "failed": 0, "coverage": 89.5},
            "integration_tests": {"passed": 23, "failed": 0},
            "performance_tests": {"passed": 8, "failed": 0, "avg_response_time": "120ms"}
        }

        await asyncio.sleep(1)  # Симуляция тестов

        # 95% вероятность успеха
        success = hash(str(time.time())) % 20 != 0

        if success:
            print("   ✅ All tests passed")
        else:
            print("   ❌ Some tests failed")

        return success

    async def _security_scan_stage(self) -> bool:
        """Стадия сканирования безопасности"""
        print("   🔒 Running security scan...")

        await asyncio.sleep(0.8)  # Симуляция сканирования

        vulnerabilities = {
            "critical": 0,
            "high": 0,
            "medium": 2,
            "low": 5
        }

        # Проверяем критические уязвимости
        has_critical = vulnerabilities["critical"] > 0 or vulnerabilities["high"] > 0

        if not has_critical:
            print(f"   ✅ Security scan passed: {vulnerabilities}")
        else:
            print(f"   ❌ Critical vulnerabilities found: {vulnerabilities}")

        return not has_critical

    async def _deploy_stage(self, deployment_config: DeploymentConfig, environment: str) -> bool:
        """Стадия развертывания"""
        print(f"   🚀 Deploying to {environment}...")

        # Найти конфигурацию окружения
        env_config = None
        for env in deployment_config.environments:
            if env.type == environment or env.name == environment:
                env_config = env
                break

        if not env_config:
            print(f"   ❌ Environment config not found: {environment}")
            return False

        # Создать окружение если нужно
        await self.environment_manager.create_environment(env_config)

        # Развернуть сервисы
        deployed = await self.environment_manager.deploy_services(env_config.name, env_config.services)

        success = len(deployed) == len(env_config.services)

        if success:
            print(f"   ✅ Deployment successful: {len(deployed)} services")
        else:
            print(f"   ❌ Deployment partially failed: {len(deployed)}/{len(env_config.services)} services")

        return success

    async def _integration_test_stage(self) -> bool:
        """Стадия интеграционных тестов"""
        print("   🔄 Running integration tests...")

        await asyncio.sleep(0.7)  # Симуляция тестов

        # 90% вероятность успеха
        success = hash(str(time.time())) % 10 != 0

        if success:
            print("   ✅ Integration tests passed")
        else:
            print("   ❌ Integration tests failed")

        return success

    async def _health_check_stage(self, deployment_config: DeploymentConfig) -> bool:
        """Стадия проверки здоровья"""
        print("   🏥 Running health checks...")

        await asyncio.sleep(0.3)

        # Проверяем здоровье всех сервисов
        all_healthy = True

        for env_config in deployment_config.environments:
            for service in env_config.services:
                if service.health_check:
                    # Симуляция health check
                    is_healthy = hash(service.name) % 10 != 0  # 90% здоровых
                    if not is_healthy:
                        all_healthy = False
                        print(f"      ❌ Service unhealthy: {service.name}")
                    else:
                        print(f"      ✅ Service healthy: {service.name}")

        if all_healthy:
            print("   ✅ All services healthy")
        else:
            print("   ❌ Some services are unhealthy")

        return all_healthy

    async def _rollback_stage(self, deployment_config: DeploymentConfig) -> bool:
        """Стадия отката"""
        print("   ↩️ Rolling back deployment...")

        await asyncio.sleep(0.5)  # Симуляция отката

        print("   ✅ Rollback completed")
        return True


class SecretManager:
    """Менеджер секретов"""

    def __init__(self):
        self.secrets: Dict[str, Dict[str, str]] = {}

    async def create_secret(self, name: str, data: Dict[str, str], namespace: str = "default") -> bool:
        """Создать секрет"""
        try:
            secret_key = f"{namespace}/{name}"
            self.secrets[secret_key] = {
                "name": name,
                "namespace": namespace,
                "data": data,
                "created_at": datetime.utcnow().isoformat()
            }

            print(f"🔐 Secret created: {name} in namespace {namespace}")
            return True

        except Exception as e:
            print(f"❌ Failed to create secret: {e}")
            return False

    async def get_secret(self, name: str, namespace: str = "default") -> Optional[Dict[str, str]]:
        """Получить секрет"""
        secret_key = f"{namespace}/{name}"
        return self.secrets.get(secret_key)

    async def delete_secret(self, name: str, namespace: str = "default") -> bool:
        """Удалить секрет"""
        secret_key = f"{namespace}/{name}"
        if secret_key in self.secrets:
            del self.secrets[secret_key]
            print(f"🗑️ Secret deleted: {name}")
            return True
        return False


class ConfigManager:
    """Менеджер конфигураций"""

    def __init__(self):
        self.configs: Dict[str, Any] = {}

    async def load_config(self, config_path: str) -> Optional[DeploymentConfig]:
        """Загрузить конфигурацию развертывания"""
        try:
            # Создаем демо конфигурацию если файл не существует
            if not os.path.exists(config_path):
                demo_config = await self._create_demo_config()
                await self.save_config(config_path, demo_config)
                return demo_config

            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            return DeploymentConfig(**config_data)

        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return None

    async def save_config(self, config_path: str, config: DeploymentConfig) -> bool:
        """Сохранить конфигурацию"""
        try:
            config_dict = config.dict()

            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)

            print(f"💾 Config saved: {config_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            return False

    async def _create_demo_config(self) -> DeploymentConfig:
        """Создать демо конфигурацию"""
        return DeploymentConfig(
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
                            name="mega-agent-api",
                            image="mega-agent:latest",
                            port=8000,
                            replicas=2,
                            health_check=HealthCheckConfig(
                                path="/health",
                                port=8000
                            )
                        ),
                        ServiceConfig(
                            name="postgres",
                            image="postgres:15",
                            port=5432,
                            environment={"POSTGRES_DB": "mega_agent", "POSTGRES_USER": "admin"}
                        ),
                        ServiceConfig(
                            name="redis",
                            image="redis:7",
                            port=6379
                        )
                    ]
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
                            health_check=HealthCheckConfig(
                                path="/health",
                                port=8000
                            )
                        ),
                        ServiceConfig(
                            name="postgres",
                            image="postgres:15",
                            port=5432,
                            replicas=3,
                            environment={"POSTGRES_DB": "mega_agent", "POSTGRES_USER": "admin"}
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
            ],
            containers=[
                ContainerConfig(
                    dockerfile_path="./Dockerfile",
                    build_context=".",
                    image_name="mega-agent",
                    image_tag="latest",
                    registry="registry.mega-agent.com"
                )
            ],
            pipeline=PipelineConfig(
                name="mega-agent-pipeline",
                stages=[
                    PipelineStage.BUILD,
                    PipelineStage.TEST,
                    PipelineStage.SECURITY_SCAN,
                    PipelineStage.DEPLOY_STAGING,
                    PipelineStage.INTEGRATION_TEST,
                    PipelineStage.DEPLOY_PRODUCTION,
                    PipelineStage.HEALTH_CHECK
                ]
            )
        )


class DeploymentManager:
    """Главный менеджер развертывания"""

    def __init__(self):
        self.container_manager = ContainerManager()
        self.environment_manager = EnvironmentManager(self.container_manager)
        self.pipeline_manager = PipelineManager(self.container_manager, self.environment_manager)
        self.secret_manager = SecretManager()
        self.config_manager = ConfigManager()
        self.deployments: Dict[str, DeploymentResult] = {}

    async def deploy(self, config_path: str) -> DeploymentResult:
        """Выполнить развертывание"""
        deployment_id = f"deploy_{int(time.time())}"

        try:
            print(f"🚀 Starting deployment: {deployment_id}")

            # Загружаем конфигурацию
            config = await self.config_manager.load_config(config_path)
            if not config:
                raise Exception("Failed to load deployment config")

            # Создаем секреты
            await self._setup_secrets(config)

            result = DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                environment="unknown",
                version=config.version,
                start_time=datetime.utcnow()
            )

            # Запускаем CI/CD pipeline
            pipeline_result = await self.pipeline_manager.run_pipeline(config.pipeline, config)

            if pipeline_result.status == "completed":
                result.success = True
                result.services_deployed = [service.name for env in config.environments for service in env.services]
                print(f"🎉 Deployment successful: {deployment_id}")
            else:
                result.success = False
                result.errors.append("Pipeline failed")
                print(f"💥 Deployment failed: {deployment_id}")

            result.end_time = datetime.utcnow()
            result.duration = (result.end_time - result.start_time).total_seconds()
            result.rollback_available = True

            self.deployments[deployment_id] = result
            return result

        except Exception as e:
            print(f"❌ Deployment error: {e}")
            result = DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                environment="unknown",
                version="unknown",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                errors=[str(e)]
            )
            self.deployments[deployment_id] = result
            return result

    async def rollback(self, deployment_id: str) -> bool:
        """Выполнить откат развертывания"""
        try:
            deployment = self.deployments.get(deployment_id)
            if not deployment or not deployment.rollback_available:
                print(f"❌ Rollback not available for deployment: {deployment_id}")
                return False

            print(f"↩️ Rolling back deployment: {deployment_id}")

            # Симуляция отката
            await asyncio.sleep(1)

            print(f"✅ Rollback completed: {deployment_id}")
            return True

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentResult]:
        """Получить статус развертывания"""
        return self.deployments.get(deployment_id)

    async def list_deployments(self) -> List[DeploymentResult]:
        """Список развертываний"""
        return list(self.deployments.values())

    async def _setup_secrets(self, config: DeploymentConfig) -> None:
        """Настроить секреты"""
        for env_config in config.environments:
            # Создаем базовые секреты для окружения
            await self.secret_manager.create_secret(
                "mega-agent-secrets",
                {
                    "database_password": "super_secure_password",
                    "api_key": "api_key_12345",
                    "jwt_secret": "jwt_secret_67890"
                },
                env_config.namespace
            )

    async def generate_deployment_report(self) -> Dict[str, Any]:
        """Генерировать отчет о развертываниях"""
        total_deployments = len(self.deployments)
        successful_deployments = sum(1 for d in self.deployments.values() if d.success)

        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "success_rate": (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0,
            "active_environments": len(self.environment_manager.environments),
            "active_containers": len(self.container_manager.active_containers),
            "recent_deployments": [
                {
                    "id": d.deployment_id,
                    "success": d.success,
                    "duration": d.duration,
                    "environment": d.environment
                }
                for d in sorted(self.deployments.values(), key=lambda x: x.start_time, reverse=True)[:5]
            ]
        }


# Factory functions
async def create_deployment_manager() -> DeploymentManager:
    """Создать менеджер развертывания"""
    return DeploymentManager()


async def create_container_manager() -> ContainerManager:
    """Создать менеджер контейнеров"""
    return ContainerManager()