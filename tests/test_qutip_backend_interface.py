from __future__ import annotations

import pytest

from photonstrust.physics.backends.qutip_backend import QutipBackend


def _emitter_source() -> dict:
    return {
        "type": "emitter_cavity",
        "physics_backend": "qutip",
        "seed": 123,
        "radiative_lifetime_ns": 1.0,
        "purcell_factor": 5.0,
        "dephasing_rate_per_ns": 0.5,
        "drive_strength": 0.05,
        "pulse_window_ns": 5.0,
        "g2_0": 0.02,
    }


def test_qutip_backend_applicability_reports_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = QutipBackend()
    monkeypatch.setattr("photonstrust.physics.backends.qutip_backend._qutip_is_available", lambda: False)

    applicability = backend.applicability("emitter", {})

    assert applicability.status == "fail"
    assert "qutip dependency not installed" in " ".join(applicability.reasons)


def test_qutip_backend_simulation_falls_back_to_analytic_when_qutip_path_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = QutipBackend()

    def _raise_qutip_failure(source: dict, emission_mode: str) -> dict:  # pragma: no cover - helper callback
        del source
        del emission_mode
        raise RuntimeError("forced qutip failure")

    monkeypatch.setattr("photonstrust.physics.emitter._qutip_emitter", _raise_qutip_failure)
    result = backend.simulate("emitter", _emitter_source(), seed=123)

    assert result["backend_requested"] == "qutip"
    assert result["backend"] == "analytic"
    assert "forced qutip failure" in str(result.get("fallback_reason", ""))


def test_qutip_backend_provenance_contains_dependency_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = QutipBackend()
    monkeypatch.setattr("photonstrust.physics.backends.qutip_backend._qutip_is_available", lambda: False)
    monkeypatch.setattr("photonstrust.physics.backends.qutip_backend._qutip_version", lambda: None)

    provenance = backend.provenance(seed=11).as_dict()

    assert provenance["backend_name"] == "qutip"
    assert provenance["backend_version"] == "0.1"
    assert provenance["seed"] == 11
    assert provenance["qutip_available"] is False
    assert provenance["qutip_version"] is None


def test_qutip_backend_rejects_unsupported_component() -> None:
    backend = QutipBackend()
    applicability = backend.applicability("memory", {})

    assert applicability.status == "fail"
    with pytest.raises(ValueError, match="does not support component"):
        backend.simulate("memory", {})
