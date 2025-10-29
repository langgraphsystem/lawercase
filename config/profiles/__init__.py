"""Pre-defined configuration profiles."""

from __future__ import annotations

from .production import ProductionProfile, load_production_profile

__all__ = ["ProductionProfile", "load_production_profile"]
