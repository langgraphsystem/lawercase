"""Experimentation package for MLOps.

Provides A/B testing and bandit optimization:
- PromptABTester: A/B testing for prompts
- BanditOptimizer: Multi-armed bandit for prompt/model selection
- ModelRouter: Bandit-based model routing
"""

from __future__ import annotations

from .ab_testing import PromptABTester
from .bandit_optimizer import (
    UCB1,
    ArmStats,
    BanditAlgorithm,
    BanditResult,
    BanditStrategy,
    EpsilonGreedy,
    ModelRouter,
    PromptOptimizer,
    SoftmaxBandit,
    ThompsonSampling,
    create_model_router,
    create_prompt_optimizer,
)

__all__ = [
    "UCB1",
    # Bandit Optimization
    "ArmStats",
    "BanditAlgorithm",
    "BanditResult",
    "BanditStrategy",
    "EpsilonGreedy",
    "ModelRouter",
    # A/B Testing
    "PromptABTester",
    "PromptOptimizer",
    "SoftmaxBandit",
    "ThompsonSampling",
    "create_model_router",
    "create_prompt_optimizer",
]
