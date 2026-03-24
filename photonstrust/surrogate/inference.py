"""Fast inference using trained surrogate models."""

from __future__ import annotations

import numpy as np

from photonstrust.surrogate.domains import get_physics_fn
from photonstrust.surrogate.registry import SurrogateRegistry
from photonstrust.surrogate.types import PredictionResult


def fast_predict(
    domain: str,
    parameters: dict,
    *,
    registry: SurrogateRegistry,
    fallback_physics: bool = True,
) -> PredictionResult:
    """Predict using a surrogate model, falling back to physics if needed.

    1. Try to load model from registry.
    2. If model exists: extract features, normalise, predict, denormalise,
       return from_surrogate=True.
    3. Confidence: parameters within training range -> 0.9, outside -> 0.5.
    4. If no model and fallback_physics: call get_physics_fn, from_surrogate=False.
    5. If no model and no fallback: raise FileNotFoundError.
    """
    # Attempt surrogate inference
    try:
        model, metadata = registry.load_model(domain)
    except (FileNotFoundError, ImportError):
        model = None
        metadata = None

    if model is not None and metadata is not None:
        feature_names = sorted(metadata.input_features)
        X = np.array([[parameters.get(f, 0.0) for f in feature_names]])

        # Apply input normalisation if available
        x_mean = getattr(model, "_surrogate_x_mean", None)
        x_std = getattr(model, "_surrogate_x_std", None)
        if x_mean is not None and x_std is not None:
            X = (X - x_mean) / x_std

        raw = model.predict(X)
        if raw.ndim == 1:
            raw = raw.reshape(1, -1)

        # Invert output normalisation if available
        y_mean = getattr(model, "_surrogate_y_mean", None)
        y_std = getattr(model, "_surrogate_y_std", None)
        if y_mean is not None and y_std is not None:
            raw = raw * y_std + y_mean

        output_features = sorted(metadata.output_features)
        predictions = {
            name: float(raw[0, j]) for j, name in enumerate(output_features)
        }

        # Confidence estimation based on parameter ranges
        ranges = metadata.training_config.get("parameter_ranges", {})
        in_range = True
        for fname in feature_names:
            val = parameters.get(fname, 0.0)
            if fname in ranges:
                r = ranges[fname]
                if isinstance(r, (list, tuple)) and len(r) == 2:
                    lo, hi = r[0], r[1]
                else:
                    continue
                if val < lo or val > hi:
                    in_range = False
                    break
        confidence = 0.9 if in_range else 0.5

        return PredictionResult(
            domain=domain,
            predictions=predictions,
            confidence=confidence,
            from_surrogate=True,
        )

    # Fallback to physics
    if fallback_physics:
        physics_fn = get_physics_fn(domain)
        predictions = physics_fn(parameters)
        return PredictionResult(
            domain=domain,
            predictions=predictions,
            confidence=1.0,
            from_surrogate=False,
        )

    raise FileNotFoundError(
        f"No surrogate model found for domain '{domain}' and fallback is disabled"
    )
