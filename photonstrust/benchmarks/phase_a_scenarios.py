"""Phase A benchmark scenarios and acceptance gates.

Three canonical benchmark scenarios that exercise the Phase A hardening:
1. Metro Fiber BB84 with Coexistence — fiber deployment + Raman + connectors
2. Satellite Downlink BBM92 — free-space + orbit pass + turbulence + pointing
3. PIC Ring Resonator Verification — chipverify pipeline (metrics only, no jax)

Each scenario returns a BenchmarkResult with pass/fail gate evaluations
and full diagnostics for deterministic replay.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AcceptanceGate:
    """Single acceptance criterion for a benchmark."""
    name: str
    metric: str
    threshold: float
    comparator: str  # "lt", "gt", "le", "ge", "eq"
    actual: float
    status: str  # "pass" or "fail"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "metric": self.metric,
            "threshold": self.threshold,
            "comparator": self.comparator,
            "actual": self.actual,
            "status": self.status,
        }


@dataclass(frozen=True)
class BenchmarkResult:
    """Result of a benchmark scenario run."""
    scenario_id: str
    scenario_name: str
    overall_status: str  # "pass" or "fail"
    gates: list[AcceptanceGate]
    diagnostics: dict[str, Any]

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "overall_status": self.overall_status,
            "gates": [g.as_dict() for g in self.gates],
            "diagnostics": dict(self.diagnostics),
        }


def _evaluate_gate(name: str, metric: str, threshold: float, comparator: str, actual: float) -> AcceptanceGate:
    if comparator == "lt":
        ok = actual < threshold
    elif comparator == "gt":
        ok = actual > threshold
    elif comparator == "le":
        ok = actual <= threshold
    elif comparator == "ge":
        ok = actual >= threshold
    elif comparator == "eq":
        ok = abs(actual - threshold) < 1e-9
    else:
        ok = False
    return AcceptanceGate(
        name=name, metric=metric, threshold=threshold,
        comparator=comparator, actual=actual,
        status="pass" if ok else "fail",
    )


# ---------------------------------------------------------------------------
# Scenario 1: Metro Fiber BB84 with Coexistence
# ---------------------------------------------------------------------------

def run_metro_fiber_bb84(
    *,
    distance_km: float = 50.0,
    seed: int | None = 42,
) -> BenchmarkResult:
    """Run the metro fiber BB84 benchmark with WDM coexistence.

    Validates fiber deployment realism including:
    - Fiber attenuation + connector/splice chain
    - Raman coexistence (forward + backward)
    - PMD contribution
    - Enhanced timing budget
    - Finite-key penalty
    """
    from photonstrust.channels.engine import compute_channel_diagnostics
    from photonstrust.channels.fiber_deployment import (
        compute_fiber_deployment_diagnostics,
        connector_splice_chain,
        combined_raman_budget,
    )

    channel_cfg = {
        "model": "fiber",
        "fiber_loss_db_per_km": 0.2,
        "connector_loss_db": 0.5,
        "background_counts_cps": 100.0,
        "coexistence": {
            "enabled": True,
            "classical_launch_power_dbm": 0.0,
            "classical_channel_count": 4,
            "filter_bandwidth_nm": 0.2,
            "raman_coeff_cps_per_km_per_mw_per_nm": 1e-4,
            "direction": "co",
            "raman_model": "effective_length",
        },
    }

    # Channel diagnostics
    ch_diag = compute_channel_diagnostics(
        distance_km=distance_km,
        wavelength_nm=1310.0,
        channel_cfg=channel_cfg,
    )

    # Fiber deployment diagnostics
    deploy_diag = compute_fiber_deployment_diagnostics(
        distance_km=distance_km,
        channel_cfg={
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 0.5,
            "splice_loss_db": 0.1,
            "pmd_coeff_ps_per_sqrt_km": 0.1,
            "coexistence": channel_cfg["coexistence"],
        },
        detector_cfg={"jitter_ps": 50.0},
        timing_cfg={"system_jitter_ps": 30.0, "dispersion_ps_per_km": 17.0},
    )

    # Connector/splice budget
    cs = connector_splice_chain(distance_km=distance_km)

    # Combined Raman
    raman = combined_raman_budget(
        distance_km=distance_km,
        coexistence=channel_cfg["coexistence"],
        fiber_loss_db_per_km=0.2,
    )

    # Evaluate gates
    total_loss_db = ch_diag.get("total_loss_db", 0.0)
    gates = [
        _evaluate_gate("max_total_loss", "total_loss_db", 25.0, "lt", total_loss_db),
        _evaluate_gate("raman_below_threshold", "total_raman_cps", 1e6, "lt", raman.total_raman_counts_cps),
        _evaluate_gate("connector_loss_budget", "connector_splice_loss_db", 20.0, "lt", cs.total_loss_db),
        _evaluate_gate("timing_budget_ok", "sigma_effective_ps", 200.0, "lt",
                       deploy_diag.timing_budget.sigma_effective_ps),
        _evaluate_gate("visibility_above_floor", "effective_visibility", 0.9, "gt",
                       deploy_diag.effective_visibility),
    ]

    overall = "pass" if all(g.status == "pass" for g in gates) else "fail"

    return BenchmarkResult(
        scenario_id="phase_a.metro_fiber_bb84",
        scenario_name="Metro Fiber BB84 with Coexistence",
        overall_status=overall,
        gates=gates,
        diagnostics={
            "channel": ch_diag,
            "deployment": deploy_diag.as_dict(),
            "connector_splice": cs.as_dict(),
            "raman_budget": raman.as_dict(),
            "distance_km": distance_km,
        },
    )


# ---------------------------------------------------------------------------
# Scenario 2: Satellite Downlink BBM92
# ---------------------------------------------------------------------------

def run_satellite_downlink_bbm92(
    *,
    orbit_altitude_km: float = 500.0,
    max_elevation_deg: float = 70.0,
    pass_duration_s: float = 300.0,
    seed: int | None = 42,
) -> BenchmarkResult:
    """Run the satellite downlink BBM92 benchmark.

    Validates free-space + satellite realism including:
    - Hufnagel-Valley Cn2 profile
    - Turbulence fading distribution selection
    - Pointing bias + jitter decomposition
    - Orbit pass envelope with time-varying link budget
    - Background noise (night)
    """
    from photonstrust.satellite.turbulence import compute_rytov_variance, select_fading_model
    from photonstrust.satellite.pointing import pointing_budget
    from photonstrust.satellite.orbit import compute_orbit_pass_envelope
    from photonstrust.satellite.background import estimate_background_counts_cps

    # Cn2 profile and Rytov variance at 30 deg zenith
    hv = compute_rytov_variance(
        wavelength_nm=810.0,
        zenith_angle_deg=30.0,
        orbit_altitude_km=orbit_altitude_km,
    )

    # Fading distribution
    fading = select_fading_model(
        scintillation_index=hv.scintillation_index,
        rytov_variance=hv.rytov_variance,
        seed=seed,
    )

    # Pointing budget
    pointing = pointing_budget(
        bias_urad=1.0,
        jitter_urad=2.0,
        beam_divergence_urad=10.0,
        seed=seed,
    )

    # Background (night)
    bg = estimate_background_counts_cps(
        wavelength_nm=810.0,
        fov_urad=100.0,
        rx_aperture_m=0.4,
        filter_bandwidth_nm=1.0,
        detector_efficiency=0.5,
        day_night="night",
    )

    # Orbit pass envelope
    env = compute_orbit_pass_envelope(
        orbit_altitude_km=orbit_altitude_km,
        max_elevation_deg=max_elevation_deg,
        pass_duration_s=pass_duration_s,
        time_step_s=10.0,
    )

    gates = [
        _evaluate_gate("fried_parameter_positive", "fried_parameter_m", 0.0, "gt", hv.fried_parameter_m),
        _evaluate_gate("fading_outage_bounded", "outage_probability", 0.5, "lt", fading.outage_probability),
        _evaluate_gate("pointing_efficiency_ok", "eta_mean", 0.5, "gt", pointing.eta_mean),
        _evaluate_gate("background_below_limit", "background_cps", 1e6, "lt", bg.counts_cps),
        _evaluate_gate("pass_generates_key", "total_key_bits", 0.0, "gt", env.total_key_bits),
        _evaluate_gate("outage_fraction_bounded", "outage_fraction", 0.8, "lt", env.outage_fraction),
    ]

    overall = "pass" if all(g.status == "pass" for g in gates) else "fail"

    return BenchmarkResult(
        scenario_id="phase_a.satellite_downlink_bbm92",
        scenario_name="Satellite Downlink BBM92",
        overall_status=overall,
        gates=gates,
        diagnostics={
            "hufnagel_valley": hv.as_dict(),
            "fading": fading.as_dict(),
            "pointing": pointing.as_dict(),
            "background": bg.as_dict(),
            "orbit_pass": env.as_dict(),
        },
    )


# ---------------------------------------------------------------------------
# Scenario 3: PIC Ring Resonator Verification (metrics only)
# ---------------------------------------------------------------------------

def run_pic_ring_resonator(*, seed: int | None = 42) -> BenchmarkResult:
    """Run the PIC ring resonator benchmark.

    Tests the ChipVerify metrics computation without requiring jax.
    Uses synthetic simulation results to validate the metrics pipeline:
    - Insertion loss
    - Phase error sensitivity
    - Group delay variation
    - Process yield estimate
    """
    try:
        from photonstrust.chipverify.metrics import compute_pic_metrics
        _has_chipverify = True
    except ImportError:
        _has_chipverify = False

    if not _has_chipverify:
        return BenchmarkResult(
            scenario_id="phase_a.pic_ring_resonator",
            scenario_name="PIC Ring Resonator Verification",
            overall_status="skip",
            gates=[],
            diagnostics={"reason": "chipverify requires jax"},
        )

    sim_results = {
        "chain_solver": {
            "applicable": True,
            "total_loss_db": 8.0,
            "per_component": [
                {"kind": "pic.grating_coupler", "loss_db": 3.0,
                 "phase_sensitivity_rad_per_nm": 0.1, "group_delay_ps": 0.5},
                {"kind": "pic.waveguide", "loss_db": 0.5,
                 "phase_sensitivity_rad_per_nm": 0.05, "group_delay_ps": 1.0},
                {"kind": "pic.ring", "loss_db": 1.0, "bandwidth_3db_nm": 0.2,
                 "phase_sensitivity_rad_per_nm": 2.0, "group_delay_ps": 5.0},
                {"kind": "pic.waveguide", "loss_db": 0.5,
                 "phase_sensitivity_rad_per_nm": 0.05, "group_delay_ps": 1.0},
                {"kind": "pic.grating_coupler", "loss_db": 3.0,
                 "phase_sensitivity_rad_per_nm": 0.1, "group_delay_ps": 0.5},
            ],
        }
    }
    netlist = {
        "nodes": [{"id": f"n{i}"} for i in range(5)],
        "edges": [{"from": f"n{i}", "to": f"n{i+1}"} for i in range(4)],
    }

    metrics = compute_pic_metrics(simulation_results=sim_results, netlist=netlist)

    gates = [
        _evaluate_gate("insertion_loss_budget", "total_insertion_loss_db", 15.0, "lt",
                       metrics.total_insertion_loss_db),
        _evaluate_gate("bandwidth_present", "bandwidth_3db_nm", 0.0, "gt",
                       metrics.bandwidth_3db_nm or 0.0),
    ]
    if metrics.phase_error_sensitivity_rad_per_nm is not None:
        gates.append(_evaluate_gate(
            "phase_error_bounded", "phase_error_sensitivity_rad_per_nm", 10.0, "lt",
            metrics.phase_error_sensitivity_rad_per_nm,
        ))
    if metrics.process_yield_estimate_pct is not None:
        gates.append(_evaluate_gate(
            "yield_acceptable", "process_yield_estimate_pct", 80.0, "gt",
            metrics.process_yield_estimate_pct,
        ))

    overall = "pass" if all(g.status == "pass" for g in gates) else "fail"

    return BenchmarkResult(
        scenario_id="phase_a.pic_ring_resonator",
        scenario_name="PIC Ring Resonator Verification",
        overall_status=overall,
        gates=gates,
        diagnostics={"metrics": metrics.as_dict()},
    )


# ---------------------------------------------------------------------------
# Run all benchmarks
# ---------------------------------------------------------------------------

def run_all_benchmarks(*, seed: int | None = 42) -> list[BenchmarkResult]:
    """Run all Phase A benchmark scenarios."""
    results = [
        run_metro_fiber_bb84(seed=seed),
        run_satellite_downlink_bbm92(seed=seed),
        run_pic_ring_resonator(seed=seed),
    ]
    return results
