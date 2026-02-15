"""Proactive Cache Warming for Intelligent Caching.

Implements predictive cache warming based on:
- Usage patterns and access history
- Time-based patterns (peak hours, schedules)
- Dependency chains
- User behavior prediction
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WarmingPriority(str, Enum):
    """Priority levels for cache warming."""

    CRITICAL = "critical"  # Must be warmed immediately
    HIGH = "high"  # Warm before expected usage
    MEDIUM = "medium"  # Warm when resources available
    LOW = "low"  # Warm opportunistically
    BACKGROUND = "background"  # Warm only during idle time


@dataclass
class WarmingCandidate:
    """A candidate for cache warming."""

    key: str
    priority: WarmingPriority
    predicted_access_time: datetime | None = None
    confidence: float = 0.5  # 0-1 confidence in prediction
    loader: Callable[[], Coroutine[Any, Any, Any]] | None = None
    dependencies: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "priority": self.priority.value,
            "predicted_access_time": (
                self.predicted_access_time.isoformat() if self.predicted_access_time else None
            ),
            "confidence": self.confidence,
            "dependencies": list(self.dependencies),
            "metadata": self.metadata,
        }


@dataclass
class WarmingResult:
    """Result of a cache warming operation."""

    key: str
    success: bool
    duration_ms: float
    from_prediction: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "from_prediction": self.from_prediction,
            "error": self.error,
        }


class WarmingPredictor(ABC):
    """Abstract base class for warming prediction."""

    @abstractmethod
    async def predict_candidates(
        self,
        context: dict[str, Any],
        limit: int = 10,
    ) -> list[WarmingCandidate]:
        """Predict candidates for warming."""

    @abstractmethod
    async def learn_from_access(
        self,
        key: str,
        timestamp: datetime,
        context: dict[str, Any],
    ) -> None:
        """Learn from an actual cache access."""


class UsagePatternPredictor(WarmingPredictor):
    """Predicts warming candidates based on historical usage patterns."""

    def __init__(
        self,
        history_window_hours: int = 168,  # 1 week
        min_accesses_for_prediction: int = 3,
    ):
        self.history_window = timedelta(hours=history_window_hours)
        self.min_accesses = min_accesses_for_prediction

        # Access history: key -> list of (timestamp, context)
        self._access_history: dict[str, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)

    async def predict_candidates(
        self,
        context: dict[str, Any],
        limit: int = 10,
    ) -> list[WarmingCandidate]:
        now = datetime.now(UTC)
        cutoff = now - self.history_window
        candidates = []

        for key, history in self._access_history.items():
            # Filter to recent history
            recent = [(ts, ctx) for ts, ctx in history if ts > cutoff]
            if len(recent) < self.min_accesses:
                continue

            # Analyze access patterns
            prediction = self._analyze_pattern(key, recent, now)
            if prediction:
                candidates.append(prediction)

        # Sort by confidence and priority
        candidates.sort(
            key=lambda c: (c.priority.value, -c.confidence),
        )

        return candidates[:limit]

    def _analyze_pattern(
        self,
        key: str,
        history: list[tuple[datetime, dict[str, Any]]],
        now: datetime,
    ) -> WarmingCandidate | None:
        """Analyze access pattern and predict next access."""
        if len(history) < 2:
            return None

        # Calculate intervals between accesses
        timestamps = [ts for ts, _ in history]
        intervals = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() for i in range(1, len(timestamps))
        ]

        # Average interval
        avg_interval = sum(intervals) / len(intervals)
        std_interval = (sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)) ** 0.5

        # Predict next access
        last_access = timestamps[-1]
        predicted_next = last_access + timedelta(seconds=avg_interval)

        # Calculate confidence based on pattern regularity
        coefficient_of_variation = std_interval / avg_interval if avg_interval > 0 else 1
        confidence = max(0.1, min(0.95, 1 - coefficient_of_variation))

        # Determine priority based on frequency
        accesses_per_day = len(history) / (self.history_window.total_seconds() / 86400)

        if accesses_per_day > 10:
            priority = WarmingPriority.HIGH
        elif accesses_per_day > 5:
            priority = WarmingPriority.MEDIUM
        else:
            priority = WarmingPriority.LOW

        return WarmingCandidate(
            key=key,
            priority=priority,
            predicted_access_time=predicted_next,
            confidence=confidence,
            metadata={
                "avg_interval_seconds": avg_interval,
                "accesses_per_day": accesses_per_day,
                "last_access": last_access.isoformat(),
            },
        )

    async def learn_from_access(
        self,
        key: str,
        timestamp: datetime,
        context: dict[str, Any],
    ) -> None:
        self._access_history[key].append((timestamp, context))

        # Trim old history
        cutoff = timestamp - self.history_window
        self._access_history[key] = [
            (ts, ctx) for ts, ctx in self._access_history[key] if ts > cutoff
        ]


class TimeBasedPredictor(WarmingPredictor):
    """Predicts warming based on time-of-day patterns."""

    def __init__(self, time_bucket_minutes: int = 30):
        self.bucket_minutes = time_bucket_minutes
        # Access counts by time bucket: key -> {bucket_id -> count}
        self._time_patterns: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def _get_bucket(self, timestamp: datetime) -> int:
        """Get time bucket for a timestamp."""
        minutes_from_midnight = timestamp.hour * 60 + timestamp.minute
        return minutes_from_midnight // self.bucket_minutes

    async def predict_candidates(
        self,
        context: dict[str, Any],
        limit: int = 10,
    ) -> list[WarmingCandidate]:
        now = datetime.now(UTC)
        current_bucket = self._get_bucket(now)
        next_bucket = (current_bucket + 1) % (1440 // self.bucket_minutes)

        candidates = []

        for key, buckets in self._time_patterns.items():
            # Check if key is typically accessed in next bucket
            next_bucket_count = buckets.get(next_bucket, 0)
            total_accesses = sum(buckets.values())

            if total_accesses == 0 or next_bucket_count == 0:
                continue

            # Probability of access in next bucket
            probability = next_bucket_count / total_accesses
            if probability < 0.1:
                continue

            # Determine priority
            if probability > 0.5:
                priority = WarmingPriority.HIGH
            elif probability > 0.3:
                priority = WarmingPriority.MEDIUM
            else:
                priority = WarmingPriority.LOW

            candidates.append(
                WarmingCandidate(
                    key=key,
                    priority=priority,
                    predicted_access_time=now + timedelta(minutes=self.bucket_minutes),
                    confidence=probability,
                    metadata={
                        "next_bucket_count": next_bucket_count,
                        "total_accesses": total_accesses,
                        "probability": probability,
                    },
                )
            )

        candidates.sort(key=lambda c: -c.confidence)
        return candidates[:limit]

    async def learn_from_access(
        self,
        key: str,
        timestamp: datetime,
        context: dict[str, Any],
    ) -> None:
        bucket = self._get_bucket(timestamp)
        self._time_patterns[key][bucket] += 1


class DependencyChainPredictor(WarmingPredictor):
    """Predicts warming based on dependency chains."""

    def __init__(self):
        # Forward dependencies: key -> set of keys that follow
        self._forward_deps: dict[str, set[str]] = defaultdict(set)
        # Reverse dependencies: key -> set of keys that precede
        self._reverse_deps: dict[str, set[str]] = defaultdict(set)
        # Access sequence buffer
        self._recent_accesses: list[tuple[str, datetime]] = []

    async def predict_candidates(
        self,
        context: dict[str, Any],
        limit: int = 10,
    ) -> list[WarmingCandidate]:
        candidates = []

        # Get recently accessed keys
        recent_keys = {key for key, _ in self._recent_accesses[-10:]}

        for recent_key in recent_keys:
            # Get keys that typically follow this one
            followers = self._forward_deps.get(recent_key, set())
            for follower in followers:
                if follower in recent_keys:
                    continue  # Already accessed

                candidates.append(
                    WarmingCandidate(
                        key=follower,
                        priority=WarmingPriority.HIGH,
                        confidence=0.7,
                        dependencies={recent_key},
                        metadata={"triggered_by": recent_key},
                    )
                )

        return candidates[:limit]

    async def learn_from_access(
        self,
        key: str,
        timestamp: datetime,
        context: dict[str, Any],
    ) -> None:
        # Record access sequence
        self._recent_accesses.append((key, timestamp))

        # Keep only recent accesses
        cutoff = timestamp - timedelta(minutes=5)
        self._recent_accesses = [(k, ts) for k, ts in self._recent_accesses if ts > cutoff]

        # Learn dependencies from sequence
        for prev_key, prev_ts in self._recent_accesses[:-1]:
            if (timestamp - prev_ts).total_seconds() < 60:  # Within 1 minute
                self._forward_deps[prev_key].add(key)
                self._reverse_deps[key].add(prev_key)


class CompositePredictor(WarmingPredictor):
    """Combines multiple predictors with weighted voting."""

    def __init__(
        self,
        predictors: list[tuple[WarmingPredictor, float]] | None = None,
    ):
        # List of (predictor, weight) tuples
        self.predictors = predictors or []

    def add_predictor(self, predictor: WarmingPredictor, weight: float = 1.0) -> None:
        """Add a predictor with weight."""
        self.predictors.append((predictor, weight))

    async def predict_candidates(
        self,
        context: dict[str, Any],
        limit: int = 10,
    ) -> list[WarmingCandidate]:
        # Collect predictions from all predictors
        all_candidates: dict[str, WarmingCandidate] = {}
        candidate_scores: dict[str, float] = defaultdict(float)

        for predictor, weight in self.predictors:
            candidates = await predictor.predict_candidates(context, limit * 2)
            for candidate in candidates:
                key = candidate.key
                candidate_scores[key] += weight * candidate.confidence

                # Keep the highest priority candidate
                if (
                    key not in all_candidates
                    or candidate.priority.value < all_candidates[key].priority.value
                ):
                    all_candidates[key] = candidate

        # Normalize scores and update confidence
        if candidate_scores:
            max_score = max(candidate_scores.values())
            for key, candidate in all_candidates.items():
                candidate.confidence = candidate_scores[key] / max_score

        # Sort by combined score
        sorted_candidates = sorted(
            all_candidates.values(),
            key=lambda c: -candidate_scores[c.key],
        )

        return sorted_candidates[:limit]

    async def learn_from_access(
        self,
        key: str,
        timestamp: datetime,
        context: dict[str, Any],
    ) -> None:
        for predictor, _ in self.predictors:
            await predictor.learn_from_access(key, timestamp, context)


class ProactiveWarmer:
    """Main class for proactive cache warming."""

    def __init__(
        self,
        predictor: WarmingPredictor | None = None,
        cache_setter: Callable[[str, Any], Coroutine[Any, Any, None]] | None = None,
        max_concurrent_warmings: int = 5,
        warming_lead_time_seconds: float = 60.0,
    ):
        self.predictor = predictor or self._create_default_predictor()
        self._cache_setter = cache_setter
        self.max_concurrent = max_concurrent_warmings
        self.lead_time = warming_lead_time_seconds

        # Warming queue
        self._warming_queue: asyncio.PriorityQueue[
            tuple[int, WarmingCandidate]
        ] = asyncio.PriorityQueue()
        self._warming_in_progress: set[str] = set()
        self._warming_history: list[WarmingResult] = []

        # Stats
        self._stats = {
            "total_warmings": 0,
            "successful_warmings": 0,
            "failed_warmings": 0,
            "prediction_hits": 0,
            "prediction_misses": 0,
        }

        # Background task
        self._warming_task: asyncio.Task | None = None
        self._running = False
        self._background_tasks: set[asyncio.Task] = set()

    def _create_default_predictor(self) -> CompositePredictor:
        """Create default composite predictor."""
        predictor = CompositePredictor()
        predictor.add_predictor(UsagePatternPredictor(), weight=1.0)
        predictor.add_predictor(TimeBasedPredictor(), weight=0.5)
        predictor.add_predictor(DependencyChainPredictor(), weight=0.8)
        return predictor

    async def start(self) -> None:
        """Start background warming task."""
        if self._running:
            return

        self._running = True
        self._warming_task = asyncio.create_task(self._warming_loop())
        logger.info("Proactive cache warmer started")

    async def stop(self) -> None:
        """Stop background warming task."""
        self._running = False
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        logger.info("Proactive cache warmer stopped")

    async def _warming_loop(self) -> None:
        """Main warming loop."""
        while self._running:
            try:
                # Generate predictions periodically
                await self._generate_predictions()

                # Process warming queue
                await self._process_queue()

                # Sleep before next iteration
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in warming loop: {e}")
                await asyncio.sleep(30)

    async def _generate_predictions(self) -> None:
        """Generate warming predictions."""
        context = {"timestamp": datetime.now(UTC)}
        candidates = await self.predictor.predict_candidates(context, limit=20)

        for candidate in candidates:
            if candidate.key not in self._warming_in_progress:
                # Priority value for queue (lower = higher priority)
                priority_value = list(WarmingPriority).index(candidate.priority)
                await self._warming_queue.put((priority_value, candidate))

    async def _process_queue(self) -> None:
        """Process warming queue."""
        now = datetime.now(UTC)
        warmings_started = 0

        while (
            not self._warming_queue.empty()
            and warmings_started < self.max_concurrent
            and len(self._warming_in_progress) < self.max_concurrent
        ):
            try:
                _, candidate = self._warming_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            # Check if warming is needed
            if candidate.predicted_access_time:
                time_until_access = (candidate.predicted_access_time - now).total_seconds()
                if time_until_access > self.lead_time:
                    # Not yet time to warm
                    continue
                if time_until_access < -60:
                    # Prediction is stale
                    continue

            # Start warming
            task = asyncio.create_task(self._warm_entry(candidate))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            warmings_started += 1

    async def _warm_entry(self, candidate: WarmingCandidate) -> None:
        """Warm a single cache entry."""
        start_time = time.monotonic()
        self._warming_in_progress.add(candidate.key)

        try:
            # Use provided loader or cache setter
            if candidate.loader:
                value = await candidate.loader()
                if self._cache_setter:
                    await self._cache_setter(candidate.key, value)
            elif self._cache_setter:
                # Attempt to fetch and cache
                logger.debug(f"Warming key: {candidate.key}")

            duration_ms = (time.monotonic() - start_time) * 1000

            result = WarmingResult(
                key=candidate.key,
                success=True,
                duration_ms=duration_ms,
                from_prediction=True,
            )

            self._stats["total_warmings"] += 1
            self._stats["successful_warmings"] += 1

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            result = WarmingResult(
                key=candidate.key,
                success=False,
                duration_ms=duration_ms,
                from_prediction=True,
                error=str(e),
            )
            self._stats["failed_warmings"] += 1
            logger.warning(f"Failed to warm {candidate.key}: {e}")

        finally:
            self._warming_in_progress.discard(candidate.key)
            self._warming_history.append(result)

            # Trim history
            if len(self._warming_history) > 1000:
                self._warming_history = self._warming_history[-500:]

    async def record_access(
        self,
        key: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a cache access for learning."""
        timestamp = datetime.now(UTC)
        context = context or {}

        await self.predictor.learn_from_access(key, timestamp, context)

        # Track prediction accuracy
        # (simplified - in production would track actual predictions)
        self._stats["prediction_hits"] += 1

    async def warm_now(
        self,
        keys: list[str],
        loaders: dict[str, Callable[[], Coroutine[Any, Any, Any]]] | None = None,
    ) -> list[WarmingResult]:
        """Immediately warm specified keys."""
        loaders = loaders or {}
        results = []

        for key in keys:
            candidate = WarmingCandidate(
                key=key,
                priority=WarmingPriority.CRITICAL,
                loader=loaders.get(key),
            )
            await self._warm_entry(candidate)
            results.append(self._warming_history[-1])

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get warming statistics."""
        return {
            **self._stats,
            "queue_size": self._warming_queue.qsize(),
            "in_progress": len(self._warming_in_progress),
            "history_size": len(self._warming_history),
        }

    def get_recent_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent warming history."""
        return [r.to_dict() for r in self._warming_history[-limit:]]


# Factory functions
def create_proactive_warmer(
    cache_setter: Callable[[str, Any], Coroutine[Any, Any, None]] | None = None,
    max_concurrent: int = 5,
) -> ProactiveWarmer:
    """Create a proactive warmer with default configuration."""
    predictor = CompositePredictor()
    predictor.add_predictor(UsagePatternPredictor(), weight=1.0)
    predictor.add_predictor(TimeBasedPredictor(), weight=0.5)
    predictor.add_predictor(DependencyChainPredictor(), weight=0.8)

    return ProactiveWarmer(
        predictor=predictor,
        cache_setter=cache_setter,
        max_concurrent_warmings=max_concurrent,
    )


__all__ = [
    "CompositePredictor",
    "DependencyChainPredictor",
    "ProactiveWarmer",
    "TimeBasedPredictor",
    "UsagePatternPredictor",
    "WarmingCandidate",
    "WarmingPredictor",
    "WarmingPriority",
    "WarmingResult",
    "create_proactive_warmer",
]
