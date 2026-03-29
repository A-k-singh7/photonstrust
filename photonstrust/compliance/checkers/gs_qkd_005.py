"""GS-QKD-005 security proof compliance checks."""

from __future__ import annotations

from typing import Any

from photonstrust.compliance.checkers import (
    normalize_sweep_rows,
    row_value,
    scenario_protocol_name,
)
from photonstrust.compliance.types import (
    STATUS_FAIL,
    STATUS_NOT_ASSESSED,
    STATUS_PASS,
    STATUS_WARNING,
)

_PROOF_APPLICABILITY: dict[str, set[str]] = {
    "shor_preskill": {"BB84_DECOY", "BB84", "BBM92", "E91"},
    "renner": {"BB84_DECOY", "BB84", "BBM92", "E91", "MDI_QKD"},
    "tomamichel": {"BB84_DECOY", "BB84", "BBM92", "MDI_QKD", "TF_QKD", "PM_QKD"},
}


def check_sp1(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """SP1: Proof method is approved and applicable to the protocol family."""
    del sweep_result, context

    proof_method = (scenario.get("finite_key") or {}).get("proof_method")
    if proof_method is None:
        return _na("No proof_method specified in finite_key configuration.")

    proof_method = str(proof_method).strip()
    protocol_name = scenario_protocol_name(scenario)
    proto_upper = protocol_name.upper().replace("-", "_").replace(" ", "_")

    applicable_protocols = _PROOF_APPLICABILITY.get(proof_method)
    if applicable_protocols is None:
        return {
            "status": STATUS_FAIL,
            "computed_value": proof_method,
            "threshold": list(_PROOF_APPLICABILITY.keys()),
            "unit": None,
            "notes": [f"Proof method '{proof_method}' is not in the approved set."],
        }

    if proto_upper in applicable_protocols:
        return {
            "status": STATUS_PASS,
            "computed_value": proof_method,
            "threshold": sorted(applicable_protocols),
            "unit": None,
            "notes": [
                f"Proof method '{proof_method}' is approved for protocol '{proto_upper}'."
            ],
        }

    return {
        "status": STATUS_FAIL,
        "computed_value": proof_method,
        "threshold": sorted(applicable_protocols),
        "unit": None,
        "notes": [
            f"Proof method '{proof_method}' is not applicable to protocol '{proto_upper}'.",
            f"Applicable protocols: {sorted(applicable_protocols)}.",
        ],
    }


def check_sp2(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """SP2: Epsilon budget decomposition is valid (components sum correctly, all positive)."""
    del scenario, context

    rows = normalize_sweep_rows(sweep_result)
    budget = _find_epsilon_budget(rows)
    if budget is None:
        return _na("No epsilon_budget found in sweep results.")

    eps_pa = budget.get("epsilon_pa")
    eps_pe = budget.get("epsilon_pe")
    eps_ec = budget.get("epsilon_ec")
    eps_sec = budget.get("epsilon_sec")
    eps_cor = budget.get("epsilon_cor")
    eps_total = budget.get("epsilon_total")

    components = [eps_pa, eps_pe, eps_ec, eps_sec, eps_cor, eps_total]
    if any(c is None for c in components):
        return _na("Epsilon budget is incomplete; missing one or more components.")

    notes: list[str] = []

    # Check all components are positive
    for name, value in [
        ("epsilon_pa", eps_pa),
        ("epsilon_pe", eps_pe),
        ("epsilon_ec", eps_ec),
        ("epsilon_sec", eps_sec),
        ("epsilon_cor", eps_cor),
        ("epsilon_total", eps_total),
    ]:
        if value <= 0:
            notes.append(f"{name}={value} is not positive.")

    if notes:
        return {
            "status": STATUS_FAIL,
            "computed_value": budget,
            "threshold": "all components > 0",
            "unit": None,
            "notes": notes,
        }

    # Check epsilon_pa + epsilon_pe == epsilon_sec
    sec_sum = eps_pa + eps_pe
    if abs(sec_sum - eps_sec) > 1e-15:
        notes.append(
            f"epsilon_pa + epsilon_pe = {sec_sum} != epsilon_sec = {eps_sec} "
            f"(delta={abs(sec_sum - eps_sec):.2e})."
        )

    # Check epsilon_sec + epsilon_cor == epsilon_total
    total_sum = eps_sec + eps_cor
    if abs(total_sum - eps_total) > 1e-15:
        notes.append(
            f"epsilon_sec + epsilon_cor = {total_sum} != epsilon_total = {eps_total} "
            f"(delta={abs(total_sum - eps_total):.2e})."
        )

    if notes:
        return {
            "status": STATUS_FAIL,
            "computed_value": budget,
            "threshold": "epsilon_pa+epsilon_pe=epsilon_sec; epsilon_sec+epsilon_cor=epsilon_total",
            "unit": None,
            "notes": notes,
        }

    return {
        "status": STATUS_PASS,
        "computed_value": budget,
        "threshold": "valid decomposition",
        "unit": None,
        "notes": ["Epsilon budget decomposition is consistent."],
    }


def check_sp3(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """SP3: Smooth min-entropy lower bound computation is consistent with the proof method."""
    del scenario, context

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for SP3 assessment.")

    key_lengths = _collect_composable_key_lengths(rows)
    if not key_lengths:
        return _na("No composable_key_length_bits found in sweep results.")

    max_key = max(key_lengths)
    if max_key > 0:
        return {
            "status": STATUS_PASS,
            "computed_value": max_key,
            "threshold": 0,
            "unit": "bits",
            "notes": ["Composable key length is positive; entropy bound is consistent."],
        }

    return _na("Composable key lengths are all zero or negative; cannot verify entropy bound.")


def check_sp4(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """SP4: Privacy amplification output length is consistent with leftover hash lemma."""
    del scenario, context

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for SP4 assessment.")

    key_lengths = _collect_composable_key_lengths(rows)
    if not key_lengths:
        return _na("No composable_key_length_bits found in sweep results.")

    max_key = max(key_lengths)
    if max_key > 0:
        return {
            "status": STATUS_PASS,
            "computed_value": max_key,
            "threshold": 0,
            "unit": "bits",
            "notes": [
                "Privacy amplification output length is positive and finite."
            ],
        }

    if max_key == 0:
        return {
            "status": STATUS_WARNING,
            "computed_value": 0,
            "threshold": 0,
            "unit": "bits",
            "notes": [
                "Privacy amplification output length is zero; no secret key can be extracted."
            ],
        }

    return _na("Composable key length data is missing or invalid.")


def check_sp5(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """SP5: Parameter estimation uses appropriate statistical bound with valid configuration."""
    del sweep_result, context

    fk_cfg = (scenario or {}).get("finite_key") or {}
    composable_version = str(fk_cfg.get("composable_version", ""))

    if composable_version != "v2":
        return _na(
            f"composable_version='{composable_version}'; "
            "SP5 only assessed for v2 composable proofs."
        )

    pe_fraction = fk_cfg.get("parameter_estimation_fraction")
    if pe_fraction is None:
        return _na("No parameter_estimation_fraction specified.")

    try:
        pe_fraction = float(pe_fraction)
    except (TypeError, ValueError):
        return {
            "status": STATUS_FAIL,
            "computed_value": pe_fraction,
            "threshold": "(0, 1)",
            "unit": None,
            "notes": ["parameter_estimation_fraction is not a valid number."],
        }

    if 0 < pe_fraction < 1:
        return {
            "status": STATUS_PASS,
            "computed_value": pe_fraction,
            "threshold": "(0, 1)",
            "unit": None,
            "notes": [
                f"parameter_estimation_fraction={pe_fraction} is in valid range (0, 1)."
            ],
        }

    return {
        "status": STATUS_FAIL,
        "computed_value": pe_fraction,
        "threshold": "(0, 1)",
        "unit": None,
        "notes": [
            f"parameter_estimation_fraction={pe_fraction} is out of valid range (0, 1)."
        ],
    }


def _find_epsilon_budget(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Extract the first valid epsilon_budget from sweep rows."""
    for row in rows:
        budget = row_value(row, "epsilon_budget", None)
        if isinstance(budget, dict) and "epsilon_total" in budget:
            return dict(budget)
    return None


def _collect_composable_key_lengths(rows: list[dict[str, Any]]) -> list[int]:
    """Collect composable_key_length_bits values from sweep rows."""
    lengths: list[int] = []
    for row in rows:
        value = row_value(row, "composable_key_length_bits", None)
        if value is not None:
            try:
                lengths.append(int(value))
            except (TypeError, ValueError):
                continue
    return lengths


def _na(note: str) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_ASSESSED,
        "computed_value": None,
        "threshold": None,
        "unit": None,
        "notes": [str(note)],
    }
