from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application-level settings loaded from environment."""

    env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    jwt_secret_key: str | None = Field(default=None)

    postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")
    redis_url: str = Field(default="redis://localhost:6379/0")

    doc_raptor_api_key: str = Field(default="", alias="DOC_RAPTOR_API_KEY")
    adobe_ocr_api_key: str = Field(default="", alias="ADOBE_OCR_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    eb1a_pdf_max_mb: int | None = Field(default=None, alias="EB1A_PDF_MAX_MB")
    tmp_dir: Path = Field(default=Path("tmp"), alias="TMP_DIR")
    out_dir: Path = Field(default=Path("out"), alias="OUT_DIR")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_users: str | None = Field(default=None, alias="TELEGRAM_ALLOWED_USERS")

    tracing_enabled: bool = Field(default=False)
    tracing_exporter: str = Field(default="console")
    tracing_service_name: str = Field(default="megaagent-pro")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }

    @property
    def tmp_path(self) -> Path:
        return self.tmp_dir

    @property
    def output_path(self) -> Path:
        return self.out_dir

    def allowed_user_ids(self) -> list[int] | None:
        if not self.telegram_allowed_users:
            return None
        ids: list[int] = []
        for part in self.telegram_allowed_users.split(","):
            stripped_part = part.strip()
            if stripped_part:
                try:
                    ids.append(int(stripped_part))
                except ValueError:
                    continue
        return ids or None


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
