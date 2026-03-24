"""Data types for AI surrogate models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrainingConfig:
    """Configuration for surrogate model training."""

    domain: str
    hidden_layer_sizes: tuple[int, ...] = (64, 64)
    max_iter: int = 500
    random_state: int = 42
    train_test_split: float = 0.2
    n_training_samples: int = 200
    parameter_ranges: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "domain": self.domain,
            "hidden_layer_sizes": list(self.hidden_layer_sizes),
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "train_test_split": self.train_test_split,
            "n_training_samples": self.n_training_samples,
            "parameter_ranges": dict(self.parameter_ranges),
        }


@dataclass(frozen=True)
class ValidationResult:
    """Validation metrics for a trained surrogate model."""

    domain: str
    r_squared: float
    mean_absolute_error: float
    max_absolute_error: float
    n_train: int
    n_test: int
    parameter_importance: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "domain": self.domain,
            "r_squared": self.r_squared,
            "mean_absolute_error": self.mean_absolute_error,
            "max_absolute_error": self.max_absolute_error,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "parameter_importance": dict(self.parameter_importance),
        }


@dataclass(frozen=True)
class SurrogateModelMetadata:
    """Metadata for a saved surrogate model."""

    domain: str
    created_at_iso: str
    input_features: list[str] = field(default_factory=list)
    output_features: list[str] = field(default_factory=list)
    training_config: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    model_hash: str = ""

    def as_dict(self) -> dict:
        return {
            "domain": self.domain,
            "created_at_iso": self.created_at_iso,
            "input_features": list(self.input_features),
            "output_features": list(self.output_features),
            "training_config": dict(self.training_config),
            "validation": dict(self.validation),
            "model_hash": self.model_hash,
        }


@dataclass(frozen=True)
class PredictionResult:
    """Result from a surrogate model prediction."""

    domain: str
    predictions: dict = field(default_factory=dict)
    confidence: float = 0.0
    from_surrogate: bool = False

    def as_dict(self) -> dict:
        return {
            "domain": self.domain,
            "predictions": dict(self.predictions),
            "confidence": self.confidence,
            "from_surrogate": self.from_surrogate,
        }
