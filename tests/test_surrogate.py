"""Tests for AI surrogate models & fast inference (Feature 11)."""

from __future__ import annotations

import pytest

sklearn = pytest.importorskip("sklearn")

from photonstrust.surrogate.domains import SURROGATE_DOMAINS, get_physics_fn
from photonstrust.surrogate.inference import fast_predict
from photonstrust.surrogate.registry import SurrogateRegistry
from photonstrust.surrogate.trainer import SurrogateTrainer
from photonstrust.surrogate.types import (
    PredictionResult,
    SurrogateModelMetadata,
    TrainingConfig,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN = "qkd_key_rate"
_RANGES = SURROGATE_DOMAINS[_DOMAIN]["default_ranges"]


def _make_config(**overrides) -> TrainingConfig:
    defaults = dict(
        domain=_DOMAIN,
        hidden_layer_sizes=(32, 32),
        max_iter=300,
        random_state=42,
        n_training_samples=60,
        parameter_ranges=_RANGES,
    )
    defaults.update(overrides)
    return TrainingConfig(**defaults)


def _train_and_save(tmp_path):
    """Train a model and persist it to *tmp_path*."""
    from datetime import datetime, timezone

    config = _make_config()
    trainer = SurrogateTrainer(config)
    physics_fn = get_physics_fn(_DOMAIN)
    X, y, feat_names, tgt_names = trainer.generate_training_data(
        physics_fn, _RANGES, n_samples=60
    )
    model, validation = trainer.train(X, y, feat_names, tgt_names)

    metadata = SurrogateModelMetadata(
        domain=_DOMAIN,
        created_at_iso=datetime.now(timezone.utc).isoformat(),
        input_features=feat_names,
        output_features=tgt_names,
        training_config=config.as_dict(),
        validation=validation.as_dict(),
    )

    registry = SurrogateRegistry(tmp_path)
    registry.save_model(_DOMAIN, model, metadata)
    return registry, model, metadata, validation


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_training_data_generation():
    """Generate data for qkd_key_rate domain, verify shape."""
    config = _make_config(n_training_samples=50)
    trainer = SurrogateTrainer(config)
    physics_fn = get_physics_fn(_DOMAIN)
    X, y, feat_names, tgt_names = trainer.generate_training_data(
        physics_fn, _RANGES, n_samples=50
    )

    n_features = len(_RANGES)
    assert X.shape == (50, n_features)
    assert y.shape[0] == 50
    assert len(feat_names) == n_features
    assert len(tgt_names) >= 1


def test_train_and_validate():
    """Train model, verify R-squared > 0 on test set."""
    config = _make_config(
        n_training_samples=200,
        hidden_layer_sizes=(64, 64),
        max_iter=1000,
    )
    trainer = SurrogateTrainer(config)
    physics_fn = get_physics_fn(_DOMAIN)
    X, y, feat_names, tgt_names = trainer.generate_training_data(
        physics_fn, _RANGES, n_samples=200
    )
    model, validation = trainer.train(X, y, feat_names, tgt_names)

    assert isinstance(validation, ValidationResult)
    assert validation.r_squared > 0
    assert validation.n_train > 0
    assert validation.n_test > 0


def test_model_save_and_load(tmp_path):
    """Save model, load it back, verify metadata matches."""
    registry, _model, metadata, _val = _train_and_save(tmp_path)

    loaded_model, loaded_meta = registry.load_model(_DOMAIN)
    assert loaded_meta.domain == metadata.domain
    assert loaded_meta.input_features == metadata.input_features
    assert loaded_meta.output_features == metadata.output_features
    assert loaded_model is not None


def test_fast_predict_with_model(tmp_path):
    """Train + save + predict -> from_surrogate=True."""
    registry, _model, _meta, _val = _train_and_save(tmp_path)

    params = {
        "distance_km": 50.0,
        "mu": 0.4,
        "pde": 0.3,
        "dark_counts_cps": 500.0,
        "fiber_loss_db_per_km": 0.2,
        "rep_rate_mhz": 100.0,
    }

    result = fast_predict(_DOMAIN, params, registry=registry)
    assert result.from_surrogate is True
    assert "key_rate_bps" in result.predictions
    assert isinstance(result.confidence, float)


def test_fast_predict_fallback_no_model(tmp_path):
    """No model -> falls back to physics -> from_surrogate=False."""
    registry = SurrogateRegistry(tmp_path)
    params = {
        "distance_km": 50.0,
        "mu": 0.4,
        "pde": 0.3,
        "dark_counts_cps": 500.0,
        "fiber_loss_db_per_km": 0.2,
        "rep_rate_mhz": 100.0,
    }

    result = fast_predict(
        _DOMAIN, params, registry=registry, fallback_physics=True
    )
    assert result.from_surrogate is False
    assert "key_rate_bps" in result.predictions


def test_domain_registry_has_qkd_key_rate():
    """'qkd_key_rate' in SURROGATE_DOMAINS."""
    assert "qkd_key_rate" in SURROGATE_DOMAINS


def test_prediction_result_serialization():
    """PredictionResult.as_dict() works."""
    pr = PredictionResult(
        domain="qkd_key_rate",
        predictions={"key_rate_bps": 42.0},
        confidence=0.9,
        from_surrogate=True,
    )
    d = pr.as_dict()
    assert d["domain"] == "qkd_key_rate"
    assert d["predictions"]["key_rate_bps"] == 42.0
    assert d["confidence"] == 0.9
    assert d["from_surrogate"] is True


def test_confidence_estimation(tmp_path):
    """Predict with params in range -> confidence >= 0.5."""
    registry, _model, _meta, _val = _train_and_save(tmp_path)

    params = {
        "distance_km": 50.0,
        "mu": 0.4,
        "pde": 0.3,
        "dark_counts_cps": 500.0,
        "fiber_loss_db_per_km": 0.2,
        "rep_rate_mhz": 100.0,
    }

    result = fast_predict(_DOMAIN, params, registry=registry)
    assert result.confidence >= 0.5
