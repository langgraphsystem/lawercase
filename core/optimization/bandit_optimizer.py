from __future__ import annotations

"""Multi-armed bandit optimizer scaffolding."""

from dataclasses import dataclass


@dataclass
class ArmStats:
    wins: int = 0
    pulls: int = 0


class EpsilonGreedyBandit:
    def __init__(self, arms: list[str], epsilon: float = 0.1) -> None:
        self.epsilon = epsilon
        self.stats: dict[str, ArmStats] = {arm: ArmStats() for arm in arms}

    def record(self, arm: str, reward: float) -> None:
        stats = self.stats[arm]
        stats.pulls += 1
        if reward > 0:
            stats.wins += 1

    def select(self) -> str:
        return next(iter(self.stats))
