from __future__ import annotations

import json
import os

from config.secrets_manager import SecretsManager


def test_secrets_manager_prefers_environment(tmp_path) -> None:
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({"FROM_FILE": "file-value"}), encoding="utf-8")

    manager = SecretsManager(secrets_file=str(secrets_file))
    assert manager.get("FROM_FILE") == "file-value"

    os.environ["FROM_FILE"] = "env-value"
    try:
        assert manager.get("FROM_FILE") == "env-value"
    finally:
        os.environ.pop("FROM_FILE")
