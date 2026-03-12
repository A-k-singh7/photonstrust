"""Compare PhotonTrust outputs against recent published QKD benchmark points.

This runner reports three views per benchmark case:
1) paper_locked: case-default parameters (metadata reproduction)
2) best_mu_fit: one-parameter mu sweep (legacy comparability)
3) best_fit: bounded multi-parameter coordinate search
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from photonstrust.qkd import compute_point

MetricMode = Literal["bps", "bpp"]


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    protocol: str
    distance_km: float
    target_value: float
    target_mode: MetricMode
    source_ref: str
    summary: str
    rep_rate_mhz: float
    fiber_loss_db_per_km: float
    connector_loss_db: float
    pde: float
    dark_counts_cps: float
    coincidence_window_ps: float
    default_mu: float

    default_nu: float = 0.02
    default_omega: float = 0.0
    default_phase_slices: int = 16
    default_sifting_factor: float = 1.0
    default_ec_efficiency: float = 1.16
    default_misalignment_prob: float = 0.01
    default_pairing_window_bins: int = 2048
    default_pairing_efficiency: float = 0.6
    default_pairing_error_prob: float = 0.0
    default_parallel_mode_count: float = 1.0
    default_entanglement_topology: str = "direct_link"
    default_relay_fraction: float = 0.5
    default_split_connector_loss: bool = True

    source_type: str = "spdc"
    collection_efficiency: float = 1.0
    coupling_efficiency: float = 1.0

    detector_class: str = "snspd"
    jitter_ps_fwhm: float = 30.0
    dead_time_ns: float = 0.0
    afterpulsing_prob: float = 0.0

    sync_drift_ps_rms: float = 10.0

    fit_mu_bounds: tuple[float, float] = (1e-3, 1.0)
    fit_phase_slices: tuple[int, ...] = (16,)
    fit_collection_efficiency_bounds: tuple[float, float] | None = None
    fit_coupling_efficiency_bounds: tuple[float, float] | None = None
    fit_rep_rate_mhz_bounds: tuple[float, float] | None = None
    fit_pde_bounds: tuple[float, float] | None = None
    fit_dark_counts_cps_bounds: tuple[float, float] | None = None
    fit_coincidence_window_ps_bounds: tuple[float, float] | None = None
    fit_misalignment_prob_bounds: tuple[float, float] | None = None
    fit_nu_ratio_bounds: tuple[float, float] | None = None
    fit_pairing_window_bins_bounds: tuple[float, float] | None = None
    fit_pairing_efficiency_bounds: tuple[float, float] | None = None
    fit_pairing_error_prob_bounds: tuple[float, float] | None = None
    fit_parallel_mode_count_bounds: tuple[float, float] | None = None


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    values: tuple[float, ...]
    is_discrete_int: bool = False


def _benchmark_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            case_id="tf_202km_111.74kbps",
            protocol="tf_qkd",
            distance_km=202.0,
            target_value=111_740.0,
            target_mode="bps",
            source_ref="https://doi.org/10.1007/s44214-023-00039-9",
            summary="TF-QKD finite-key at 202 km",
            rep_rate_mhz=877.5,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.805,
            dark_counts_cps=1.0,
            coincidence_window_ps=200.0,
            default_mu=0.330868201540854,
            fit_mu_bounds=(0.02, 0.60),
            fit_phase_slices=(16, 32),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.90),
            fit_dark_counts_cps_bounds=(1.0, 20.0),
            fit_coincidence_window_ps_bounds=(200.0, 800.0),
        ),
        BenchmarkCase(
            case_id="tf_303km_23.44kbps",
            protocol="tf_qkd",
            distance_km=303.0,
            target_value=23_440.0,
            target_mode="bps",
            source_ref="https://doi.org/10.1007/s44214-023-00039-9",
            summary="TF-QKD finite-key at 303 km",
            rep_rate_mhz=1060.0,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.79,
            dark_counts_cps=0.05,
            coincidence_window_ps=100.0,
            default_mu=0.152111829893243,
            fit_mu_bounds=(0.02, 0.80),
            fit_phase_slices=(16, 32),
            fit_rep_rate_mhz_bounds=(800.0, 1200.0),
            fit_pde_bounds=(0.70, 0.90),
            fit_dark_counts_cps_bounds=(0.05, 20.0),
            fit_coincidence_window_ps_bounds=(100.0, 1200.0),
        ),
        BenchmarkCase(
            case_id="tf_404km_2.80kbps",
            protocol="tf_qkd",
            distance_km=404.0,
            target_value=2_800.0,
            target_mode="bps",
            source_ref="https://doi.org/10.1007/s44214-023-00039-9",
            summary="TF-QKD finite-key at 404 km",
            rep_rate_mhz=882.5,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.85,
            dark_counts_cps=5.59876510967031,
            coincidence_window_ps=725.0,
            default_mu=0.100614967594448,
            fit_mu_bounds=(0.02, 0.60),
            fit_phase_slices=(16, 32),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.90),
            fit_dark_counts_cps_bounds=(1.0, 20.0),
            fit_coincidence_window_ps_bounds=(200.0, 800.0),
        ),
        BenchmarkCase(
            case_id="tf_505km_338bps",
            protocol="tf_qkd",
            distance_km=505.0,
            target_value=338.0,
            target_mode="bps",
            source_ref="https://doi.org/10.1007/s44214-023-00039-9",
            summary="TF-QKD finite-key at 505 km",
            rep_rate_mhz=917.5,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.85,
            dark_counts_cps=0.5,
            coincidence_window_ps=525.0,
            default_mu=0.060485042906644,
            fit_mu_bounds=(0.02, 0.80),
            fit_phase_slices=(16, 32),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.90),
            fit_dark_counts_cps_bounds=(0.5, 20.0),
            fit_coincidence_window_ps_bounds=(150.0, 900.0),
        ),
        BenchmarkCase(
            case_id="tf_1002km_3.11e-12_bpp",
            protocol="tf_qkd",
            distance_km=1002.0,
            target_value=3.11e-12,
            target_mode="bpp",
            source_ref="https://doi.org/10.1007/s44214-023-00039-9",
            summary="TF-QKD finite-key at 1002 km (per pulse)",
            rep_rate_mhz=850.0,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.80,
            dark_counts_cps=0.10,
            coincidence_window_ps=100.0,
            default_mu=0.017069704018035,
            fit_mu_bounds=(1e-4, 0.30),
            fit_phase_slices=(16, 32, 64, 128),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.95),
            fit_dark_counts_cps_bounds=(0.01, 1.0),
            fit_coincidence_window_ps_bounds=(50.0, 200.0),
        ),
        BenchmarkCase(
            case_id="tf_615.6km_0.32bps",
            protocol="tf_qkd",
            distance_km=615.6,
            target_value=0.32,
            target_mode="bps",
            source_ref="https://doi.org/10.1038/s41467-023-36573-2",
            summary="TF-QKD open channel at 615.6 km (model-effective rep-rate baseline)",
            # Paper reports a 500 MHz effective QKD clock; this PM-model
            # benchmark keeps an effective post-selection-normalized pulse
            # rate to preserve comparability with prior PhotonTrust runs.
            rep_rate_mhz=4.8,
            fiber_loss_db_per_km=0.159,
            connector_loss_db=0.0,
            pde=0.72,
            dark_counts_cps=0.05,
            coincidence_window_ps=100.0,
            default_mu=0.139846576648369,
            fit_mu_bounds=(0.02, 1.20),
            fit_phase_slices=(8, 16, 32, 64),
            fit_rep_rate_mhz_bounds=(1.0, 5.0),
            fit_pde_bounds=(0.70, 0.90),
            fit_dark_counts_cps_bounds=(0.05, 0.5),
            fit_coincidence_window_ps_bounds=(100.0, 400.0),
        ),
        BenchmarkCase(
            case_id="tf_50km_1.27mbps",
            protocol="tf_qkd",
            distance_km=50.0,
            target_value=1_270_000.0,
            target_mode="bps",
            source_ref="https://arxiv.org/abs/2212.04311",
            summary="TF-QKD without phase locking at 50 km",
            rep_rate_mhz=1000.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=0.0,
            pde=0.80,
            dark_counts_cps=1.0,
            coincidence_window_ps=100.0,
            default_mu=0.35,
            fit_mu_bounds=(0.02, 1.20),
            fit_phase_slices=(8, 16, 32),
            fit_rep_rate_mhz_bounds=(200.0, 2500.0),
            fit_pde_bounds=(0.70, 0.95),
            fit_dark_counts_cps_bounds=(0.01, 50.0),
            fit_coincidence_window_ps_bounds=(50.0, 400.0),
        ),
        BenchmarkCase(
            case_id="tf_952km_8.75e-12_bpp",
            protocol="tf_qkd",
            distance_km=952.0,
            target_value=8.75e-12,
            target_mode="bpp",
            source_ref="https://arxiv.org/abs/2303.15795",
            summary="TF-QKD finite-size simulation at 952 km (per pulse)",
            rep_rate_mhz=850.0,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.80,
            dark_counts_cps=0.02,
            coincidence_window_ps=100.0,
            default_mu=0.02,
            fit_mu_bounds=(1e-4, 0.30),
            fit_phase_slices=(16, 32, 64, 128),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.95),
            fit_dark_counts_cps_bounds=(0.005, 1.0),
            fit_coincidence_window_ps_bounds=(50.0, 200.0),
        ),
        BenchmarkCase(
            case_id="tf_1002km_9.53e-12_bpp",
            protocol="tf_qkd",
            distance_km=1002.0,
            target_value=9.53e-12,
            target_mode="bpp",
            source_ref="https://arxiv.org/abs/2303.15795",
            summary="TF-QKD asymptotic simulation at 1002 km (per pulse)",
            rep_rate_mhz=850.0,
            fiber_loss_db_per_km=0.160,
            connector_loss_db=0.0,
            pde=0.80,
            dark_counts_cps=0.02,
            coincidence_window_ps=100.0,
            default_mu=0.02,
            fit_mu_bounds=(1e-4, 0.30),
            fit_phase_slices=(16, 32, 64, 128),
            fit_rep_rate_mhz_bounds=(850.0, 950.0),
            fit_pde_bounds=(0.70, 0.95),
            fit_dark_counts_cps_bounds=(0.005, 1.0),
            fit_coincidence_window_ps_bounds=(50.0, 200.0),
        ),
        BenchmarkCase(
            case_id="mdi_30db_267bps",
            protocol="mdi_qkd",
            distance_km=150.0,
            target_value=267.0,
            target_mode="bps",
            source_ref="https://doi.org/10.1038/s41534-025-01052-7",
            summary="MDI-QKD over 30 dB attenuation",
            rep_rate_mhz=88.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=0.0,
            pde=0.69,
            dark_counts_cps=0.1,
            coincidence_window_ps=265.0,
            default_mu=0.131950791077289,
            default_nu=0.064326010292677,
            default_omega=0.054,
            fit_mu_bounds=(0.05, 0.80),
            fit_nu_ratio_bounds=(0.10, 0.60),
            fit_rep_rate_mhz_bounds=(80.0, 120.0),
            fit_pde_bounds=(0.40, 0.80),
            fit_dark_counts_cps_bounds=(0.1, 100.0),
            fit_coincidence_window_ps_bounds=(200.0, 1500.0),
        ),
        BenchmarkCase(
            case_id="mdi_413km_590.61bps",
            protocol="amdi_qkd",
            distance_km=413.0,
            target_value=590.61,
            target_mode="bps",
            source_ref="https://doi.org/10.1103/PhysRevLett.130.250801",
            summary="Asynchronous-pairing MDI-QKD at 413 km",
            rep_rate_mhz=1000.0,
            fiber_loss_db_per_km=0.180,
            connector_loss_db=0.0,
            pde=0.85,
            dark_counts_cps=0.02,
            coincidence_window_ps=100.0,
            default_mu=0.20,
            default_nu=0.05,
            default_omega=0.0,
            fit_mu_bounds=(0.01, 1.00),
            fit_nu_ratio_bounds=(0.05, 0.70),
            fit_rep_rate_mhz_bounds=(100.0, 5000.0),
            fit_pde_bounds=(0.60, 0.98),
            fit_dark_counts_cps_bounds=(0.001, 20.0),
            fit_coincidence_window_ps_bounds=(20.0, 800.0),
            fit_pairing_window_bins_bounds=(128.0, 65536.0),
            fit_pairing_efficiency_bounds=(0.05, 1.0),
            fit_pairing_error_prob_bounds=(0.0, 0.20),
        ),
        BenchmarkCase(
            case_id="mdi_508km_42.64bps",
            protocol="amdi_qkd",
            distance_km=508.0,
            target_value=42.64,
            target_mode="bps",
            source_ref="https://doi.org/10.1103/PhysRevLett.130.250801",
            summary="Asynchronous-pairing MDI-QKD at 508 km",
            rep_rate_mhz=1000.0,
            fiber_loss_db_per_km=0.180,
            connector_loss_db=0.0,
            pde=0.85,
            dark_counts_cps=0.02,
            coincidence_window_ps=100.0,
            default_mu=0.20,
            default_nu=0.05,
            default_omega=0.0,
            fit_mu_bounds=(0.01, 1.00),
            fit_nu_ratio_bounds=(0.05, 0.70),
            fit_rep_rate_mhz_bounds=(100.0, 5000.0),
            fit_pde_bounds=(0.60, 0.98),
            fit_dark_counts_cps_bounds=(0.001, 20.0),
            fit_coincidence_window_ps_bounds=(20.0, 800.0),
            fit_pairing_window_bins_bounds=(128.0, 65536.0),
            fit_pairing_efficiency_bounds=(0.05, 1.0),
            fit_pairing_error_prob_bounds=(0.0, 0.20),
        ),
        BenchmarkCase(
            case_id="bbm92_200km_440.8bps",
            protocol="bbm92",
            distance_km=200.0,
            target_value=440.80,
            target_mode="bps",
            source_ref="https://doi.org/10.1103/PhysRevLett.134.230801",
            summary="Ultrabright entanglement-based BBM92 over 200 km",
            rep_rate_mhz=500.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=22.0,
            pde=0.80,
            dark_counts_cps=5.0,
            coincidence_window_ps=100.0,
            default_mu=0.05,
            default_sifting_factor=0.5,
            default_misalignment_prob=0.02,
            default_parallel_mode_count=256.0,
            default_entanglement_topology="midpoint_source",
            default_relay_fraction=0.5,
            default_split_connector_loss=True,
            source_type="spdc",
            fit_mu_bounds=(1e-4, 0.50),
            fit_rep_rate_mhz_bounds=(50.0, 2000.0),
            fit_pde_bounds=(0.40, 0.95),
            fit_dark_counts_cps_bounds=(0.01, 200.0),
            fit_coincidence_window_ps_bounds=(20.0, 800.0),
            fit_misalignment_prob_bounds=(0.001, 0.10),
            fit_collection_efficiency_bounds=(0.01, 1.0),
            fit_parallel_mode_count_bounds=(16.0, 512.0),
        ),
        BenchmarkCase(
            case_id="bbm92_26km_4.5bps",
            protocol="bbm92",
            distance_km=26.0,
            target_value=4.5,
            target_mode="bps",
            source_ref="https://doi.org/10.1038/s41534-025-00991-5",
            summary="Frequency-bin BBM92 over 26 km (>=4.5 bps)",
            rep_rate_mhz=100.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=0.0,
            pde=0.20,
            dark_counts_cps=20.0,
            coincidence_window_ps=200.0,
            default_mu=0.01,
            default_sifting_factor=0.5,
            default_misalignment_prob=0.03,
            source_type="spdc",
            fit_mu_bounds=(1e-5, 0.20),
            fit_rep_rate_mhz_bounds=(1.0, 500.0),
            fit_pde_bounds=(0.05, 0.80),
            fit_dark_counts_cps_bounds=(0.01, 500.0),
            fit_coincidence_window_ps_bounds=(20.0, 2000.0),
            fit_misalignment_prob_bounds=(0.001, 0.20),
            fit_collection_efficiency_bounds=(1e-4, 1.0),
        ),
        BenchmarkCase(
            case_id="bbm92_40km_245bps",
            protocol="bbm92",
            distance_km=40.0,
            target_value=245.0,
            target_mode="bps",
            source_ref="https://arxiv.org/abs/2305.18696",
            summary="Energy-time BBM92 coexistence over 40 km",
            rep_rate_mhz=100.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=0.0,
            pde=0.50,
            dark_counts_cps=5.0,
            coincidence_window_ps=200.0,
            default_mu=0.02,
            default_sifting_factor=0.5,
            default_misalignment_prob=0.04,
            source_type="spdc",
            fit_mu_bounds=(1e-5, 0.30),
            fit_rep_rate_mhz_bounds=(1.0, 1000.0),
            fit_pde_bounds=(0.10, 0.95),
            fit_dark_counts_cps_bounds=(0.01, 200.0),
            fit_coincidence_window_ps_bounds=(20.0, 1000.0),
            fit_misalignment_prob_bounds=(0.001, 0.20),
            fit_collection_efficiency_bounds=(1e-4, 1.0),
        ),
        BenchmarkCase(
            case_id="bb84_14.6db_1.08e-3_bpp",
            protocol="bb84_decoy",
            distance_km=73.0,
            target_value=1.08e-3,
            target_mode="bpp",
            source_ref="https://arxiv.org/abs/2406.02045",
            summary="Single-photon QKD at 14.6 dB (per pulse)",
            rep_rate_mhz=100.0,
            fiber_loss_db_per_km=0.200,
            connector_loss_db=0.0,
            pde=0.71,
            dark_counts_cps=1.0,
            coincidence_window_ps=200.0,
            default_mu=0.20546962412685682,
            default_misalignment_prob=0.03,
            fit_mu_bounds=(0.005, 0.60),
            fit_nu_ratio_bounds=(0.05, 0.50),
            fit_collection_efficiency_bounds=(0.20, 1.0),
            fit_pde_bounds=(0.50, 0.90),
            fit_dark_counts_cps_bounds=(0.1, 10.0),
            fit_coincidence_window_ps_bounds=(100.0, 500.0),
            fit_misalignment_prob_bounds=(0.01, 0.08),
        ),
        BenchmarkCase(
            case_id="bb84_33km_7.58e-7_bpp",
            protocol="bb84_decoy",
            distance_km=33.0,
            target_value=7.58e-7,
            target_mode="bpp",
            source_ref="https://arxiv.org/abs/2409.18502",
            summary="GaN time-bin QKD at 33 km spool (per pulse)",
            rep_rate_mhz=100.0,
            fiber_loss_db_per_km=0.339,
            connector_loss_db=0.0,
            pde=0.20,
            dark_counts_cps=100.0,
            coincidence_window_ps=500.0,
            default_mu=0.5047271017361658,
            default_nu=0.06664987083968684,
            default_misalignment_prob=0.05,
            collection_efficiency=0.003,
            fit_mu_bounds=(1e-4, 0.80),
            fit_nu_ratio_bounds=(0.05, 0.50),
            fit_collection_efficiency_bounds=(3e-4, 0.03),
            fit_pde_bounds=(0.10, 0.40),
            fit_dark_counts_cps_bounds=(10.0, 500.0),
            fit_coincidence_window_ps_bounds=(200.0, 1000.0),
            fit_misalignment_prob_bounds=(0.01, 0.10),
        ),
        BenchmarkCase(
            case_id="bb84_30km_6.06e-8_bpp",
            protocol="bb84_decoy",
            distance_km=30.0,
            target_value=6.06e-8,
            target_mode="bpp",
            source_ref="https://arxiv.org/abs/2409.18502",
            summary="GaN time-bin QKD at 30 km deployed line (per pulse)",
            rep_rate_mhz=100.0,
            fiber_loss_db_per_km=0.333,
            connector_loss_db=0.0,
            pde=0.1505,
            dark_counts_cps=759.7435261681776,
            coincidence_window_ps=420.0,
            default_mu=0.067567871877295,
            default_nu=0.014780472598158,
            default_misalignment_prob=0.0375,
            collection_efficiency=0.003563754284892,
            fit_mu_bounds=(1e-4, 0.80),
            fit_nu_ratio_bounds=(0.05, 0.50),
            fit_collection_efficiency_bounds=(1e-4, 0.05),
            fit_pde_bounds=(0.02, 0.20),
            fit_dark_counts_cps_bounds=(50.0, 1500.0),
            fit_coincidence_window_ps_bounds=(300.0, 1500.0),
            fit_misalignment_prob_bounds=(0.01, 0.12),
        ),
    ]


def _baseline_params(case: BenchmarkCase) -> dict[str, float]:
    nu_ratio = 0.2
    if case.default_mu > 0:
        nu_ratio = max(1e-6, min(0.95, float(case.default_nu) / float(case.default_mu)))

    return {
        "mu": float(case.default_mu),
        "nu_ratio": float(nu_ratio),
        "phase_slices": float(case.default_phase_slices),
        "rep_rate_mhz": float(case.rep_rate_mhz),
        "parallel_mode_count": float(case.default_parallel_mode_count),
        "relay_fraction": float(case.default_relay_fraction),
        "collection_efficiency": float(case.collection_efficiency),
        "coupling_efficiency": float(case.coupling_efficiency),
        "pde": float(case.pde),
        "dark_counts_cps": float(case.dark_counts_cps),
        "coincidence_window_ps": float(case.coincidence_window_ps),
        "misalignment_prob": float(case.default_misalignment_prob),
        "pairing_window_bins": float(case.default_pairing_window_bins),
        "pairing_efficiency": float(case.default_pairing_efficiency),
        "pairing_error_prob": float(case.default_pairing_error_prob),
    }


def _scenario_from_case(case: BenchmarkCase, params: dict[str, float]) -> dict:
    protocol = {
        "name": case.protocol,
        "ec_efficiency": float(case.default_ec_efficiency),
        "sifting_factor": float(case.default_sifting_factor),
    }

    mu = float(params["mu"])
    nu_ratio = max(1e-6, min(0.95, float(params.get("nu_ratio", 0.2))))

    if case.protocol in {"tf_qkd", "pm_qkd"}:
        protocol["mu"] = mu
        protocol["phase_slices"] = int(round(float(params["phase_slices"])))
    elif case.protocol in {"mdi_qkd", "amdi_qkd"}:
        nu = max(1e-6, min(0.95 * mu, nu_ratio * mu))
        protocol["mu"] = mu
        protocol["nu"] = nu
        protocol["omega"] = float(case.default_omega)
        if case.protocol == "amdi_qkd":
            protocol["pairing_window_bins"] = int(round(float(params["pairing_window_bins"])))
            protocol["pairing_efficiency"] = float(params["pairing_efficiency"])
            protocol["pairing_error_prob"] = float(params["pairing_error_prob"])
    elif case.protocol == "bb84_decoy":
        nu = max(1e-6, min(0.90 * mu, nu_ratio * mu))
        protocol["mu"] = mu
        protocol["nu"] = nu
        protocol["omega"] = 0.0
        protocol["misalignment_prob"] = float(params["misalignment_prob"])
        protocol["sifting_factor"] = 0.5
    elif case.protocol == "bbm92":
        protocol["misalignment_prob"] = float(params["misalignment_prob"])
        protocol["sifting_factor"] = float(case.default_sifting_factor)
        protocol["entanglement_topology"] = str(case.default_entanglement_topology)
        protocol["relay_fraction"] = float(params["relay_fraction"])
        protocol["split_connector_loss"] = bool(case.default_split_connector_loss)
    else:
        raise ValueError(f"unsupported protocol in benchmark case: {case.protocol}")

    source_payload = {
        "type": case.source_type,
        "rep_rate_mhz": float(params["rep_rate_mhz"]),
        "parallel_mode_count": float(params["parallel_mode_count"]),
        "collection_efficiency": float(params["collection_efficiency"]),
        "coupling_efficiency": float(params["coupling_efficiency"]),
    }
    if case.protocol == "bbm92":
        source_payload["mu"] = float(mu)

    return {
        "source": source_payload,
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": float(case.fiber_loss_db_per_km),
            "connector_loss_db": float(case.connector_loss_db),
            "background_counts_cps": 0.0,
            "raman_model": "off",
            "dispersion_ps_per_km": 0.0,
        },
        "detector": {
            "class": case.detector_class,
            "pde": float(params["pde"]),
            "dark_counts_cps": float(params["dark_counts_cps"]),
            "jitter_ps_fwhm": float(case.jitter_ps_fwhm),
            "dead_time_ns": float(case.dead_time_ns),
            "afterpulsing_prob": float(case.afterpulsing_prob),
        },
        "timing": {
            "sync_drift_ps_rms": float(case.sync_drift_ps_rms),
            "coincidence_window_ps": float(params["coincidence_window_ps"]),
        },
        "protocol": protocol,
    }


def _to_metric(case: BenchmarkCase, *, key_rate_bps: float, rep_rate_mhz: float) -> float:
    if case.target_mode == "bps":
        return float(key_rate_bps)
    rep_hz = float(rep_rate_mhz) * 1e6
    return float(key_rate_bps) / max(rep_hz, 1e-30)


def _relative_error(model_value: float, target_value: float) -> float:
    return abs(float(model_value) - float(target_value)) / max(abs(float(target_value)), 1e-30)


def _log_grid(low: float, high: float, count: int) -> tuple[float, ...]:
    low = float(low)
    high = float(high)
    if count <= 1 or not math.isfinite(low) or not math.isfinite(high):
        return (low,)
    if low <= 0.0 or high <= 0.0:
        return _lin_grid(low, high, count)
    if low == high:
        return (low,)

    lo = math.log10(min(low, high))
    hi = math.log10(max(low, high))
    out = [10 ** (lo + (hi - lo) * idx / (count - 1)) for idx in range(count)]
    return _dedupe_float_grid(out)


def _lin_grid(low: float, high: float, count: int) -> tuple[float, ...]:
    low = float(low)
    high = float(high)
    if count <= 1 or low == high:
        return (low,)
    lo = min(low, high)
    hi = max(low, high)
    out = [lo + (hi - lo) * idx / (count - 1) for idx in range(count)]
    return _dedupe_float_grid(out)


def _dedupe_float_grid(values: list[float]) -> tuple[float, ...]:
    uniq = sorted({round(float(v), 15) for v in values})
    return tuple(float(v) for v in uniq)


def _grid_with_baseline(values: tuple[float, ...], baseline: float) -> tuple[float, ...]:
    return _dedupe_float_grid(list(values) + [float(baseline)])


def _parameter_specs(case: BenchmarkCase, *, baseline_params: dict[str, float], grid_size: int) -> list[ParameterSpec]:
    specs: list[ParameterSpec] = []
    g = max(5, int(grid_size))

    specs.append(
        ParameterSpec(
            name="mu",
            values=_grid_with_baseline(
                _log_grid(case.fit_mu_bounds[0], case.fit_mu_bounds[1], g),
                baseline_params["mu"],
            ),
        )
    )

    if case.protocol in {"tf_qkd", "pm_qkd"} and len(case.fit_phase_slices) > 1:
        vals = sorted({int(v) for v in case.fit_phase_slices} | {int(round(baseline_params["phase_slices"]))})
        specs.append(ParameterSpec(name="phase_slices", values=tuple(float(v) for v in vals), is_discrete_int=True))

    if case.fit_rep_rate_mhz_bounds is not None:
        specs.append(
            ParameterSpec(
                name="rep_rate_mhz",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_rep_rate_mhz_bounds[0], case.fit_rep_rate_mhz_bounds[1], g),
                    baseline_params["rep_rate_mhz"],
                ),
            )
        )

    if case.fit_collection_efficiency_bounds is not None:
        specs.append(
            ParameterSpec(
                name="collection_efficiency",
                values=_grid_with_baseline(
                    _log_grid(case.fit_collection_efficiency_bounds[0], case.fit_collection_efficiency_bounds[1], g),
                    baseline_params["collection_efficiency"],
                ),
            )
        )

    if case.fit_coupling_efficiency_bounds is not None:
        specs.append(
            ParameterSpec(
                name="coupling_efficiency",
                values=_grid_with_baseline(
                    _log_grid(case.fit_coupling_efficiency_bounds[0], case.fit_coupling_efficiency_bounds[1], g),
                    baseline_params["coupling_efficiency"],
                ),
            )
        )

    if case.fit_pde_bounds is not None:
        specs.append(
            ParameterSpec(
                name="pde",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_pde_bounds[0], case.fit_pde_bounds[1], g),
                    baseline_params["pde"],
                ),
            )
        )

    if case.fit_dark_counts_cps_bounds is not None:
        specs.append(
            ParameterSpec(
                name="dark_counts_cps",
                values=_grid_with_baseline(
                    _log_grid(case.fit_dark_counts_cps_bounds[0], case.fit_dark_counts_cps_bounds[1], g),
                    baseline_params["dark_counts_cps"],
                ),
            )
        )

    if case.fit_coincidence_window_ps_bounds is not None:
        specs.append(
            ParameterSpec(
                name="coincidence_window_ps",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_coincidence_window_ps_bounds[0], case.fit_coincidence_window_ps_bounds[1], g),
                    baseline_params["coincidence_window_ps"],
                ),
            )
        )

    if case.fit_parallel_mode_count_bounds is not None and case.protocol == "bbm92":
        specs.append(
            ParameterSpec(
                name="parallel_mode_count",
                values=_grid_with_baseline(
                    _log_grid(case.fit_parallel_mode_count_bounds[0], case.fit_parallel_mode_count_bounds[1], g),
                    baseline_params["parallel_mode_count"],
                ),
            )
        )

    if case.fit_misalignment_prob_bounds is not None and case.protocol in {"bb84_decoy", "bbm92"}:
        specs.append(
            ParameterSpec(
                name="misalignment_prob",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_misalignment_prob_bounds[0], case.fit_misalignment_prob_bounds[1], g),
                    baseline_params["misalignment_prob"],
                ),
            )
        )

    if case.fit_nu_ratio_bounds is not None and case.protocol in {"mdi_qkd", "amdi_qkd", "bb84_decoy"}:
        specs.append(
            ParameterSpec(
                name="nu_ratio",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_nu_ratio_bounds[0], case.fit_nu_ratio_bounds[1], g),
                    baseline_params["nu_ratio"],
                ),
            )
        )

    if case.fit_pairing_window_bins_bounds is not None and case.protocol == "amdi_qkd":
        specs.append(
            ParameterSpec(
                name="pairing_window_bins",
                values=_grid_with_baseline(
                    _log_grid(case.fit_pairing_window_bins_bounds[0], case.fit_pairing_window_bins_bounds[1], g),
                    baseline_params["pairing_window_bins"],
                ),
                is_discrete_int=True,
            )
        )

    if case.fit_pairing_efficiency_bounds is not None and case.protocol == "amdi_qkd":
        specs.append(
            ParameterSpec(
                name="pairing_efficiency",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_pairing_efficiency_bounds[0], case.fit_pairing_efficiency_bounds[1], g),
                    baseline_params["pairing_efficiency"],
                ),
            )
        )

    if case.fit_pairing_error_prob_bounds is not None and case.protocol == "amdi_qkd":
        specs.append(
            ParameterSpec(
                name="pairing_error_prob",
                values=_grid_with_baseline(
                    _lin_grid(case.fit_pairing_error_prob_bounds[0], case.fit_pairing_error_prob_bounds[1], g),
                    baseline_params["pairing_error_prob"],
                ),
            )
        )

    return specs


def _evaluate_params(case: BenchmarkCase, params: dict[str, float]) -> dict | None:
    try:
        result = compute_point(_scenario_from_case(case, params), case.distance_km)
    except Exception:
        return None

    metric = _to_metric(case, key_rate_bps=result.key_rate_bps, rep_rate_mhz=float(params["rep_rate_mhz"]))
    rel_err = _relative_error(metric, case.target_value)
    return {
        "metric": float(metric),
        "relative_error": float(rel_err),
        "key_rate_bps": float(result.key_rate_bps),
        "qber_total": float(result.qber_total),
        "loss_db": float(result.loss_db),
    }


def _fit_mu_only(case: BenchmarkCase, baseline_params: dict[str, float], grid_size: int) -> tuple[dict, dict[str, float]]:
    params = dict(baseline_params)
    best_eval = _evaluate_params(case, params)
    if best_eval is None:
        raise ValueError(f"baseline evaluation failed for case {case.case_id}")

    best_params = dict(params)
    mu_candidates = _grid_with_baseline(
        _log_grid(case.fit_mu_bounds[0], case.fit_mu_bounds[1], max(20, int(grid_size) * 2)),
        baseline_params["mu"],
    )
    for mu in mu_candidates:
        trial_params = dict(params)
        trial_params["mu"] = float(mu)
        trial_eval = _evaluate_params(case, trial_params)
        if trial_eval is None:
            continue
        if trial_eval["relative_error"] < best_eval["relative_error"]:
            best_eval = trial_eval
            best_params = trial_params

    return best_eval, best_params


def _fit_multi_parameter(
    case: BenchmarkCase,
    baseline_params: dict[str, float],
    *,
    grid_size: int,
    fit_passes: int,
) -> tuple[dict, dict[str, float]]:
    specs = _parameter_specs(case, baseline_params=baseline_params, grid_size=grid_size)

    params = dict(baseline_params)
    best_eval = _evaluate_params(case, params)
    if best_eval is None:
        raise ValueError(f"baseline evaluation failed for case {case.case_id}")

    if not specs:
        return best_eval, params

    # Warm start: random bounded samples to escape local zero-key plateaus.
    seed = sum(ord(ch) for ch in case.case_id) + 7919
    rng = random.Random(seed)
    random_trials = max(200, min(1200, int(grid_size) * 25))
    for _ in range(random_trials):
        trial_params = dict(baseline_params)
        for spec in specs:
            choice = rng.choice(spec.values)
            trial_params[spec.name] = float(int(round(choice))) if spec.is_discrete_int else float(choice)
        trial_eval = _evaluate_params(case, trial_params)
        if trial_eval is None:
            continue
        if trial_eval["relative_error"] < best_eval["relative_error"]:
            best_eval = trial_eval
            params = trial_params

    for _ in range(max(1, int(fit_passes))):
        improved = False
        for spec in specs:
            local_best_eval = best_eval
            local_best_val = params[spec.name]
            for raw_value in spec.values:
                value = float(int(round(raw_value))) if spec.is_discrete_int else float(raw_value)
                if spec.is_discrete_int and int(round(params[spec.name])) == int(round(value)):
                    continue
                if (not spec.is_discrete_int) and math.isclose(float(params[spec.name]), float(value), rel_tol=0.0, abs_tol=1e-15):
                    continue

                trial_params = dict(params)
                trial_params[spec.name] = value
                trial_eval = _evaluate_params(case, trial_params)
                if trial_eval is None:
                    continue
                if trial_eval["relative_error"] < local_best_eval["relative_error"]:
                    local_best_eval = trial_eval
                    local_best_val = value

            changed = int(round(params[spec.name])) != int(round(local_best_val)) if spec.is_discrete_int else (
                not math.isclose(float(params[spec.name]), float(local_best_val), rel_tol=0.0, abs_tol=1e-15)
            )
            if changed:
                params[spec.name] = local_best_val
                best_eval = local_best_eval
                improved = True

        if not improved:
            break

    return best_eval, params


def _changed_params(
    baseline_params: dict[str, float],
    fitted_params: dict[str, float],
) -> dict[str, float | int]:
    changed: dict[str, float | int] = {}
    for key in sorted(fitted_params.keys()):
        base_v = float(baseline_params[key])
        fit_v = float(fitted_params[key])
        if key in {"phase_slices", "pairing_window_bins"}:
            if int(round(base_v)) != int(round(fit_v)):
                changed[key] = int(round(fit_v))
            continue
        if not math.isclose(base_v, fit_v, rel_tol=0.0, abs_tol=1e-12):
            changed[key] = float(fit_v)
    return changed


def _pack_result(eval_payload: dict, params: dict[str, float], *, changed: dict[str, float | int] | None = None) -> dict:
    packed = {
        "metric": float(eval_payload["metric"]),
        "relative_error": float(eval_payload["relative_error"]),
        "key_rate_bps": float(eval_payload["key_rate_bps"]),
        "qber_total": float(eval_payload["qber_total"]),
        "loss_db": float(eval_payload["loss_db"]),
        "params": {
            "mu": float(params["mu"]),
            "nu_ratio": float(params["nu_ratio"]),
            "phase_slices": int(round(params["phase_slices"])),
            "rep_rate_mhz": float(params["rep_rate_mhz"]),
            "parallel_mode_count": float(params["parallel_mode_count"]),
            "relay_fraction": float(params["relay_fraction"]),
            "collection_efficiency": float(params["collection_efficiency"]),
            "coupling_efficiency": float(params["coupling_efficiency"]),
            "pde": float(params["pde"]),
            "dark_counts_cps": float(params["dark_counts_cps"]),
            "coincidence_window_ps": float(params["coincidence_window_ps"]),
            "misalignment_prob": float(params["misalignment_prob"]),
            "pairing_window_bins": int(round(params["pairing_window_bins"])),
            "pairing_efficiency": float(params["pairing_efficiency"]),
            "pairing_error_prob": float(params["pairing_error_prob"]),
        },
    }
    if changed is not None:
        packed["tuned_params"] = changed
    return packed


def _fit_bounds_for_case(case: BenchmarkCase) -> dict:
    return {
        "mu_bounds": case.fit_mu_bounds,
        "phase_slices": list(case.fit_phase_slices),
        "collection_efficiency_bounds": case.fit_collection_efficiency_bounds,
        "coupling_efficiency_bounds": case.fit_coupling_efficiency_bounds,
        "rep_rate_mhz_bounds": case.fit_rep_rate_mhz_bounds,
        "pde_bounds": case.fit_pde_bounds,
        "dark_counts_cps_bounds": case.fit_dark_counts_cps_bounds,
        "coincidence_window_ps_bounds": case.fit_coincidence_window_ps_bounds,
        "misalignment_prob_bounds": case.fit_misalignment_prob_bounds,
        "nu_ratio_bounds": case.fit_nu_ratio_bounds,
        "pairing_window_bins_bounds": case.fit_pairing_window_bins_bounds,
        "pairing_efficiency_bounds": case.fit_pairing_efficiency_bounds,
        "pairing_error_prob_bounds": case.fit_pairing_error_prob_bounds,
        "parallel_mode_count_bounds": case.fit_parallel_mode_count_bounds,
    }


def _evaluate_case(case: BenchmarkCase, *, grid_size: int, fit_passes: int) -> dict:
    baseline_params = _baseline_params(case)
    baseline_eval = _evaluate_params(case, baseline_params)
    if baseline_eval is None:
        raise ValueError(f"failed baseline evaluation for case {case.case_id}")

    mu_eval, mu_params = _fit_mu_only(case, baseline_params, grid_size=grid_size)
    best_eval, best_params = _fit_multi_parameter(
        case,
        mu_params,
        grid_size=grid_size,
        fit_passes=fit_passes,
    )

    return {
        "case_id": case.case_id,
        "protocol": case.protocol,
        "summary": case.summary,
        "source_ref": case.source_ref,
        "target": {
            "value": float(case.target_value),
            "mode": case.target_mode,
            "distance_km": float(case.distance_km),
        },
        "fit_bounds": _fit_bounds_for_case(case),
        "paper_locked": _pack_result(baseline_eval, baseline_params, changed={}),
        "baseline": _pack_result(baseline_eval, baseline_params, changed={}),
        "best_mu_fit": _pack_result(
            mu_eval,
            mu_params,
            changed=_changed_params(baseline_params, mu_params),
        ),
        "best_fit": _pack_result(
            best_eval,
            best_params,
            changed=_changed_params(baseline_params, best_params),
        ),
    }


def _build_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# Recent Research Benchmark Comparison")
    lines.append("")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Cases: {len(report['cases'])}")
    lines.append("- Modes: `paper_locked`, `best_mu_fit`, `best_fit`")
    lines.append(
        f"- Median paper-locked relative error: {report['summary']['median_paper_locked_relative_error']:.6g}"
    )
    lines.append(
        f"- Median best-fit relative error: {report['summary']['median_best_fit_relative_error']:.6g}"
    )
    lines.append(
        f"- Cases <= 1% error (paper-locked): {report['summary']['cases_within_1pct_paper_locked']}/{len(report['cases'])}"
    )
    lines.append(
        f"- Cases <= 1% error (best-fit): {report['summary']['cases_within_1pct_best_fit']}/{len(report['cases'])}"
    )
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Case | Paper-Locked Err | Mu-Only Err | Best-Fit Err |")
    lines.append("|---|---:|---:|---:|")
    for case in report["cases"]:
        lines.append(
            "| {case_id} | {paper:.6g} | {mu:.6g} | {best:.6g} |".format(
                case_id=case["case_id"],
                paper=float(case["paper_locked"]["relative_error"]),
                mu=float(case["best_mu_fit"]["relative_error"]),
                best=float(case["best_fit"]["relative_error"]),
            )
        )
    lines.append("")
    lines.append("## Cases")
    lines.append("")

    for case in report["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append(f"- Protocol: `{case['protocol']}`")
        lines.append(f"- Benchmark: {case['summary']}")
        lines.append(f"- Source: {case['source_ref']}")
        lines.append(
            f"- Target: {case['target']['value']:.12g} ({case['target']['mode']}) at {case['target']['distance_km']:.6g} km"
        )
        lines.append(
            f"- Paper-locked: {case['paper_locked']['metric']:.12g}, rel_err={case['paper_locked']['relative_error']:.6g}, "
            f"mu={case['paper_locked']['params']['mu']:.6g}, qber={case['paper_locked']['qber_total']:.6g}"
        )
        lines.append(
            f"- Mu-only fit: {case['best_mu_fit']['metric']:.12g}, rel_err={case['best_mu_fit']['relative_error']:.6g}, "
            f"mu={case['best_mu_fit']['params']['mu']:.6g}, qber={case['best_mu_fit']['qber_total']:.6g}"
        )
        lines.append(
            f"- Best fit: {case['best_fit']['metric']:.12g}, rel_err={case['best_fit']['relative_error']:.6g}, "
            f"mu={case['best_fit']['params']['mu']:.6g}, qber={case['best_fit']['qber_total']:.6g}"
        )
        tuned = case["best_fit"].get("tuned_params", {})
        if tuned:
            tuned_str = ", ".join(f"{k}={v}" for k, v in tuned.items())
            lines.append(f"- Tuned params: {tuned_str}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run_comparison(*, grid_size: int, fit_passes: int) -> dict:
    cases = _benchmark_cases()
    evaluations = [_evaluate_case(case, grid_size=grid_size, fit_passes=fit_passes) for case in cases]

    paper_locked_errors = [float(item["paper_locked"]["relative_error"]) for item in evaluations]
    best_fit_errors = [float(item["best_fit"]["relative_error"]) for item in evaluations]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "photonstrust.research_benchmark_comparison",
        "cases": evaluations,
        "summary": {
            "median_paper_locked_relative_error": float(statistics.median(paper_locked_errors)),
            "median_best_fit_relative_error": float(statistics.median(best_fit_errors)),
            "mean_paper_locked_relative_error": float(statistics.fmean(paper_locked_errors)),
            "mean_best_fit_relative_error": float(statistics.fmean(best_fit_errors)),
            "cases_within_1pct_paper_locked": int(sum(err <= 0.01 for err in paper_locked_errors)),
            "cases_within_1pct_best_fit": int(sum(err <= 0.01 for err in best_fit_errors)),
            "median_baseline_relative_error": float(statistics.median(paper_locked_errors)),
            "median_best_fit_relative_error_legacy_alias": float(statistics.median(best_fit_errors)),
            "mean_baseline_relative_error": float(statistics.fmean(paper_locked_errors)),
            "mean_best_fit_relative_error_legacy_alias": float(statistics.fmean(best_fit_errors)),
        },
        "settings": {
            "grid_size": int(grid_size),
            "fit_passes": int(fit_passes),
            "notes": "best_fit uses bounded coordinate search over per-case parameter ranges",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare PhotonTrust against recent research benchmark points.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/research_validation/recent_research_benchmark_comparison.json"),
        help="Path to write machine-readable comparison report.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("results/research_validation/recent_research_benchmark_comparison.md"),
        help="Path to write markdown summary report.",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=41,
        help="Grid resolution per fitted parameter (>=5).",
    )
    parser.add_argument(
        "--fit-passes",
        type=int,
        default=4,
        help="Coordinate-descent passes for bounded multi-parameter fitting.",
    )
    args = parser.parse_args()

    report = run_comparison(grid_size=max(5, args.grid_size), fit_passes=max(1, args.fit_passes))
    md = _build_markdown(report)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")

    print(f"Recent benchmark comparison JSON: {args.output_json}")
    print(f"Recent benchmark comparison Markdown: {args.output_md}")
    print(
        "Median paper-locked rel error:",
        f"{report['summary']['median_paper_locked_relative_error']:.6g}",
    )
    print(
        "Median best-fit rel error:",
        f"{report['summary']['median_best_fit_relative_error']:.6g}",
    )
    print(
        "Cases <=1% (best-fit):",
        f"{report['summary']['cases_within_1pct_best_fit']}/{len(report['cases'])}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
