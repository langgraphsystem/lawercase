"""Fallback Manager for LLM provider resilience.

Tracks provider health and manages fallback chains:
- Circuit breaker pattern
- Exponential backoff
- Health recovery
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Any


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class ProviderHealth:
    """Health status for a provider."""

    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # Circuit breaker thresholds
    failure_threshold: int = 3  # Failures before opening circuit
    success_threshold: int = 2  # Successes to close circuit
    recovery_timeout: float = 60.0  # Seconds before half-open


@dataclass
class FallbackChain:
    """Ordered chain of providers for fallback."""

    providers: list[str]
    name: str = "default"


class FallbackManager:
    """Manages provider fallback with circuit breaker pattern.

    Features:
    - Circuit breaker to prevent cascading failures
    - Automatic recovery testing
    - Health metrics per provider
    - Configurable thresholds

    Usage:
        manager = FallbackManager()

        # Record outcomes
        manager.record_success("opus-4.5")
        manager.record_failure("chatgpt-5.2")

        # Check availability
        if manager.is_available("opus-4.5"):
            # Use provider
            pass

        # Get healthy providers
        healthy = manager.get_healthy_providers(["opus-4.5", "chatgpt-5.2", "gemini-3"])
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        success_threshold: int = 2,
        recovery_timeout: float = 60.0,
    ) -> None:
        """Initialize fallback manager.

        Args:
            failure_threshold: Failures before opening circuit
            success_threshold: Successes to close circuit
            recovery_timeout: Seconds before testing recovery
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout

        self._health: dict[str, ProviderHealth] = {}
        self._chains: dict[str, FallbackChain] = {}

    def _get_health(self, provider: str) -> ProviderHealth:
        """Get or create health record for provider."""
        if provider not in self._health:
            self._health[provider] = ProviderHealth(
                name=provider,
                failure_threshold=self.failure_threshold,
                success_threshold=self.success_threshold,
                recovery_timeout=self.recovery_timeout,
            )
        return self._health[provider]

    def _update_circuit_state(self, health: ProviderHealth) -> None:
        """Update circuit breaker state based on health."""
        current_time = time.time()

        if health.state == CircuitState.CLOSED:
            # Check if should open
            if health.consecutive_failures >= health.failure_threshold:
                health.state = CircuitState.OPEN

        elif health.state == CircuitState.OPEN:
            # Check if should try half-open
            if current_time - health.last_failure_time >= health.recovery_timeout:
                health.state = CircuitState.HALF_OPEN

        elif health.state == CircuitState.HALF_OPEN:
            # Check if should close or re-open
            if health.consecutive_successes >= health.success_threshold:
                health.state = CircuitState.CLOSED
                health.consecutive_failures = 0
            elif health.consecutive_failures > 0:
                health.state = CircuitState.OPEN

    def record_success(self, provider: str) -> None:
        """Record successful request to provider."""
        health = self._get_health(provider)
        health.success_count += 1
        health.consecutive_successes += 1
        health.consecutive_failures = 0
        health.last_success_time = time.time()
        self._update_circuit_state(health)

    def record_failure(self, provider: str) -> None:
        """Record failed request to provider."""
        health = self._get_health(provider)
        health.failure_count += 1
        health.consecutive_failures += 1
        health.consecutive_successes = 0
        health.last_failure_time = time.time()
        self._update_circuit_state(health)

    def is_available(self, provider: str) -> bool:
        """Check if provider is available (circuit not open)."""
        health = self._get_health(provider)
        self._update_circuit_state(health)
        return health.state != CircuitState.OPEN

    def get_state(self, provider: str) -> CircuitState:
        """Get current circuit state for provider."""
        health = self._get_health(provider)
        self._update_circuit_state(health)
        return health.state

    def get_healthy_providers(self, providers: list[str]) -> list[str]:
        """Filter to only healthy providers."""
        return [p for p in providers if self.is_available(p)]

    def reset(self, provider: str) -> None:
        """Reset health for provider (manual recovery)."""
        if provider in self._health:
            self._health[provider] = ProviderHealth(
                name=provider,
                failure_threshold=self.failure_threshold,
                success_threshold=self.success_threshold,
                recovery_timeout=self.recovery_timeout,
            )

    def reset_all(self) -> None:
        """Reset all provider health."""
        self._health.clear()

    def register_chain(self, name: str, providers: list[str]) -> None:
        """Register a fallback chain."""
        self._chains[name] = FallbackChain(providers=providers, name=name)

    def get_chain(self, name: str) -> list[str]:
        """Get providers in fallback chain, filtered by health."""
        chain = self._chains.get(name)
        if not chain:
            return []
        return self.get_healthy_providers(chain.providers)

    def get_stats(self) -> dict[str, Any]:
        """Get health statistics for all providers."""
        stats = {}
        for name, health in self._health.items():
            self._update_circuit_state(health)
            stats[name] = {
                "state": health.state.value,
                "failure_count": health.failure_count,
                "success_count": health.success_count,
                "consecutive_failures": health.consecutive_failures,
                "consecutive_successes": health.consecutive_successes,
                "success_rate": health.success_count
                / max(1, health.success_count + health.failure_count),
            }
        return stats

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all provider health."""
        healthy = []
        degraded = []
        unavailable = []

        for name in self._health:
            state = self.get_state(name)
            if state == CircuitState.CLOSED:
                healthy.append(name)
            elif state == CircuitState.HALF_OPEN:
                degraded.append(name)
            else:
                unavailable.append(name)

        return {
            "healthy": healthy,
            "degraded": degraded,
            "unavailable": unavailable,
            "total_tracked": len(self._health),
        }
