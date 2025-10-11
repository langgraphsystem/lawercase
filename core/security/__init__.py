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

from .config import (CORSConfig, SecurityConfig, SecurityHeaders,
                     security_config)
from .advanced_rbac import RBACManager, get_rbac_manager
from .prompt_injection_detector import (PromptInjectionDetector,
                                        PromptInjectionResult,
                                        get_prompt_detector)
from .audit_trail import AuditTrail, get_audit_trail

__all__ = [
    "CORSConfig",
    "SecurityConfig",
    "SecurityHeaders",
    "security_config",
    "RBACManager",
    "get_rbac_manager",
    "PromptInjectionDetector",
    "PromptInjectionResult",
    "get_prompt_detector",
    "AuditTrail",
    "get_audit_trail",
]
