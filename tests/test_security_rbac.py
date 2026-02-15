"""Tests for RBAC (Role-Based Access Control) system.

This module tests the advanced RBAC implementation including:
- Permission checking
- Role-based access
- Action-to-permission mapping
- User management
"""

from __future__ import annotations

import pytest

from core.security.advanced_rbac import (
    AccessContext,
    Permission,
    RBACManager,
    Role,
    User,
    get_rbac_manager,
)


class TestPermissionEnum:
    """Tests for Permission enum."""

    def test_permission_values(self):
        """Test that all permission values are properly formatted."""
        for perm in Permission:
            assert "." in perm.value
            parts = perm.value.split(".")
            assert len(parts) >= 2

    def test_permission_categories(self):
        """Test permission category coverage."""
        categories = set()
        for perm in Permission:
            categories.add(perm.value.split(".")[0])

        expected_categories = {
            "case",
            "document",
            "agent",
            "system",
            "user",
            "role",
            "audit",
            "data",
        }
        assert expected_categories.issubset(categories)


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values(self):
        """Test that all expected roles exist."""
        expected_roles = {"admin", "lawyer", "paralegal", "client", "viewer", "system"}
        actual_roles = {role.value for role in Role}
        assert expected_roles == actual_roles


class TestUser:
    """Tests for User dataclass."""

    def test_user_creation(self):
        """Test basic user creation."""
        user = User(user_id="test-123", username="testuser")
        assert user.user_id == "test-123"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.roles == []
        assert user.custom_permissions == []
        assert user.denied_permissions == []

    def test_user_with_roles(self):
        """Test user creation with roles."""
        user = User(
            user_id="test-123",
            username="admin_user",
            roles=[Role.ADMIN, Role.LAWYER],
        )
        assert Role.ADMIN in user.roles
        assert Role.LAWYER in user.roles

    def test_user_with_custom_permissions(self):
        """Test user with custom permissions."""
        user = User(
            user_id="test-123",
            username="custom_user",
            custom_permissions=[Permission.DATA_EXPORT],
        )
        assert Permission.DATA_EXPORT in user.custom_permissions


class TestRBACManager:
    """Tests for RBACManager."""

    @pytest.fixture
    def rbac_manager(self):
        """Create fresh RBAC manager for each test."""
        return RBACManager()

    def test_default_roles_setup(self, rbac_manager):
        """Test that default roles are properly configured."""
        # Admin should have all permissions
        admin_perms = rbac_manager.role_permissions[Role.ADMIN]
        assert len(admin_perms) == len(Permission)

        # Lawyer should have comprehensive permissions
        lawyer_perms = rbac_manager.role_permissions[Role.LAWYER]
        assert Permission.CASE_CREATE in lawyer_perms
        assert Permission.DOCUMENT_APPROVE in lawyer_perms
        assert Permission.AGENT_EXECUTE in lawyer_perms

        # Client should have limited permissions
        client_perms = rbac_manager.role_permissions[Role.CLIENT]
        assert Permission.CASE_READ in client_perms
        assert Permission.CASE_CREATE not in client_perms

    def test_register_user(self, rbac_manager):
        """Test user registration."""
        user = User(user_id="u1", username="user1")
        rbac_manager.register_user(user)

        retrieved = rbac_manager.get_user("u1")
        assert retrieved is not None
        assert retrieved.username == "user1"

    def test_has_permission_with_role(self, rbac_manager):
        """Test permission checking with role."""
        user = User(
            user_id="u1",
            username="lawyer1",
            roles=[Role.LAWYER],
        )
        rbac_manager.register_user(user)

        # Lawyer should have these permissions
        assert rbac_manager.has_permission(user, Permission.CASE_CREATE) is True
        assert rbac_manager.has_permission(user, Permission.DOCUMENT_APPROVE) is True

        # Lawyer should NOT have admin permissions
        assert rbac_manager.has_permission(user, Permission.SYSTEM_ADMIN) is False
        assert rbac_manager.has_permission(user, Permission.USER_MANAGE) is False

    def test_has_permission_with_custom_permission(self, rbac_manager):
        """Test permission checking with custom permission."""
        user = User(
            user_id="u1",
            username="custom1",
            roles=[Role.CLIENT],
            custom_permissions=[Permission.DATA_EXPORT],
        )
        rbac_manager.register_user(user)

        # Custom permission should be granted
        assert rbac_manager.has_permission(user, Permission.DATA_EXPORT) is True
        # Role permission should still work
        assert rbac_manager.has_permission(user, Permission.CASE_READ) is True

    def test_has_permission_with_denied_permission(self, rbac_manager):
        """Test that denied permissions override role permissions."""
        user = User(
            user_id="u1",
            username="restricted",
            roles=[Role.LAWYER],
            denied_permissions=[Permission.CASE_DELETE],
        )
        rbac_manager.register_user(user)

        # Denied permission should be blocked even if role has it
        assert rbac_manager.has_permission(user, Permission.CASE_DELETE) is False
        # Other permissions should still work
        assert rbac_manager.has_permission(user, Permission.CASE_CREATE) is True

    def test_inactive_user_has_no_permissions(self, rbac_manager):
        """Test that inactive users have no permissions."""
        user = User(
            user_id="u1",
            username="inactive",
            roles=[Role.ADMIN],
            is_active=False,
        )
        rbac_manager.register_user(user)

        # Inactive user should have no permissions even with admin role
        assert rbac_manager.has_permission(user, Permission.SYSTEM_ADMIN) is False

    def test_check_access(self, rbac_manager):
        """Test context-based access checking."""
        user = User(
            user_id="u1",
            username="lawyer1",
            roles=[Role.LAWYER],
        )
        rbac_manager.register_user(user)

        context = AccessContext(
            user=user,
            resource_type="case",
            resource_id="case-123",
            action="read",
        )

        assert rbac_manager.check_access(context, Permission.CASE_READ) is True
        assert rbac_manager.check_access(context, Permission.SYSTEM_ADMIN) is False

    def test_grant_permission(self, rbac_manager):
        """Test granting custom permission."""
        user = User(user_id="u1", username="user1", roles=[Role.CLIENT])
        rbac_manager.register_user(user)

        # Before grant
        assert rbac_manager.has_permission(user, Permission.DATA_EXPORT) is False

        # Grant permission
        result = rbac_manager.grant_permission("u1", Permission.DATA_EXPORT)
        assert result is True

        # After grant
        assert rbac_manager.has_permission(user, Permission.DATA_EXPORT) is True

    def test_revoke_permission(self, rbac_manager):
        """Test revoking custom permission."""
        user = User(
            user_id="u1",
            username="user1",
            custom_permissions=[Permission.DATA_EXPORT],
        )
        rbac_manager.register_user(user)

        # Before revoke
        assert rbac_manager.has_permission(user, Permission.DATA_EXPORT) is True

        # Revoke permission
        result = rbac_manager.revoke_permission("u1", Permission.DATA_EXPORT)
        assert result is True

        # After revoke
        assert rbac_manager.has_permission(user, Permission.DATA_EXPORT) is False

    def test_deny_permission(self, rbac_manager):
        """Test explicitly denying permission."""
        user = User(user_id="u1", username="lawyer1", roles=[Role.LAWYER])
        rbac_manager.register_user(user)

        # Before deny
        assert rbac_manager.has_permission(user, Permission.CASE_DELETE) is True

        # Deny permission
        result = rbac_manager.deny_permission("u1", Permission.CASE_DELETE)
        assert result is True

        # After deny
        assert rbac_manager.has_permission(user, Permission.CASE_DELETE) is False

    def test_assign_role(self, rbac_manager):
        """Test assigning role to user."""
        user = User(user_id="u1", username="user1")
        rbac_manager.register_user(user)

        # Before assignment
        assert Role.LAWYER not in user.roles

        # Assign role
        result = rbac_manager.assign_role("u1", Role.LAWYER)
        assert result is True

        # After assignment
        assert Role.LAWYER in user.roles
        assert rbac_manager.has_permission(user, Permission.CASE_CREATE) is True

    def test_remove_role(self, rbac_manager):
        """Test removing role from user."""
        user = User(user_id="u1", username="lawyer1", roles=[Role.LAWYER])
        rbac_manager.register_user(user)

        # Before removal
        assert rbac_manager.has_permission(user, Permission.CASE_CREATE) is True

        # Remove role
        result = rbac_manager.remove_role("u1", Role.LAWYER)
        assert result is True

        # After removal
        assert Role.LAWYER not in user.roles
        assert rbac_manager.has_permission(user, Permission.CASE_CREATE) is False

    def test_get_user_permissions(self, rbac_manager):
        """Test getting all effective permissions for user."""
        user = User(
            user_id="u1",
            username="user1",
            roles=[Role.CLIENT],
            custom_permissions=[Permission.DATA_EXPORT],
            denied_permissions=[Permission.DOCUMENT_READ],
        )
        rbac_manager.register_user(user)

        permissions = rbac_manager.get_user_permissions("u1")

        # Should have client permissions
        assert Permission.CASE_READ in permissions
        # Should have custom permission
        assert Permission.DATA_EXPORT in permissions
        # Should NOT have denied permission
        assert Permission.DOCUMENT_READ not in permissions

    def test_create_admin_user(self, rbac_manager):
        """Test creating admin user."""
        admin = rbac_manager.create_admin_user("admin1", "administrator")

        assert admin.user_id == "admin1"
        assert admin.username == "administrator"
        assert Role.ADMIN in admin.roles
        assert rbac_manager.has_permission(admin, Permission.SYSTEM_ADMIN) is True


class TestCheckPermissionMethod:
    """Tests for the simplified check_permission method."""

    @pytest.fixture
    def rbac_manager(self):
        """Create fresh RBAC manager for each test."""
        return RBACManager()

    def test_check_permission_admin_role(self, rbac_manager):
        """Test admin role has all permissions."""
        assert rbac_manager.check_permission("admin", "create", "case") is True
        assert rbac_manager.check_permission("admin", "delete", "document") is True
        assert rbac_manager.check_permission("admin", "admin", "system") is True

    def test_check_permission_lawyer_role(self, rbac_manager):
        """Test lawyer role permissions."""
        # Lawyer should have case and document permissions
        assert rbac_manager.check_permission("lawyer", "create", "case") is True
        assert rbac_manager.check_permission("lawyer", "read", "document") is True
        assert rbac_manager.check_permission("lawyer", "ask", "agent") is True

        # Lawyer should NOT have admin permissions
        assert rbac_manager.check_permission("lawyer", "admin", "system") is False
        assert rbac_manager.check_permission("lawyer", "manage", "user") is False

    def test_check_permission_client_role(self, rbac_manager):
        """Test client role has limited permissions."""
        # Client should only have read permissions
        assert rbac_manager.check_permission("client", "read", "case") is True
        assert rbac_manager.check_permission("client", "read", "document") is True

        # Client should NOT have write permissions
        assert rbac_manager.check_permission("client", "create", "case") is False
        assert rbac_manager.check_permission("client", "delete", "document") is False

    def test_check_permission_compound_action(self, rbac_manager):
        """Test compound actions like case_get."""
        # Should parse case_get as resource=case, action=get
        assert rbac_manager.check_permission("lawyer", "case_get", "api") is True
        assert rbac_manager.check_permission("lawyer", "document_create", "api") is True
        assert rbac_manager.check_permission("client", "case_create", "api") is False

    def test_check_permission_unknown_role(self, rbac_manager):
        """Test unknown role is denied."""
        assert rbac_manager.check_permission("unknown_role", "read", "case") is False

    def test_check_permission_unknown_resource(self, rbac_manager):
        """Test unknown resource is denied."""
        assert rbac_manager.check_permission("admin", "read", "unknown_resource") is False

    def test_check_permission_unknown_action(self, rbac_manager):
        """Test unknown action is denied."""
        assert rbac_manager.check_permission("admin", "unknown_action", "case") is False

    def test_check_permission_case_insensitive(self, rbac_manager):
        """Test role and action are case-insensitive."""
        assert rbac_manager.check_permission("ADMIN", "CREATE", "CASE") is True
        assert rbac_manager.check_permission("Lawyer", "Read", "Document") is True

    def test_check_permission_agent_operations(self, rbac_manager):
        """Test agent-specific permissions."""
        # Lawyer can execute agents
        assert rbac_manager.check_permission("lawyer", "execute", "agent") is True
        assert rbac_manager.check_permission("lawyer", "ask", "agent") is True
        assert rbac_manager.check_permission("lawyer", "run", "agent") is True

        # Lawyer cannot configure agents
        assert rbac_manager.check_permission("lawyer", "configure", "agent") is False

        # Admin can do everything
        assert rbac_manager.check_permission("admin", "configure", "agent") is True


class TestLoadPolicy:
    """Tests for loading RBAC policies."""

    @pytest.fixture
    def rbac_manager(self):
        """Create fresh RBAC manager for each test."""
        return RBACManager()

    def test_load_policy_with_roles(self, rbac_manager):
        """Test loading policy with custom role definitions."""
        policy = {
            "roles": {
                "lawyer": ["case.create", "case.read", "case.update"],
            },
            "users": [],
        }

        rbac_manager.load_policy(policy)

        # Check that lawyer role was updated
        lawyer_perms = rbac_manager.role_permissions[Role.LAWYER]
        assert Permission.CASE_CREATE in lawyer_perms
        assert Permission.CASE_READ in lawyer_perms
        assert Permission.CASE_UPDATE in lawyer_perms

    def test_load_policy_with_users(self, rbac_manager):
        """Test loading policy with user definitions."""
        policy = {
            "roles": {},
            "users": [
                {
                    "user_id": "user-123",
                    "username": "testuser",
                    "roles": ["lawyer"],
                    "custom_permissions": ["data.export"],
                },
            ],
        }

        rbac_manager.load_policy(policy)

        user = rbac_manager.get_user("user-123")
        assert user is not None
        assert user.username == "testuser"
        assert Role.LAWYER in user.roles
        assert Permission.DATA_EXPORT in user.custom_permissions

    def test_load_policy_wildcard_permissions(self, rbac_manager):
        """Test loading policy with wildcard permissions."""
        policy = {
            "roles": {
                "admin": ["*"],
            },
            "users": [],
        }

        rbac_manager.load_policy(policy)

        admin_perms = rbac_manager.role_permissions[Role.ADMIN]
        assert len(admin_perms) == len(Permission)


class TestGlobalRBACManager:
    """Tests for global RBAC manager instance."""

    def test_get_rbac_manager_singleton(self):
        """Test that get_rbac_manager returns singleton."""
        manager1 = get_rbac_manager()
        manager2 = get_rbac_manager()

        # Should be the same instance
        assert manager1 is manager2
