from __future__ import annotations

import csv
import json
import logging
import pickle  # nosec B403 - required for model serialization
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from core.monitoring.model_monitor import ModelMonitor

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """
    Configuration options for the training pipeline.
    """

    target_column: str = "label"
    feature_columns: Sequence[str] | None = None
    test_size: float = 0.2
    random_seed: int = 42
    learning_rate: float = 0.1
    epochs: int = 400
    l2_regularization: float = 0.0
    model_dir: Path = field(default_factory=lambda: Path("artifacts") / "models")
    registry_path: Path = field(default_factory=lambda: Path("artifacts") / "model_registry.json")
    monitor_window: int = 200
    min_samples: int = 30
    max_class_imbalance: float = 0.95
    decision_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if self.epochs <= 0:
            raise ValueError("epochs must be greater than 0.")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")
        if self.monitor_window <= 0:
            raise ValueError("monitor_window must be positive.")
        if not 0.5 <= self.max_class_imbalance <= 1.0:
            raise ValueError("max_class_imbalance must be between 0.5 and 1.0.")
        self.model_dir = Path(self.model_dir)
        self.registry_path = Path(self.registry_path)


@dataclass
class DatasetSummary:
    """
    High-level statistics about the dataset used for model training.
    """

    num_rows: int
    num_features: int
    feature_names: list[str]
    class_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_rows": self.num_rows,
            "num_features": self.num_features,
            "feature_names": list(self.feature_names),
            "class_distribution": dict(self.class_distribution),
        }


@dataclass
class TrainingMetrics:
    """
    Evaluation metrics for a trained model.
    """

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc: float | None
    loss: float

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "accuracy": float(self.accuracy),
            "precision": float(self.precision),
            "recall": float(self.recall),
            "f1_score": float(self.f1_score),
            "loss": float(self.loss),
        }
        if self.auc is not None:
            result["auc"] = float(self.auc)
        else:
            result["auc"] = None
        return result


@dataclass
class ModelRegistryEntry:
    """
    Representation of a model record inside the local registry.
    """

    model_name: str
    version: str
    created_at: str
    artifact_path: str
    metrics: dict[str, Any]
    data_summary: dict[str, Any]
    feature_scaler: dict[str, Any]
    label_mapping: dict[str, Any]
    training_params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "version": self.version,
            "created_at": self.created_at,
            "artifact_path": self.artifact_path,
            "metrics": self.metrics,
            "data_summary": self.data_summary,
            "feature_scaler": self.feature_scaler,
            "label_mapping": self.label_mapping,
            "training_params": self.training_params,
        }


class LabelEncoder:
    """
    Simple binary label encoder compatible with numpy arrays.
    """

    def __init__(self) -> None:
        self.class_to_index: dict[Any, int] = {}
        self.index_to_class: dict[int, Any] = {}

    def fit(self, labels: Iterable[Any]) -> None:
        unique = sorted({self._normalize_label(label) for label in labels})
        if len(unique) < 2:
            raise ValueError("Training data must contain at least two classes.")
        if len(unique) > 2:
            raise ValueError("Only binary classification is supported by this pipeline.")
        self.class_to_index = {label: idx for idx, label in enumerate(unique)}
        self.index_to_class = {idx: label for label, idx in self.class_to_index.items()}

    def transform(self, labels: Iterable[Any]) -> np.ndarray:
        if not self.class_to_index:
            raise ValueError("LabelEncoder must be fitted before calling transform.")
        transformed = []
        for label in labels:
            normalized = self._normalize_label(label)
            if normalized not in self.class_to_index:
                raise ValueError(f"Unknown label encountered: {label!r}")
            transformed.append(self.class_to_index[normalized])
        return np.array(transformed, dtype=np.float64)

    def inverse_transform(self, encoded: Iterable[int]) -> list[Any]:
        if not self.index_to_class:
            raise ValueError("LabelEncoder must be fitted before calling inverse_transform.")
        return [self.index_to_class[int(index)] for index in encoded]

    def to_dict(self) -> dict[str, Any]:
        return {
            "classes": [self.index_to_class[idx] for idx in sorted(self.index_to_class)],
            "class_to_index": {str(k): int(v) for k, v in self.class_to_index.items()},
        }

    @staticmethod
    def _normalize_label(label: Any) -> Any:
        if isinstance(label, str):
            return label.strip()
        return label


@dataclass
class LoadedDataset:
    """
    Container for the processed dataset.
    """

    features: np.ndarray
    labels: np.ndarray
    feature_names: list[str]
    label_encoder: LabelEncoder
    class_distribution: dict[str, int]


class DatasetLoader:
    """
    Loads datasets from disk and converts them into numpy arrays.
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def load(self, data_path: str) -> LoadedDataset:
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"Training data not found at path: {data_path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            records = self._load_csv(path)
        elif suffix in {".json", ".jsonl"}:
            records = self._load_json(path)
        else:
            raise ValueError(
                f"Unsupported data format '{suffix}'. Only CSV, JSON, and JSONL are supported."
            )

        if not records:
            raise ValueError("Training data file is empty.")

        feature_names = self._determine_feature_columns(records[0])
        features, raw_labels = self._extract_arrays(records, feature_names)

        label_encoder = LabelEncoder()
        label_encoder.fit(raw_labels)
        encoded_labels = label_encoder.transform(raw_labels)

        class_distribution = Counter([str(label) for label in raw_labels])

        return LoadedDataset(
            features=features,
            labels=encoded_labels,
            feature_names=feature_names,
            label_encoder=label_encoder,
            class_distribution=dict(class_distribution),
        )

    def _determine_feature_columns(self, sample_row: Mapping[str, Any]) -> list[str]:
        if self.config.feature_columns:
            return [str(col) for col in self.config.feature_columns]

        feature_names = [
            key
            for key in sample_row
            if key != self.config.target_column and not key.startswith("_")
        ]
        if not feature_names:
            raise ValueError(
                "No feature columns detected. Provide feature_columns in TrainingConfig."
            )
        return feature_names

    def _extract_arrays(
        self, records: Sequence[Mapping[str, Any]], feature_names: Sequence[str]
    ) -> tuple[np.ndarray, list[Any]]:
        feature_matrix: list[list[float]] = []
        labels: list[Any] = []

        for idx, row in enumerate(records):
            try:
                features = [self._to_float(row[col]) for col in feature_names]
            except KeyError as exc:
                raise ValueError(f"Missing feature column '{exc.args[0]}' in row {idx}.") from exc
            except ValueError as exc:
                raise ValueError(f"Non-numeric value in row {idx}: {exc}") from exc

            if self.config.target_column not in row:
                raise ValueError(
                    f"Target column '{self.config.target_column}' missing in row {idx}."
                )

            feature_matrix.append(features)
            labels.append(row[self.config.target_column])

        return np.array(feature_matrix, dtype=np.float64), labels

    @staticmethod
    def _to_float(value: Any) -> float:
        if value is None:
            raise ValueError("Encountered null value in dataset.")
        return float(value)

    @staticmethod
    def _load_csv(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            if path.suffix.lower() == ".jsonl":
                return [json.loads(line) for line in handle if line.strip()]
            data = json.load(handle)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return data["data"]
        raise ValueError("JSON file must contain a list of records or a 'data' array.")


class DatasetValidator:
    """
    Performs sanity checks on the loaded dataset before training.
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def validate(self, dataset: LoadedDataset) -> None:
        num_rows = dataset.features.shape[0]
        if num_rows < self.config.min_samples:
            raise ValueError(
                f"Insufficient training samples ({num_rows}). "
                f"Minimum required: {self.config.min_samples}."
            )

        if np.isnan(dataset.features).any() or np.isinf(dataset.features).any():
            raise ValueError("Training features contain NaN or infinite values.")

        _, counts = np.unique(dataset.labels, return_counts=True)
        max_ratio = max(counts) / num_rows
        if max_ratio > self.config.max_class_imbalance:
            raise ValueError(
                "Class imbalance exceeds the allowed threshold. "
                "Consider collecting more data or adjusting max_class_imbalance."
            )


class FeatureScaler:
    """
    Standard score feature scaler.
    """

    def __init__(self) -> None:
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def fit(self, features: np.ndarray) -> None:
        self.mean_ = np.mean(features, axis=0)
        self.std_ = np.std(features, axis=0)
        self.std_[self.std_ == 0] = 1.0  # Avoid division by zero

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("FeatureScaler must be fitted before calling transform.")
        return (features - self.mean_) / self.std_

    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        self.fit(features)
        return self.transform(features)

    def to_dict(self) -> dict[str, Any]:
        if self.mean_ is None or self.std_ is None:
            raise ValueError("FeatureScaler must be fitted before serialization.")
        return {"mean": self.mean_.tolist(), "std": self.std_.tolist()}


class LogisticRegressionModel:
    """
    Binary logistic regression implemented with gradient descent.
    """

    def __init__(self, learning_rate: float, epochs: int, l2_regularization: float = 0.0) -> None:
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.l2_regularization = l2_regularization
        self.weights: np.ndarray | None = None

    def fit(self, features: np.ndarray, labels: np.ndarray) -> list[float]:
        n_samples, n_features = features.shape
        extended = np.hstack([features, np.ones((n_samples, 1))])
        self.weights = np.zeros(n_features + 1)

        losses: list[float] = []
        for _ in range(self.epochs):
            logits = extended @ self.weights
            predictions = self._sigmoid(logits)

            errors = predictions - labels
            gradient = extended.T @ errors / n_samples
            if self.l2_regularization > 0:
                gradient[:-1] += self.l2_regularization * self.weights[:-1]

            self.weights -= self.learning_rate * gradient

            loss = self._binary_cross_entropy(labels, predictions)
            if self.l2_regularization > 0:
                loss += (self.l2_regularization / 2) * np.sum(self.weights[:-1] ** 2)
            losses.append(float(loss))

        return losses

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        if self.weights is None:
            raise ValueError("Model must be trained before calling predict_proba.")
        extended = np.hstack([features, np.ones((features.shape[0], 1))])
        logits = extended @ self.weights
        return self._sigmoid(logits)

    def predict(self, features: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probabilities = self.predict_proba(features)
        return (probabilities >= threshold).astype(int)

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        # Clip values to avoid overflow in exp
        x = np.clip(x, -500, 500)
        return 1.0 / (1.0 + np.exp(-x))

    @staticmethod
    def _binary_cross_entropy(labels: np.ndarray, predictions: np.ndarray) -> float:
        eps = 1e-12
        predictions = np.clip(predictions, eps, 1 - eps)
        return float(
            -np.mean(labels * np.log(predictions) + (1 - labels) * np.log(1 - predictions))
        )


def train_test_split(
    features: np.ndarray,
    labels: np.ndarray,
    test_size: float,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    rng = np.random.default_rng(seed=random_seed)
    indices = np.arange(features.shape[0])
    rng.shuffle(indices)

    test_count = max(1, int(len(indices) * test_size))
    train_indices = indices[test_count:]
    test_indices = indices[:test_count]

    if not len(train_indices):
        raise ValueError("Training split is empty. Adjust test_size or provide more data.")

    return (
        features[train_indices],
        features[test_indices],
        labels[train_indices],
        labels[test_indices],
    )


def compute_metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    loss: float,
) -> TrainingMetrics:
    tp = float(np.sum((labels == 1) & (predictions == 1)))
    tn = float(np.sum((labels == 0) & (predictions == 0)))
    fp = float(np.sum((labels == 0) & (predictions == 1)))
    fn = float(np.sum((labels == 1) & (predictions == 0)))

    total = len(labels)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    auc = _compute_auc(labels, probabilities)

    return TrainingMetrics(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        auc=auc,
        loss=loss,
    )


def _compute_auc(labels: np.ndarray, probabilities: np.ndarray) -> float | None:
    positive = probabilities[labels == 1]
    negative = probabilities[labels == 0]

    if len(positive) == 0 or len(negative) == 0:
        return None

    positives = positive[:, np.newaxis]
    comparison = positives - negative
    greater = np.sum(comparison > 0)
    equal = np.sum(comparison == 0)

    return float((greater + 0.5 * equal) / (len(positive) * len(negative)))


class ModelRegistry:
    """
    Minimal local model registry that tracks training metadata.
    """

    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, entry: ModelRegistryEntry) -> dict[str, Any]:
        records = self._load_registry()
        serialized = entry.to_dict()
        records.append(serialized)
        self._save_registry(records)
        return serialized

    def _load_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        with self.registry_path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                logger.warning("Model registry file was corrupted. Starting with a fresh registry.")
                return []

    def _save_registry(self, entries: list[dict[str, Any]]) -> None:
        with self.registry_path.open("w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, ensure_ascii=False)


class TrainingPipeline:
    """
    End-to-end training pipeline orchestration.
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self.loader = DatasetLoader(config)
        self.validator = DatasetValidator(config)
        self.scaler = FeatureScaler()
        self.registry = ModelRegistry(config.registry_path)

    def run(self, model_name: str, data_path: str) -> dict[str, Any]:
        logger.info("Starting training pipeline for '%s'.", model_name)

        dataset = self.loader.load(data_path)
        self.validator.validate(dataset)

        summary = DatasetSummary(
            num_rows=int(dataset.features.shape[0]),
            num_features=int(dataset.features.shape[1]),
            feature_names=list(dataset.feature_names),
            class_distribution=dict(dataset.class_distribution),
        )

        scaled_features = self.scaler.fit_transform(dataset.features)
        (
            train_features,
            test_features,
            train_labels,
            test_labels,
        ) = train_test_split(
            scaled_features,
            dataset.labels,
            test_size=self.config.test_size,
            random_seed=self.config.random_seed,
        )

        model = LogisticRegressionModel(
            learning_rate=self.config.learning_rate,
            epochs=self.config.epochs,
            l2_regularization=self.config.l2_regularization,
        )
        loss_history = model.fit(train_features, train_labels)

        train_probabilities = model.predict_proba(train_features)
        test_probabilities = model.predict_proba(test_features)
        test_predictions = model.predict(test_features, threshold=self.config.decision_threshold)

        metrics = compute_metrics(
            labels=test_labels,
            predictions=test_predictions,
            probabilities=test_probabilities,
            loss=loss_history[-1],
        )

        artifact_path, model_version = self._persist_artifact(
            model_name=model_name,
            model=model,
            dataset=dataset,
        )

        registry_entry = self.registry.register(
            ModelRegistryEntry(
                model_name=model_name,
                version=model_version,
                created_at=datetime.utcnow().isoformat(),
                artifact_path=str(artifact_path),
                metrics=metrics.to_dict(),
                data_summary=summary.to_dict(),
                feature_scaler=self.scaler.to_dict(),
                label_mapping=dataset.label_encoder.to_dict(),
                training_params={
                    "learning_rate": self.config.learning_rate,
                    "epochs": self.config.epochs,
                    "l2_regularization": self.config.l2_regularization,
                    "decision_threshold": self.config.decision_threshold,
                },
            )
        )

        monitor_snapshot = self._initialize_monitor(
            model_name=model_name,
            train_probabilities=train_probabilities,
            test_probabilities=test_probabilities,
        )

        logger.info(
            "Training pipeline for '%s' completed with version '%s'.",
            model_name,
            model_version,
        )

        return {
            "model_name": model_name,
            "model_version": model_version,
            "model_artifact": str(artifact_path),
            "metrics": metrics.to_dict(),
            "data_summary": summary.to_dict(),
            "training_history": {"loss": [float(value) for value in loss_history]},
            "monitoring": monitor_snapshot,
            "registry_entry": registry_entry,
        }

    def _persist_artifact(
        self,
        model_name: str,
        model: LogisticRegressionModel,
        dataset: LoadedDataset,
    ) -> tuple[Path, str]:
        if model.weights is None:
            raise ValueError("Cannot persist an untrained model.")

        model_dir = self.config.model_dir
        model_dir.mkdir(parents=True, exist_ok=True)

        version = self._generate_version()
        artifact_path = model_dir / f"{model_name}-{version}.pkl"

        payload = {
            "model_name": model_name,
            "version": version,
            "weights": model.weights.tolist(),
            "feature_names": dataset.feature_names,
            "feature_scaler": self.scaler.to_dict(),
            "label_mapping": dataset.label_encoder.to_dict(),
            "training_params": {
                "learning_rate": self.config.learning_rate,
                "epochs": self.config.epochs,
                "l2_regularization": self.config.l2_regularization,
            },
        }

        with artifact_path.open("wb") as handle:
            pickle.dump(payload, handle)

        return artifact_path, version

    def _generate_version(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"{timestamp}-{short_uuid}"

    def _initialize_monitor(
        self,
        model_name: str,
        train_probabilities: np.ndarray,
        test_probabilities: np.ndarray,
    ) -> dict[str, Any]:
        monitor = ModelMonitor(window_size=self.config.monitor_window)
        monitor.set_reference_data(model_name, train_probabilities.tolist())

        for value in test_probabilities.tolist():
            monitor.track_prediction(model_name, float(value))

        status = monitor.detect_drift(model_name)
        return {
            "window_size": self.config.monitor_window,
            "reference_sample_size": len(train_probabilities),
            "live_sample_size": len(test_probabilities),
            "drift_status": {
                key: (float(value) if isinstance(value, np.floating | np.integer) else value)
                for key, value in status.items()
            },
        }


def run_training_pipeline(
    model_name: str,
    data_path: str,
    config: TrainingConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute the full MLOps training pipeline for the provided dataset.
    """

    if isinstance(config, Mapping):
        pipeline_config = TrainingConfig(**config)
    elif isinstance(config, TrainingConfig):
        pipeline_config = config
    else:
        pipeline_config = TrainingConfig()

    pipeline = TrainingPipeline(pipeline_config)
    return pipeline.run(model_name=model_name, data_path=data_path)
