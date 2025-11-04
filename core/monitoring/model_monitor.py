from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np


class ModelMonitor:
    """
    A simple model drift monitor.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initializes the model monitor.

        Args:
            window_size: The size of the sliding window for drift detection.
        """
        self.window_size = window_size
        self.reference_data: dict[str, np.ndarray] = {}
        self.live_data: dict[str, deque] = {}

    def set_reference_data(self, model_name: str, data: list[float]):
        """
        Sets the reference data for a model.

        Args:
            model_name: The name of the model.
            data: A list of numerical data points (e.g., prediction scores).
        """
        self.reference_data[model_name] = np.array(data)
        self.live_data[model_name] = deque(maxlen=self.window_size)

    def track_prediction(self, model_name: str, prediction: float):
        """
        Tracks a new prediction.

        Args:
            model_name: The name of the model.
            prediction: The numerical prediction to track.
        """
        if model_name not in self.live_data:
            raise ValueError(f"Reference data for model '{model_name}' not set.")

        self.live_data[model_name].append(prediction)

    def detect_drift(self, model_name: str) -> dict[str, Any]:
        """
        Detects drift for a model using the Kolmogorov-Smirnov test.

        Args:
            model_name: The name of the model.

        Returns:
            A dictionary containing the drift detection results.
        """
        if model_name not in self.reference_data or model_name not in self.live_data:
            raise ValueError(f"Model '{model_name}' not found.")

        reference_dist = self.reference_data[model_name]
        live_dist = np.array(self.live_data[model_name])

        if len(live_dist) < self.window_size / 2:  # Wait for enough data
            return {
                "drift_detected": False,
                "p_value": None,
                "message": "Not enough live data to detect drift.",
            }

        # A simple drift detection using Kolmogorov-Smirnov test
        # In a real system, you would use more sophisticated methods.
        try:
            from scipy.stats import ks_2samp

            ks_statistic, p_value = ks_2samp(reference_dist, live_dist)
        except ImportError:
            return {
                "drift_detected": False,
                "p_value": None,
                "message": "scipy is not installed. Cannot perform drift detection.",
            }

        drift_detected = p_value < 0.05  # Significance level

        return {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "ks_statistic": ks_statistic,
            "live_data_size": len(live_dist),
        }
