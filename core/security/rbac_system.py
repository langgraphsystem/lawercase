"""
Role-Based Access Control (RBAC) System для mega_agent_pro.

Обеспечивает:
- Fine-grained permissions management
- Role-based access control с наследованием
- Dynamic permission checking
- Session management и authentication
- Audit logging для security events
- Multi-tenant support
- Policy-based authorization
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    """Типы разрешений в системе."""
    # Case management
    CASE_CREATE = "case:create"
    CASE_READ = "case:read"
    CASE_UPDATE = "case:update"
    CASE_DELETE = "case:delete"
    CASE_LIST = "case:list"
    CASE_ASSIGN = "case:assign"

    # Document management
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_APPROVE = "document:approve"
    DOCUMENT_SHARE = "document:share"

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    USER_ASSIGN_ROLE = "user:assign_role"

    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_MONITOR = "system:monitor"

    # Agent operations
    AGENT_INVOKE = "agent:invoke"
    AGENT_CONFIGURE = "agent:configure"
    AGENT_MONITOR = "agent:monitor"

    # Data operations
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_SEARCH = "data:search"
    DATA_ANALYTICS = "data:analytics"


class RoleType(str, Enum):
    """Предопределенные роли в системе."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    CLIENT = "client"
    VIEWER = "viewer"
    GUEST = "guest"


class AuthenticationMethod(str, Enum):
    """Методы аутентификации."""
    PASSWORD = "password"
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    SSO = "sso"
    MULTI_FACTOR = "multi_factor"


class Permission(BaseModel):
    """Разрешение в системе."""
    name: PermissionType = Field(..., description="Тип разрешения")
    resource: Optional[str] = Field(None, description="Ресурс (опционально)")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Условия применения")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    granted_by: Optional[str] = Field(None, description="Кто предоставил разрешение")


class Role(BaseModel):
    """Роль пользователя."""
    name: str = Field(..., description="Название роли")
    type: RoleType = Field(..., description="Тип роли")
    permissions: List[Permission] = Field(default_factory=list, description="Разрешения роли")
    parent_roles: List[str] = Field(default_factory=list, description="Родительские роли")
    description: Optional[str] = Field(None, description="Описание роли")
    is_active: bool = Field(True, description="Активна ли роль")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """Пользователь системы."""
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: Optional[str] = Field(None, description="Email")
    roles: List[str] = Field(default_factory=list, description="Роли пользователя")
    tenant_id: Optional[str] = Field(None, description="ID арендатора (для multi-tenant)")
    is_active: bool = Field(True, description="Активен ли пользователь")
    is_verified: bool = Field(False, description="Верифицирован ли пользователь")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None, description="Последний вход")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")


class Session(BaseModel):
    """Сессия пользователя."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID пользователя")
    tenant_id: Optional[str] = Field(None, description="ID арендатора")
    auth_method: AuthenticationMethod = Field(..., description="Метод аутентификации")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Время истечения сессии")
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User agent")
    is_active: bool = Field(True, description="Активна ли сессия")


class SecurityAuditEvent(BaseModel):
    """Событие аудита безопасности."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., description="Тип события")
    user_id: Optional[str] = Field(None, description="ID пользователя")
    session_id: Optional[str] = Field(None, description="ID сессии")
    resource: Optional[str] = Field(None, description="Ресурс")
    action: str = Field(..., description="Действие")
    result: str = Field(..., description="Результат (success/failure/denied)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Детали события")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="IP адрес")
    risk_score: int = Field(0, ge=0, le=100, description="Оценка риска 0-100")


class AuthorizationRequest(BaseModel):
    """Запрос на авторизацию."""
    user_id: str = Field(..., description="ID пользователя")
    permission: PermissionType = Field(..., description="Требуемое разрешение")
    resource: Optional[str] = Field(None, description="Ресурс")
    context: Dict[str, Any] = Field(default_factory=dict, description="Контекст запроса")
    session_id: Optional[str] = Field(None, description="ID сессии")


class AuthorizationResponse(BaseModel):
    """Ответ на запрос авторизации."""
    granted: bool = Field(..., description="Разрешен ли доступ")
    reason: Optional[str] = Field(None, description="Причина решения")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Условия доступа")
    expires_at: Optional[datetime] = Field(None, description="Время истечения разрешения")


# Abstract interfaces

class UserStore(ABC):
    """Абстрактный интерфейс для хранения пользователей."""

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID."""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени."""
        pass

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Создать пользователя."""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Обновить пользователя."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Удалить пользователя."""
        pass

    @abstractmethod
    async def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        """Список пользователей."""
        pass


class RoleStore(ABC):
    """Абстрактный интерфейс для хранения ролей."""

    @abstractmethod
    async def get_role(self, role_name: str) -> Optional[Role]:
        """Получить роль по имени."""
        pass

    @abstractmethod
    async def create_role(self, role: Role) -> Role:
        """Создать роль."""
        pass

    @abstractmethod
    async def update_role(self, role: Role) -> Role:
        """Обновить роль."""
        pass

    @abstractmethod
    async def delete_role(self, role_name: str) -> bool:
        """Удалить роль."""
        pass

    @abstractmethod
    async def list_roles(self) -> List[Role]:
        """Список ролей."""
        pass


class SessionStore(ABC):
    """Абстрактный интерфейс для хранения сессий."""

    @abstractmethod
    async def create_session(self, session: Session) -> Session:
        """Создать сессию."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Получить сессию."""
        pass

    @abstractmethod
    async def update_session(self, session: Session) -> Session:
        """Обновить сессию."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Удалить сессию."""
        pass

    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Получить сессии пользователя."""
        pass


class AuditStore(ABC):
    """Абстрактный интерфейс для хранения аудита."""

    @abstractmethod
    async def log_event(self, event: SecurityAuditEvent) -> None:
        """Записать событие аудита."""
        pass

    @abstractmethod
    async def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityAuditEvent]:
        """Получить события аудита."""
        pass


# In-memory implementations

class InMemoryUserStore(UserStore):
    """In-memory реализация UserStore."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.username_index: Dict[str, str] = {}  # username -> user_id

    async def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        user_id = self.username_index.get(username)
        return self.users.get(user_id) if user_id else None

    async def create_user(self, user: User) -> User:
        if user.user_id in self.users:
            raise ValueError(f"User {user.user_id} already exists")
        if user.username in self.username_index:
            raise ValueError(f"Username {user.username} already exists")

        self.users[user.user_id] = user
        self.username_index[user.username] = user.user_id
        return user

    async def update_user(self, user: User) -> User:
        if user.user_id not in self.users:
            raise ValueError(f"User {user.user_id} not found")

        old_user = self.users[user.user_id]
        if old_user.username != user.username:
            # Update username index
            del self.username_index[old_user.username]
            self.username_index[user.username] = user.user_id

        user.updated_at = datetime.utcnow()
        self.users[user.user_id] = user
        return user

    async def delete_user(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False

        del self.users[user_id]
        del self.username_index[user.username]
        return True

    async def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        users = list(self.users.values())
        if tenant_id:
            users = [u for u in users if u.tenant_id == tenant_id]
        return users


class InMemoryRoleStore(RoleStore):
    """In-memory реализация RoleStore."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self._init_default_roles()

    def _init_default_roles(self):
        """Инициализация предопределенных ролей."""
        # Super Admin - все разрешения
        super_admin = Role(
            name="super_admin",
            type=RoleType.SUPER_ADMIN,
            permissions=[Permission(name=perm) for perm in PermissionType],
            description="Супер администратор с полными правами"
        )

        # Admin - административные разрешения
        admin_permissions = [
            PermissionType.CASE_CREATE, PermissionType.CASE_READ, PermissionType.CASE_UPDATE, PermissionType.CASE_DELETE,
            PermissionType.CASE_LIST, PermissionType.CASE_ASSIGN,
            PermissionType.DOCUMENT_CREATE, PermissionType.DOCUMENT_READ, PermissionType.DOCUMENT_UPDATE,
            PermissionType.DOCUMENT_DELETE, PermissionType.DOCUMENT_APPROVE, PermissionType.DOCUMENT_SHARE,
            PermissionType.USER_CREATE, PermissionType.USER_READ, PermissionType.USER_UPDATE, PermissionType.USER_LIST,
            PermissionType.AGENT_INVOKE, PermissionType.AGENT_CONFIGURE,
            PermissionType.DATA_EXPORT, PermissionType.DATA_IMPORT, PermissionType.DATA_SEARCH, PermissionType.DATA_ANALYTICS
        ]
        admin = Role(
            name="admin",
            type=RoleType.ADMIN,
            permissions=[Permission(name=perm) for perm in admin_permissions],
            description="Администратор системы"
        )

        # Lawyer - права юриста
        lawyer_permissions = [
            PermissionType.CASE_CREATE, PermissionType.CASE_READ, PermissionType.CASE_UPDATE, PermissionType.CASE_LIST,
            PermissionType.DOCUMENT_CREATE, PermissionType.DOCUMENT_READ, PermissionType.DOCUMENT_UPDATE,
            PermissionType.DOCUMENT_APPROVE, PermissionType.DOCUMENT_SHARE,
            PermissionType.AGENT_INVOKE,
            PermissionType.DATA_SEARCH, PermissionType.DATA_ANALYTICS
        ]
        lawyer = Role(
            name="lawyer",
            type=RoleType.LAWYER,
            permissions=[Permission(name=perm) for perm in lawyer_permissions],
            description="Юрист с правами на работу с делами и документами"
        )

        # Paralegal - права помощника юриста
        paralegal_permissions = [
            PermissionType.CASE_READ, PermissionType.CASE_UPDATE, PermissionType.CASE_LIST,
            PermissionType.DOCUMENT_CREATE, PermissionType.DOCUMENT_READ, PermissionType.DOCUMENT_UPDATE,
            PermissionType.AGENT_INVOKE,
            PermissionType.DATA_SEARCH
        ]
        paralegal = Role(
            name="paralegal",
            type=RoleType.PARALEGAL,
            permissions=[Permission(name=perm) for perm in paralegal_permissions],
            description="Помощник юриста"
        )

        # Client - права клиента
        client_permissions = [
            PermissionType.CASE_READ,
            PermissionType.DOCUMENT_READ,
            PermissionType.DATA_SEARCH
        ]
        client = Role(
            name="client",
            type=RoleType.CLIENT,
            permissions=[Permission(name=perm) for perm in client_permissions],
            description="Клиент с ограниченными правами"
        )

        # Viewer - только просмотр
        viewer_permissions = [
            PermissionType.CASE_READ,
            PermissionType.DOCUMENT_READ
        ]
        viewer = Role(
            name="viewer",
            type=RoleType.VIEWER,
            permissions=[Permission(name=perm) for perm in viewer_permissions],
            description="Наблюдатель с правами только на просмотр"
        )

        # Сохраняем роли
        for role in [super_admin, admin, lawyer, paralegal, client, viewer]:
            self.roles[role.name] = role

    async def get_role(self, role_name: str) -> Optional[Role]:
        return self.roles.get(role_name)

    async def create_role(self, role: Role) -> Role:
        if role.name in self.roles:
            raise ValueError(f"Role {role.name} already exists")
        self.roles[role.name] = role
        return role

    async def update_role(self, role: Role) -> Role:
        if role.name not in self.roles:
            raise ValueError(f"Role {role.name} not found")
        role.updated_at = datetime.utcnow()
        self.roles[role.name] = role
        return role

    async def delete_role(self, role_name: str) -> bool:
        if role_name not in self.roles:
            return False
        del self.roles[role_name]
        return True

    async def list_roles(self) -> List[Role]:
        return list(self.roles.values())


class InMemorySessionStore(SessionStore):
    """In-memory реализация SessionStore."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids

    async def create_session(self, session: Session) -> Session:
        self.sessions[session.session_id] = session

        if session.user_id not in self.user_sessions:
            self.user_sessions[session.user_id] = set()
        self.user_sessions[session.user_id].add(session.session_id)

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        session = self.sessions.get(session_id)
        if session and session.expires_at < datetime.utcnow():
            # Session expired
            await self.delete_session(session_id)
            return None
        return session

    async def update_session(self, session: Session) -> Session:
        if session.session_id not in self.sessions:
            raise ValueError(f"Session {session.session_id} not found")
        self.sessions[session.session_id] = session
        return session

    async def delete_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False

        del self.sessions[session_id]
        if session.user_id in self.user_sessions:
            self.user_sessions[session.user_id].discard(session_id)
            if not self.user_sessions[session.user_id]:
                del self.user_sessions[session.user_id]

        return True

    async def get_user_sessions(self, user_id: str) -> List[Session]:
        session_ids = self.user_sessions.get(user_id, set())
        sessions = []
        for session_id in list(session_ids):  # Copy to avoid modification during iteration
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
        return sessions


class InMemoryAuditStore(AuditStore):
    """In-memory реализация AuditStore."""

    def __init__(self):
        self.events: List[SecurityAuditEvent] = []

    async def log_event(self, event: SecurityAuditEvent) -> None:
        self.events.append(event)

    async def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityAuditEvent]:
        filtered_events = self.events

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # Sort by timestamp descending and limit
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_events[:limit]


class RBACManager:
    """Основной менеджер RBAC системы."""

    def __init__(
        self,
        user_store: Optional[UserStore] = None,
        role_store: Optional[RoleStore] = None,
        session_store: Optional[SessionStore] = None,
        audit_store: Optional[AuditStore] = None,
        session_timeout_hours: int = 24
    ):
        self.user_store = user_store or InMemoryUserStore()
        self.role_store = role_store or InMemoryRoleStore()
        self.session_store = session_store or InMemorySessionStore()
        self.audit_store = audit_store or InMemoryAuditStore()
        self.session_timeout_hours = session_timeout_hours

    # User management

    async def create_user(
        self,
        username: str,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        **metadata
    ) -> User:
        """Создать пользователя."""
        user = User(
            username=username,
            email=email,
            roles=roles or [],
            tenant_id=tenant_id,
            metadata=metadata
        )

        created_user = await self.user_store.create_user(user)

        await self.audit_store.log_event(SecurityAuditEvent(
            event_type="user_created",
            user_id=created_user.user_id,
            action="create_user",
            result="success",
            details={"username": username, "roles": roles}
        ))

        return created_user

    async def get_user(self, user_id: str) -> Optional[User]:
        """Получить пользователя."""
        return await self.user_store.get_user(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени."""
        return await self.user_store.get_user_by_username(username)

    async def assign_role(self, user_id: str, role_name: str, assigned_by: Optional[str] = None) -> bool:
        """Назначить роль пользователю."""
        user = await self.user_store.get_user(user_id)
        if not user:
            return False

        # Проверяем, что роль существует
        role = await self.role_store.get_role(role_name)
        if not role:
            return False

        if role_name not in user.roles:
            user.roles.append(role_name)
            await self.user_store.update_user(user)

            await self.audit_store.log_event(SecurityAuditEvent(
                event_type="role_assigned",
                user_id=user_id,
                action="assign_role",
                result="success",
                details={"role": role_name, "assigned_by": assigned_by}
            ))

        return True

    async def revoke_role(self, user_id: str, role_name: str, revoked_by: Optional[str] = None) -> bool:
        """Отозвать роль у пользователя."""
        user = await self.user_store.get_user(user_id)
        if not user:
            return False

        if role_name in user.roles:
            user.roles.remove(role_name)
            await self.user_store.update_user(user)

            await self.audit_store.log_event(SecurityAuditEvent(
                event_type="role_revoked",
                user_id=user_id,
                action="revoke_role",
                result="success",
                details={"role": role_name, "revoked_by": revoked_by}
            ))

        return True

    # Session management

    async def create_session(
        self,
        user_id: str,
        auth_method: AuthenticationMethod,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Session:
        """Создать сессию пользователя."""
        user = await self.user_store.get_user(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        expires_at = datetime.utcnow() + timedelta(hours=self.session_timeout_hours)

        session = Session(
            user_id=user_id,
            tenant_id=tenant_id or user.tenant_id,
            auth_method=auth_method,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        created_session = await self.session_store.create_session(session)

        # Update user last login
        user.last_login = datetime.utcnow()
        await self.user_store.update_user(user)

        await self.audit_store.log_event(SecurityAuditEvent(
            event_type="session_created",
            user_id=user_id,
            session_id=created_session.session_id,
            action="login",
            result="success",
            details={"auth_method": auth_method.value},
            ip_address=ip_address
        ))

        return created_session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Получить сессию."""
        return await self.session_store.get_session(session_id)

    async def invalidate_session(self, session_id: str, reason: str = "logout") -> bool:
        """Аннулировать сессию."""
        session = await self.session_store.get_session(session_id)
        if not session:
            return False

        deleted = await self.session_store.delete_session(session_id)

        if deleted:
            await self.audit_store.log_event(SecurityAuditEvent(
                event_type="session_invalidated",
                user_id=session.user_id,
                session_id=session_id,
                action="logout",
                result="success",
                details={"reason": reason}
            ))

        return deleted

    async def invalidate_user_sessions(self, user_id: str, reason: str = "security") -> int:
        """Аннулировать все сессии пользователя."""
        sessions = await self.session_store.get_user_sessions(user_id)
        count = 0

        for session in sessions:
            if await self.session_store.delete_session(session.session_id):
                count += 1

        if count > 0:
            await self.audit_store.log_event(SecurityAuditEvent(
                event_type="user_sessions_invalidated",
                user_id=user_id,
                action="invalidate_sessions",
                result="success",
                details={"count": count, "reason": reason}
            ))

        return count

    # Authorization

    async def check_permission(
        self,
        user_id: str,
        permission: PermissionType,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AuthorizationResponse:
        """Проверить разрешение пользователя."""
        user = await self.user_store.get_user(user_id)
        if not user or not user.is_active:
            await self._log_authorization_event(
                user_id, permission, resource, "denied", "user_not_found", session_id
            )
            return AuthorizationResponse(
                granted=False,
                reason="User not found or inactive"
            )

        # Проверяем сессию если указана
        if session_id:
            session = await self.session_store.get_session(session_id)
            if not session or not session.is_active:
                await self._log_authorization_event(
                    user_id, permission, resource, "denied", "invalid_session", session_id
                )
                return AuthorizationResponse(
                    granted=False,
                    reason="Invalid or expired session"
                )

            # Обновляем активность сессии
            session.last_activity = datetime.utcnow()
            await self.session_store.update_session(session)

        # Получаем все разрешения пользователя
        user_permissions = await self._get_user_permissions(user)

        # Проверяем наличие разрешения
        for perm in user_permissions:
            if perm.name == permission:
                # Проверяем ресурс если указан
                if resource and perm.resource and perm.resource != resource:
                    continue

                # Проверяем условия если есть
                if perm.conditions and context:
                    if not self._check_conditions(perm.conditions, context):
                        continue

                await self._log_authorization_event(
                    user_id, permission, resource, "granted", "permission_found", session_id
                )
                return AuthorizationResponse(granted=True)

        await self._log_authorization_event(
            user_id, permission, resource, "denied", "permission_not_found", session_id
        )
        return AuthorizationResponse(
            granted=False,
            reason="Permission not granted"
        )

    async def _get_user_permissions(self, user: User) -> List[Permission]:
        """Получить все разрешения пользователя (включая наследованные от ролей)."""
        permissions = []
        processed_roles = set()

        async def collect_role_permissions(role_name: str):
            if role_name in processed_roles:
                return
            processed_roles.add(role_name)

            role = await self.role_store.get_role(role_name)
            if not role or not role.is_active:
                return

            # Добавляем разрешения роли
            permissions.extend(role.permissions)

            # Рекурсивно обрабатываем родительские роли
            for parent_role in role.parent_roles:
                await collect_role_permissions(parent_role)

        # Собираем разрешения от всех ролей пользователя
        for role_name in user.roles:
            await collect_role_permissions(role_name)

        return permissions

    def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Проверить условия разрешения."""
        for key, expected_value in conditions.items():
            if key not in context:
                return False

            context_value = context[key]

            # Простая проверка равенства (можно расширить логикой)
            if isinstance(expected_value, list):
                if context_value not in expected_value:
                    return False
            elif context_value != expected_value:
                return False

        return True

    async def _log_authorization_event(
        self,
        user_id: str,
        permission: PermissionType,
        resource: Optional[str],
        result: str,
        reason: str,
        session_id: Optional[str] = None
    ):
        """Логировать событие авторизации."""
        await self.audit_store.log_event(SecurityAuditEvent(
            event_type="authorization",
            user_id=user_id,
            session_id=session_id,
            resource=resource,
            action=permission.value,
            result=result,
            details={"permission": permission.value, "reason": reason}
        ))

    # Role management

    async def create_role(
        self,
        name: str,
        role_type: RoleType,
        permissions: List[PermissionType],
        parent_roles: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Role:
        """Создать роль."""
        role = Role(
            name=name,
            type=role_type,
            permissions=[Permission(name=perm) for perm in permissions],
            parent_roles=parent_roles or [],
            description=description
        )

        return await self.role_store.create_role(role)

    async def get_role(self, role_name: str) -> Optional[Role]:
        """Получить роль."""
        return await self.role_store.get_role(role_name)

    async def list_roles(self) -> List[Role]:
        """Список ролей."""
        return await self.role_store.list_roles()

    # Audit and monitoring

    async def get_audit_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityAuditEvent]:
        """Получить события аудита."""
        return await self.audit_store.get_events(
            user_id=user_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

    async def get_user_activity(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Получить активность пользователя."""
        start_time = datetime.utcnow() - timedelta(days=days)
        events = await self.audit_store.get_events(
            user_id=user_id,
            start_time=start_time,
            limit=1000
        )

        # Агрегируем статистику
        stats = {
            "total_events": len(events),
            "successful_logins": len([e for e in events if e.event_type == "session_created" and e.result == "success"]),
            "failed_logins": len([e for e in events if e.event_type == "session_created" and e.result == "failure"]),
            "permission_denials": len([e for e in events if e.event_type == "authorization" and e.result == "denied"]),
            "last_activity": max([e.timestamp for e in events]) if events else None,
            "unique_days": len(set(e.timestamp.date() for e in events)),
            "event_types": {}
        }

        # Подсчет по типам событий
        for event in events:
            event_type = event.event_type
            if event_type not in stats["event_types"]:
                stats["event_types"][event_type] = 0
            stats["event_types"][event_type] += 1

        return stats