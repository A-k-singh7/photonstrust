"""Model registry for saving / loading / listing surrogate models."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from photonstrust.surrogate.types import SurrogateModelMetadata


class SurrogateRegistry:
    """Persist surrogate models as JSON weights + metadata."""

    def __init__(self, model_dir: Path) -> None:
        self._model_dir = Path(model_dir)

    def save_model(
        self, domain: str, model: Any, metadata: SurrogateModelMetadata
    ) -> Path:
        """Save a trained MLPRegressor to *model_dir/domain/*."""
        domain_dir = self._model_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        # Weights (including normalization stats when present)
        weights: dict[str, Any] = {
            "coefs": [c.tolist() for c in model.coefs_],
            "intercepts": [i.tolist() for i in model.intercepts_],
            "n_features_in": int(model.n_features_in_),
            "hidden_layer_sizes": list(model.hidden_layer_sizes),
        }

        # Persist normalization parameters attached by SurrogateTrainer
        for attr in ("_surrogate_x_mean", "_surrogate_x_std",
                      "_surrogate_y_mean", "_surrogate_y_std"):
            val = getattr(model, attr, None)
            if val is not None:
                import numpy as np

                weights[attr] = val.tolist() if isinstance(val, np.ndarray) else val

        weights_path = domain_dir / "weights.json"
        raw = json.dumps(weights)
        weights_path.write_text(raw)

        # Store model hash in metadata
        model_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        updated_meta = SurrogateModelMetadata(
            domain=metadata.domain,
            created_at_iso=metadata.created_at_iso,
            input_features=metadata.input_features,
            output_features=metadata.output_features,
            training_config=metadata.training_config,
            validation=metadata.validation,
            model_hash=model_hash,
        )
        meta_path = domain_dir / "metadata.json"
        meta_path.write_text(json.dumps(updated_meta.as_dict(), indent=2))

        return domain_dir

    def load_model(self, domain: str) -> tuple[Any, SurrogateModelMetadata]:
        """Load a saved surrogate model and its metadata."""
        try:
            from sklearn.neural_network import MLPRegressor
        except ImportError:
            raise ImportError(
                "scikit-learn is required to load surrogate models. "
                "Install it with: pip install scikit-learn"
            )
        import numpy as np

        domain_dir = self._model_dir / domain
        meta_path = domain_dir / "metadata.json"
        weights_path = domain_dir / "weights.json"

        if not meta_path.exists():
            raise FileNotFoundError(f"No surrogate model found for domain '{domain}'")

        meta_raw = json.loads(meta_path.read_text())
        metadata = SurrogateModelMetadata(
            domain=meta_raw["domain"],
            created_at_iso=meta_raw["created_at_iso"],
            input_features=meta_raw.get("input_features", []),
            output_features=meta_raw.get("output_features", []),
            training_config=meta_raw.get("training_config", {}),
            validation=meta_raw.get("validation", {}),
            model_hash=meta_raw.get("model_hash", ""),
        )

        weights = json.loads(weights_path.read_text())

        model = MLPRegressor(
            hidden_layer_sizes=tuple(weights["hidden_layer_sizes"]),
        )
        # Restore fitted state
        model.coefs_ = [np.array(c) for c in weights["coefs"]]
        model.intercepts_ = [np.array(i) for i in weights["intercepts"]]
        model.n_features_in_ = weights["n_features_in"]
        # Mark as fitted
        model.n_layers_ = len(model.coefs_) + 1
        model.n_iter_ = 0
        model.out_activation_ = "identity"
        model._no_val_X = True  # noqa: SLF001

        # Restore normalization parameters
        for attr in ("_surrogate_x_mean", "_surrogate_x_std",
                      "_surrogate_y_mean", "_surrogate_y_std"):
            if attr in weights:
                setattr(model, attr, np.array(weights[attr]))

        return model, metadata

    def list_models(self) -> list[SurrogateModelMetadata]:
        """Return metadata for every saved model."""
        results: list[SurrogateModelMetadata] = []
        if not self._model_dir.exists():
            return results
        for subdir in sorted(self._model_dir.iterdir()):
            meta_path = subdir / "metadata.json"
            if subdir.is_dir() and meta_path.exists():
                raw = json.loads(meta_path.read_text())
                results.append(
                    SurrogateModelMetadata(
                        domain=raw["domain"],
                        created_at_iso=raw["created_at_iso"],
                        input_features=raw.get("input_features", []),
                        output_features=raw.get("output_features", []),
                        training_config=raw.get("training_config", {}),
                        validation=raw.get("validation", {}),
                        model_hash=raw.get("model_hash", ""),
                    )
                )
        return results

    def delete_model(self, domain: str) -> bool:
        """Remove the domain directory. Return True if it existed."""
        domain_dir = self._model_dir / domain
        if domain_dir.exists() and domain_dir.is_dir():
            shutil.rmtree(domain_dir)
            return True
        return False
