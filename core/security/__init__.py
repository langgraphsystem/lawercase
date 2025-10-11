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

from .advanced_rbac import Permission, RBACManager, Role, User, get_rbac_manager
from .audit_trail import AuditEvent, AuditEventType, AuditTrail, get_audit_trail
from .config import CORSConfig, SecurityConfig, SecurityHeaders, security_config
from .pii_detector import PIIDetectionResult, PIIDetector, PIIType, get_pii_detector
from .prompt_injection_detector import (
    InjectionType,
    PromptInjectionDetector,
    PromptInjectionResult,
    get_prompt_detector,
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
    "get_audit_trail",
    "get_pii_detector",
    "get_prompt_detector",
    "get_rbac_manager",
    "security_config",
]
