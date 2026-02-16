from __future__ import annotations

import pytest

from photonstrust.protocols.circuits import repeater_bsm_success_probability


def test_repeater_bsm_success_probability_matches_formula_when_qiskit_available() -> None:
    pytest.importorskip("qiskit")
    result = repeater_bsm_success_probability(seed=1)

    assert result["primitive"] == "swap_bsm_equal_bits"
    assert result["formula_probability"] == pytest.approx(0.5, abs=1.0e-12)
    assert result["circuit_probability"] == pytest.approx(0.5, abs=1.0e-12)
    assert result["absolute_delta"] == pytest.approx(0.0, abs=1.0e-12)
