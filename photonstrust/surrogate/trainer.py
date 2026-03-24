"""Surrogate model training with Latin hypercube sampling."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from photonstrust.surrogate.types import TrainingConfig, ValidationResult


class SurrogateTrainer:
    """Train sklearn MLPRegressor surrogate models."""

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config

    def generate_training_data(
        self,
        physics_fn: Callable[[dict], dict],
        parameter_ranges: dict[str, tuple[float, float]],
        n_samples: int = 200,
    ) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
        """Generate training data via Latin hypercube sampling.

        For each feature: divide [min, max] into *n_samples* equal intervals,
        randomly shuffle interval assignments per feature, and pick a random
        point within each interval.  Then call *physics_fn* for every sample.
        """
        rng = np.random.RandomState(self._config.random_state)
        feature_names = sorted(parameter_ranges.keys())
        n_features = len(feature_names)

        # Latin hypercube sampling
        X = np.zeros((n_samples, n_features))
        for j, fname in enumerate(feature_names):
            lo, hi = parameter_ranges[fname]
            intervals = np.linspace(lo, hi, n_samples + 1)
            perm = rng.permutation(n_samples)
            for i in range(n_samples):
                idx = perm[i]
                X[i, j] = rng.uniform(intervals[idx], intervals[idx + 1])

        # Evaluate physics function for each sample
        target_names: list[str] | None = None
        y_rows: list[list[float]] = []
        for i in range(n_samples):
            params = {fname: float(X[i, j]) for j, fname in enumerate(feature_names)}
            result = physics_fn(params)
            if target_names is None:
                target_names = sorted(result.keys())
            y_rows.append([result[t] for t in target_names])

        y = np.array(y_rows)
        return X, y, feature_names, target_names or []

    @staticmethod
    def _normalize(
        arr: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (normalized, mean, std) -- std clamped to avoid /0."""
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        std = np.where(std < 1e-12, 1.0, std)
        return (arr - mean) / std, mean, std

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
        target_names: list[str],
    ) -> tuple[Any, ValidationResult]:
        """Train an MLPRegressor and return (model, validation)."""
        try:
            from sklearn.neural_network import MLPRegressor
        except ImportError:
            raise ImportError(
                "scikit-learn is required for surrogate model training. "
                "Install it with: pip install scikit-learn"
            )

        cfg = self._config
        split = cfg.train_test_split
        n = len(X)
        n_train = int(n * (1 - split))

        X_train_raw, X_test_raw = X[:n_train], X[n_train:]
        y_train_raw, y_test_raw = y[:n_train], y[n_train:]

        # Standardize inputs and outputs for better convergence
        X_train, x_mean, x_std = self._normalize(X_train_raw)
        X_test = (X_test_raw - x_mean) / x_std

        y_train, y_mean, y_std = self._normalize(y_train_raw)
        y_test_norm = (y_test_raw - y_mean) / y_std

        model = MLPRegressor(
            hidden_layer_sizes=cfg.hidden_layer_sizes,
            max_iter=cfg.max_iter,
            random_state=cfg.random_state,
        )
        model.fit(X_train, y_train.ravel() if y_train.shape[1] == 1 else y_train)

        # Predict in normalised space, then invert for real metrics
        y_pred_norm = model.predict(X_test)
        if y_pred_norm.ndim == 1:
            y_pred_norm = y_pred_norm.reshape(-1, 1)

        y_pred = y_pred_norm * y_std + y_mean
        y_test = y_test_raw
        if y_test.ndim == 1:
            y_test = y_test.reshape(-1, 1)

        ss_res = np.sum((y_test - y_pred) ** 2)
        ss_tot = np.sum((y_test - np.mean(y_test, axis=0)) ** 2)
        r_squared = float(1 - ss_res / (ss_tot + 1e-30))

        abs_errors = np.abs(y_test - y_pred)
        mae = float(np.mean(abs_errors))
        max_err = float(np.max(abs_errors))

        # Feature importance from first-layer weight magnitudes
        importance: dict[str, float] = {}
        if hasattr(model, "coefs_") and len(model.coefs_) > 0:
            w = np.abs(model.coefs_[0])  # shape (n_features, hidden_size)
            magnitudes = np.sum(w, axis=1)
            total = float(np.sum(magnitudes)) + 1e-30
            for j, fname in enumerate(feature_names):
                importance[fname] = round(float(magnitudes[j] / total), 4)

        # Attach normalization params so registry can persist them
        model._surrogate_x_mean = x_mean  # noqa: SLF001
        model._surrogate_x_std = x_std  # noqa: SLF001
        model._surrogate_y_mean = y_mean  # noqa: SLF001
        model._surrogate_y_std = y_std  # noqa: SLF001

        validation = ValidationResult(
            domain=cfg.domain,
            r_squared=r_squared,
            mean_absolute_error=mae,
            max_absolute_error=max_err,
            n_train=n_train,
            n_test=n - n_train,
            parameter_importance=importance,
        )
        return model, validation
