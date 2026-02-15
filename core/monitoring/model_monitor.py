"""Model Monitoring for MLOps - Drift Detection and Performance Tracking.

Implements continuous monitoring for LLM agents:
- Model drift detection (statistical, percentile, consecutive failure)
- Performance degradation alerts
- Quality metrics tracking
- Automated retraining triggers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
import statistics
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    """Types of model drift."""

    CONCEPT_DRIFT = "concept_drift"
    DATA_DRIFT = "data_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Alert for detected drift."""

    drift_type: DriftType
    severity: AlertSeverity
    metric_name: str
    current_value: float
    baseline_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class MetricWindow:
    """Sliding window for metric tracking."""

    name: str
    window_size: int = 100
    values: deque = field(default_factory=lambda: deque(maxlen=100))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=100))

    def __post_init__(self):
        self.values = deque(maxlen=self.window_size)
        self.timestamps = deque(maxlen=self.window_size)

    def add(self, value: float, timestamp: datetime | None = None) -> None:
        self.values.append(value)
        self.timestamps.append(timestamp or datetime.now(UTC))

    @property
    def mean(self) -> float:
        return statistics.mean(self.values) if self.values else 0.0

    @property
    def std(self) -> float:
        return statistics.stdev(self.values) if len(self.values) > 1 else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.values) if self.values else 0.0

    @property
    def min_val(self) -> float:
        return min(self.values) if self.values else 0.0

    @property
    def max_val(self) -> float:
        return max(self.values) if self.values else 0.0

    @property
    def count(self) -> int:
        return len(self.values)


class DriftDetector(ABC):
    """Abstract base class for drift detectors."""

    @abstractmethod
    def detect(
        self,
        current_window: MetricWindow,
        baseline_window: MetricWindow,
    ) -> DriftAlert | None:
        """Detect drift between current and baseline windows."""


class StatisticalDriftDetector(DriftDetector):
    """Statistical drift detection using z-score."""

    def __init__(self, z_threshold: float = 2.0, min_samples: int = 30):
        self.z_threshold = z_threshold
        self.min_samples = min_samples

    def detect(
        self,
        current_window: MetricWindow,
        baseline_window: MetricWindow,
    ) -> DriftAlert | None:
        if current_window.count < self.min_samples:
            return None
        if baseline_window.count < self.min_samples:
            return None

        current_mean = current_window.mean
        baseline_mean = baseline_window.mean
        baseline_std = baseline_window.std

        if baseline_std == 0:
            return None

        z_score = abs(current_mean - baseline_mean) / baseline_std

        if z_score > self.z_threshold:
            severity = AlertSeverity.CRITICAL if z_score > 3.0 else AlertSeverity.WARNING
            return DriftAlert(
                drift_type=DriftType.PERFORMANCE_DRIFT,
                severity=severity,
                metric_name=current_window.name,
                current_value=current_mean,
                baseline_value=baseline_mean,
                threshold=self.z_threshold,
                metadata={"z_score": z_score},
            )
        return None


class KSTestDriftDetector(DriftDetector):
    """Kolmogorov-Smirnov test for distribution drift."""

    def __init__(self, p_value_threshold: float = 0.05, min_samples: int = 50):
        self.p_value_threshold = p_value_threshold
        self.min_samples = min_samples

    def detect(
        self,
        current_window: MetricWindow,
        baseline_window: MetricWindow,
    ) -> DriftAlert | None:
        if current_window.count < self.min_samples:
            return None
        if baseline_window.count < self.min_samples:
            return None

        try:
            from scipy.stats import ks_2samp

            ks_stat, p_value = ks_2samp(
                list(baseline_window.values),
                list(current_window.values),
            )

            if p_value < self.p_value_threshold:
                return DriftAlert(
                    drift_type=DriftType.DATA_DRIFT,
                    severity=AlertSeverity.WARNING,
                    metric_name=current_window.name,
                    current_value=current_window.mean,
                    baseline_value=baseline_window.mean,
                    threshold=self.p_value_threshold,
                    metadata={"ks_statistic": ks_stat, "p_value": p_value},
                )
        except ImportError:
            pass  # scipy not available
        return None


class ConsecutiveFailureDetector(DriftDetector):
    """Detect drift based on consecutive failures."""

    def __init__(self, failure_threshold: float = 0.5, consecutive_count: int = 5):
        self.failure_threshold = failure_threshold
        self.consecutive_count = consecutive_count

    def detect(
        self,
        current_window: MetricWindow,
        baseline_window: MetricWindow,
    ) -> DriftAlert | None:
        if current_window.count < self.consecutive_count:
            return None

        recent = list(current_window.values)[-self.consecutive_count :]
        failures = sum(1 for v in recent if v < self.failure_threshold)

        if failures == self.consecutive_count:
            return DriftAlert(
                drift_type=DriftType.PERFORMANCE_DRIFT,
                severity=AlertSeverity.CRITICAL,
                metric_name=current_window.name,
                current_value=statistics.mean(recent),
                baseline_value=baseline_window.mean,
                threshold=self.failure_threshold,
                metadata={"consecutive_failures": failures},
            )
        return None


class ModelMonitor:
    """Main class for monitoring model performance and drift."""

    def __init__(
        self,
        model_id: str = "default",
        baseline_window_size: int = 1000,
        current_window_size: int = 100,
        check_interval_seconds: float = 60.0,
    ):
        self.model_id = model_id
        self.baseline_window_size = baseline_window_size
        self.current_window_size = current_window_size
        self.check_interval = check_interval_seconds

        # For backward compatibility
        self.window_size = baseline_window_size
        self.reference_data: dict[str, np.ndarray] = {}
        self.live_data: dict[str, deque] = {}

        # Enhanced metric windows
        self._baseline_windows: dict[str, MetricWindow] = {}
        self._current_windows: dict[str, MetricWindow] = {}

        # Drift detectors
        self._detectors: list[DriftDetector] = [
            StatisticalDriftDetector(),
            KSTestDriftDetector(),
            ConsecutiveFailureDetector(),
        ]

        # Alerts and callbacks
        self._alerts: list[DriftAlert] = []
        self._alert_callbacks: list[Callable[[DriftAlert], Coroutine[Any, Any, None]]] = []

        # Monitoring state
        self._running = False
        self._monitor_task: asyncio.Task | None = None

        self._stats = {
            "total_observations": 0,
            "total_alerts": 0,
            "last_check": None,
        }

    # Backward compatibility methods
    def set_reference_data(self, model_name: str, data: list[float]) -> None:
        """Sets the reference data for a model (legacy API)."""
        self.reference_data[model_name] = np.array(data)
        self.live_data[model_name] = deque(maxlen=self.window_size)
        # Also set up new-style windows
        self._baseline_windows[model_name] = MetricWindow(
            name=model_name, window_size=self.baseline_window_size
        )
        for val in data[-self.baseline_window_size :]:
            self._baseline_windows[model_name].add(val)
        self._current_windows[model_name] = MetricWindow(
            name=model_name, window_size=self.current_window_size
        )

    def track_prediction(self, model_name: str, prediction: float) -> None:
        """Tracks a new prediction (legacy API)."""
        if model_name not in self.live_data:
            self.live_data[model_name] = deque(maxlen=self.window_size)
            self.reference_data[model_name] = np.array([])
        self.live_data[model_name].append(prediction)
        self.record_metric(model_name, prediction)

    def detect_drift(self, model_name: str) -> dict[str, Any]:
        """Detects drift for a model using the Kolmogorov-Smirnov test (legacy API)."""
        if model_name not in self.reference_data or model_name not in self.live_data:
            raise ValueError(f"Model '{model_name}' not found.")

        reference_dist = self.reference_data[model_name]
        live_dist = np.array(self.live_data[model_name])

        if len(live_dist) < self.window_size / 2:
            return {
                "drift_detected": False,
                "p_value": None,
                "message": "Not enough live data to detect drift.",
            }

        try:
            from scipy.stats import ks_2samp

            ks_statistic, p_value = ks_2samp(reference_dist, live_dist)
        except ImportError:
            return {
                "drift_detected": False,
                "p_value": None,
                "message": "scipy is not installed.",
            }

        drift_detected = p_value < 0.05

        return {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "ks_statistic": ks_statistic,
            "live_data_size": len(live_dist),
        }

    # Enhanced API methods
    def add_detector(self, detector: DriftDetector) -> None:
        """Add a custom drift detector."""
        self._detectors.append(detector)

    def register_alert_callback(
        self,
        callback: Callable[[DriftAlert], Coroutine[Any, Any, None]],
    ) -> None:
        """Register callback for drift alerts."""
        self._alert_callbacks.append(callback)

    def record_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a metric observation."""
        if metric_name not in self._baseline_windows:
            self._baseline_windows[metric_name] = MetricWindow(
                name=metric_name, window_size=self.baseline_window_size
            )
        if metric_name not in self._current_windows:
            self._current_windows[metric_name] = MetricWindow(
                name=metric_name, window_size=self.current_window_size
            )

        self._current_windows[metric_name].add(value, timestamp)

        if self._current_windows[metric_name].count >= self.current_window_size:
            self._baseline_windows[metric_name].add(value, timestamp)

        self._stats["total_observations"] += 1

    async def check_drift(self) -> list[DriftAlert]:
        """Check for drift across all metrics."""
        alerts = []

        for metric_name in self._current_windows:
            current = self._current_windows[metric_name]
            baseline = self._baseline_windows.get(metric_name)

            if baseline is None:
                continue

            for detector in self._detectors:
                alert = detector.detect(current, baseline)
                if alert:
                    alerts.append(alert)
                    self._alerts.append(alert)
                    self._stats["total_alerts"] += 1

                    for callback in self._alert_callbacks:
                        try:
                            await callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")

        self._stats["last_check"] = datetime.now(UTC).isoformat()
        return alerts

    async def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started monitoring for model {self.model_id}")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped monitoring for model {self.model_id}")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self.check_drift()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    def get_metric_stats(self, metric_name: str) -> dict[str, Any] | None:
        """Get statistics for a specific metric."""
        current = self._current_windows.get(metric_name)
        baseline = self._baseline_windows.get(metric_name)

        if current is None:
            return None

        return {
            "metric_name": metric_name,
            "current": {
                "mean": current.mean,
                "std": current.std,
                "median": current.median,
                "min": current.min_val,
                "max": current.max_val,
                "count": current.count,
            },
            "baseline": (
                {
                    "mean": baseline.mean,
                    "std": baseline.std,
                    "count": baseline.count,
                }
                if baseline
                else None
            ),
        }

    def get_all_stats(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "model_id": self.model_id,
            "metrics": list(self._current_windows.keys()),
            "stats": self._stats,
            "recent_alerts": [a.to_dict() for a in self._alerts[-10:]],
        }

    def get_alerts(
        self,
        since: datetime | None = None,
        severity: AlertSeverity | None = None,
    ) -> list[DriftAlert]:
        """Get alerts with optional filtering."""
        alerts = self._alerts
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def should_retrain(self) -> tuple[bool, str]:
        """Determine if model should be retrained."""
        recent_alerts = self.get_alerts(
            since=datetime.now(UTC) - timedelta(hours=1),
        )

        critical_count = sum(1 for a in recent_alerts if a.severity == AlertSeverity.CRITICAL)
        if critical_count >= 3:
            return True, f"Multiple critical alerts ({critical_count})"

        for metric_name, current in self._current_windows.items():
            baseline = self._baseline_windows.get(metric_name)
            if baseline and baseline.mean > 0:
                drop = (baseline.mean - current.mean) / baseline.mean
                if drop > 0.2:
                    return True, f"Sustained performance drop in {metric_name}"

        return False, "No retraining needed"


class MultiModelMonitor:
    """Monitor multiple models simultaneously."""

    def __init__(self):
        self._monitors: dict[str, ModelMonitor] = {}

    def add_model(self, model_id: str, **kwargs: Any) -> ModelMonitor:
        """Add a model to monitor."""
        if model_id in self._monitors:
            raise ValueError(f"Model already monitored: {model_id}")
        monitor = ModelMonitor(model_id, **kwargs)
        self._monitors[model_id] = monitor
        return monitor

    def get_monitor(self, model_id: str) -> ModelMonitor | None:
        """Get monitor for a specific model."""
        return self._monitors.get(model_id)

    async def start_all(self) -> None:
        """Start monitoring all models."""
        await asyncio.gather(*[m.start_monitoring() for m in self._monitors.values()])

    async def stop_all(self) -> None:
        """Stop monitoring all models."""
        await asyncio.gather(*[m.stop_monitoring() for m in self._monitors.values()])

    def get_retraining_recommendations(self) -> list[dict[str, Any]]:
        """Get retraining recommendations for all models."""
        recommendations = []
        for model_id, monitor in self._monitors.items():
            should_retrain, reason = monitor.should_retrain()
            if should_retrain:
                recommendations.append(
                    {
                        "model_id": model_id,
                        "reason": reason,
                        "stats": monitor.get_all_stats(),
                    }
                )
        return recommendations


def create_model_monitor(
    model_id: str = "default",
    baseline_window: int = 1000,
    current_window: int = 100,
) -> ModelMonitor:
    """Create a model monitor with default configuration."""
    return ModelMonitor(
        model_id=model_id,
        baseline_window_size=baseline_window,
        current_window_size=current_window,
    )


__all__ = [
    "AlertSeverity",
    "ConsecutiveFailureDetector",
    "DriftAlert",
    "DriftDetector",
    "DriftType",
    "KSTestDriftDetector",
    "MetricWindow",
    "ModelMonitor",
    "MultiModelMonitor",
    "StatisticalDriftDetector",
    "create_model_monitor",
]
