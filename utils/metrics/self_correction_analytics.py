"""Self-Correction Analytics - Tracks and analyzes agent self-correction behavior.

Provides comprehensive analytics for agent self-correction patterns:
- Correction event tracking
- Pattern analysis and trending
- Effectiveness measurement
- Learning curve estimation
- Anomaly detection

Metrics exported:
- correction_events_total (counter)
- correction_success_rate (gauge)
- correction_latency_seconds (histogram)
- correction_iterations (histogram)
- correction_confidence_delta (histogram)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
from typing import Any
from uuid import uuid4

import structlog

from .llm_metrics import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)


class CorrectionType(str, Enum):
    """Types of self-corrections."""

    FACTUAL = "factual"  # Correcting factual errors
    LOGICAL = "logical"  # Correcting logical inconsistencies
    COMPLETENESS = "completeness"  # Adding missing information
    COHERENCE = "coherence"  # Improving flow and structure
    SOURCE = "source"  # Source verification corrections
    CONFIDENCE = "confidence"  # Confidence score adjustments
    FORMAT = "format"  # Output format corrections
    RELEVANCE = "relevance"  # Relevance adjustments


class CorrectionTrigger(str, Enum):
    """What triggered the correction."""

    SELF_REVIEW = "self_review"  # Agent's own review
    VALIDATOR = "validator"  # External validator
    USER_FEEDBACK = "user_feedback"  # User-provided feedback
    FACT_CHECK = "fact_check"  # Fact checking system
    CONSISTENCY_CHECK = "consistency_check"  # Cross-reference check
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Below threshold


class CorrectionOutcome(str, Enum):
    """Outcome of the correction attempt."""

    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    DEGRADED = "degraded"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class CorrectionEvent:
    """Record of a single correction event."""

    event_id: str
    session_id: str
    agent_id: str
    correction_type: CorrectionType
    trigger: CorrectionTrigger
    outcome: CorrectionOutcome
    original_content: str
    corrected_content: str
    original_confidence: float
    corrected_confidence: float
    latency_seconds: float
    iteration_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "correction_type": self.correction_type.value,
            "trigger": self.trigger.value,
            "outcome": self.outcome.value,
            "original_confidence": self.original_confidence,
            "corrected_confidence": self.corrected_confidence,
            "confidence_delta": self.corrected_confidence - self.original_confidence,
            "latency_seconds": self.latency_seconds,
            "iteration_count": self.iteration_count,
            "timestamp": self.timestamp.isoformat(),
        }

    @property
    def confidence_delta(self) -> float:
        return self.corrected_confidence - self.original_confidence


@dataclass
class CorrectionPattern:
    """Identified pattern in correction behavior."""

    pattern_id: str
    correction_type: CorrectionType
    trigger: CorrectionTrigger
    frequency: int
    avg_confidence_improvement: float
    avg_latency: float
    success_rate: float
    first_seen: datetime
    last_seen: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "correction_type": self.correction_type.value,
            "trigger": self.trigger.value,
            "frequency": self.frequency,
            "avg_confidence_improvement": self.avg_confidence_improvement,
            "avg_latency": self.avg_latency,
            "success_rate": self.success_rate,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


@dataclass
class LearningCurve:
    """Tracks learning progress over time."""

    agent_id: str
    data_points: list[tuple[datetime, float]] = field(default_factory=list)
    improvement_rate: float = 0.0
    plateau_detected: bool = False
    estimated_convergence: datetime | None = None

    def add_point(self, timestamp: datetime, success_rate: float) -> None:
        self.data_points.append((timestamp, success_rate))
        self._update_analysis()

    def _update_analysis(self) -> None:
        if len(self.data_points) < 3:
            return

        # Calculate improvement rate from recent points
        recent = self.data_points[-10:]
        if len(recent) >= 2:
            time_delta = (recent[-1][0] - recent[0][0]).total_seconds()
            if time_delta > 0:
                rate_delta = recent[-1][1] - recent[0][1]
                self.improvement_rate = rate_delta / (time_delta / 3600)  # per hour

        # Detect plateau (low variance in recent points)
        if len(recent) >= 5:
            rates = [p[1] for p in recent]
            variance = sum((r - sum(rates) / len(rates)) ** 2 for r in rates) / len(rates)
            self.plateau_detected = variance < 0.001 and self.improvement_rate < 0.01

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "data_points_count": len(self.data_points),
            "improvement_rate": self.improvement_rate,
            "plateau_detected": self.plateau_detected,
            "estimated_convergence": (
                self.estimated_convergence.isoformat() if self.estimated_convergence else None
            ),
        }


@dataclass
class AnalyticsSummary:
    """Summary of self-correction analytics."""

    total_corrections: int
    success_rate: float
    avg_confidence_improvement: float
    avg_latency: float
    avg_iterations: float
    corrections_by_type: dict[str, int]
    corrections_by_trigger: dict[str, int]
    corrections_by_outcome: dict[str, int]
    top_patterns: list[CorrectionPattern]
    anomalies: list[dict[str, Any]]
    time_range: tuple[datetime, datetime]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_corrections": self.total_corrections,
            "success_rate": self.success_rate,
            "avg_confidence_improvement": self.avg_confidence_improvement,
            "avg_latency": self.avg_latency,
            "avg_iterations": self.avg_iterations,
            "corrections_by_type": self.corrections_by_type,
            "corrections_by_trigger": self.corrections_by_trigger,
            "corrections_by_outcome": self.corrections_by_outcome,
            "top_patterns": [p.to_dict() for p in self.top_patterns],
            "anomalies": self.anomalies,
            "time_range": [
                self.time_range[0].isoformat(),
                self.time_range[1].isoformat(),
            ],
        }


class SelfCorrectionAnalytics:
    """Analytics system for tracking and analyzing agent self-correction behavior.

    Features:
    - Correction event tracking
    - Pattern identification
    - Effectiveness measurement
    - Learning curve estimation
    - Anomaly detection

    Usage:
        >>> analytics = SelfCorrectionAnalytics()
        >>> event = await analytics.record_correction(
        ...     session_id="session_001",
        ...     agent_id="researcher_001",
        ...     correction_type=CorrectionType.FACTUAL,
        ...     trigger=CorrectionTrigger.FACT_CHECK,
        ...     original_content="incorrect statement",
        ...     corrected_content="corrected statement",
        ...     original_confidence=0.6,
        ...     corrected_confidence=0.85,
        ...     latency_seconds=2.5,
        ...     iteration_count=1,
        ... )
        >>> summary = analytics.get_summary()
    """

    def __init__(
        self,
        max_events: int = 50000,
        anomaly_threshold: float = 2.0,
    ) -> None:
        """Initialize self-correction analytics.

        Args:
            max_events: Maximum events to store
            anomaly_threshold: Standard deviations for anomaly detection
        """
        self.max_events = max_events
        self.anomaly_threshold = anomaly_threshold

        # Event storage
        self._events: list[CorrectionEvent] = []
        self._events_lock = asyncio.Lock()

        # Metrics
        self.corrections_total = Counter(
            "correction_events_total",
            "Total number of correction events",
            labels=["type", "trigger", "outcome"],
        )
        self.success_rate = Gauge(
            "correction_success_rate",
            "Rolling success rate of corrections",
            labels=["agent_id"],
        )
        self.latency = Histogram(
            "correction_latency_seconds",
            "Correction latency in seconds",
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
            labels=["type"],
        )
        self.iterations = Histogram(
            "correction_iterations",
            "Number of correction iterations",
            buckets=(1, 2, 3, 4, 5, 7, 10, float("inf")),
            labels=["type"],
        )
        self.confidence_delta = Histogram(
            "correction_confidence_delta",
            "Change in confidence after correction",
            buckets=(-0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1.0, float("inf")),
            labels=["type", "outcome"],
        )

        # Pattern tracking
        self._patterns: dict[tuple[CorrectionType, CorrectionTrigger], CorrectionPattern] = {}

        # Learning curves per agent
        self._learning_curves: dict[str, LearningCurve] = {}

        # Anomaly detection baselines
        self._baselines: dict[str, dict[str, float]] = defaultdict(
            lambda: {"mean": 0.0, "std": 1.0}
        )

        self.logger = logger.bind(component="SelfCorrectionAnalytics")

    async def record_correction(
        self,
        session_id: str,
        agent_id: str,
        correction_type: CorrectionType,
        trigger: CorrectionTrigger,
        original_content: str,
        corrected_content: str,
        original_confidence: float,
        corrected_confidence: float,
        latency_seconds: float,
        iteration_count: int,
        outcome: CorrectionOutcome | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CorrectionEvent:
        """Record a correction event.

        Args:
            session_id: Session identifier
            agent_id: Agent identifier
            correction_type: Type of correction
            trigger: What triggered the correction
            original_content: Content before correction
            corrected_content: Content after correction
            original_confidence: Confidence before
            corrected_confidence: Confidence after
            latency_seconds: Time taken
            iteration_count: Number of correction iterations
            outcome: Outcome (auto-detected if None)
            metadata: Additional metadata

        Returns:
            Recorded CorrectionEvent
        """
        # Auto-detect outcome if not provided
        if outcome is None:
            confidence_delta = corrected_confidence - original_confidence
            if confidence_delta > 0.1:
                outcome = CorrectionOutcome.IMPROVED
            elif confidence_delta < -0.1:
                outcome = CorrectionOutcome.DEGRADED
            elif abs(confidence_delta) <= 0.1 and original_content != corrected_content:
                outcome = CorrectionOutcome.PARTIAL
            else:
                outcome = CorrectionOutcome.NO_CHANGE

        event = CorrectionEvent(
            event_id=f"corr_{uuid4().hex[:12]}",
            session_id=session_id,
            agent_id=agent_id,
            correction_type=correction_type,
            trigger=trigger,
            outcome=outcome,
            original_content=original_content,
            corrected_content=corrected_content,
            original_confidence=original_confidence,
            corrected_confidence=corrected_confidence,
            latency_seconds=latency_seconds,
            iteration_count=iteration_count,
            metadata=metadata or {},
        )

        async with self._events_lock:
            self._events.append(event)
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events :]

        # Update metrics
        labels = {"type": correction_type.value}
        await self.corrections_total.inc(
            labels={
                "type": correction_type.value,
                "trigger": trigger.value,
                "outcome": outcome.value,
            }
        )
        await self.latency.observe(latency_seconds, labels=labels)
        await self.iterations.observe(iteration_count, labels=labels)
        await self.confidence_delta.observe(
            event.confidence_delta,
            labels={"type": correction_type.value, "outcome": outcome.value},
        )

        # Update pattern
        self._update_pattern(event)

        # Update learning curve
        self._update_learning_curve(agent_id, outcome)

        # Check for anomalies
        anomalies = self._detect_anomalies(event)
        if anomalies:
            for anomaly in anomalies:
                self.logger.warning(
                    "analytics.anomaly_detected",
                    event_id=event.event_id,
                    anomaly=anomaly,
                )

        self.logger.debug(
            "analytics.correction_recorded",
            event_id=event.event_id,
            type=correction_type.value,
            outcome=outcome.value,
            confidence_delta=event.confidence_delta,
        )

        return event

    def _update_pattern(self, event: CorrectionEvent) -> None:
        """Update pattern tracking."""
        key = (event.correction_type, event.trigger)

        if key not in self._patterns:
            self._patterns[key] = CorrectionPattern(
                pattern_id=f"pattern_{uuid4().hex[:8]}",
                correction_type=event.correction_type,
                trigger=event.trigger,
                frequency=0,
                avg_confidence_improvement=0.0,
                avg_latency=0.0,
                success_rate=0.0,
                first_seen=event.timestamp,
                last_seen=event.timestamp,
            )

        pattern = self._patterns[key]
        n = pattern.frequency

        # Running averages
        pattern.avg_confidence_improvement = (
            pattern.avg_confidence_improvement * n + event.confidence_delta
        ) / (n + 1)
        pattern.avg_latency = (pattern.avg_latency * n + event.latency_seconds) / (n + 1)

        # Success rate
        is_success = event.outcome in (CorrectionOutcome.IMPROVED, CorrectionOutcome.PARTIAL)
        pattern.success_rate = (pattern.success_rate * n + (1 if is_success else 0)) / (n + 1)

        pattern.frequency = n + 1
        pattern.last_seen = event.timestamp

    def _update_learning_curve(self, agent_id: str, outcome: CorrectionOutcome) -> None:
        """Update learning curve for an agent."""
        if agent_id not in self._learning_curves:
            self._learning_curves[agent_id] = LearningCurve(agent_id=agent_id)

        curve = self._learning_curves[agent_id]

        # Calculate recent success rate
        recent_events = [e for e in self._events[-100:] if e.agent_id == agent_id]

        if recent_events:
            success_count = sum(
                1
                for e in recent_events
                if e.outcome in (CorrectionOutcome.IMPROVED, CorrectionOutcome.PARTIAL)
            )
            success_rate = success_count / len(recent_events)
            curve.add_point(datetime.now(UTC), success_rate)

            # Update gauge
            self.success_rate.set_sync(success_rate, labels={"agent_id": agent_id})

    def _detect_anomalies(self, event: CorrectionEvent) -> list[dict[str, Any]]:
        """Detect anomalies in the correction event."""
        anomalies = []

        # Check latency
        latency_key = f"latency_{event.correction_type.value}"
        baseline = self._baselines[latency_key]
        if baseline["std"] > 0:
            z_score = (event.latency_seconds - baseline["mean"]) / baseline["std"]
            if abs(z_score) > self.anomaly_threshold:
                anomalies.append(
                    {
                        "type": "latency_anomaly",
                        "z_score": z_score,
                        "value": event.latency_seconds,
                        "expected_mean": baseline["mean"],
                    }
                )

        # Check confidence degradation
        if event.confidence_delta < -0.3:
            anomalies.append(
                {
                    "type": "confidence_degradation",
                    "delta": event.confidence_delta,
                    "original": event.original_confidence,
                    "corrected": event.corrected_confidence,
                }
            )

        # Check excessive iterations
        if event.iteration_count > 5:
            anomalies.append(
                {
                    "type": "excessive_iterations",
                    "count": event.iteration_count,
                }
            )

        # Update baselines
        self._update_baseline(latency_key, event.latency_seconds)

        return anomalies

    def _update_baseline(self, key: str, value: float) -> None:
        """Update running baseline statistics using Welford's algorithm."""
        baseline = self._baselines[key]
        count = baseline.get("count", 0) + 1

        if count == 1:
            baseline["mean"] = value
            baseline["std"] = 0.0
            baseline["m2"] = 0.0
        else:
            delta = value - baseline["mean"]
            baseline["mean"] += delta / count
            delta2 = value - baseline["mean"]
            baseline["m2"] += delta * delta2

            if count > 1:
                baseline["std"] = (baseline["m2"] / (count - 1)) ** 0.5

        baseline["count"] = count

    def get_events(
        self,
        agent_id: str | None = None,
        session_id: str | None = None,
        correction_type: CorrectionType | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CorrectionEvent]:
        """Get correction events with filters.

        Args:
            agent_id: Filter by agent
            session_id: Filter by session
            correction_type: Filter by type
            since: Events since this time
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        events = self._events

        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        if correction_type:
            events = [e for e in events if e.correction_type == correction_type]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def get_patterns(
        self,
        min_frequency: int = 5,
        top_n: int = 10,
    ) -> list[CorrectionPattern]:
        """Get top correction patterns.

        Args:
            min_frequency: Minimum occurrences
            top_n: Number of patterns to return

        Returns:
            List of top patterns
        """
        patterns = [p for p in self._patterns.values() if p.frequency >= min_frequency]

        # Sort by effectiveness (success rate * frequency)
        patterns.sort(
            key=lambda p: p.success_rate * p.frequency,
            reverse=True,
        )

        return patterns[:top_n]

    def get_learning_curve(self, agent_id: str) -> LearningCurve | None:
        """Get learning curve for an agent."""
        return self._learning_curves.get(agent_id)

    def get_summary(
        self,
        since: datetime | None = None,
    ) -> AnalyticsSummary:
        """Get analytics summary.

        Args:
            since: Start time for summary (default: all time)

        Returns:
            AnalyticsSummary
        """
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since]

        if not events:
            return AnalyticsSummary(
                total_corrections=0,
                success_rate=0.0,
                avg_confidence_improvement=0.0,
                avg_latency=0.0,
                avg_iterations=0.0,
                corrections_by_type={},
                corrections_by_trigger={},
                corrections_by_outcome={},
                top_patterns=[],
                anomalies=[],
                time_range=(datetime.now(UTC), datetime.now(UTC)),
            )

        # Calculate aggregates
        success_outcomes = (CorrectionOutcome.IMPROVED, CorrectionOutcome.PARTIAL)
        successes = sum(1 for e in events if e.outcome in success_outcomes)

        by_type: dict[str, int] = defaultdict(int)
        by_trigger: dict[str, int] = defaultdict(int)
        by_outcome: dict[str, int] = defaultdict(int)

        for e in events:
            by_type[e.correction_type.value] += 1
            by_trigger[e.trigger.value] += 1
            by_outcome[e.outcome.value] += 1

        # Get anomalies from recent events
        recent_anomalies = []
        for event in events[-50:]:
            anomalies = self._detect_anomalies(event)
            for anomaly in anomalies:
                recent_anomalies.append(
                    {
                        "event_id": event.event_id,
                        **anomaly,
                    }
                )

        return AnalyticsSummary(
            total_corrections=len(events),
            success_rate=successes / len(events),
            avg_confidence_improvement=sum(e.confidence_delta for e in events) / len(events),
            avg_latency=sum(e.latency_seconds for e in events) / len(events),
            avg_iterations=sum(e.iteration_count for e in events) / len(events),
            corrections_by_type=dict(by_type),
            corrections_by_trigger=dict(by_trigger),
            corrections_by_outcome=dict(by_outcome),
            top_patterns=self.get_patterns(),
            anomalies=recent_anomalies[-10:],
            time_range=(events[0].timestamp, events[-1].timestamp),
        )

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        sections = [
            self.corrections_total.to_prometheus(),
            self.success_rate.to_prometheus(),
            self.latency.to_prometheus(),
            self.iterations.to_prometheus(),
            self.confidence_delta.to_prometheus(),
        ]
        return "\n\n".join(sections)

    def export_report(self, output_format: str = "json") -> str:
        """Export analytics report.

        Args:
            output_format: Output format (json, markdown)

        Returns:
            Formatted report
        """
        summary = self.get_summary()

        if output_format == "json":
            return json.dumps(summary.to_dict(), indent=2)

        if output_format == "markdown":
            lines = [
                "# Self-Correction Analytics Report",
                "",
                f"**Time Range:** {summary.time_range[0]} to {summary.time_range[1]}",
                "",
                "## Summary Statistics",
                "",
                f"- Total Corrections: {summary.total_corrections}",
                f"- Success Rate: {summary.success_rate:.2%}",
                f"- Avg Confidence Improvement: {summary.avg_confidence_improvement:+.3f}",
                f"- Avg Latency: {summary.avg_latency:.2f}s",
                f"- Avg Iterations: {summary.avg_iterations:.1f}",
                "",
                "## Corrections by Type",
                "",
            ]

            for type_name, count in sorted(
                summary.corrections_by_type.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"- {type_name}: {count}")

            lines.extend(
                [
                    "",
                    "## Corrections by Trigger",
                    "",
                ]
            )

            for trigger_name, count in sorted(
                summary.corrections_by_trigger.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"- {trigger_name}: {count}")

            lines.extend(
                [
                    "",
                    "## Top Patterns",
                    "",
                ]
            )

            for pattern in summary.top_patterns[:5]:
                lines.append(
                    f"- {pattern.correction_type.value} via {pattern.trigger.value}: "
                    f"{pattern.frequency} occurrences, "
                    f"{pattern.success_rate:.1%} success rate"
                )

            if summary.anomalies:
                lines.extend(
                    [
                        "",
                        "## Recent Anomalies",
                        "",
                    ]
                )
                for anomaly in summary.anomalies:
                    lines.append(f"- Event {anomaly['event_id']}: {anomaly['type']}")

            return "\n".join(lines)

        raise ValueError(f"Unknown format: {output_format}")

    async def reset(self) -> None:
        """Reset all analytics data."""
        async with self._events_lock:
            self._events.clear()

        self.corrections_total.reset()
        self.success_rate.reset()
        self.latency.reset()
        self.iterations.reset()
        self.confidence_delta.reset()

        self._patterns.clear()
        self._learning_curves.clear()
        self._baselines.clear()

        self.logger.info("analytics.reset")


# Global instance
_analytics: SelfCorrectionAnalytics | None = None


def get_self_correction_analytics() -> SelfCorrectionAnalytics:
    """Get global self-correction analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = SelfCorrectionAnalytics()
    return _analytics


def set_self_correction_analytics(analytics: SelfCorrectionAnalytics) -> None:
    """Set global self-correction analytics instance."""
    global _analytics
    _analytics = analytics


__all__ = [
    "AnalyticsSummary",
    "CorrectionEvent",
    "CorrectionOutcome",
    "CorrectionPattern",
    "CorrectionTrigger",
    "CorrectionType",
    "LearningCurve",
    "SelfCorrectionAnalytics",
    "get_self_correction_analytics",
    "set_self_correction_analytics",
]
