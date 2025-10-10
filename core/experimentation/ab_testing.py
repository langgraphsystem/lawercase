from __future__ import annotations

"""A/B testing harness scaffolding for MegaAgent.

Defines experiments, variants, and lightweight telemetry hooks.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ExperimentVariant:
    name: str
    weight: float
    handler: Callable[[dict[str, Any]], Any]


@dataclass(slots=True)
class Experiment:
    key: str
    description: str
    variants: list[ExperimentVariant]


class ExperimentRegistry:
    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}

    def register(self, experiment: Experiment) -> None:
        if experiment.key in self._experiments:
            raise ValueError(f"Experiment '{experiment.key}' already registered")
        self._experiments[experiment.key] = experiment

    def get(self, key: str) -> Experiment:
        return self._experiments[key]
