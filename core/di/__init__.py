"""Dependency Injection module for MegaAgent Pro."""

from __future__ import annotations

from .container import Container, get_container, reset_container

__all__ = [
    "Container",
    "get_container",
    "reset_container",
]
