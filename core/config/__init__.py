"""Configuration package for mega_agent_pro.

Provides settings and static configuration loaded from environment and files.
"""

from __future__ import annotations

from .settings import AppSettings, get_settings

__all__ = ["AppSettings", "get_settings"]
