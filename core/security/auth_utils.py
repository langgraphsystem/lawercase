"""
Authentication utilities для mega_agent_pro RBAC system.

Обеспечивает:
- Password hashing и verification
- JWT token generation и validation
- API key management
- Multi-factor authentication support
- Rate limiting для защиты от brute force атак
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class PasswordConfig(BaseModel):
    """Конфигурация для паролей."""
    min_length: int = Field(8, description="Минимальная длина пароля")
    require_uppercase: bool = Field(True, description="Требовать заглавные буквы")
    require_lowercase: bool = Field(True, description="Требовать строчные буквы")
    require_digits: bool = Field(True, description="Требовать цифры")
    require_special: bool = Field(True, description="Требовать специальные символы")
    special_chars: str = Field("!@#$%^&*()_+-=[]{}|;:,.<>?", description="Специальные символы")


class JWTConfig(BaseModel):
    """Конфигурация для JWT токенов."""
    secret_key: str = Field(..., description="Секретный ключ для подписи")
    algorithm: str = Field("HS256", description="Алгоритм подписи")
    access_token_expire_minutes: int = Field(30, description="Время жизни access токена")
    refresh_token_expire_days: int = Field(7, description="Время жизни refresh токена")
    issuer: str = Field("mega_agent_pro", description="Издатель токена")


class APIKeyConfig(BaseModel):
    """Конфигурация для API ключей."""
    prefix: str = Field("map_", description="Префикс для API ключей")
    length: int = Field(32, description="Длина ключа")
    expire_days: Optional[int] = Field(None, description="Время жизни ключа в днях")


class RateLimitConfig(BaseModel):
    """Конфигурация для rate limiting."""
    max_attempts: int = Field(5, description="Максимальное количество попыток")
    window_minutes: int = Field(15, description="Временное окно в минутах")
    lockout_minutes: int = Field(30, description="Время блокировки в минутах")


class HashResult(BaseModel):
    """Результат хеширования пароля."""
    hash: str = Field(..., description="Хеш пароля")
    salt: str = Field(..., description="Соль")
    algorithm: str = Field(..., description="Алгоритм хеширования")
    iterations: int = Field(..., description="Количество итераций")


class TokenPair(BaseModel):
    """Пара токенов."""
    access_token: str = Field(..., description="Access токен")
    refresh_token: str = Field(..., description="Refresh токен")
    token_type: str = Field("bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access токена в секундах")


class APIKey(BaseModel):
    """API ключ."""
    key_id: str = Field(..., description="ID ключа")
    key: str = Field(..., description="API ключ")
    user_id: str = Field(..., description="ID пользователя")
    name: str = Field(..., description="Название ключа")
    permissions: list[str] = Field(default_factory=list, description="Разрешения ключа")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Время истечения")
    last_used: Optional[datetime] = Field(None, description="Последнее использование")
    is_active: bool = Field(True, description="Активен ли ключ")


class PasswordValidator:
    """Валидатор паролей."""

    def __init__(self, config: PasswordConfig = None):
        self.config = config or PasswordConfig()

    def validate(self, password: str) -> Tuple[bool, list[str]]:
        """Валидировать пароль. Возвращает (is_valid, errors)."""
        errors = []

        if len(password) < self.config.min_length:
            errors.append(f"Password must be at least {self.config.min_length} characters long")

        if self.config.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if self.config.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if self.config.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if self.config.require_special and not any(c in self.config.special_chars for c in password):
            errors.append(f"Password must contain at least one special character: {self.config.special_chars}")

        return len(errors) == 0, errors

    def generate_password(self, length: int = 12) -> str:
        """Сгенерировать безопасный пароль."""
        chars = ""
        password = ""

        # Обеспечиваем наличие требуемых символов
        if self.config.require_lowercase:
            chars += "abcdefghijklmnopqrstuvwxyz"
            password += secrets.choice("abcdefghijklmnopqrstuvwxyz")

        if self.config.require_uppercase:
            chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            password += secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        if self.config.require_digits:
            chars += "0123456789"
            password += secrets.choice("0123456789")

        if self.config.require_special:
            chars += self.config.special_chars
            password += secrets.choice(self.config.special_chars)

        # Заполняем оставшуюся длину
        for _ in range(length - len(password)):
            password += secrets.choice(chars)

        # Перемешиваем символы
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return ''.join(password_list)


class PasswordHasher:
    """Хеширование паролей с использованием PBKDF2."""

    def __init__(self, iterations: int = 100000):
        self.iterations = iterations

    def hash_password(self, password: str, salt: Optional[str] = None) -> HashResult:
        """Хешировать пароль."""
        if salt is None:
            salt = secrets.token_hex(32)

        # Используем PBKDF2 с SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            self.iterations
        )

        return HashResult(
            hash=password_hash.hex(),
            salt=salt,
            algorithm="pbkdf2_sha256",
            iterations=self.iterations
        )

    def verify_password(self, password: str, hash_result: HashResult) -> bool:
        """Проверить пароль."""
        # Воссоздаем хеш с теми же параметрами
        test_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            hash_result.salt.encode('utf-8'),
            hash_result.iterations
        )

        # Используем hmac.compare_digest для защиты от timing атак
        return hmac.compare_digest(hash_result.hash, test_hash.hex())


class JWTManager:
    """Менеджер JWT токенов."""

    def __init__(self, config: JWTConfig):
        if not JWT_AVAILABLE:
            raise ImportError("PyJWT library is required for JWT functionality")
        self.config = config

    def create_access_token(self, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
        """Создать access токен."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "iss": self.config.issuer,
            "type": "access"
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_refresh_token(self, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
        """Создать refresh токен."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "iss": self.config.issuer,
            "type": "refresh"
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_token_pair(self, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> TokenPair:
        """Создать пару токенов."""
        access_token = self.create_access_token(user_id, extra_claims)
        refresh_token = self.create_refresh_token(user_id, extra_claims)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60
        )

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Проверить токен."""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer
            )

            # Проверяем тип токена
            if payload.get("type") != token_type:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Обновить access токен используя refresh токен."""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return self.create_access_token(user_id)


class APIKeyManager:
    """Менеджер API ключей."""

    def __init__(self, config: APIKeyConfig = None):
        self.config = config or APIKeyConfig()
        self.keys: Dict[str, APIKey] = {}  # key -> APIKey

    def generate_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[list[str]] = None,
        expire_days: Optional[int] = None
    ) -> APIKey:
        """Сгенерировать API ключ."""
        key_id = str(secrets.token_hex(16))
        key = f"{self.config.prefix}{secrets.token_urlsafe(self.config.length)}"

        expires_at = None
        if expire_days or self.config.expire_days:
            days = expire_days or self.config.expire_days
            expires_at = datetime.utcnow() + timedelta(days=days)

        api_key = APIKey(
            key_id=key_id,
            key=key,
            user_id=user_id,
            name=name,
            permissions=permissions or [],
            expires_at=expires_at
        )

        self.keys[key] = api_key
        return api_key

    def verify_key(self, key: str) -> Optional[APIKey]:
        """Проверить API ключ."""
        api_key = self.keys.get(key)
        if not api_key:
            return None

        if not api_key.is_active:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Обновляем время последнего использования
        api_key.last_used = datetime.utcnow()
        return api_key

    def revoke_key(self, key: str) -> bool:
        """Отозвать API ключ."""
        api_key = self.keys.get(key)
        if not api_key:
            return False

        api_key.is_active = False
        return True

    def list_user_keys(self, user_id: str) -> list[APIKey]:
        """Список ключей пользователя."""
        return [key for key in self.keys.values() if key.user_id == user_id]


class RateLimiter:
    """Rate limiter для защиты от brute force атак."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.attempts: Dict[str, list[datetime]] = {}  # identifier -> list of attempt times
        self.lockouts: Dict[str, datetime] = {}  # identifier -> lockout until time

    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[datetime]]:
        """Проверить, разрешен ли запрос. Возвращает (allowed, locked_until)."""
        now = datetime.utcnow()

        # Проверяем блокировку
        if identifier in self.lockouts:
            lockout_until = self.lockouts[identifier]
            if now < lockout_until:
                return False, lockout_until
            else:
                # Блокировка истекла
                del self.lockouts[identifier]

        # Очищаем старые попытки
        window_start = now - timedelta(minutes=self.config.window_minutes)
        if identifier in self.attempts:
            self.attempts[identifier] = [
                attempt for attempt in self.attempts[identifier]
                if attempt > window_start
            ]

        # Проверяем количество попыток
        current_attempts = len(self.attempts.get(identifier, []))
        if current_attempts >= self.config.max_attempts:
            # Блокируем
            lockout_until = now + timedelta(minutes=self.config.lockout_minutes)
            self.lockouts[identifier] = lockout_until
            return False, lockout_until

        return True, None

    def record_attempt(self, identifier: str, success: bool = False) -> None:
        """Записать попытку."""
        now = datetime.utcnow()

        if success:
            # При успешной попытке очищаем историю
            if identifier in self.attempts:
                del self.attempts[identifier]
            if identifier in self.lockouts:
                del self.lockouts[identifier]
        else:
            # Записываем неудачную попытку
            if identifier not in self.attempts:
                self.attempts[identifier] = []
            self.attempts[identifier].append(now)

    def reset_attempts(self, identifier: str) -> None:
        """Сбросить попытки для идентификатора."""
        if identifier in self.attempts:
            del self.attempts[identifier]
        if identifier in self.lockouts:
            del self.lockouts[identifier]


class MultiFactorAuth:
    """Multi-factor authentication support."""

    def __init__(self):
        self.pending_verifications: Dict[str, Dict[str, Any]] = {}

    def generate_otp_secret(self) -> str:
        """Сгенерировать секрет для OTP."""
        return secrets.token_hex(20)

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """Сгенерировать backup коды."""
        return [secrets.token_hex(8) for _ in range(count)]

    def start_verification(self, user_id: str, method: str) -> str:
        """Начать процесс верификации. Возвращает verification_id."""
        verification_id = str(secrets.token_hex(16))
        verification_code = str(secrets.randbelow(1000000)).zfill(6)

        self.pending_verifications[verification_id] = {
            "user_id": user_id,
            "method": method,
            "code": verification_code,
            "created_at": datetime.utcnow(),
            "attempts": 0
        }

        return verification_id

    def verify_code(self, verification_id: str, code: str) -> bool:
        """Проверить код верификации."""
        verification = self.pending_verifications.get(verification_id)
        if not verification:
            return False

        # Проверяем время жизни (5 минут)
        if datetime.utcnow() - verification["created_at"] > timedelta(minutes=5):
            del self.pending_verifications[verification_id]
            return False

        # Проверяем количество попыток
        verification["attempts"] += 1
        if verification["attempts"] > 3:
            del self.pending_verifications[verification_id]
            return False

        # Проверяем код
        if verification["code"] == code:
            del self.pending_verifications[verification_id]
            return True

        return False


class AuthenticationManager:
    """Основной менеджер аутентификации."""

    def __init__(
        self,
        password_config: Optional[PasswordConfig] = None,
        jwt_config: Optional[JWTConfig] = None,
        api_key_config: Optional[APIKeyConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        self.password_validator = PasswordValidator(password_config)
        self.password_hasher = PasswordHasher()
        self.rate_limiter = RateLimiter(rate_limit_config)
        self.mfa = MultiFactorAuth()

        if jwt_config:
            self.jwt_manager = JWTManager(jwt_config)
        else:
            self.jwt_manager = None

        self.api_key_manager = APIKeyManager(api_key_config)

    def hash_password(self, password: str) -> HashResult:
        """Хешировать пароль."""
        is_valid, errors = self.password_validator.validate(password)
        if not is_valid:
            raise ValueError(f"Password validation failed: {', '.join(errors)}")

        return self.password_hasher.hash_password(password)

    def verify_password(self, password: str, hash_result: HashResult) -> bool:
        """Проверить пароль."""
        return self.password_hasher.verify_password(password, hash_result)

    def authenticate_user(
        self,
        identifier: str,  # username, email, или API key
        credential: str,  # password или пустая строка для API key
        auth_method: str = "password"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Аутентифицировать пользователя.
        Возвращает (success, user_id, error_message).
        """
        # Проверяем rate limiting
        allowed, locked_until = self.rate_limiter.is_allowed(identifier)
        if not allowed:
            lockout_msg = f"Account locked until {locked_until}" if locked_until else "Too many attempts"
            return False, None, lockout_msg

        try:
            if auth_method == "api_key":
                # Проверяем API ключ
                api_key = self.api_key_manager.verify_key(identifier)
                if api_key:
                    self.rate_limiter.record_attempt(identifier, success=True)
                    return True, api_key.user_id, None
                else:
                    self.rate_limiter.record_attempt(identifier, success=False)
                    return False, None, "Invalid API key"

            elif auth_method == "password":
                # Здесь должна быть логика проверки пароля с базой данных
                # Для демонстрации возвращаем ошибку
                self.rate_limiter.record_attempt(identifier, success=False)
                return False, None, "Password authentication not implemented in this demo"

            else:
                return False, None, f"Unsupported authentication method: {auth_method}"

        except Exception as e:
            self.rate_limiter.record_attempt(identifier, success=False)
            return False, None, f"Authentication error: {str(e)}"