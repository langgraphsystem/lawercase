"""Quality Metrics Tracking.

This module provides quality metrics tracking and analytics for
self-correcting agents.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QualityMetrics:
    """Quality metrics for an agent operation."""

    operation_id: str
    agent_name: str
    timestamp: datetime
    confidence_score: float
    retry_count: int
    duration_seconds: float
    success: bool
    error_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class QualityTracker:
    """
    Tracks and analyzes quality metrics for self-correcting agents.

    Features:
    - Real-time quality tracking
    - Historical analytics
    - Performance degradation detection
    - Quality trends analysis
    - Per-agent metrics

    Example:
        >>> tracker = QualityTracker()
        >>> tracker.record_operation(
        ...     agent_name="research_agent",
        ...     confidence_score=0.85,
        ...     retry_count=1,
        ...     duration_seconds=2.5,
        ...     success=True
        ... )
    """

    def __init__(self, history_size: int = 1000):
        """
        Initialize quality tracker.

        Args:
            history_size: Number of operations to keep in memory
        """
        self.history_size = history_size
        self.operations: deque[QualityMetrics] = deque(maxlen=history_size)
        self.agent_stats: dict[str, dict[str, Any]] = {}

    def record_operation(
        self,
        agent_name: str,
        confidence_score: float,
        retry_count: int,
        duration_seconds: float,
        success: bool,
        operation_id: str | None = None,
        error_type: str | None = None,
        **metadata: Any,
    ) -> None:
        """
        Record an agent operation.

        Args:
            agent_name: Name of the agent
            confidence_score: Confidence score (0-1)
            retry_count: Number of retries
            duration_seconds: Operation duration
            success: Whether operation succeeded
            operation_id: Optional operation ID
            error_type: Error type if failed
            **metadata: Additional metadata

        Example:
            >>> tracker.record_operation(
            ...     "writer_agent",
            ...     confidence_score=0.9,
            ...     retry_count=0,
            ...     duration_seconds=1.5,
            ...     success=True,
            ...     user_id="123"
            ... )
        """
        operation_id = operation_id or f"{agent_name}_{int(time.time() * 1000)}"

        metrics = QualityMetrics(
            operation_id=operation_id,
            agent_name=agent_name,
            timestamp=datetime.utcnow(),
            confidence_score=confidence_score,
            retry_count=retry_count,
            duration_seconds=duration_seconds,
            success=success,
            error_type=error_type,
            metadata=metadata,
        )

        self.operations.append(metrics)
        self._update_agent_stats(agent_name, metrics)

    def _update_agent_stats(self, agent_name: str, metrics: QualityMetrics) -> None:
        """Update per-agent statistics."""
        if agent_name not in self.agent_stats:
            self.agent_stats[agent_name] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_retries": 0,
                "total_duration": 0.0,
                "avg_confidence": 0.0,
                "avg_retries": 0.0,
                "avg_duration": 0.0,
                "success_rate": 0.0,
            }

        stats = self.agent_stats[agent_name]
        stats["total_operations"] += 1

        if metrics.success:
            stats["successful_operations"] += 1
        else:
            stats["failed_operations"] += 1

        stats["total_retries"] += metrics.retry_count
        stats["total_duration"] += metrics.duration_seconds

        # Calculate averages
        total = stats["total_operations"]
        stats["avg_confidence"] = (
            stats["avg_confidence"] * (total - 1) + metrics.confidence_score
        ) / total

        stats["avg_retries"] = stats["total_retries"] / total
        stats["avg_duration"] = stats["total_duration"] / total
        stats["success_rate"] = stats["successful_operations"] / total

    def get_agent_stats(self, agent_name: str) -> dict[str, Any]:
        """
        Get statistics for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with agent statistics

        Example:
            >>> stats = tracker.get_agent_stats("research_agent")
            >>> print(stats["avg_confidence"])
            0.85
        """
        return self.agent_stats.get(agent_name, {}).copy()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all agents."""
        return {name: stats.copy() for name, stats in self.agent_stats.items()}

    def get_recent_operations(
        self,
        agent_name: str | None = None,
        limit: int = 10,
    ) -> list[QualityMetrics]:
        """
        Get recent operations.

        Args:
            agent_name: Optional filter by agent name
            limit: Maximum number of operations to return

        Returns:
            List of recent QualityMetrics

        Example:
            >>> recent = tracker.get_recent_operations("research_agent", limit=5)
        """
        operations = list(self.operations)

        if agent_name:
            operations = [op for op in operations if op.agent_name == agent_name]

        # Most recent first
        operations.reverse()

        return operations[:limit]

    def get_quality_trend(
        self,
        agent_name: str | None = None,
        window_size: int = 100,
    ) -> dict[str, Any]:
        """
        Analyze quality trends.

        Args:
            agent_name: Optional filter by agent name
            window_size: Number of recent operations to analyze

        Returns:
            Dictionary with trend analysis

        Example:
            >>> trend = tracker.get_quality_trend("research_agent")
            >>> print(trend["confidence_trend"])
            'improving'
        """
        operations = self.get_recent_operations(agent_name, window_size)

        if len(operations) < 10:
            return {
                "status": "insufficient_data",
                "operations_count": len(operations),
            }

        # Split into old and recent halves
        mid = len(operations) // 2
        recent_half = operations[:mid]
        older_half = operations[mid:]

        # Calculate averages
        recent_conf = sum(op.confidence_score for op in recent_half) / len(recent_half)
        older_conf = sum(op.confidence_score for op in older_half) / len(older_half)

        recent_retries = sum(op.retry_count for op in recent_half) / len(recent_half)
        older_retries = sum(op.retry_count for op in older_half) / len(older_half)

        recent_duration = sum(op.duration_seconds for op in recent_half) / len(recent_half)
        older_duration = sum(op.duration_seconds for op in older_half) / len(older_half)

        # Determine trends
        conf_trend = "improving" if recent_conf > older_conf else "declining"
        retry_trend = "improving" if recent_retries < older_retries else "declining"
        duration_trend = "improving" if recent_duration < older_duration else "declining"

        # Overall health
        health_score = (
            (recent_conf * 0.5)
            + ((1 - min(recent_retries / 3, 1)) * 0.3)
            + ((1 - min(recent_duration / 10, 1)) * 0.2)
        )

        return {
            "status": "analyzed",
            "operations_count": len(operations),
            "recent_avg_confidence": recent_conf,
            "older_avg_confidence": older_conf,
            "confidence_trend": conf_trend,
            "recent_avg_retries": recent_retries,
            "older_avg_retries": older_retries,
            "retry_trend": retry_trend,
            "recent_avg_duration": recent_duration,
            "older_avg_duration": older_duration,
            "duration_trend": duration_trend,
            "health_score": health_score,
            "health_status": "good" if health_score > 0.7 else "attention_needed",
        }

    def detect_anomalies(
        self,
        agent_name: str | None = None,
        threshold: float = 2.0,
    ) -> list[dict[str, Any]]:
        """
        Detect anomalous operations.

        Args:
            agent_name: Optional filter by agent name
            threshold: Standard deviations for anomaly detection

        Returns:
            List of anomalous operations

        Example:
            >>> anomalies = tracker.detect_anomalies(threshold=2.5)
        """
        operations = list(self.operations)

        if agent_name:
            operations = [op for op in operations if op.agent_name == agent_name]

        if len(operations) < 10:
            return []

        # Calculate mean and std dev for confidence
        confidences = [op.confidence_score for op in operations]
        mean_conf = sum(confidences) / len(confidences)
        var_conf = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
        std_conf = var_conf**0.5

        # Calculate for duration
        durations = [op.duration_seconds for op in operations]
        mean_dur = sum(durations) / len(durations)
        var_dur = sum((d - mean_dur) ** 2 for d in durations) / len(durations)
        std_dur = var_dur**0.5

        # Find anomalies
        anomalies = []
        for op in operations:
            reasons = []

            # Check confidence anomaly
            if abs(op.confidence_score - mean_conf) > threshold * std_conf:
                reasons.append("unusual_confidence")

            # Check duration anomaly
            if abs(op.duration_seconds - mean_dur) > threshold * std_dur:
                reasons.append("unusual_duration")

            # Check excessive retries
            if op.retry_count > 3:
                reasons.append("excessive_retries")

            if reasons:
                anomalies.append(
                    {
                        "operation_id": op.operation_id,
                        "agent_name": op.agent_name,
                        "timestamp": op.timestamp.isoformat(),
                        "confidence_score": op.confidence_score,
                        "duration_seconds": op.duration_seconds,
                        "retry_count": op.retry_count,
                        "reasons": reasons,
                    }
                )

        return anomalies

    def get_summary(self) -> dict[str, Any]:
        """
        Get overall quality summary.

        Returns:
            Summary statistics across all agents

        Example:
            >>> summary = tracker.get_summary()
            >>> print(summary["overall_success_rate"])
            0.92
        """
        if not self.operations:
            return {"status": "no_data"}

        total_ops = len(self.operations)
        successful_ops = sum(1 for op in self.operations if op.success)
        total_retries = sum(op.retry_count for op in self.operations)
        total_duration = sum(op.duration_seconds for op in self.operations)
        avg_confidence = sum(op.confidence_score for op in self.operations) / total_ops

        return {
            "status": "active",
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "failed_operations": total_ops - successful_ops,
            "overall_success_rate": successful_ops / total_ops,
            "total_retries": total_retries,
            "avg_retries": total_retries / total_ops,
            "avg_confidence": avg_confidence,
            "avg_duration": total_duration / total_ops,
            "agents_count": len(self.agent_stats),
            "agents": list(self.agent_stats.keys()),
        }

    def export_metrics(self, output_format: str = "dict") -> Any:
        """
        Export metrics in various formats.

        Args:
            output_format: Export format (dict, csv, json)

        Returns:
            Metrics in requested format
        """
        if output_format == "dict":
            return {
                "operations": [
                    {
                        "operation_id": op.operation_id,
                        "agent_name": op.agent_name,
                        "timestamp": op.timestamp.isoformat(),
                        "confidence_score": op.confidence_score,
                        "retry_count": op.retry_count,
                        "duration_seconds": op.duration_seconds,
                        "success": op.success,
                        "error_type": op.error_type,
                        "metadata": op.metadata,
                    }
                    for op in self.operations
                ],
                "agent_stats": self.get_all_stats(),
                "summary": self.get_summary(),
            }

        # TODO: Implement CSV and JSON exports
        raise NotImplementedError(f"Export format '{output_format}' not implemented")


# Global singleton
_quality_tracker: QualityTracker | None = None


def get_quality_tracker() -> QualityTracker:
    """
    Get global quality tracker instance.

    Returns:
        QualityTracker instance

    Example:
        >>> tracker = get_quality_tracker()
        >>> tracker.record_operation(...)
    """
    global _quality_tracker

    if _quality_tracker is None:
        _quality_tracker = QualityTracker()

    return _quality_tracker
