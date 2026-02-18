"""Research-anchored validation checks for core QKD model behaviors.

Each check maps a model behavior to a published formula/claim and reports a
machine-readable pass/fail result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

from photonstrust.physics import build_source_profile
from photonstrust.qkd import compute_point


@dataclass(frozen=True)
class ResearchCheckResult:
    name: str
    ok: bool
    details: list[str]
    references: list[str]
    metrics: dict[str, Any]


def run_research_validation_suite(*, repo_root: Path | None = None) -> dict[str, Any]:
    checks = [
        _check_spdc_thermal_distribution(),
        _check_pm_qkd_geometric_mean_scaling(),
        _check_plob_direct_link_bound(),
        _check_mdi_key_rate_term_sensitivity(),
    ]
    ok = all(check.ok for check in checks)
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.research_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str((repo_root or Path.cwd()).resolve()),
        "ok": ok,
        "check_count": len(checks),
        "failed_checks": sum(1 for check in checks if not check.ok),
        "checks": [asdict(check) for check in checks],
    }


def _check_spdc_thermal_distribution() -> ResearchCheckResult:
    mu_values = [0.01, 0.1, 0.5, 1.0]
    details: list[str] = []
    rows: list[dict[str, float]] = []
    ok = True
    for mu in mu_values:
        profile = build_source_profile({"type": "spdc", "mu": mu})
        expected_emission = mu / (1.0 + mu)
        expected_p_multi = mu / (1.0 + mu)
        rows.append(
            {
                "mu": float(mu),
                "emission_prob": float(profile.emission_prob),
                "expected_emission_prob": float(expected_emission),
                "p_multi": float(profile.p_multi),
                "expected_p_multi": float(expected_p_multi),
            }
        )
        if not math.isclose(profile.emission_prob, expected_emission, rel_tol=0.0, abs_tol=1e-12):
            ok = False
            details.append(
                f"mu={mu}: emission_prob mismatch observed={profile.emission_prob:.12g} "
                f"expected={expected_emission:.12g}"
            )
        if not math.isclose(profile.p_multi, expected_p_multi, rel_tol=0.0, abs_tol=1e-12):
            ok = False
            details.append(
                f"mu={mu}: p_multi mismatch observed={profile.p_multi:.12g} expected={expected_p_multi:.12g}"
            )
    if ok:
        details.append("SPDC source profile matches thermal/geometric pair statistics for tested mu grid.")
    return ResearchCheckResult(
        name="spdc_thermal_geometric_statistics",
        ok=ok,
        details=details,
        references=[
            "https://arxiv.org/abs/1805.05538",
            "https://doi.org/10.1103/PhysRevX.8.031043",
        ],
        metrics={"samples": rows},
    )


def _check_pm_qkd_geometric_mean_scaling() -> ResearchCheckResult:
    scenario = _pm_reference_scenario()
    distance_km = 100.0
    relay_fracs = [0.5, 0.1, 0.9]
    rates: dict[str, float] = {}

    for frac in relay_fracs:
        sc = _deep_copy_scenario(scenario)
        sc["protocol"]["relay_fraction"] = float(frac)
        rates[f"{frac:.1f}"] = float(compute_point(sc, distance_km=distance_km).key_rate_bps)

    ref = rates["0.5"]
    max_rel_dev = 0.0
    details: list[str] = []
    ok = ref > 0.0
    if not ok:
        details.append("reference PM_QKD key rate at relay_fraction=0.5 is zero")
    else:
        for key, rate in rates.items():
            rel_dev = abs(rate - ref) / max(abs(ref), 1e-30)
            max_rel_dev = max(max_rel_dev, rel_dev)
        tol = 0.05
        if max_rel_dev > tol:
            ok = False
            details.append(
                f"asymmetric-link rate drift too large: max_rel_dev={max_rel_dev:.3g} "
                f"(expected <= {tol:.3g})"
            )
        else:
            details.append(
                f"PM_QKD split invariance holds in loss-only setting (max_rel_dev={max_rel_dev:.3g})."
            )

    return ResearchCheckResult(
        name="pm_qkd_geometric_mean_asymmetry_scaling",
        ok=ok,
        details=details,
        references=[
            "https://arxiv.org/abs/1805.05538",
            "https://doi.org/10.1103/PhysRevX.8.031043",
        ],
        metrics={"distance_km": distance_km, "key_rate_bps_by_relay_fraction": rates, "max_rel_dev": max_rel_dev},
    )


def _check_plob_direct_link_bound() -> ResearchCheckResult:
    scenario = _bbm92_reference_scenario()
    distances_km = [0.0, 10.0, 50.0, 100.0, 200.0]
    rows: list[dict[str, float]] = []
    details: list[str] = []
    ok = True
    rep_rate_hz = float(scenario["source"]["rep_rate_mhz"]) * 1e6

    for distance_km in distances_km:
        result = compute_point(scenario, distance_km=distance_km)
        eta = 10.0 ** (-float(result.loss_db) / 10.0)
        plob = _plob_capacity_bits_per_use(eta) * rep_rate_hz
        margin = 1.01 * plob
        rows.append(
            {
                "distance_km": float(distance_km),
                "key_rate_bps": float(result.key_rate_bps),
                "plob_bound_bps": float(plob),
                "allowed_margin_bps": float(margin),
            }
        )
        if not (math.isfinite(result.key_rate_bps) and result.key_rate_bps >= 0.0):
            ok = False
            details.append(f"distance={distance_km} km: non-finite/negative key rate {result.key_rate_bps}")
            continue
        if result.key_rate_bps > margin:
            ok = False
            details.append(
                f"distance={distance_km} km: key rate {result.key_rate_bps:.12g} exceeds "
                f"PLOB margin {margin:.12g}"
            )

    if ok:
        details.append("Direct-link BBM92 key rates stay below repeaterless PLOB bound (1% margin).")

    return ResearchCheckResult(
        name="direct_link_plob_bound",
        ok=ok,
        details=details,
        references=[
            "https://doi.org/10.1038/ncomms15043",
            "https://arxiv.org/abs/1805.05538",
        ],
        metrics={"samples": rows},
    )


def _check_mdi_key_rate_term_sensitivity() -> ResearchCheckResult:
    scenario = _mdi_reference_scenario()
    low = _deep_copy_scenario(scenario)
    high = _deep_copy_scenario(scenario)
    low["protocol"]["ec_efficiency"] = 1.00
    high["protocol"]["ec_efficiency"] = 1.20

    distance_km = 100.0
    result_low = compute_point(low, distance_km=distance_km)
    result_high = compute_point(high, distance_km=distance_km)

    ok = math.isfinite(result_low.key_rate_bps) and math.isfinite(result_high.key_rate_bps)
    details: list[str] = []
    if not ok:
        details.append("non-finite MDI key rates encountered while sweeping ec_efficiency")
    elif result_high.key_rate_bps > result_low.key_rate_bps + 1e-12:
        ok = False
        details.append(
            f"higher ec_efficiency increased key rate unexpectedly: "
            f"ec=1.00 -> {result_low.key_rate_bps:.12g}, ec=1.20 -> {result_high.key_rate_bps:.12g}"
        )
    else:
        details.append(
            f"MDI key rate decreases with higher EC overhead as expected from Eq. (1): "
            f"{result_low.key_rate_bps:.6g} -> {result_high.key_rate_bps:.6g}"
        )

    return ResearchCheckResult(
        name="mdi_eq1_ec_efficiency_sensitivity",
        ok=ok,
        details=details,
        references=["https://arxiv.org/abs/1305.6965"],
        metrics={
            "distance_km": distance_km,
            "key_rate_bps_ec_1_00": float(result_low.key_rate_bps),
            "key_rate_bps_ec_1_20": float(result_high.key_rate_bps),
        },
    )


def _plob_capacity_bits_per_use(eta: float) -> float:
    eta = float(eta)
    if not math.isfinite(eta) or eta <= 0.0:
        return 0.0
    if eta >= 1.0:
        return float("inf")
    return -math.log2(1.0 - eta)


def _bbm92_reference_scenario() -> dict[str, Any]:
    return {
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16, "misalignment_prob": 0.0},
    }


def _mdi_reference_scenario() -> dict[str, Any]:
    scenario = _bbm92_reference_scenario()
    scenario["protocol"] = {
        "name": "MDI_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.4,
        "nu": 0.1,
        "omega": 0.0,
    }
    return scenario


def _pm_reference_scenario() -> dict[str, Any]:
    scenario = _bbm92_reference_scenario()
    scenario["channel"]["connector_loss_db"] = 0.0
    scenario["channel"]["dispersion_ps_per_km"] = 0.0
    scenario["detector"]["pde"] = 0.8
    scenario["detector"]["dark_counts_cps"] = 0.0
    scenario["detector"]["dead_time_ns"] = 0.0
    scenario["detector"]["afterpulsing_prob"] = 0.0
    scenario["timing"]["sync_drift_ps_rms"] = 0.0
    scenario["timing"]["coincidence_window_ps"] = 100.0
    scenario["protocol"] = {
        "name": "PM_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.0,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.2,
        "phase_slices": 16,
    }
    return scenario


def _deep_copy_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in scenario.items():
        if isinstance(value, dict):
            out[key] = dict(value)
        else:
            out[key] = value
    return out

