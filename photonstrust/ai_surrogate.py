"""AI Surrogate modeling module for accelerating QuTiP and JAX operations.

This module provides caching wrappers for heavy simulation tasks, and
seamlessly scales into training live Multi-Layer Perceptrons (MLPs)
to infer dynamics without direct numerical integration.
"""

from __future__ import annotations
import hashlib
import json
import warnings
from typing import Any, Callable
import numpy as np

try:
    from sklearn.neural_network import MLPRegressor
    from sklearn.exceptions import ConvergenceWarning
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

_CACHE: dict[str, Any] = {}
_MODELS: dict[str, dict] = {}

def _hash_params(params: dict[str, Any]) -> str:
    """Create a deterministic hash from a parameter dictionary."""
    serialized = json.dumps(params, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def _extract_numeric_vector(params: dict[str, Any]) -> list[float]:
    """Flattens a parameter dict into a predictable numerical vector for ML."""
    vec = []
    for key in sorted(params.keys()):
        val = params[key]
        if isinstance(val, (int, float)):
            vec.append(float(val))
    return vec

def cached_surrogate(domain: str, train_threshold: int = 50) -> Callable:
    """Decorator to cache heavy physics functions and train AI surrogates.

    Args:
        domain: A string identifying the context, e.g., "qutip_trajectory"
        train_threshold: The number of unique runs before an MLP is trained
                         to approximate the outputs instantly.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{domain}_{_hash_params(kwargs)}"
            if cache_key in _CACHE:
                return _CACHE[cache_key]

            # Check if we have a trained surrogate model to infer the result
            if HAS_SKLEARN and domain in _MODELS and _MODELS[domain]["ready"]:
                vec = _extract_numeric_vector(kwargs)
                if vec and len(vec) == _MODELS[domain]["input_dim"]:
                    X = np.array([vec])
                    model = _MODELS[domain]["model"]
                    is_complex = _MODELS[domain]["is_complex"]
                    y_pred = model.predict(X)[0]

                    if is_complex:
                        n = len(y_pred) // 2
                        result = [complex(y_pred[i], y_pred[i+n]) for i in range(n)]
                        if len(result) == 1:
                            return result[0]
                        return result
                    else:
                        if isinstance(y_pred, (float, int, np.number)):
                            return float(y_pred)
                        if getattr(y_pred, "shape", ()) and len(y_pred.shape) > 0 and y_pred.shape[0] == 1:
                            return float(y_pred[0])
                        return y_pred.tolist()

            # Execute true physics function
            result = func(*args, **kwargs)
            _CACHE[cache_key] = result

            # Logic: Collect training data if we haven't trained a model yet
            if HAS_SKLEARN:
                domain_state = _MODELS.setdefault(domain, {
                    "ready": False,
                    "history_X": [],
                    "history_y": [],
                    "input_dim": 0,
                    "is_complex": False
                })

                if not domain_state["ready"]:
                    vec = _extract_numeric_vector(kwargs)
                    if vec:
                        domain_state["input_dim"] = len(vec)
                        domain_state["history_X"].append(vec)

                        # Process output data safely
                        y_val = result
                        if isinstance(y_val, complex):
                            y_vec = [y_val.real, y_val.imag]
                            domain_state["is_complex"] = True
                        elif isinstance(y_val, (int, float)):
                            y_vec = [float(y_val)]
                        elif isinstance(y_val, (list, tuple)):
                            if len(y_val) > 0 and isinstance(y_val[0], complex):
                                y_vec = [v.real for v in y_val] + [v.imag for v in y_val]
                                domain_state["is_complex"] = True
                            else:
                                y_vec = [float(v) for v in y_val]
                        else:
                            y_vec = [] # Can't process easily, ignore

                        if y_vec:
                            domain_state["history_y"].append(y_vec)

                        # Trigger threshold-based training
                        if len(domain_state["history_X"]) >= train_threshold:
                            X_train = np.array(domain_state["history_X"])
                            y_train = np.array(domain_state["history_y"])
                            model = MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=500, random_state=42)

                            with warnings.catch_warnings():
                                warnings.filterwarnings("ignore", category=ConvergenceWarning)
                                model.fit(X_train, y_train)

                            domain_state["model"] = model
                            domain_state["ready"] = True
                            print(f"\n[PhotonTrust AI] Automatically trained Surrogate MLP for domain '{domain}' on {train_threshold} physics evaluations.")

            return result
        return wrapper
    return decorator

def clear_surrogate_cache() -> None:
    """Clear the in-memory surrogate cache and wipe ML models."""
    _CACHE.clear()
    _MODELS.clear()
