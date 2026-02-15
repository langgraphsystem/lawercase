"""Monitoring Package for MLOps.

Provides model monitoring and drift detection:
- ModelMonitor: Comprehensive model performance monitoring
- DriftDetector: Abstract base for drift detection algorithms
- StatisticalDriftDetector: Statistical drift detection
- KSTestDriftDetector: Kolmogorov-Smirnov test based detection
- ConsecutiveFailureDetector: Consecutive failure detection
- MultiModelMonitor: Monitor multiple models
"""

from __future__ import annotations

from .model_monitor import (
    AlertSeverity,
    ConsecutiveFailureDetector,
    DriftAlert,
    DriftDetector,
    DriftType,
    KSTestDriftDetector,
    MetricWindow,
    ModelMonitor,
    MultiModelMonitor,
    StatisticalDriftDetector,
    create_model_monitor,
)

__all__ = [
    "AlertSeverity",
    "ConsecutiveFailureDetector",
    # Data Classes
    "DriftAlert",
    # Drift Detectors
    "DriftDetector",
    # Enums
    "DriftType",
    "KSTestDriftDetector",
    "MetricWindow",
    # Monitors
    "ModelMonitor",
    "MultiModelMonitor",
    "StatisticalDriftDetector",
    "create_model_monitor",
]
