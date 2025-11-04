"""
Security configuration for MEGA Agent Pro.

This module provides centralized security configuration including:
- Authentication settings
- CORS configuration
- Rate limiting settings
- Security headers
- RBAC enforcement
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from config.secrets_manager import secrets_manager


def _default_jwt_secret() -> str:
    return secrets_manager.get("SECURITY_JWT_SECRET_KEY") or os.getenv(
        "JWT_SECRET_KEY", "dev-secret-change-in-production"
    )


class SecurityConfig(BaseModel):
    """Central security configuration."""

    # Authentication
    jwt_secret_key: str = Field(
        default_factory=lambda: _default_jwt_secret(), description="JWT signing key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT token expiration in hours")

    # Password policies
    min_password_length: int = Field(default=8, description="Minimum password length")
    require_password_complexity: bool = Field(default=True, description="Require complex passwords")

    # Session management
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    max_concurrent_sessions: int = Field(default=5, description="Max concurrent sessions per user")

    # CORS settings
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
        ).split(","),
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allowed_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    cors_allowed_headers: list[str] = Field(
        default=["Authorization", "Content-Type", "Accept", "Origin", "User-Agent"],
        description="Allowed HTTP headers",
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        default=100, description="Requests per minute limit"
    )
    rate_limit_burst: int = Field(default=20, description="Burst limit for rate limiting")

    # Security headers
    security_headers_enabled: bool = Field(default=True, description="Enable security headers")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    csp_policy: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        description="Content Security Policy",
    )

    # Audit and monitoring
    audit_enabled: bool = Field(default=True, description="Enable audit logging")
    audit_retention_days: int = Field(default=90, description="Audit log retention in days")
    security_monitoring_enabled: bool = Field(
        default=True, description="Enable security monitoring"
    )
    audit_log_path: str = Field(
        default_factory=lambda: secrets_manager.get("AUDIT_LOG_PATH", "audits/immutable_audit.log"),
        description="Path for immutable audit trail",
    )
    audit_hash_algorithm: str = Field(
        default="sha256", description="Hash algorithm for audit chain"
    )

    # RBAC enforcement
    rbac_strict_mode: bool = Field(default=True, description="Enable strict RBAC enforcement")
    rbac_cache_ttl_seconds: int = Field(default=300, description="RBAC cache TTL in seconds")
    rbac_policy_path: str | None = Field(
        default_factory=lambda: secrets_manager.get("RBAC_POLICY_PATH"),
        description="Optional path to custom RBAC policy JSON",
    )

    # Prompt injection detection
    prompt_detection_enabled: bool = Field(
        default_factory=lambda: os.getenv("PROMPT_DETECTION_ENABLED", "true").lower() == "true",
        description="Enable prompt injection detection",
    )
    prompt_detection_threshold: float = Field(
        default_factory=lambda: float(os.getenv("PROMPT_DETECTION_THRESHOLD", "0.7")),
        description="Threshold above which prompt is blocked",
    )

    # API Security
    api_key_required: bool = Field(default=False, description="Require API key for requests")
    api_version_header: str = Field(default="X-API-Version", description="API version header name")
    request_size_limit_mb: int = Field(default=10, description="Request size limit in MB")

    # Encryption
    encryption_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    encryption_key_rotation_days: int = Field(default=30, description="Key rotation period in days")

    # Development settings
    debug_mode: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
        description="Enable debug mode",
    )
    dev_bypass_auth: bool = Field(
        default_factory=lambda: os.getenv("DEV_BYPASS_AUTH", "false").lower() == "true",
        description="Bypass authentication in development",
    )

    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class CORSConfig(BaseModel):
    """CORS-specific configuration."""

    def __init__(self, security_config: SecurityConfig):
        super().__init__()
        self.security_config = security_config

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration dictionary for FastAPI/Starlette."""
        return {
            "allow_origins": self.security_config.cors_allowed_origins,
            "allow_credentials": self.security_config.cors_allow_credentials,
            "allow_methods": self.security_config.cors_allowed_methods,
            "allow_headers": self.security_config.cors_allowed_headers,
        }


class SecurityHeaders(BaseModel):
    """Security headers configuration."""

    def __init__(self, security_config: SecurityConfig):
        super().__init__()
        self.security_config = security_config

    def get_security_headers(self) -> dict[str, str]:
        """Get security headers dictionary."""
        if not self.security_config.security_headers_enabled:
            return {}

        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": f"max-age={self.security_config.hsts_max_age}; includeSubDomains",
            "Content-Security-Policy": self.security_config.csp_policy,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }


# Global security configuration instance
security_config = SecurityConfig()
