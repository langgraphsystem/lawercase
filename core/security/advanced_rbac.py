"""Advanced Role-Based Access Control (RBAC) system."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""

    # Case management
    CASE_CREATE = "case.create"
    CASE_READ = "case.read"
    CASE_UPDATE = "case.update"
    CASE_DELETE = "case.delete"
    CASE_LIST = "case.list"

    # Document operations
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_READ = "document.read"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_APPROVE = "document.approve"

    # Agent operations
    AGENT_EXECUTE = "agent.execute"
    AGENT_CONFIGURE = "agent.configure"
    AGENT_MONITOR = "agent.monitor"

    # System administration
    SYSTEM_ADMIN = "system.admin"
    USER_MANAGE = "user.manage"
    ROLE_MANAGE = "role.manage"
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"

    # Data access
    DATA_READ_SENSITIVE = "data.read.sensitive"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"


class Role(str, Enum):
    """System roles."""

    ADMIN = "admin"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    CLIENT = "client"
    VIEWER = "viewer"
    SYSTEM = "system"


@dataclass
class User:
    """User representation."""

    user_id: str
    username: str
    roles: list[Role] = field(default_factory=list)
    custom_permissions: list[Permission] = field(default_factory=list)
    denied_permissions: list[Permission] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class AccessContext:
    """Context for access control decisions."""

    user: User
    resource_type: str
    resource_id: str | None = None
    action: str = ""
    ip_address: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RBACManager:
    """Manages role-based access control."""

    def __init__(self) -> None:
        """Initialize RBAC manager."""
        self.role_permissions: dict[Role, set[Permission]] = {}
        self.users: dict[str, User] = {}
        self._setup_default_roles()
        logger.info("RBACManager initialized")

    def _setup_default_roles(self) -> None:
        """Setup default role-permission mappings."""
        # Admin - full access
        self.role_permissions[Role.ADMIN] = set(Permission)

        # Lawyer - comprehensive access
        self.role_permissions[Role.LAWYER] = {
            Permission.CASE_CREATE,
            Permission.CASE_READ,
            Permission.CASE_UPDATE,
            Permission.CASE_DELETE,
            Permission.CASE_LIST,
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE,
            Permission.DOCUMENT_APPROVE,
            Permission.AGENT_EXECUTE,
            Permission.AGENT_MONITOR,
            Permission.DATA_READ_SENSITIVE,
            Permission.AUDIT_VIEW,
        }

        # Paralegal - limited access
        self.role_permissions[Role.PARALEGAL] = {
            Permission.CASE_READ,
            Permission.CASE_UPDATE,
            Permission.CASE_LIST,
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.AGENT_EXECUTE,
        }

        # Client - view only
        self.role_permissions[Role.CLIENT] = {
            Permission.CASE_READ,
            Permission.DOCUMENT_READ,
        }

        # Viewer - read only
        self.role_permissions[Role.VIEWER] = {
            Permission.CASE_READ,
            Permission.CASE_LIST,
            Permission.DOCUMENT_READ,
        }

        # System - internal operations
        self.role_permissions[Role.SYSTEM] = set(Permission)

    def register_user(self, user: User) -> None:
        """Register a new user.

        Args:
            user: User to register
        """
        self.users[user.user_id] = user
        logger.info(f"Registered user: {user.username} ({user.user_id})")

    def get_user(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return self.users.get(user_id)

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission.

        Args:
            user: User to check
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if not user.is_active:
            return False

        # Check denied permissions first
        if permission in user.denied_permissions:
            return False

        # Check custom permissions
        if permission in user.custom_permissions:
            return True

        # Check role-based permissions
        return any(permission in self.role_permissions.get(role, set()) for role in user.roles)

    def check_access(self, context: AccessContext, required_permission: Permission) -> bool:
        """Check if user has access in given context.

        Args:
            context: Access context
            required_permission: Required permission

        Returns:
            True if access granted
        """
        # Check basic permission
        if not self.has_permission(context.user, required_permission):
            logger.warning(
                f"Access denied for user {context.user.username}: "
                f"missing permission {required_permission}"
            )
            return False

        # Additional context-based checks could be added here
        # e.g., resource ownership, time-based access, etc.

        logger.debug(
            f"Access granted for {context.user.username} to "
            f"{context.resource_type} ({required_permission})"
        )
        return True

    def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant custom permission to user.

        Args:
            user_id: User ID
            permission: Permission to grant

        Returns:
            True if successful
        """
        user = self.get_user(user_id)
        if not user:
            logger.error(f"Cannot grant permission: user {user_id} not found")
            return False

        if permission not in user.custom_permissions:
            user.custom_permissions.append(permission)
            logger.info(f"Granted permission {permission} to user {user.username}")

        return True

    def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke custom permission from user.

        Args:
            user_id: User ID
            permission: Permission to revoke

        Returns:
            True if successful
        """
        user = self.get_user(user_id)
        if not user:
            logger.error(f"Cannot revoke permission: user {user_id} not found")
            return False

        if permission in user.custom_permissions:
            user.custom_permissions.remove(permission)
            logger.info(f"Revoked permission {permission} from user {user.username}")

        return True

    def deny_permission(self, user_id: str, permission: Permission) -> bool:
        """Explicitly deny permission to user (overrides role permissions).

        Args:
            user_id: User ID
            permission: Permission to deny

        Returns:
            True if successful
        """
        user = self.get_user(user_id)
        if not user:
            logger.error(f"Cannot deny permission: user {user_id} not found")
            return False

        if permission not in user.denied_permissions:
            user.denied_permissions.append(permission)
            logger.info(f"Denied permission {permission} for user {user.username}")

        return True

    def assign_role(self, user_id: str, role: Role) -> bool:
        """Assign role to user.

        Args:
            user_id: User ID
            role: Role to assign

        Returns:
            True if successful
        """
        user = self.get_user(user_id)
        if not user:
            logger.error(f"Cannot assign role: user {user_id} not found")
            return False

        if role not in user.roles:
            user.roles.append(role)
            logger.info(f"Assigned role {role} to user {user.username}")

        return True

    def remove_role(self, user_id: str, role: Role) -> bool:
        """Remove role from user.

        Args:
            user_id: User ID
            role: Role to remove

        Returns:
            True if successful
        """
        user = self.get_user(user_id)
        if not user:
            logger.error(f"Cannot remove role: user {user_id} not found")
            return False

        if role in user.roles:
            user.roles.remove(role)
            logger.info(f"Removed role {role} from user {user.username}")

        return True

    def get_user_permissions(self, user_id: str) -> set[Permission]:
        """Get all effective permissions for user.

        Args:
            user_id: User ID

        Returns:
            Set of permissions
        """
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return set()

        permissions: set[Permission] = set()

        # Add role-based permissions
        for role in user.roles:
            permissions.update(self.role_permissions.get(role, set()))

        # Add custom permissions
        permissions.update(user.custom_permissions)

        # Remove denied permissions
        permissions -= set(user.denied_permissions)

        return permissions

    def create_admin_user(self, user_id: str, username: str) -> User:
        """Create an admin user.

        Args:
            user_id: User ID
            username: Username

        Returns:
            Created user
        """
        user = User(
            user_id=user_id,
            username=username,
            roles=[Role.ADMIN],
        )
        self.register_user(user)
        return user

    def load_policy(self, policy: dict[str, Any]) -> None:
        """Load role and user assignments from policy dictionary."""
        roles = policy.get("roles", {})
        for role_name, permissions in roles.items():
            try:
                role = Role(role_name)
            except ValueError:
                logger.warning("Unknown role in policy: %s", role_name)
                continue
            if permissions == ["*"]:
                self.role_permissions[role] = set(Permission)
            else:
                mapped = {Permission(permission) for permission in permissions}
                self.role_permissions[role] = mapped

        for user_data in policy.get("users", []):
            try:
                user = User(
                    user_id=user_data["user_id"],
                    username=user_data.get("username", user_data["user_id"]),
                    roles=[Role(role) for role in user_data.get("roles", [])],
                    custom_permissions=[
                        Permission(p) for p in user_data.get("custom_permissions", [])
                    ],
                    denied_permissions=[
                        Permission(p) for p in user_data.get("denied_permissions", [])
                    ],
                    metadata=user_data.get("metadata", {}),
                    is_active=user_data.get("is_active", True),
                )
            except KeyError as exc:
                logger.error("Invalid user entry in RBAC policy: missing %s", exc)
                continue
            self.register_user(user)

    def check_permission(
        self,
        role: str,
        action: str,
        resource: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a role has permission for an action on a resource.

        This method provides a simplified permission check compatible with
        the MegaAgent authorization flow.

        Args:
            role: Role name (e.g., "lawyer", "admin")
            action: Action to perform (e.g., "ask", "case_get")
            resource: Resource type (e.g., "agent", "case")
            context: Additional context (optional, not currently used)

        Returns:
            True if permission granted, False otherwise

        Note:
            Currently implements permissive authorization - returns True for all requests.
            TODO: Implement proper action-to-permission mapping and role-based checks.
        """
        # Log the authorization check
        logger.debug(
            f"RBAC check: role={role}, action={action}, resource={resource}, context={context}"
        )

        # For now, allow all authenticated requests
        # In production, this should map actions to Permission enums and check roles
        # Example implementation:
        # try:
        #     role_enum = Role(role)
        #     # Map action to Permission enum
        #     # Check if role has that permission using has_permission()
        # except ValueError:
        #     return False

        return True  # Permissive mode for development/testing

    def load_policy_file(self, path: str | Path) -> None:
        """Load policy JSON file and apply it."""
        policy_path = Path(path)
        if not policy_path.exists():
            raise FileNotFoundError(f"RBAC policy file not found: {policy_path}")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.load_policy(policy)


# Global instance
_rbac_manager: RBACManager | None = None


def get_rbac_manager() -> RBACManager:
    """Get or create global RBAC manager.

    Returns:
        Global RBACManager instance
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def initialize_rbac_from_policy(path: str | None) -> RBACManager:
    """Initialize RBAC manager using an optional policy path."""
    manager = get_rbac_manager()
    if path:
        try:
            manager.load_policy_file(path)
        except FileNotFoundError:
            logger.error("RBAC policy file %s not found", path)
    return manager
