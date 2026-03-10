from __future__ import annotations

import pytest

from photonstrust.protocols.engines import available_protocol_engines, get_protocol_engine
from photonstrust.protocols.engines import cirq_engine, pennylane_engine, qiskit_engine
from photonstrust.protocols.engines.base import ProtocolEngineUnavailableError


def test_protocol_engine_registry_contains_expected_engines() -> None:
    engines = set(available_protocol_engines())
    assert {"analytic", "qiskit", "cirq", "pennylane"}.issubset(engines)


def test_analytic_engine_contract_for_swap_bsm_equal_bits() -> None:
    engine = get_protocol_engine("analytic")
    result = engine.run_primitive("swap_bsm_equal_bits", seed=123)

    assert result.engine_id == "analytic"
    assert result.primitive == "swap_bsm_equal_bits"
    assert result.metrics["success_probability"] == pytest.approx(0.5, abs=1.0e-12)


def test_qiskit_engine_unavailable_error_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qiskit_engine, "_module_available", lambda module_name: False)
    engine = get_protocol_engine("qiskit")

    available, reason = engine.availability()
    assert available is False
    assert isinstance(reason, str)
    with pytest.raises(ProtocolEngineUnavailableError):
        engine.run_primitive("swap_bsm_equal_bits")


def test_optional_adapters_fail_cleanly_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cirq_engine, "_module_available", lambda module_name: False)
    monkeypatch.setattr(pennylane_engine, "_module_available", lambda module_name: False)

    cirq_adapter = get_protocol_engine("cirq")
    pennylane_adapter = get_protocol_engine("pennylane")

    with pytest.raises(ProtocolEngineUnavailableError):
        cirq_adapter.run_primitive("swap_bsm_equal_bits")
    with pytest.raises(ProtocolEngineUnavailableError):
        pennylane_adapter.run_primitive("swap_bsm_equal_bits")
