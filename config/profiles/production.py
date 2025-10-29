"""Production configuration profile helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.secrets_manager import secrets_manager
from core.config.production_settings import (AppSettings,
                                             get_production_settings)
from core.security.config import SecurityConfig


@dataclass(slots=True)
class ProductionProfile:
    """Snapshot of production-ready configuration."""

    settings: AppSettings
    security: SecurityConfig
    secrets: dict[str, Any]


def load_production_profile() -> ProductionProfile:
    """Load production settings, security configuration, and secrets snapshot."""
    settings = get_production_settings()
    security = SecurityConfig()
    secrets = {
        "PINECONE_API_KEY": bool(secrets_manager.get("PINECONE_API_KEY")),
        "R2_BUCKET_NAME": secrets_manager.get("R2_BUCKET_NAME"),
        "LLM_OPENAI_API_KEY": bool(secrets_manager.get("OPENAI_API_KEY")),
        "LLM_ANTHROPIC_API_KEY": bool(secrets_manager.get("ANTHROPIC_API_KEY")),
        "LLM_GEMINI_API_KEY": bool(secrets_manager.get("GEMINI_API_KEY")),
    }
    return ProductionProfile(settings=settings, security=security, secrets=secrets)


__all__ = ["ProductionProfile", "load_production_profile"]
