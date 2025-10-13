from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application-level settings loaded from environment.

    This is a minimal scaffold to satisfy configuration requirements.
    """

    env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    jwt_secret_key: str | None = None

    # External services
    postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Observability
    tracing_enabled: bool = Field(default=False)
    tracing_exporter: str = Field(default="console")
    tracing_service_name: str = Field(default="megaagent-pro")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
