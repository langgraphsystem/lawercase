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

from .advanced_rbac import RBACManager, get_rbac_manager
from .audit_trail import AuditTrail, get_audit_trail
from .config import (CORSConfig, SecurityConfig, SecurityHeaders,
                     security_config)
from .prompt_injection_detector import (PromptInjectionDetector,
                                        PromptInjectionResult,
                                        get_prompt_detector)

__all__ = [
    "AuditTrail",
    "CORSConfig",
    "PromptInjectionDetector",
    "PromptInjectionResult",
    "RBACManager",
    "SecurityConfig",
    "SecurityHeaders",
    "get_audit_trail",
    "get_prompt_detector",
    "get_rbac_manager",
    "security_config",
]
