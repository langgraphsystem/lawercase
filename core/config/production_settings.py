"""Production-ready configuration management system.

This module provides:
- Environment-specific profiles (development, staging, production)
- Secure secrets management
- Feature flags system
- Configuration validation
- Hot-reload support
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
import os
from pathlib import Path
import secrets
from typing import Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str = Field(default="megaagent")
    postgres_password: SecretStr = Field(default=SecretStr("changeme"))
    postgres_db: str = Field(default="megaagent_pro")
    postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")

    # Connection pool
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1)
    pool_recycle: int = Field(default=3600, ge=60)

    @property
    def get_postgres_dsn(self) -> str:
        """Construct PostgreSQL DSN."""
        if self.postgres_dsn:
            return self.postgres_dsn

        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: SecretStr | None = Field(default=None)
    url: str | None = Field(default=None, alias="REDIS_URL")

    # Connection settings
    max_connections: int = Field(default=50, ge=1)
    socket_timeout: int = Field(default=5, ge=1)
    socket_connect_timeout: int = Field(default=5, ge=1)

    @property
    def get_redis_url(self) -> str:
        """Construct Redis URL."""
        if self.url:
            return self.url

        if self.password:
            return (
                f"redis://:{self.password.get_secret_value()}@" f"{self.host}:{self.port}/{self.db}"
            )
        return f"redis://{self.host}:{self.port}/{self.db}"


class PineconeSettings(BaseSettings):
    """Pinecone vector store configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PINECONE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: SecretStr | None = Field(default=None)
    environment: str | None = Field(default=None)
    index_name: str = Field(default="mega-agent-semantic")
    namespace: str | None = Field(default=None)


class R2Settings(BaseSettings):
    """Cloudflare R2 object storage configuration."""

    model_config = SettingsConfigDict(
        env_prefix="R2_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    account_id: str | None = Field(default=None)
    access_key_id: SecretStr | None = Field(default=None)
    secret_access_key: SecretStr | None = Field(default=None)
    bucket_name: str | None = Field(default=None)
    endpoint: str | None = Field(default=None)


class SecuritySettings(BaseSettings):
    """Security configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # JWT
    # WARNING: In production, jwt_secret_key MUST be set via environment variable (SECURITY_JWT_SECRET_KEY)
    # Auto-generation is only for development/testing. In distributed systems, all instances must share the same secret.
    jwt_secret_key: SecretStr | None = Field(default=None)
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60, ge=1)
    jwt_refresh_expiration_days: int = Field(default=7, ge=1)

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def generate_jwt_secret_if_missing(cls, v: SecretStr | None) -> SecretStr:
        """Generate JWT secret if not provided (development only)."""
        if v is None:
            # Auto-generate ONLY for development/testing
            import warnings

            warnings.warn(
                "JWT secret key is auto-generated. This is INSECURE for production. "
                "Set SECURITY_JWT_SECRET_KEY environment variable.",
                UserWarning,
                stacklevel=2,
            )
            return SecretStr(secrets.token_urlsafe(32))
        return v

    # API Keys
    api_key_length: int = Field(default=32, ge=16, le=64)
    api_key_prefix: str = Field(default="sk_")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_per_hour: int = Field(default=1000, ge=1)

    # CORS
    cors_enabled: bool = Field(default=True)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)

    # Encryption
    encryption_key: SecretStr | None = Field(default=None)


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider API Keys
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    cohere_api_key: SecretStr | None = Field(default=None, alias="COHERE_API_KEY")

    # Default models
    default_model: str = Field(default="gpt-4")
    fast_model: str = Field(default="gpt-3.5-turbo")
    embedding_model: str = Field(default="text-embedding-ada-002")

    # Request settings
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout_seconds: int = Field(default=60, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = Field(default=SecretStr(""), alias="TELEGRAM_BOT_TOKEN")
    allowed_users: str | None = Field(default=None, alias="TELEGRAM_ALLOWED_USERS")
    webhook_url: str | None = Field(default=None)
    webhook_secret: SecretStr | None = Field(default=None)

    def get_allowed_user_ids(self) -> list[int] | None:
        """Parse allowed user IDs from comma-separated string."""
        if not self.allowed_users:
            return None

        ids: list[int] = []
        for part in self.allowed_users.split(","):
            stripped = part.strip()
            if stripped:
                try:
                    ids.append(int(stripped))
                except ValueError:
                    continue
        return ids or None


class ObservabilitySettings(BaseSettings):
    """Observability and monitoring configuration."""

    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Tracing
    tracing_enabled: bool = Field(default=False)
    tracing_exporter: str = Field(default="console")
    tracing_service_name: str = Field(default="megaagent-pro")
    tracing_endpoint: str | None = Field(default=None)

    # Metrics
    metrics_enabled: bool = Field(default=False)
    metrics_port: int = Field(default=9090, ge=1024, le=65535)

    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_format: str = Field(default="json")
    log_file: Path | None = Field(default=None)
    log_rotation: str = Field(default="1 day")
    log_retention: str = Field(default="30 days")

    # Health checks
    health_check_enabled: bool = Field(default=True)
    health_check_interval: int = Field(default=30, ge=1)


class FeatureFlags(BaseSettings):
    """Feature flags for gradual rollout."""

    model_config = SettingsConfigDict(
        env_prefix="FEATURE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Agent features
    enable_self_correction: bool = Field(default=True)
    enable_evidence_analysis: bool = Field(default=True)
    enable_rag_pipeline: bool = Field(default=True)
    enable_workflow_orchestration: bool = Field(default=True)

    # LLM features
    enable_streaming: bool = Field(default=False)
    enable_function_calling: bool = Field(default=True)
    enable_vision: bool = Field(default=False)

    # Storage features
    enable_caching: bool = Field(default=True)
    enable_vector_store: bool = Field(default=True)
    enable_audit_logging: bool = Field(default=True)

    # API features
    enable_api_auth: bool = Field(default=True)
    enable_rate_limiting: bool = Field(default=True)
    enable_request_validation: bool = Field(default=True)

    # Experimental
    enable_experimental_features: bool = Field(default=False)


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Environment
    env: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    testing: bool = Field(default=False)

    # Application
    app_name: str = Field(default="MegaAgent Pro")
    app_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")
    docs_url: str | None = Field(default="/docs")
    redoc_url: str | None = Field(default="/redoc")

    # Paths
    tmp_dir: Path = Field(default=Path("tmp"))
    out_dir: Path = Field(default=Path("out"))
    data_dir: Path = Field(default=Path("data"))
    log_dir: Path = Field(default=Path("logs"))

    # File processing
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_file_types: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".txt"])

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    r2: R2Settings = Field(default_factory=R2Settings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @model_validator(mode="after")
    def validate_production_settings(self) -> AppSettings:
        """Validate production-specific requirements."""
        if self.env == Environment.PRODUCTION:
            # Ensure secure settings in production
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")

            if not self.security.jwt_secret_key.get_secret_value():
                raise ValueError("JWT secret key is required in production")

            # Strict CORS validation - must be explicit origins, not wildcards
            if "*" in self.security.cors_origins:
                raise ValueError(
                    "CORS wildcard (*) is not allowed in production. Specify explicit origins."
                )

            # Validate required API keys in production
            if (
                not self.llm.openai_api_key
                and not self.llm.anthropic_api_key
                and not self.llm.gemini_api_key
            ):
                raise ValueError(
                    "At least one LLM API key (OpenAI, Anthropic, or Gemini) is required in production"
                )

            if not self.pinecone.api_key or not self.pinecone.environment:
                raise ValueError("Pinecone API key and environment are required in production")

            if not (
                self.r2.bucket_name
                and self.r2.account_id
                and self.r2.access_key_id
                and self.r2.secret_access_key
            ):
                raise ValueError(
                    "R2 storage requires account id, bucket name, access key id, and secret in production"
                )

            # Validate database configuration
            if not self.database.postgres_dsn and not all(
                [
                    self.database.postgres_host,
                    self.database.postgres_user,
                    self.database.postgres_password.get_secret_value(),
                ]
            ):
                raise ValueError(
                    "Database configuration (postgres_dsn or host/user/password) is required in production"
                )

        return self

    @field_validator("tmp_dir", "out_dir", "data_dir", "log_dir")
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging."""
        return self.env == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        """Check if running tests."""
        return self.env == Environment.TEST or self.testing

    def get_log_config(self) -> dict[str, Any]:
        """Get logging configuration."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": ("json" if self.observability.log_format == "json" else "default"),
                    "stream": "ext://sys.stdout",
                },
                "file": (
                    {
                        "class": "logging.handlers.TimedRotatingFileHandler",
                        "formatter": "json",
                        "filename": str(self.log_dir / "app.log"),
                        "when": "midnight",
                        "interval": 1,
                        "backupCount": 30,
                    }
                    if self.observability.log_file
                    else None
                ),
            },
            "root": {
                "level": self.observability.log_level.value,
                "handlers": (["console", "file"] if self.observability.log_file else ["console"]),
            },
        }


# Singleton pattern for settings
_settings: AppSettings | None = None


@lru_cache
def get_settings() -> AppSettings:
    """Get application settings (cached singleton)."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reload_settings() -> AppSettings:
    """Force reload settings (useful for testing)."""
    global _settings
    get_settings.cache_clear()
    _settings = AppSettings()
    return _settings


# Environment-specific presets
def get_development_settings() -> AppSettings:
    """Get development environment settings."""
    os.environ["ENV"] = "development"
    os.environ["DEBUG"] = "true"
    os.environ["OBSERVABILITY_LOG_LEVEL"] = "DEBUG"
    return reload_settings()


def get_staging_settings() -> AppSettings:
    """Get staging environment settings."""
    os.environ["ENV"] = "staging"
    os.environ["DEBUG"] = "false"
    os.environ["OBSERVABILITY_LOG_LEVEL"] = "INFO"
    return reload_settings()


def get_production_settings() -> AppSettings:
    """Get production environment settings."""
    os.environ["ENV"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["OBSERVABILITY_LOG_LEVEL"] = "WARNING"
    os.environ["FEATURE_ENABLE_EXPERIMENTAL_FEATURES"] = "false"
    return reload_settings()


def get_test_settings() -> AppSettings:
    """Get test environment settings."""
    os.environ["ENV"] = "test"
    os.environ["DEBUG"] = "true"
    os.environ["TESTING"] = "true"
    return reload_settings()
