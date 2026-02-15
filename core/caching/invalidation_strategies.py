"""Cache Invalidation Strategies for Intelligent Caching.

Implements various invalidation strategies for the multi-level cache:
- TTL-based expiration
- Event-driven invalidation
- Pattern-based invalidation
- Dependency-tracking invalidation
- Adaptive invalidation based on usage patterns
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import re
from re import Pattern
import time
from typing import Any

logger = logging.getLogger(__name__)


class InvalidationReason(str, Enum):
    """Reason for cache invalidation."""

    TTL_EXPIRED = "ttl_expired"
    MANUAL = "manual"
    DEPENDENCY_CHANGED = "dependency_changed"
    PATTERN_MATCH = "pattern_match"
    EVENT_TRIGGERED = "event_triggered"
    ADAPTIVE = "adaptive"
    MEMORY_PRESSURE = "memory_pressure"


@dataclass
class InvalidationEvent:
    """Record of a cache invalidation."""

    key: str
    reason: InvalidationReason
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "reason": self.reason.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class CacheEntry:
    """Cache entry with metadata for invalidation tracking."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: float | None = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    dependencies: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


class InvalidationStrategy(ABC):
    """Abstract base class for invalidation strategies."""

    @abstractmethod
    async def should_invalidate(self, entry: CacheEntry) -> bool:
        """Determine if entry should be invalidated."""

    @abstractmethod
    async def on_access(self, entry: CacheEntry) -> None:
        """Called when entry is accessed."""

    @abstractmethod
    async def on_write(self, entry: CacheEntry) -> None:
        """Called when entry is written."""


class TTLInvalidationStrategy(InvalidationStrategy):
    """Time-to-live based invalidation."""

    def __init__(
        self,
        default_ttl: float = 3600.0,
        max_ttl: float = 86400.0,
    ):
        self.default_ttl = default_ttl
        self.max_ttl = max_ttl

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        return entry.is_expired

    async def on_access(self, entry: CacheEntry) -> None:
        entry.last_accessed = time.time()
        entry.access_count += 1

    async def on_write(self, entry: CacheEntry) -> None:
        if entry.ttl is None:
            entry.ttl = self.default_ttl
        entry.ttl = min(entry.ttl, self.max_ttl)


class SlidingWindowStrategy(InvalidationStrategy):
    """Sliding window TTL that extends on access."""

    def __init__(
        self,
        base_ttl: float = 3600.0,
        extension_per_access: float = 300.0,
        max_ttl: float = 86400.0,
    ):
        self.base_ttl = base_ttl
        self.extension_per_access = extension_per_access
        self.max_ttl = max_ttl

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        effective_ttl = min(
            self.base_ttl + entry.access_count * self.extension_per_access,
            self.max_ttl,
        )
        return time.time() > entry.created_at + effective_ttl

    async def on_access(self, entry: CacheEntry) -> None:
        entry.last_accessed = time.time()
        entry.access_count += 1
        # Extend TTL on access
        if entry.ttl:
            entry.ttl = min(entry.ttl + self.extension_per_access, self.max_ttl)

    async def on_write(self, entry: CacheEntry) -> None:
        if entry.ttl is None:
            entry.ttl = self.base_ttl


class DependencyTrackingStrategy(InvalidationStrategy):
    """Invalidation based on dependency changes."""

    def __init__(self):
        self._dependencies: dict[str, set[str]] = defaultdict(set)
        self._invalidated: set[str] = set()

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        # Check if any dependency was invalidated
        return bool(entry.dependencies & self._invalidated)

    async def on_access(self, entry: CacheEntry) -> None:
        entry.last_accessed = time.time()
        entry.access_count += 1

    async def on_write(self, entry: CacheEntry) -> None:
        # Register dependencies
        for dep in entry.dependencies:
            self._dependencies[dep].add(entry.key)

    async def invalidate_dependency(self, dependency_key: str) -> set[str]:
        """Invalidate all entries depending on a key."""
        self._invalidated.add(dependency_key)
        dependent_keys = self._dependencies.get(dependency_key, set())

        # Cascade invalidation
        all_invalidated = {dependency_key}
        for key in dependent_keys:
            all_invalidated.update(await self.invalidate_dependency(key))

        return all_invalidated

    def clear_invalidation_state(self) -> None:
        """Clear invalidation tracking."""
        self._invalidated.clear()


class PatternMatchingStrategy(InvalidationStrategy):
    """Invalidation based on pattern matching."""

    def __init__(self):
        self._patterns: list[tuple[Pattern[str], InvalidationReason]] = []
        self._pattern_hits: dict[str, int] = defaultdict(int)

    def add_pattern(
        self, pattern: str, reason: InvalidationReason = InvalidationReason.PATTERN_MATCH
    ) -> None:
        """Add an invalidation pattern."""
        compiled = re.compile(pattern)
        self._patterns.append((compiled, reason))

    def remove_pattern(self, pattern: str) -> bool:
        """Remove an invalidation pattern."""
        for i, (compiled, _) in enumerate(self._patterns):
            if compiled.pattern == pattern:
                self._patterns.pop(i)
                return True
        return False

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        for pattern, _ in self._patterns:
            if pattern.match(entry.key):
                self._pattern_hits[pattern.pattern] += 1
                return True
        return False

    async def on_access(self, entry: CacheEntry) -> None:
        entry.last_accessed = time.time()
        entry.access_count += 1

    async def on_write(self, entry: CacheEntry) -> None:
        pass

    def get_pattern_stats(self) -> dict[str, int]:
        """Get statistics on pattern matches."""
        return dict(self._pattern_hits)


class AdaptiveInvalidationStrategy(InvalidationStrategy):
    """Adaptive invalidation based on usage patterns."""

    def __init__(
        self,
        base_ttl: float = 3600.0,
        min_ttl: float = 60.0,
        max_ttl: float = 86400.0,
        learning_rate: float = 0.1,
    ):
        self.base_ttl = base_ttl
        self.min_ttl = min_ttl
        self.max_ttl = max_ttl
        self.learning_rate = learning_rate

        # Track access patterns
        self._access_history: dict[str, list[float]] = defaultdict(list)
        self._optimal_ttls: dict[str, float] = {}

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        optimal_ttl = self._optimal_ttls.get(entry.key, self.base_ttl)
        return time.time() > entry.created_at + optimal_ttl

    async def on_access(self, entry: CacheEntry) -> None:
        now = time.time()
        entry.last_accessed = now
        entry.access_count += 1

        # Record access for pattern learning
        history = self._access_history[entry.key]
        history.append(now)

        # Keep only recent history
        cutoff = now - self.max_ttl
        self._access_history[entry.key] = [t for t in history if t > cutoff]

        # Update optimal TTL
        await self._update_optimal_ttl(entry.key)

    async def on_write(self, entry: CacheEntry) -> None:
        if entry.key not in self._optimal_ttls:
            self._optimal_ttls[entry.key] = self.base_ttl

    async def _update_optimal_ttl(self, key: str) -> None:
        """Update optimal TTL based on access history."""
        history = self._access_history[key]
        if len(history) < 2:
            return

        # Calculate average inter-access time
        intervals = [history[i] - history[i - 1] for i in range(1, len(history))]
        avg_interval = sum(intervals) / len(intervals)

        # Adjust optimal TTL toward average interval
        current_ttl = self._optimal_ttls.get(key, self.base_ttl)
        new_ttl = current_ttl + self.learning_rate * (avg_interval - current_ttl)

        # Clamp to bounds
        self._optimal_ttls[key] = max(self.min_ttl, min(self.max_ttl, new_ttl))


class EventDrivenInvalidationStrategy(InvalidationStrategy):
    """Event-driven cache invalidation."""

    def __init__(self):
        self._event_handlers: dict[str, list[Callable[[Any], set[str]]]] = defaultdict(list)
        self._invalidated_by_event: set[str] = set()

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[Any], set[str]],
    ) -> None:
        """Register handler that returns keys to invalidate for an event."""
        self._event_handlers[event_type].append(handler)

    async def emit_event(self, event_type: str, event_data: Any) -> set[str]:
        """Emit event and collect keys to invalidate."""
        invalidated = set()
        for handler in self._event_handlers.get(event_type, []):
            keys = handler(event_data)
            invalidated.update(keys)
            self._invalidated_by_event.update(keys)
        return invalidated

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        return entry.key in self._invalidated_by_event

    async def on_access(self, entry: CacheEntry) -> None:
        entry.last_accessed = time.time()
        entry.access_count += 1
        # Remove from invalidation set on access (entry was refreshed)
        self._invalidated_by_event.discard(entry.key)

    async def on_write(self, entry: CacheEntry) -> None:
        # Clear invalidation flag on write
        self._invalidated_by_event.discard(entry.key)


class CompositeInvalidationStrategy(InvalidationStrategy):
    """Composite strategy combining multiple strategies."""

    def __init__(
        self,
        strategies: list[InvalidationStrategy] | None = None,
        mode: str = "any",  # "any" or "all"
    ):
        self.strategies = strategies or []
        self.mode = mode

    def add_strategy(self, strategy: InvalidationStrategy) -> None:
        """Add a strategy to the composite."""
        self.strategies.append(strategy)

    async def should_invalidate(self, entry: CacheEntry) -> bool:
        if not self.strategies:
            return False

        results = await asyncio.gather(*[s.should_invalidate(entry) for s in self.strategies])

        if self.mode == "any":
            return any(results)
        return all(results)

    async def on_access(self, entry: CacheEntry) -> None:
        await asyncio.gather(*[s.on_access(entry) for s in self.strategies])

    async def on_write(self, entry: CacheEntry) -> None:
        await asyncio.gather(*[s.on_write(entry) for s in self.strategies])


class InvalidationManager:
    """Central manager for cache invalidation."""

    def __init__(
        self,
        strategy: InvalidationStrategy | None = None,
    ):
        self.strategy = strategy or TTLInvalidationStrategy()
        self._invalidation_history: list[InvalidationEvent] = []
        self._stats = {
            "total_invalidations": 0,
            "by_reason": defaultdict(int),
        }

    async def check_entry(self, entry: CacheEntry) -> tuple[bool, InvalidationReason | None]:
        """Check if entry should be invalidated."""
        should_invalidate = await self.strategy.should_invalidate(entry)

        if should_invalidate:
            reason = self._determine_reason(entry)
            return True, reason

        return False, None

    def _determine_reason(self, entry: CacheEntry) -> InvalidationReason:
        """Determine the reason for invalidation."""
        if entry.is_expired:
            return InvalidationReason.TTL_EXPIRED
        return InvalidationReason.ADAPTIVE

    async def invalidate(
        self,
        entry: CacheEntry,
        reason: InvalidationReason = InvalidationReason.MANUAL,
        metadata: dict[str, Any] | None = None,
    ) -> InvalidationEvent:
        """Record an invalidation event."""
        event = InvalidationEvent(
            key=entry.key,
            reason=reason,
            metadata=metadata or {},
        )

        self._invalidation_history.append(event)
        self._stats["total_invalidations"] += 1
        self._stats["by_reason"][reason.value] += 1

        return event

    async def on_access(self, entry: CacheEntry) -> None:
        """Handle entry access."""
        await self.strategy.on_access(entry)

    async def on_write(self, entry: CacheEntry) -> None:
        """Handle entry write."""
        await self.strategy.on_write(entry)

    def get_stats(self) -> dict[str, Any]:
        """Get invalidation statistics."""
        return {
            "total_invalidations": self._stats["total_invalidations"],
            "by_reason": dict(self._stats["by_reason"]),
            "history_size": len(self._invalidation_history),
        }

    def get_recent_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent invalidation history."""
        return [e.to_dict() for e in self._invalidation_history[-limit:]]


# Factory functions
def create_default_invalidation_strategy() -> CompositeInvalidationStrategy:
    """Create default composite invalidation strategy."""
    return CompositeInvalidationStrategy(
        strategies=[
            TTLInvalidationStrategy(),
            SlidingWindowStrategy(),
            AdaptiveInvalidationStrategy(),
        ],
        mode="any",
    )


def create_invalidation_manager(
    use_adaptive: bool = True,
    base_ttl: float = 3600.0,
) -> InvalidationManager:
    """Create an invalidation manager with common configuration."""
    if use_adaptive:
        strategy = create_default_invalidation_strategy()
    else:
        strategy = TTLInvalidationStrategy(default_ttl=base_ttl)

    return InvalidationManager(strategy=strategy)


__all__ = [
    "AdaptiveInvalidationStrategy",
    "CacheEntry",
    "CompositeInvalidationStrategy",
    "DependencyTrackingStrategy",
    "EventDrivenInvalidationStrategy",
    "InvalidationEvent",
    "InvalidationManager",
    "InvalidationReason",
    "InvalidationStrategy",
    "PatternMatchingStrategy",
    "SlidingWindowStrategy",
    "TTLInvalidationStrategy",
    "create_default_invalidation_strategy",
    "create_invalidation_manager",
]
