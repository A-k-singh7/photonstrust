"""Benchmark ingestion, checking, and reproducibility pack tooling."""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy imports to avoid forcing jax at package load time."""
    _LAZY = {
        "ingest_bundle_file": "photonstrust.benchmarks.ingest",
        "check_open_benchmarks": "photonstrust.benchmarks.open_benchmarks",
        "generate_repro_pack": "photonstrust.benchmarks.repro_pack",
        "run_research_validation_suite": "photonstrust.benchmarks.research_validation",
        "run_validation_harness": "photonstrust.benchmarks.validation_harness",
        "run_metro_fiber_bb84": "photonstrust.benchmarks.phase_a_scenarios",
        "run_satellite_downlink_bbm92": "photonstrust.benchmarks.phase_a_scenarios",
        "run_pic_ring_resonator": "photonstrust.benchmarks.phase_a_scenarios",
        "run_all_benchmarks": "photonstrust.benchmarks.phase_a_scenarios",
        "BenchmarkResult": "photonstrust.benchmarks.phase_a_scenarios",
    }
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BenchmarkResult",
    "check_open_benchmarks",
    "generate_repro_pack",
    "ingest_bundle_file",
    "run_all_benchmarks",
    "run_metro_fiber_bb84",
    "run_pic_ring_resonator",
    "run_research_validation_suite",
    "run_satellite_downlink_bbm92",
    "run_validation_harness",
]
