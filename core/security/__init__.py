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

from .config import CORSConfig, SecurityConfig, SecurityHeaders, security_config

__all__ = [
    "CORSConfig",
    "SecurityConfig",
    "SecurityHeaders",
    "security_config",
]
