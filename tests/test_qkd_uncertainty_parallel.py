from __future__ import annotations

from copy import deepcopy

from photonstrust.qkd import compute_sweep


def _scenario(workers: int) -> dict:
    return {
        "scenario_id": "uq_parallel_deterministic",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [10.0, 20.0],
        "execution_mode": "preview",
        "preview_uncertainty_samples": 12,
        "uncertainty_workers": workers,
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
            "dispersion_ps_per_km": 5.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 100.0,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10.0, "coincidence_window_ps": 200.0},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {
            "seed": 123,
            "fiber_loss_db_per_km": 0.02,
            "pde": 0.05,
            "dark_counts": 0.5,
            "jitter": 0.1,
            "g2_0": 0.2,
        },
    }


def test_uncertainty_parallel_matches_serial_for_same_seed() -> None:
    serial = compute_sweep(_scenario(workers=1), include_uncertainty=True)
    parallel = compute_sweep(_scenario(workers=2), include_uncertainty=True)

    assert serial["performance"]["uncertainty_workers"] == 1
    assert parallel["performance"]["uncertainty_workers"] == 2
    assert serial["uncertainty"] == parallel["uncertainty"]


def test_uncertainty_worker_count_invariance() -> None:
    base = _scenario(workers=1)
    sweep_1 = compute_sweep(deepcopy(base), include_uncertainty=True)

    base["uncertainty_workers"] = 2
    sweep_2 = compute_sweep(base, include_uncertainty=True)

    assert sweep_1["uncertainty"] == sweep_2["uncertainty"]


def test_uncertainty_parallel_reproducible_across_runs() -> None:
    scenario = _scenario(workers=2)
    first = compute_sweep(deepcopy(scenario), include_uncertainty=True)
    second = compute_sweep(deepcopy(scenario), include_uncertainty=True)

    assert first["uncertainty"] == second["uncertainty"]
