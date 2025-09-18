"""
Deployment & DevOps module для mega_agent_pro.

Provides comprehensive deployment and DevOps capabilities:
- Docker containerization и orchestration
- CI/CD pipeline configuration
- Environment management (dev/staging/prod)
- Infrastructure as Code (IaC)
- Health checks и monitoring integration
- Auto-scaling и load balancing
- Secret management и configuration
- Deployment strategies (blue-green, rolling, canary)
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # Core Deployment System
    "DeploymentManager",
    "ContainerManager",
    "PipelineManager",
    "EnvironmentManager",
    "ConfigManager",
    "SecretManager",

    # Models
    "DeploymentConfig",
    "ContainerConfig",
    "PipelineConfig",
    "EnvironmentConfig",
    "ServiceConfig",
    "HealthCheckConfig",

    # Enums
    "DeploymentStrategy",
    "EnvironmentType",
    "ServiceStatus",
    "PipelineStage",

    # Factories
    "create_deployment_manager",
    "create_container_manager",
]

# Import core deployment system
from .deployment_system import (
    DeploymentManager,
    ContainerManager,
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
    ServiceStatus,
    PipelineStage,
    create_deployment_manager,
    create_container_manager,
)