#!/usr/bin/env python3
"""
Security & RBAC System Demo для mega_agent_pro.

Демонстрирует:
1. Создание пользователей и ролей
2. Управление разрешениями
3. Сессии и аутентификацию
4. Проверку авторизации
5. Rate limiting и security features
6. Audit logging
7. Multi-factor authentication
8. API key management

Запуск:
    python security_rbac_demo.py
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.security import (
    PermissionType,
    RoleType,
    AuthenticationMethod,
    create_default_rbac_manager,
    create_testing_rbac_manager,
    initialize_default_users,
)


async def demo_user_management():
    """Демонстрация управления пользователями."""
    print("👥 === User Management Demo ===\n")

    rbac_manager = create_default_rbac_manager()

    # Создаем пользователей
    print("📝 Creating users...")
    users = await initialize_default_users(rbac_manager)

    for username, user in users.items():
        print(f"   ✅ {username}: {user.user_id} (roles: {user.roles})")

    print()

    # Демонстрируем получение пользователя
    lawyer = await rbac_manager.get_user_by_username("lawyer")
    if lawyer:
        print(f"🔍 Found lawyer: {lawyer.username} ({lawyer.user_id})")
        print(f"   📧 Email: {lawyer.email}")
        print(f"   🏢 Tenant: {lawyer.tenant_id}")
        print(f"   🎭 Roles: {lawyer.roles}")
        print()

    # Демонстрируем назначение роли
    print("🎭 Role assignment demo...")
    paralegal = await rbac_manager.get_user_by_username("paralegal")
    if paralegal:
        # Добавляем дополнительную роль
        success = await rbac_manager.assign_role(paralegal.user_id, "viewer", "admin")
        print(f"   ✅ Assigned 'viewer' role to paralegal: {success}")

        # Проверяем обновленные роли
        updated_paralegal = await rbac_manager.get_user(paralegal.user_id)
        print(f"   📋 Updated roles: {updated_paralegal.roles}")

    print()


async def demo_role_management():
    """Демонстрация управления ролями."""
    print("🎭 === Role Management Demo ===\n")

    rbac_manager = create_default_rbac_manager()

    # Показываем все роли
    print("📋 Available roles:")
    roles = await rbac_manager.list_roles()
    for role in roles:
        print(f"   🎯 {role.name} ({role.type.value})")
        print(f"      📝 {role.description}")
        print(f"      🔐 Permissions: {len(role.permissions)}")
        for perm in role.permissions[:3]:  # Показываем первые 3 разрешения
            print(f"         - {perm.name.value}")
        if len(role.permissions) > 3:
            print(f"         ... and {len(role.permissions) - 3} more")
        print()

    # Создаем кастомную роль
    print("🆕 Creating custom role...")
    custom_permissions = [
        PermissionType.CASE_READ,
        PermissionType.DOCUMENT_READ,
        PermissionType.DATA_SEARCH
    ]

    custom_role = await rbac_manager.create_role(
        name="custom_researcher",
        role_type=RoleType.VIEWER,
        permissions=custom_permissions,
        description="Custom role for research tasks"
    )

    print(f"   ✅ Created custom role: {custom_role.name}")
    print(f"   🔐 With permissions: {[p.value for p in custom_permissions]}")
    print()


async def demo_session_management():
    """Демонстрация управления сессиями."""
    print("🔐 === Session Management Demo ===\n")

    rbac_manager = create_default_rbac_manager()
    users = await initialize_default_users(rbac_manager)

    lawyer = users["lawyer"]

    # Создаем сессию
    print("🚀 Creating session...")
    session = await rbac_manager.create_session(
        user_id=lawyer.user_id,
        auth_method=AuthenticationMethod.PASSWORD,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Demo Browser)"
    )

    print(f"   ✅ Session created: {session.session_id}")
    print(f"   ⏰ Expires at: {session.expires_at}")
    print(f"   🌐 IP: {session.ip_address}")
    print()

    # Проверяем сессию
    print("🔍 Verifying session...")
    retrieved_session = await rbac_manager.get_session(session.session_id)
    if retrieved_session:
        print(f"   ✅ Session valid: {retrieved_session.is_active}")
        print(f"   👤 User: {retrieved_session.user_id}")
        print(f"   ⏱️ Last activity: {retrieved_session.last_activity}")
    print()

    # Создаем еще несколько сессий для демонстрации
    session2 = await rbac_manager.create_session(
        user_id=lawyer.user_id,
        auth_method=AuthenticationMethod.API_KEY,
        ip_address="10.0.0.50"
    )

    # Показываем все сессии пользователя
    print("📊 User sessions:")
    user_sessions = await rbac_manager.session_store.get_user_sessions(lawyer.user_id)
    for sess in user_sessions:
        print(f"   🔑 {sess.session_id[:8]}... ({sess.auth_method.value}) - {sess.ip_address}")

    print()

    # Аннулируем сессию
    print("❌ Invalidating session...")
    success = await rbac_manager.invalidate_session(session.session_id, "demo logout")
    print(f"   ✅ Session invalidated: {success}")

    # Аннулируем все сессии пользователя
    print("🧹 Invalidating all user sessions...")
    count = await rbac_manager.invalidate_user_sessions(lawyer.user_id, "security reset")
    print(f"   ✅ Invalidated {count} sessions")
    print()


async def demo_authorization():
    """Демонстрация проверки авторизации."""
    print("🛡️ === Authorization Demo ===\n")

    rbac_manager = create_default_rbac_manager()
    users = await initialize_default_users(rbac_manager)

    # Тестируем разрешения для разных ролей
    test_cases = [
        ("lawyer", PermissionType.CASE_CREATE, "Should be allowed"),
        ("lawyer", PermissionType.SYSTEM_CONFIG, "Should be denied"),
        ("client", PermissionType.CASE_READ, "Should be allowed"),
        ("client", PermissionType.CASE_DELETE, "Should be denied"),
        ("admin", PermissionType.USER_CREATE, "Should be allowed"),
        ("viewer", PermissionType.DOCUMENT_UPDATE, "Should be denied"),
        ("super_admin", PermissionType.SYSTEM_BACKUP, "Should be allowed"),
    ]

    for username, permission, expected in test_cases:
        user = users[username]
        response = await rbac_manager.check_permission(
            user_id=user.user_id,
            permission=permission
        )

        status = "✅ GRANTED" if response.granted else "❌ DENIED"
        print(f"   {status} {username:12} {permission.value:20} ({expected})")
        if response.reason:
            print(f"      💭 Reason: {response.reason}")

    print()

    # Демонстрируем проверку с контекстом
    print("🎯 Context-based authorization demo...")
    lawyer = users["lawyer"]

    # Проверяем доступ к конкретному ресурсу
    response = await rbac_manager.check_permission(
        user_id=lawyer.user_id,
        permission=PermissionType.CASE_READ,
        resource="case_123",
        context={"case_id": "case_123", "assigned_lawyer": lawyer.user_id}
    )

    status = "✅ GRANTED" if response.granted else "❌ DENIED"
    print(f"   {status} Lawyer access to specific case")
    print()


async def demo_authentication():
    """Демонстрация аутентификации."""
    print("🔑 === Authentication Demo ===\n")

    # Создаем authentication manager с тестовыми настройками
    rbac_manager, auth_manager = create_testing_rbac_manager()

    # Демонстрируем валидацию пароля
    print("🔐 Password validation demo...")
    test_passwords = [
        "123",           # Слишком короткий
        "password",      # Простой
        "Password123!",  # Хороший
    ]

    for password in test_passwords:
        is_valid, errors = auth_manager.password_validator.validate(password)
        status = "✅" if is_valid else "❌"
        print(f"   {status} '{password}': {'Valid' if is_valid else ', '.join(errors)}")

    print()

    # Демонстрируем хеширование пароля
    print("🔒 Password hashing demo...")
    password = "SecurePassword123!"
    hash_result = auth_manager.hash_password(password)

    print(f"   📝 Password: {password}")
    print(f"   🧂 Salt: {hash_result.salt[:16]}...")
    print(f"   #️⃣ Hash: {hash_result.hash[:32]}...")
    print(f"   🔧 Algorithm: {hash_result.algorithm}")
    print(f"   🔄 Iterations: {hash_result.iterations}")

    # Проверяем пароль
    is_correct = auth_manager.verify_password(password, hash_result)
    is_wrong = auth_manager.verify_password("WrongPassword", hash_result)

    print(f"   ✅ Correct password verification: {is_correct}")
    print(f"   ❌ Wrong password verification: {is_wrong}")
    print()

    # Демонстрируем JWT токены (если доступны)
    if auth_manager.jwt_manager:
        print("🎫 JWT token demo...")
        user_id = "test_user_123"

        # Создаем токены
        token_pair = auth_manager.jwt_manager.create_token_pair(user_id)
        print(f"   🎟️ Access token: {token_pair.access_token[:50]}...")
        print(f"   🔄 Refresh token: {token_pair.refresh_token[:50]}...")
        print(f"   ⏰ Expires in: {token_pair.expires_in} seconds")

        # Проверяем токен
        payload = auth_manager.jwt_manager.verify_token(token_pair.access_token)
        if payload:
            print(f"   ✅ Token valid for user: {payload.get('sub')}")
            print(f"   🎯 Token type: {payload.get('type')}")

        print()

    # Демонстрируем API ключи
    print("🗝️ API key demo...")
    api_key = auth_manager.api_key_manager.generate_key(
        user_id="test_user_123",
        name="Demo API Key",
        permissions=["case:read", "document:read"]
    )

    print(f"   🔑 Generated key: {api_key.key}")
    print(f"   📝 Name: {api_key.name}")
    print(f"   🔐 Permissions: {api_key.permissions}")
    print(f"   ⏰ Expires: {api_key.expires_at}")

    # Проверяем ключ
    verified_key = auth_manager.api_key_manager.verify_key(api_key.key)
    if verified_key:
        print("   ✅ Key verification successful")
        print(f"   👤 User ID: {verified_key.user_id}")
        print(f"   ⏱️ Last used: {verified_key.last_used}")

    print()


async def demo_rate_limiting():
    """Демонстрация rate limiting."""
    print("🚦 === Rate Limiting Demo ===\n")

    rbac_manager, auth_manager = create_testing_rbac_manager()
    rate_limiter = auth_manager.rate_limiter

    identifier = "demo_user"

    print("🔄 Testing rate limiting...")
    print(f"   Max attempts: {rate_limiter.config.max_attempts}")
    print(f"   Window: {rate_limiter.config.window_minutes} minutes")
    print(f"   Lockout: {rate_limiter.config.lockout_minutes} minutes")
    print()

    # Симулируем неудачные попытки
    for attempt in range(1, 8):
        allowed, locked_until = rate_limiter.is_allowed(identifier)

        if allowed:
            print(f"   Attempt {attempt}: ✅ Allowed")
            # Записываем неудачную попытку
            rate_limiter.record_attempt(identifier, success=False)
        else:
            print(f"   Attempt {attempt}: ❌ Blocked (locked until {locked_until})")

    print()

    # Демонстрируем сброс при успешной попытке
    print("🔓 Simulating successful authentication...")
    rate_limiter.record_attempt(identifier, success=True)

    allowed, _ = rate_limiter.is_allowed(identifier)
    print(f"   After successful auth: {'✅ Allowed' if allowed else '❌ Still blocked'}")
    print()


async def demo_audit_logging():
    """Демонстрация audit logging."""
    print("📋 === Audit Logging Demo ===\n")

    rbac_manager = create_default_rbac_manager()
    users = await initialize_default_users(rbac_manager)

    # Генерируем активность для демонстрации
    lawyer = users["lawyer"]
    client = users["client"]

    # Создаем сессии
    lawyer_session = await rbac_manager.create_session(
        user_id=lawyer.user_id,
        auth_method=AuthenticationMethod.PASSWORD,
        ip_address="192.168.1.100"
    )

    client_session = await rbac_manager.create_session(
        user_id=client.user_id,
        auth_method=AuthenticationMethod.API_KEY,
        ip_address="192.168.1.200"
    )

    # Проверяем несколько разрешений
    await rbac_manager.check_permission(
        user_id=lawyer.user_id,
        permission=PermissionType.CASE_CREATE,
        session_id=lawyer_session.session_id
    )

    await rbac_manager.check_permission(
        user_id=client.user_id,
        permission=PermissionType.CASE_DELETE,  # Должно быть отклонено
        session_id=client_session.session_id
    )

    # Показываем audit события
    print("📊 Recent audit events:")
    events = await rbac_manager.get_audit_events(limit=10)

    for event in events:
        print(f"   🕐 {event.timestamp.strftime('%H:%M:%S')} {event.event_type}")
        print(f"      👤 User: {event.user_id}")
        print(f"      🎯 Action: {event.action}")
        print(f"      📈 Result: {event.result}")
        if event.details:
            print(f"      📝 Details: {event.details}")
        print()

    # Показываем активность пользователя
    print("📈 User activity summary:")
    lawyer_activity = await rbac_manager.get_user_activity(lawyer.user_id, days=1)

    print("   👤 Lawyer activity:")
    print(f"      📊 Total events: {lawyer_activity['total_events']}")
    print(f"      ✅ Successful logins: {lawyer_activity['successful_logins']}")
    print(f"      ❌ Permission denials: {lawyer_activity['permission_denials']}")
    print(f"      📅 Unique days: {lawyer_activity['unique_days']}")
    print(f"      ⏰ Last activity: {lawyer_activity['last_activity']}")

    if lawyer_activity['event_types']:
        print("      📋 Event types:")
        for event_type, count in lawyer_activity['event_types'].items():
            print(f"         - {event_type}: {count}")

    print()


async def demo_multi_factor_auth():
    """Демонстрация multi-factor authentication."""
    print("🔐 === Multi-Factor Authentication Demo ===\n")

    rbac_manager, auth_manager = create_testing_rbac_manager()
    mfa = auth_manager.mfa

    user_id = "test_user_123"

    # Генерируем OTP секрет
    print("🔑 OTP Setup...")
    otp_secret = mfa.generate_otp_secret()
    print(f"   🔐 OTP Secret: {otp_secret}")

    # Генерируем backup коды
    backup_codes = mfa.generate_backup_codes(5)
    print(f"   🗝️ Backup codes: {backup_codes}")
    print()

    # Демонстрируем процесс верификации
    print("📱 Verification process...")

    # Начинаем верификацию
    verification_id = mfa.start_verification(user_id, "sms")
    print(f"   🚀 Started verification: {verification_id}")

    # В реальной системе код был бы отправлен пользователю
    # Для демонстрации получаем код из внутреннего состояния
    verification_data = mfa.pending_verifications.get(verification_id)
    if verification_data:
        demo_code = verification_data["code"]
        print(f"   📧 Verification code (demo): {demo_code}")

        # Проверяем код
        success = mfa.verify_code(verification_id, demo_code)
        print(f"   ✅ Code verification: {'Success' if success else 'Failed'}")

        # Пробуем неправильный код
        wrong_success = mfa.verify_code("invalid_id", "123456")
        print(f"   ❌ Wrong code verification: {'Success' if wrong_success else 'Failed'}")

    print()


async def main():
    """Главная функция демонстрации."""
    print("🛡️ MEGA AGENT PRO - Security & RBAC System Demo")
    print("=" * 60)
    print()

    try:
        # Демонстрируем различные аспекты системы безопасности
        await demo_user_management()
        await demo_role_management()
        await demo_session_management()
        await demo_authorization()
        await demo_authentication()
        await demo_rate_limiting()
        await demo_audit_logging()
        await demo_multi_factor_auth()

        print("✅ === Security Demo Complete ===")
        print()
        print("🎯 Key Features Demonstrated:")
        print("   ✅ User and role management")
        print("   ✅ Session management with timeout")
        print("   ✅ Fine-grained permission checking")
        print("   ✅ Password hashing and validation")
        print("   ✅ JWT token management")
        print("   ✅ API key generation and verification")
        print("   ✅ Rate limiting for brute force protection")
        print("   ✅ Comprehensive audit logging")
        print("   ✅ Multi-factor authentication support")
        print()
        print("🚀 Next Steps:")
        print("   1. Integrate with persistent storage (PostgreSQL, MongoDB)")
        print("   2. Add Redis for session and rate limiting storage")
        print("   3. Implement real OTP/SMS providers")
        print("   4. Add SSO integration (SAML, OAuth)")
        print("   5. Create middleware for automatic authorization checks")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())