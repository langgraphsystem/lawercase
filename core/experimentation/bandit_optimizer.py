"""Multi-Armed Bandit Optimizer for Prompt and Model Selection.

Implements various bandit algorithms for optimizing:
- Prompt variants
- Model selection
- Parameter tuning
- Agent routing decisions

Supports Thompson Sampling, UCB, and Epsilon-Greedy strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import logging
import math
import random
from typing import Any, Generic, TypeVar

import numpy as np

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BanditStrategy(str, Enum):
    """Available bandit strategies."""

    EPSILON_GREEDY = "epsilon_greedy"
    UCB1 = "ucb1"
    THOMPSON_SAMPLING = "thompson_sampling"
    SOFTMAX = "softmax"
    EXP3 = "exp3"  # Adversarial bandit


@dataclass
class ArmStats:
    """Statistics for a single arm."""

    arm_id: str
    pulls: int = 0
    total_reward: float = 0.0
    squared_reward: float = 0.0
    last_pulled: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    @property
    def variance(self) -> float:
        if self.pulls < 2:
            return float("inf")
        mean = self.mean_reward
        return (self.squared_reward / self.pulls) - (mean * mean)

    @property
    def std_dev(self) -> float:
        var = self.variance
        return math.sqrt(var) if var != float("inf") else float("inf")


@dataclass
class BanditResult:
    """Result of a bandit selection."""

    selected_arm: str
    exploration: bool
    confidence: float
    all_scores: dict[str, float]


class BanditAlgorithm(ABC, Generic[T]):
    """Abstract base class for bandit algorithms."""

    def __init__(self, arm_ids: list[str]):
        self.arms: dict[str, ArmStats] = {arm_id: ArmStats(arm_id=arm_id) for arm_id in arm_ids}
        self._total_pulls = 0

    @abstractmethod
    def select_arm(self) -> BanditResult:
        """Select an arm to pull."""

    def update(self, arm_id: str, reward: float) -> None:
        """Update arm statistics after observing reward."""
        if arm_id not in self.arms:
            raise ValueError(f"Unknown arm: {arm_id}")

        arm = self.arms[arm_id]
        arm.pulls += 1
        arm.total_reward += reward
        arm.squared_reward += reward * reward
        arm.last_pulled = datetime.now(UTC)
        self._total_pulls += 1

    def add_arm(self, arm_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a new arm."""
        if arm_id in self.arms:
            raise ValueError(f"Arm already exists: {arm_id}")
        self.arms[arm_id] = ArmStats(arm_id=arm_id, metadata=metadata or {})

    def remove_arm(self, arm_id: str) -> None:
        """Remove an arm."""
        self.arms.pop(arm_id, None)

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all arms."""
        return {
            arm_id: {
                "pulls": arm.pulls,
                "mean_reward": arm.mean_reward,
                "std_dev": arm.std_dev,
                "total_reward": arm.total_reward,
            }
            for arm_id, arm in self.arms.items()
        }


class EpsilonGreedy(BanditAlgorithm):
    """Epsilon-greedy bandit algorithm."""

    def __init__(
        self,
        arm_ids: list[str],
        epsilon: float = 0.1,
        decay: float = 0.999,
        min_epsilon: float = 0.01,
    ):
        super().__init__(arm_ids)
        self.epsilon = epsilon
        self.decay = decay
        self.min_epsilon = min_epsilon
        self._current_epsilon = epsilon

    def select_arm(self) -> BanditResult:
        exploration = random.random() < self._current_epsilon

        if exploration or self._total_pulls < len(self.arms):
            # Explore: select randomly
            selected = random.choice(list(self.arms.keys()))
        else:
            # Exploit: select best arm
            selected = max(self.arms.keys(), key=lambda a: self.arms[a].mean_reward)

        # Decay epsilon
        self._current_epsilon = max(
            self.min_epsilon,
            self._current_epsilon * self.decay,
        )

        scores = {arm_id: arm.mean_reward for arm_id, arm in self.arms.items()}

        return BanditResult(
            selected_arm=selected,
            exploration=exploration,
            confidence=1 - self._current_epsilon,
            all_scores=scores,
        )


class UCB1(BanditAlgorithm):
    """Upper Confidence Bound (UCB1) bandit algorithm."""

    def __init__(self, arm_ids: list[str], exploration_weight: float = 2.0):
        super().__init__(arm_ids)
        self.exploration_weight = exploration_weight

    def _ucb_score(self, arm: ArmStats) -> float:
        if arm.pulls == 0:
            return float("inf")

        exploitation = arm.mean_reward
        exploration = math.sqrt(
            self.exploration_weight * math.log(self._total_pulls + 1) / arm.pulls
        )
        return exploitation + exploration

    def select_arm(self) -> BanditResult:
        scores = {arm_id: self._ucb_score(arm) for arm_id, arm in self.arms.items()}
        selected = max(scores.keys(), key=lambda a: scores[a])

        arm = self.arms[selected]
        exploration = arm.pulls == 0 or scores[selected] > arm.mean_reward * 1.5

        return BanditResult(
            selected_arm=selected,
            exploration=exploration,
            confidence=1.0 / (1.0 + math.exp(-arm.mean_reward * arm.pulls / 10)),
            all_scores=scores,
        )


class ThompsonSampling(BanditAlgorithm):
    """Thompson Sampling bandit algorithm (Beta-Bernoulli)."""

    def __init__(
        self,
        arm_ids: list[str],
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
    ):
        super().__init__(arm_ids)
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        # Track successes and failures for Beta distribution
        self._successes: dict[str, float] = dict.fromkeys(arm_ids, 0)
        self._failures: dict[str, float] = dict.fromkeys(arm_ids, 0)

    def update(self, arm_id: str, reward: float) -> None:
        """Update with reward in [0, 1] range."""
        super().update(arm_id, reward)

        # For Beta distribution, treat reward as probability of success
        if reward > 0.5:
            self._successes[arm_id] += reward
        else:
            self._failures[arm_id] += 1 - reward

    def add_arm(self, arm_id: str, metadata: dict[str, Any] | None = None) -> None:
        super().add_arm(arm_id, metadata)
        self._successes[arm_id] = 0
        self._failures[arm_id] = 0

    def remove_arm(self, arm_id: str) -> None:
        super().remove_arm(arm_id)
        self._successes.pop(arm_id, None)
        self._failures.pop(arm_id, None)

    def select_arm(self) -> BanditResult:
        samples = {}
        for arm_id in self.arms:
            alpha = self.prior_alpha + self._successes[arm_id]
            beta = self.prior_beta + self._failures[arm_id]
            samples[arm_id] = np.random.beta(alpha, beta)

        selected = max(samples.keys(), key=lambda a: samples[a])

        arm = self.arms[selected]
        exploration = arm.pulls < 10

        return BanditResult(
            selected_arm=selected,
            exploration=exploration,
            confidence=samples[selected],
            all_scores=samples,
        )


class SoftmaxBandit(BanditAlgorithm):
    """Softmax (Boltzmann) exploration bandit."""

    def __init__(
        self,
        arm_ids: list[str],
        temperature: float = 1.0,
        temperature_decay: float = 0.99,
        min_temperature: float = 0.1,
    ):
        super().__init__(arm_ids)
        self.temperature = temperature
        self.temperature_decay = temperature_decay
        self.min_temperature = min_temperature
        self._current_temp = temperature

    def select_arm(self) -> BanditResult:
        # Compute softmax probabilities
        rewards = [self.arms[a].mean_reward for a in self.arms]
        max_reward = max(rewards) if rewards else 0

        # Numerical stability
        exp_rewards = [math.exp((r - max_reward) / self._current_temp) for r in rewards]
        total = sum(exp_rewards)
        probs = [e / total for e in exp_rewards]

        # Sample according to probabilities
        arm_ids = list(self.arms.keys())
        selected = random.choices(arm_ids, weights=probs)[0]

        # Decay temperature
        self._current_temp = max(
            self.min_temperature,
            self._current_temp * self.temperature_decay,
        )

        scores = dict(zip(arm_ids, probs, strict=False))

        return BanditResult(
            selected_arm=selected,
            exploration=self._current_temp > 0.5,
            confidence=max(probs),
            all_scores=scores,
        )


class PromptOptimizer:
    """High-level optimizer for prompt selection using bandits."""

    def __init__(
        self,
        prompts: dict[str, str],
        strategy: BanditStrategy = BanditStrategy.THOMPSON_SAMPLING,
        **kwargs: Any,
    ):
        self.prompts = prompts
        self.strategy = strategy

        arm_ids = list(prompts.keys())
        if strategy == BanditStrategy.EPSILON_GREEDY:
            self.bandit = EpsilonGreedy(arm_ids, **kwargs)
        elif strategy == BanditStrategy.UCB1:
            self.bandit = UCB1(arm_ids, **kwargs)
        elif strategy == BanditStrategy.THOMPSON_SAMPLING:
            self.bandit = ThompsonSampling(arm_ids, **kwargs)
        elif strategy == BanditStrategy.SOFTMAX:
            self.bandit = SoftmaxBandit(arm_ids, **kwargs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        self._history: list[dict[str, Any]] = []

    def get_prompt(self) -> tuple[str, str]:
        """Get optimized prompt. Returns (prompt_id, prompt_text)."""
        result = self.bandit.select_arm()
        prompt_text = self.prompts[result.selected_arm]

        self._history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "selected": result.selected_arm,
                "exploration": result.exploration,
                "confidence": result.confidence,
            }
        )

        return result.selected_arm, prompt_text

    def record_outcome(self, prompt_id: str, score: float) -> None:
        """Record outcome for a prompt (score in [0, 1])."""
        self.bandit.update(prompt_id, score)

    def get_best_prompt(self) -> tuple[str, str]:
        """Get the current best prompt based on statistics."""
        best_id = max(
            self.bandit.arms.keys(),
            key=lambda a: self.bandit.arms[a].mean_reward,
        )
        return best_id, self.prompts[best_id]

    def get_stats(self) -> dict[str, Any]:
        """Get optimization statistics."""
        return {
            "strategy": self.strategy.value,
            "total_trials": sum(a.pulls for a in self.bandit.arms.values()),
            "arms": self.bandit.get_stats(),
            "history_length": len(self._history),
        }


class ModelRouter:
    """Bandit-based model router for optimal model selection."""

    def __init__(
        self,
        models: list[str],
        strategy: BanditStrategy = BanditStrategy.UCB1,
        cost_weights: dict[str, float] | None = None,
        **kwargs: Any,
    ):
        self.models = models
        self.strategy = strategy
        self.cost_weights = cost_weights or {}

        if strategy == BanditStrategy.EPSILON_GREEDY:
            self.bandit = EpsilonGreedy(models, **kwargs)
        elif strategy == BanditStrategy.UCB1:
            self.bandit = UCB1(models, **kwargs)
        elif strategy == BanditStrategy.THOMPSON_SAMPLING:
            self.bandit = ThompsonSampling(models, **kwargs)
        else:
            self.bandit = UCB1(models)

    def select_model(self, task_type: str | None = None) -> str:
        """Select optimal model for a task."""
        result = self.bandit.select_arm()
        return result.selected_arm

    def record_outcome(
        self,
        model: str,
        quality_score: float,
        latency_ms: float,
        cost: float,
    ) -> None:
        """Record model performance."""
        # Combine metrics into single reward
        cost_weight = self.cost_weights.get(model, 1.0)
        normalized_latency = 1.0 / (1.0 + latency_ms / 1000)  # Inverse latency
        normalized_cost = 1.0 / (1.0 + cost * cost_weight)

        # Weighted combination
        reward = 0.6 * quality_score + 0.2 * normalized_latency + 0.2 * normalized_cost

        self.bandit.update(model, reward)

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get model recommendations sorted by performance."""
        stats = self.bandit.get_stats()
        recommendations = [{"model": model, **stat} for model, stat in stats.items()]
        recommendations.sort(key=lambda x: x["mean_reward"], reverse=True)
        return recommendations


# Factory functions
def create_prompt_optimizer(
    prompts: dict[str, str],
    strategy: str = "thompson_sampling",
) -> PromptOptimizer:
    """Create a prompt optimizer with specified strategy."""
    strategy_enum = BanditStrategy(strategy)
    return PromptOptimizer(prompts, strategy=strategy_enum)


def create_model_router(
    models: list[str],
    strategy: str = "ucb1",
) -> ModelRouter:
    """Create a model router with specified strategy."""
    strategy_enum = BanditStrategy(strategy)
    return ModelRouter(models, strategy=strategy_enum)


__all__ = [
    "UCB1",
    "ArmStats",
    "BanditAlgorithm",
    "BanditResult",
    "BanditStrategy",
    "EpsilonGreedy",
    "ModelRouter",
    "PromptOptimizer",
    "SoftmaxBandit",
    "ThompsonSampling",
    "create_model_router",
    "create_prompt_optimizer",
]
