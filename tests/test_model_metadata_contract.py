from __future__ import annotations

from photonstrust.physics.backends import resolve_backend
from photonstrust.physics.model_metadata import model_metadata_for_backend, validate_model_metadata_registry


def test_model_metadata_registry_entries_are_contract_complete() -> None:
    registry = validate_model_metadata_registry()
    assert registry
    for model in registry.values():
        assert model.citation
        assert model.validity_domain
        assert model.uncertainty_model
        assert model.known_failure_regimes


def test_backend_provenance_includes_model_metadata() -> None:
    backend = resolve_backend("analytic")
    provenance = backend.provenance(seed=3).as_dict()
    metadata = provenance.get("model_metadata")
    assert isinstance(metadata, dict)
    assert metadata
    first = next(iter(metadata.values()))
    assert "citation" in first
    assert "validity_domain" in first
    assert "uncertainty_model" in first


def test_unknown_backend_metadata_lookup_is_empty() -> None:
    assert model_metadata_for_backend("unknown_backend") == {}
