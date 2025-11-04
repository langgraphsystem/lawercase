from __future__ import annotations

import random
from typing import Any


class EpsilonGreedyBandit:
    """
    An Epsilon-Greedy multi-armed bandit optimizer.
    """

    def __init__(self, epsilon: float = 0.1, storage: dict[str, Any] | None = None):
        """
        Initializes the Epsilon-Greedy bandit.

        Args:
            epsilon: The exploration factor (0.0 to 1.0). Defaults to 0.1.
            storage: A dictionary-like object to store bandit data.
                     If None, an in-memory dictionary is used.
        """
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("Epsilon must be between 0.0 and 1.0.")
        self.epsilon = epsilon
        self.storage = storage if storage is not None else {}

    def select_arm(self, experiment_name: str, arms: list[str]) -> str:
        """
        Selects an arm (prompt) to play.

        Args:
            experiment_name: The name of the experiment.
            arms: A list of arms (prompts) to choose from.

        Returns:
            The selected arm.
        """
        if experiment_name not in self.storage:
            self._initialize_experiment(experiment_name, arms)

        if random.random() < self.epsilon:  # nosec B311 - not used for security
            # Explore
            return random.choice(arms)  # nosec B311 - not used for security
        # Exploit
        return self._get_best_arm(experiment_name)

    def update_arm(self, experiment_name: str, arm: str, reward: float):
        """
        Updates the value of an arm based on a reward.

        Args:
            experiment_name: The name of the experiment.
            arm: The arm that was played.
            reward: The reward received.
        """
        if experiment_name not in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' not found.")

        experiment = self.storage[experiment_name]
        if arm not in experiment["arms"]:
            raise ValueError(f"Arm '{arm}' not found in experiment '{experiment_name}'.")

        arm_data = experiment["arms"][arm]
        arm_data["pulls"] += 1
        # Update the average reward
        arm_data["value"] = ((arm_data["value"] * (arm_data["pulls"] - 1)) + reward) / arm_data[
            "pulls"
        ]

    def _initialize_experiment(self, experiment_name: str, arms: list[str]):
        """
        Initializes a new experiment.
        """
        self.storage[experiment_name] = {"arms": {arm: {"pulls": 0, "value": 0.0} for arm in arms}}

    def _get_best_arm(self, experiment_name: str) -> str:
        """
        Gets the arm with the highest estimated value.
        """
        experiment = self.storage[experiment_name]
        if not experiment or not experiment["arms"]:
            raise ValueError(f"No arms found for experiment '{experiment_name}'.")

        return max(experiment["arms"], key=lambda arm: experiment["arms"][arm]["value"])

    def get_experiment_stats(self, experiment_name: str) -> dict[str, Any]:
        """
        Gets the stats of an experiment.

        Args:
            experiment_name: The name of the experiment.

        Returns:
            A dictionary with the experiment stats.
        """
        if experiment_name not in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' not found.")

        return self.storage[experiment_name]
