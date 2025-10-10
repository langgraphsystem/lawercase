from __future__ import annotations

"""Training pipeline scaffolding for Phase 3 MLOps."""

from dataclasses import dataclass


@dataclass
class TrainingJob:
    name: str
    dataset: str
    schedule: str


def submit_training_job(job: TrainingJob) -> str:
    """Submit training job (stub)."""
    return f"submitted:{job.name}"
