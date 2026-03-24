"""Tests for GS-QKD-005 security proof compliance checks."""

from __future__ import annotations

from typing import Any

import pytest

from photonstrust.compliance.checkers.gs_qkd_005 import (
    check_sp1,
    check_sp2,
    check_sp3,
    check_sp4,
    check_sp5,
)
from photonstrust.compliance.registry import get_requirements


def _empty_context() -> dict[str, Any]:
    return {}


def _make_scenario(
    *,
    protocol_name: str = "BB84_DECOY",
    proof_method: str | None = "shor_preskill",
    composable_version: str = "",
    pe_fraction: float | None = None,
) -> dict[str, Any]:
    scenario: dict[str, Any] = {
        "protocol": {"name": protocol_name},
    }
    fk: dict[str, Any] = {}
    if proof_method is not None:
        fk["proof_method"] = proof_method
    if composable_version:
        fk["composable_version"] = composable_version
    if pe_fraction is not None:
        fk["parameter_estimation_fraction"] = pe_fraction
    if fk:
        scenario["finite_key"] = fk
    return scenario


def _make_sweep(
    *,
    epsilon_budget: dict[str, Any] | None = None,
    composable_key_length_bits: int | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "distance_km": 50.0,
        "key_rate_bps": 1000.0,
        "qber_total": 0.03,
    }
    if epsilon_budget is not None:
        row["epsilon_budget"] = epsilon_budget
    if composable_key_length_bits is not None:
        row["composable_key_length_bits"] = composable_key_length_bits
    return {"results": [row]}


def _valid_epsilon_budget() -> dict[str, Any]:
    eps_pa = 1e-11
    eps_pe = 1e-11
    eps_ec = 1e-11
    eps_sec = eps_pa + eps_pe  # 2e-11
    eps_cor = 1e-11
    eps_total = eps_sec + eps_cor  # 3e-11
    return {
        "epsilon_pa": eps_pa,
        "epsilon_pe": eps_pe,
        "epsilon_ec": eps_ec,
        "epsilon_sec": eps_sec,
        "epsilon_cor": eps_cor,
        "epsilon_total": eps_total,
    }


# ---------------------------------------------------------------------------
# SP1: Proof method is approved and applicable
# ---------------------------------------------------------------------------


def test_sp1_shor_preskill_bb84_passes() -> None:
    scenario = _make_scenario(protocol_name="BB84_DECOY", proof_method="shor_preskill")
    result = check_sp1(None, scenario, context=_empty_context())
    assert result["status"] == "PASS"


def test_sp1_shor_preskill_mdi_fails() -> None:
    scenario = _make_scenario(protocol_name="MDI_QKD", proof_method="shor_preskill")
    result = check_sp1(None, scenario, context=_empty_context())
    assert result["status"] == "FAIL"


def test_sp1_missing_proof_method() -> None:
    scenario = _make_scenario(proof_method=None)
    result = check_sp1(None, scenario, context=_empty_context())
    assert result["status"] == "NOT_ASSESSED"


# ---------------------------------------------------------------------------
# SP2: Epsilon budget decomposition
# ---------------------------------------------------------------------------


def test_sp2_valid_budget() -> None:
    budget = _valid_epsilon_budget()
    sweep = _make_sweep(epsilon_budget=budget)
    result = check_sp2(sweep, {}, context=_empty_context())
    assert result["status"] == "PASS"


def test_sp2_negative_component() -> None:
    budget = _valid_epsilon_budget()
    budget["epsilon_pa"] = -1e-11
    sweep = _make_sweep(epsilon_budget=budget)
    result = check_sp2(sweep, {}, context=_empty_context())
    assert result["status"] == "FAIL"


def test_sp2_sum_mismatch() -> None:
    budget = _valid_epsilon_budget()
    # Break the sum: epsilon_sec != epsilon_pa + epsilon_pe
    budget["epsilon_sec"] = 9e-11
    sweep = _make_sweep(epsilon_budget=budget)
    result = check_sp2(sweep, {}, context=_empty_context())
    assert result["status"] == "FAIL"


# ---------------------------------------------------------------------------
# SP3: Smooth min-entropy lower bound
# ---------------------------------------------------------------------------


def test_sp3_positive_key_length_passes() -> None:
    sweep = _make_sweep(composable_key_length_bits=1024)
    result = check_sp3(sweep, {}, context=_empty_context())
    assert result["status"] == "PASS"


# ---------------------------------------------------------------------------
# SP4: Privacy amplification output length
# ---------------------------------------------------------------------------


def test_sp4_zero_key_length_warning() -> None:
    sweep = _make_sweep(composable_key_length_bits=0)
    result = check_sp4(sweep, {}, context=_empty_context())
    assert result["status"] == "WARNING"


# ---------------------------------------------------------------------------
# SP5: Parameter estimation bound configuration
# ---------------------------------------------------------------------------


def test_sp5_valid_pe_config() -> None:
    scenario = _make_scenario(composable_version="v2", pe_fraction=0.1)
    result = check_sp5(None, scenario, context=_empty_context())
    assert result["status"] == "PASS"


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


def test_gs_qkd_005_in_registry() -> None:
    reqs = get_requirements(["GS-QKD-005"])
    assert len(reqs) == 5
    ids = {r.id for r in reqs}
    assert ids == {
        "GS-QKD-005-SP1",
        "GS-QKD-005-SP2",
        "GS-QKD-005-SP3",
        "GS-QKD-005-SP4",
        "GS-QKD-005-SP5",
    }
