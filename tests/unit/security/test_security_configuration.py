from __future__ import annotations

from core.security import configure_security, get_prompt_detector
from core.security.config import SecurityConfig


def test_configure_security_updates_prompt_detector(monkeypatch) -> None:
    config = SecurityConfig(prompt_detection_enabled=False, prompt_detection_threshold=0.3)
    configure_security(config)

    detector = get_prompt_detector()
    assert detector.strictness == 0.3
    assert detector.enabled is False
