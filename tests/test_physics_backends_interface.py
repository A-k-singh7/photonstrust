from __future__ import annotations

import pytest

from photonstrust.physics.backends import available_backends, resolve_backend
from photonstrust.physics.backends.analytic import AnalyticBackend
from photonstrust.physics.backends.qiskit_backend import QiskitBackend
from photonstrust.physics.backends.qutip_backend import QutipBackend
from photonstrust.physics.backends.stochastic import StochasticBackend
from photonstrust.physics.detector import simulate_detector
from photonstrust.physics.emitter import get_emitter_stats
from photonstrust.physics.memory import simulate_memory


def test_available_backends_contains_expected_scaffolding() -> None:
    assert available_backends() == ("analytic", "qiskit", "qutip", "stochastic")


def test_resolve_backend_returns_expected_instances() -> None:
    assert isinstance(resolve_backend("analytic"), AnalyticBackend)
    assert isinstance(resolve_backend("qiskit"), QiskitBackend)
    assert isinstance(resolve_backend("qutip"), QutipBackend)
    assert isinstance(resolve_backend("stochastic"), StochasticBackend)


def test_resolve_backend_unknown_falls_back_to_analytic() -> None:
    with pytest.warns(UserWarning, match="Unsupported physics backend"):
        backend = resolve_backend("unsupported_backend")
    assert isinstance(backend, AnalyticBackend)


def test_analytic_backend_emitter_matches_public_api() -> None:
    source = {
        "type": "emitter_cavity",
        "physics_backend": "analytic",
        "seed": 123,
        "radiative_lifetime_ns": 1.0,
        "purcell_factor": 5.0,
        "dephasing_rate_per_ns": 0.5,
        "drive_strength": 0.05,
        "pulse_window_ns": 5.0,
        "g2_0": 0.02,
    }
    expected = get_emitter_stats(source)

    backend = resolve_backend("analytic")
    observed = backend.simulate("emitter", source, seed=123)

    assert observed == expected


def test_analytic_backend_memory_matches_public_api() -> None:
    memory_cfg = {
        "t1_ms": 50.0,
        "t2_ms": 10.0,
        "store_efficiency": 0.95,
        "retrieval_efficiency": 0.8,
        "physics_backend": "analytic",
    }
    wait_time_ns = 1e7
    expected = simulate_memory(memory_cfg, wait_time_ns=wait_time_ns)

    backend = resolve_backend("analytic")
    observed = backend.simulate(
        "memory",
        {"memory_cfg": memory_cfg, "wait_time_ns": wait_time_ns},
    )

    assert observed == expected


def test_stochastic_backend_detector_matches_public_api_for_fixed_seed() -> None:
    detector_cfg = {
        "pde": 0.55,
        "dark_counts_cps": 200.0,
        "jitter_ps_fwhm": 30.0,
        "dead_time_ns": 10.0,
        "afterpulsing_prob": 0.01,
        "afterpulse_delay_ns": 50.0,
        "time_bin_ps": 10.0,
        "seed": 1234,
    }
    arrivals = [float(v) for v in range(0, 2500, 25)]
    expected = simulate_detector(detector_cfg, arrivals)

    backend = resolve_backend("stochastic")
    observed = backend.simulate(
        "detector",
        {"detector_cfg": detector_cfg, "arrival_times_ps": arrivals},
        seed=1234,
    )

    assert observed == expected


def test_backend_applicability_and_provenance_payload_shapes() -> None:
    analytic = resolve_backend("analytic")
    stochastic = resolve_backend("stochastic")

    app_ok = analytic.applicability("emitter", {})
    app_fail = stochastic.applicability("memory", {})

    assert app_ok.as_dict() == {"status": "pass", "reasons": []}
    assert app_fail.as_dict()["status"] == "fail"
    assert app_fail.as_dict()["reasons"]

    provenance = stochastic.provenance(seed=77).as_dict()
    assert provenance["backend_name"] == "stochastic"
    assert provenance["backend_version"] == "0.1"
    assert provenance["seed"] == 77
