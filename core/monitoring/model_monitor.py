from __future__ import annotations

"""Model drift monitoring placeholder."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MetricEvent:
    name: str
    value: float
    metadata: dict[str, Any]


class ModelMonitor:
    def __init__(self) -> None:
        self._events: list[MetricEvent] = []

    def record(self, event: MetricEvent) -> None:
        self._events.append(event)

    def get_events(self) -> list[MetricEvent]:
        return list(self._events)
