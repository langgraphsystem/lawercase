"""
Security module для mega_agent_pro.

Provides comprehensive security and RBAC functionality:
- Role-Based Access Control (RBAC)
- Authentication и authorization
- Session management
- Password hashing и validation
- JWT token management
- API key management
- Multi-factor authentication
- Rate limiting
- Security audit logging
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "mega_agent_pro team"

__all__ = [
    # RBAC System
    "RBACManager",
    "User",
    "Role",
    "Session",
    "Permission",
    "PermissionType",
    "RoleType",
    "AuthenticationMethod",
    "SecurityAuditEvent",
    "AuthorizationRequest",
    "AuthorizationResponse",

    # Stores
    "UserStore",
    "RoleStore",
    "SessionStore",
    "AuditStore",
    "InMemoryUserStore",
    "InMemoryRoleStore",
    "InMemorySessionStore",
    "InMemoryAuditStore",

    # Authentication Utils
    "AuthenticationManager",
    "PasswordValidator",
    "PasswordHasher",
    "JWTManager",
    "APIKeyManager",
    "RateLimiter",
    "MultiFactorAuth",
    "PasswordConfig",
    "JWTConfig",
    "APIKeyConfig",
    "RateLimitConfig",
    "HashResult",
    "TokenPair",
    "APIKey",

    # Factory functions
    "create_default_rbac_manager",
    "create_production_rbac_manager",
    "create_testing_rbac_manager",
]

# Import RBAC system
from .rbac_system import (
    RBACManager,
    User,
    Role,
    Session,
    Permission,
    PermissionType,
    RoleType,
    AuthenticationMethod,
    SecurityAuditEvent,
    AuthorizationRequest,
    AuthorizationResponse,
    UserStore,
    RoleStore,
    SessionStore,
    AuditStore,
    InMemoryUserStore,
    InMemoryRoleStore,
    InMemorySessionStore,
    InMemoryAuditStore,
)

# Import authentication utilities
from .auth_utils import (
    AuthenticationManager,
    PasswordValidator,
    PasswordHasher,
    JWTManager,
    APIKeyManager,
    RateLimiter,
    MultiFactorAuth,
    PasswordConfig,
    JWTConfig,
    APIKeyConfig,
    RateLimitConfig,
    HashResult,
    TokenPair,
    APIKey,
)


# Factory functions for common configurations

def create_default_rbac_manager() -> RBACManager:
    """Create default RBAC manager with in-memory stores."""
    return RBACManager()


def create_production_rbac_manager(
    jwt_secret: str,
    session_timeout_hours: int = 8
) -> tuple[RBACManager, AuthenticationManager]:
    """
    Create production RBAC manager with authentication.

    Args:
        jwt_secret: Secret key for JWT tokens
        session_timeout_hours: Session timeout in hours

    Returns:
        Tuple of (RBACManager, AuthenticationManager)
    """
    # Create RBAC manager
    rbac_manager = RBACManager(session_timeout_hours=session_timeout_hours)

    # Create authentication manager with production settings
    auth_manager = AuthenticationManager(
        password_config=PasswordConfig(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_digits=True,
            require_special=True
        ),
        jwt_config=JWTConfig(
            secret_key=jwt_secret,
            access_token_expire_minutes=60,
            refresh_token_expire_days=7
        ),
        api_key_config=APIKeyConfig(
            expire_days=90
        ),
        rate_limit_config=RateLimitConfig(
            max_attempts=3,
            window_minutes=15,
            lockout_minutes=60
        )
    )

    return rbac_manager, auth_manager


def create_testing_rbac_manager() -> tuple[RBACManager, AuthenticationManager]:
    """
    Create RBAC manager for testing with relaxed settings.

    Returns:
        Tuple of (RBACManager, AuthenticationManager)
    """
    # Create RBAC manager with short session timeout for testing
    rbac_manager = RBACManager(session_timeout_hours=1)

    # Create authentication manager with relaxed settings for testing
    auth_manager = AuthenticationManager(
        password_config=PasswordConfig(
            min_length=4,
            require_uppercase=False,
            require_lowercase=False,
            require_digits=False,
            require_special=False
        ),
        jwt_config=JWTConfig(
            secret_key="test-secret-key-not-for-production",
            access_token_expire_minutes=5,
            refresh_token_expire_days=1
        ),
        api_key_config=APIKeyConfig(
            expire_days=1
        ),
        rate_limit_config=RateLimitConfig(
            max_attempts=10,
            window_minutes=1,
            lockout_minutes=1
        )
    )

    return rbac_manager, auth_manager


async def initialize_default_users(rbac_manager: RBACManager) -> dict[str, User]:
    """
    Initialize default users for development/testing.

    Args:
        rbac_manager: RBAC manager instance

    Returns:
        Dictionary mapping username to User object
    """
    users = {}

    # Create super admin
    super_admin = await rbac_manager.create_user(
        username="super_admin",
        email="admin@mega-agent-pro.com",
        roles=["super_admin"],
        tenant_id="default"
    )
    users["super_admin"] = super_admin

    # Create admin
    admin = await rbac_manager.create_user(
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        tenant_id="default"
    )
    users["admin"] = admin

    # Create lawyer
    lawyer = await rbac_manager.create_user(
        username="lawyer",
        email="lawyer@example.com",
        roles=["lawyer"],
        tenant_id="default"
    )
    users["lawyer"] = lawyer

    # Create paralegal
    paralegal = await rbac_manager.create_user(
        username="paralegal",
        email="paralegal@example.com",
        roles=["paralegal"],
        tenant_id="default"
    )
    users["paralegal"] = paralegal

    # Create client
    client = await rbac_manager.create_user(
        username="client",
        email="client@example.com",
        roles=["client"],
        tenant_id="default"
    )
    users["client"] = client

    # Create viewer
    viewer = await rbac_manager.create_user(
        username="viewer",
        email="viewer@example.com",
        roles=["viewer"],
        tenant_id="default"
    )
    users["viewer"] = viewer

    return users


# Convenience decorators and middleware (for future use)

def require_permission(permission: PermissionType, resource: str = None):
    """
    Decorator to require specific permission for function access.

    Usage:
        @require_permission(PermissionType.CASE_CREATE)
        async def create_case(...):
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Implementation would extract user context and check permissions
            # This is a placeholder for future implementation
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: RoleType):
    """
    Decorator to require specific role for function access.

    Usage:
        @require_role(RoleType.LAWYER)
        async def lawyer_function(...):
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Implementation would extract user context and check roles
            # This is a placeholder for future implementation
            return await func(*args, **kwargs)
        return wrapper
    return decorator