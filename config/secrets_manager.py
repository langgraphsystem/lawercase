"""Utility helpers for loading secrets across environments."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class SecretsManager:
    """Load secrets from environment variables or an optional JSON file."""

    def __init__(self, *, secrets_file: str | None = None) -> None:
        self._secrets_file = secrets_file or os.getenv("SECRETS_FILE")
        self._cache: dict[str, Any] = {}
        self._load_file_secrets()

    def _load_file_secrets(self) -> None:
        if not self._secrets_file:
            return
        path = Path(self._secrets_file)
        if not path.exists():
            return
        try:
            self._cache = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse secrets file {path}") from exc

    def get(self, key: str, default: Any | None = None) -> Any | None:
        if key in os.environ:
            return os.environ[key]
        return self._cache.get(key, default)

    def require(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise RuntimeError(f"Missing required secret: {key}")
        return value


secrets_manager = SecretsManager()

__all__ = ["SecretsManager", "secrets_manager"]
