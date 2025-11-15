"""
Security module for MEGA Agent Pro.

Provides comprehensive security features:
- Authentication and authorization
- CORS configuration
- Security headers
- Rate limiting
- Audit logging
- RBAC enforcement
"""

from __future__ import annotations

from .advanced_rbac import (
    Permission,
    RBACManager,
    Role,
    User,
    get_rbac_manager,
    initialize_rbac_from_policy,
)
from .audit_trail import AuditEvent, AuditEventType, AuditTrail, get_audit_trail
from .config import CORSConfig, SecurityConfig, SecurityHeaders, security_config
from .pii_detector import PIIDetectionResult, PIIDetector, PIIType, get_pii_detector
from .prompt_injection_detector import (
    InjectionType,
    PromptInjectionDetector,
    PromptInjectionResult,
    configure_prompt_detector,
    get_prompt_detector,
)


def configure_security(config: SecurityConfig) -> None:
    """Apply runtime security configuration (RBAC, prompt detector, etc.)."""
    initialize_rbac_from_policy(config.rbac_policy_path)
    configure_prompt_detector(
        enabled=config.prompt_detection_enabled,
        threshold=config.prompt_detection_threshold,
    )


__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditTrail",
    "CORSConfig",
    "InjectionType",
    "PIIDetectionResult",
    "PIIDetector",
    "PIIType",
    "Permission",
    "PromptInjectionDetector",
    "PromptInjectionResult",
    "RBACManager",
    "Role",
    "SecurityConfig",
    "SecurityHeaders",
    "User",
    "configure_prompt_detector",
    "configure_security",
    "get_audit_trail",
    "get_pii_detector",
    "get_prompt_detector",
    "get_rbac_manager",
    "initialize_rbac_from_policy",
    "security_config",
]
