from __future__ import annotations

import pytest

from photonstrust.physics.backends.qiskit_backend import QiskitBackend


def test_qiskit_backend_applicability_reports_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = QiskitBackend()
    monkeypatch.setattr("photonstrust.physics.backends.qiskit_backend._qiskit_is_available", lambda: False)

    applicability = backend.applicability("repeater_primitive", {})

    assert applicability.status == "fail"
    assert "qiskit dependency not installed" in " ".join(applicability.reasons)


def test_qiskit_backend_provenance_contains_dependency_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = QiskitBackend()
    monkeypatch.setattr("photonstrust.physics.backends.qiskit_backend._qiskit_is_available", lambda: False)
    monkeypatch.setattr("photonstrust.physics.backends.qiskit_backend._qiskit_version", lambda: None)

    provenance = backend.provenance(seed=7).as_dict()

    assert provenance["backend_name"] == "qiskit"
    assert provenance["backend_version"] == "0.1"
    assert provenance["seed"] == 7
    assert provenance["qiskit_available"] is False
    assert provenance["qiskit_version"] is None


def test_qiskit_backend_repeater_crosscheck_is_deterministic() -> None:
    pytest.importorskip("qiskit")
    backend = QiskitBackend()
    out = backend.simulate("repeater_primitive", {"tolerance": 1.0e-12}, seed=123)

    assert out["status"] == "pass"
    assert out["summary"]["primitive"] == "swap_bsm_equal_bits"
    assert out["summary"]["formula_probability"] == pytest.approx(0.5, abs=1.0e-12)
    assert out["summary"]["circuit_probability"] == pytest.approx(0.5, abs=1.0e-12)
    assert out["summary"]["absolute_delta"] == pytest.approx(0.0, abs=1.0e-12)


def test_qiskit_backend_rejects_unsupported_component() -> None:
    backend = QiskitBackend()
    applicability = backend.applicability("detector", {})

    assert applicability.status == "fail"
    with pytest.raises(ValueError, match="does not support component"):
        backend.simulate("detector", {})
