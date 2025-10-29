"""Configuration management for mega_agent_pro.

Provides two configuration systems:
1. Simple Settings (core.config.get_settings) - Basic, backward-compatible
2. Production Settings (core.config.get_production_settings) - Comprehensive, production-ready

Usage:
    # Simple settings (backward compatible)
    from core.config import get_settings
    settings = get_settings()

    # Production settings (comprehensive)
    from core.config import get_production_settings
    settings = get_production_settings()
"""

from __future__ import annotations

import os

from pydantic import BaseModel

# Import production settings (optional, comprehensive)
try:
    from .config.production_settings import \
        get_settings as get_production_settings_internal

    PRODUCTION_SETTINGS_AVAILABLE = True
except ImportError:
    PRODUCTION_SETTINGS_AVAILABLE = False


class GeminiSettings(BaseModel):
    enabled: bool = os.getenv("GEMINI_ENABLED", "false").lower() == "true"
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    # Only gemini-embedding-001 supported
    embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    output_dim: int | None = (
        int(os.getenv("GEMINI_OUTPUT_DIM")) if os.getenv("GEMINI_OUTPUT_DIM") else None
    )


class Settings(BaseModel):
    gemini: GeminiSettings = GeminiSettings()


def get_settings() -> Settings:
    """Get simple settings (backward compatible).

    Returns basic settings loaded from environment variables.
    """
    return Settings()


def get_production_settings():
    """Get comprehensive production settings.

    Returns production-ready settings with all subsystems.
    Raises ImportError if production_settings module is not available.
    """
    if not PRODUCTION_SETTINGS_AVAILABLE:
        raise ImportError(
            "Production settings not available. " "Use core.config.settings.get_settings() instead."
        )
    return get_production_settings_internal()


__all__ = [
    "GeminiSettings",
    "Settings",
    "get_production_settings",
    "get_settings",
]
