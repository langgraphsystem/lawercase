from __future__ import annotations

import hashlib
from typing import Any


class PromptABTester:
    """
    A/B testing framework for prompts.
    """

    def __init__(self, storage: dict[str, Any] = None):
        """
        Initializes the A/B tester.

        Args:
            storage: A dictionary-like object to store experiment data.
                     If None, an in-memory dictionary is used.
        """
        self.storage = storage if storage is not None else {}

    def create_experiment(
        self, experiment_name: str, prompts: list[str], distribution: list[float] = None
    ):
        """
        Creates a new A/B testing experiment.

        Args:
            experiment_name: The name of the experiment.
            prompts: A list of prompts to test.
            distribution: The distribution of traffic to each prompt. If None, a uniform distribution is used.
        """
        if experiment_name in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' already exists.")

        if not prompts:
            raise ValueError("At least one prompt is required.")

        if distribution and len(prompts) != len(distribution):
            raise ValueError("The number of prompts and distribution weights must be the same.")

        if distribution and not abs(sum(distribution) - 1.0) < 1e-6:
            raise ValueError("The sum of distribution weights must be 1.")

        self.storage[experiment_name] = {
            "prompts": prompts,
            "distribution": distribution or [1.0 / len(prompts)] * len(prompts),
            "results": [0] * len(prompts),
            "trials": [0] * len(prompts),
        }

    def get_prompt_variant(self, experiment_name: str, user_id: str) -> str:
        """
        Gets a prompt variant for a given user.

        Args:
            experiment_name: The name of the experiment.
            user_id: The ID of the user.

        Returns:
            The selected prompt variant.
        """
        if experiment_name not in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' not found.")

        experiment = self.storage[experiment_name]

        # Use a hash of the user ID to ensure a consistent assignment
        user_hash = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)

        # Use the distribution to select a variant
        rand_val = user_hash % 100 / 100.0

        cumulative_dist = 0.0
        for i, weight in enumerate(experiment["distribution"]):
            cumulative_dist += weight
            if rand_val < cumulative_dist:
                variant_index = i
                break
        else:
            variant_index = len(experiment["prompts"]) - 1

        experiment["trials"][variant_index] += 1
        return experiment["prompts"][variant_index]

    def record_outcome(self, experiment_name: str, prompt: str, score: float):
        """
        Records the outcome of a prompt variant.

        Args:
            experiment_name: The name of the experiment.
            prompt: The prompt that was used.
            score: The score of the outcome (e.g., 1 for success, 0 for failure).
        """
        if experiment_name not in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' not found.")

        experiment = self.storage[experiment_name]

        try:
            prompt_index = experiment["prompts"].index(prompt)
            experiment["results"][prompt_index] += score
        except ValueError:
            # The prompt was not found in the experiment, which might happen
            # if the experiment was modified after the prompt was served.
            # In a real system, you would want to log this event.
            pass

    def get_experiment_results(self, experiment_name: str) -> dict[str, Any]:
        """
        Gets the results of an experiment.

        Args:
            experiment_name: The name of the experiment.

        Returns:
            A dictionary with the experiment results.
        """
        if experiment_name not in self.storage:
            raise ValueError(f"Experiment '{experiment_name}' not found.")

        experiment = self.storage[experiment_name]

        results = []
        for i, prompt in enumerate(experiment["prompts"]):
            trials = experiment["trials"][i]
            successes = experiment["results"][i]
            conversion_rate = successes / trials if trials > 0 else 0
            results.append(
                {
                    "prompt": prompt,
                    "trials": trials,
                    "successes": successes,
                    "conversion_rate": conversion_rate,
                }
            )

        return {"experiment_name": experiment_name, "results": results}
