"""API routes for AI surrogate model training and inference."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/surrogate", tags=["surrogate"])

_DEFAULT_MODEL_DIR = Path("data/surrogate_models")


def _get_registry() -> "SurrogateRegistry":  # noqa: F821
    from photonstrust.surrogate.registry import SurrogateRegistry

    return SurrogateRegistry(_DEFAULT_MODEL_DIR)


@router.post("/train/{domain}")
def train_surrogate(domain: str, payload: dict) -> dict:
    """Train a surrogate model for the given domain."""
    from datetime import datetime, timezone

    from photonstrust.surrogate.domains import SURROGATE_DOMAINS, get_physics_fn
    from photonstrust.surrogate.trainer import SurrogateTrainer
    from photonstrust.surrogate.types import SurrogateModelMetadata, TrainingConfig

    if domain not in SURROGATE_DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")

    domain_info = SURROGATE_DOMAINS[domain]
    ranges = payload.get("parameter_ranges", domain_info["default_ranges"])
    n_samples = payload.get("n_training_samples", 200)

    config = TrainingConfig(
        domain=domain,
        hidden_layer_sizes=tuple(payload.get("hidden_layer_sizes", (64, 64))),
        max_iter=payload.get("max_iter", 500),
        random_state=payload.get("random_state", 42),
        n_training_samples=n_samples,
        parameter_ranges=ranges,
    )

    trainer = SurrogateTrainer(config)
    physics_fn = get_physics_fn(domain)

    X, y, feat_names, tgt_names = trainer.generate_training_data(
        physics_fn, ranges, n_samples
    )
    model, validation = trainer.train(X, y, feat_names, tgt_names)

    metadata = SurrogateModelMetadata(
        domain=domain,
        created_at_iso=datetime.now(timezone.utc).isoformat(),
        input_features=feat_names,
        output_features=tgt_names,
        training_config=config.as_dict(),
        validation=validation.as_dict(),
    )

    registry = _get_registry()
    registry.save_model(domain, model, metadata)

    return {"status": "ok", "validation": validation.as_dict()}


@router.post("/predict/{domain}")
def predict(domain: str, payload: dict) -> dict:
    """Run fast inference using a surrogate or physics fallback."""
    from photonstrust.surrogate.inference import fast_predict

    registry = _get_registry()
    try:
        result = fast_predict(
            domain,
            payload.get("parameters", payload),
            registry=registry,
            fallback_physics=payload.get("fallback_physics", True),
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return result.as_dict()


@router.get("/models")
def list_models() -> dict:
    """List all saved surrogate models."""
    registry = _get_registry()
    models = registry.list_models()
    return {"models": [m.as_dict() for m in models]}


@router.get("/models/{domain}")
def get_model_info(domain: str) -> dict:
    """Get metadata for a specific surrogate model."""
    registry = _get_registry()
    try:
        _, metadata = registry.load_model(domain)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"No model found for domain '{domain}'"
        )
    return metadata.as_dict()


@router.delete("/models/{domain}")
def delete_model(domain: str) -> dict:
    """Delete a surrogate model."""
    registry = _get_registry()
    deleted = registry.delete_model(domain)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"No model found for domain '{domain}'"
        )
    return {"status": "ok", "domain": domain}
