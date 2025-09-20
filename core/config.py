from __future__ import annotations

import os

from pydantic import BaseModel


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
    return Settings()
