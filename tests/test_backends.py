"""Tests for the multi-fidelity backend framework."""

from __future__ import annotations

import pytest

from photonstrust.backends.analytic import AnalyticBackend
from photonstrust.backends.comparison import (
    build_multifidelity_evidence,
    run_cross_fidelity_comparison,
)
from photonstrust.backends.registry import (
    _REGISTRY,
    discover_backends,
    get_backend,
    get_backend_for_tier,
    list_backends,
)
from photonstrust.backends.stochastic import StochasticBackend
from photonstrust.backends.types import (
    BackendProvenance,
    ComparisonResult,
    MultifidelityEvidence,
    PhysicsBackend,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Clear the global registry before every test."""
    _REGISTRY.clear()
    yield
    _REGISTRY.clear()


# ------------------------------------------------------------------
# 1. discover_backends returns >= 2 built-in backends
# ------------------------------------------------------------------
def test_registry_discovers_builtins():
    backends = discover_backends()
    assert len(backends) >= 2
    names = {b.name for b in backends}
    assert "analytic" in names
    assert "stochastic" in names


# ------------------------------------------------------------------
# 2. get_backend("analytic") works
# ------------------------------------------------------------------
def test_registry_get_backend_by_name():
    backend = get_backend("analytic")
    assert isinstance(backend, PhysicsBackend)
    assert backend.name == "analytic"
    assert backend.tier == 0


# ------------------------------------------------------------------
# 3. get_backend_for_tier(2, fallback=True) falls back to tier 1
# ------------------------------------------------------------------
def test_fallback_tier2_to_tier1():
    b = get_backend_for_tier(2, fallback=True)
    assert b is not None
    assert b.tier < 2


# ------------------------------------------------------------------
# 4. get_backend_for_tier(2, fallback=False) returns None
# ------------------------------------------------------------------
def test_fallback_disabled_returns_none():
    result = get_backend_for_tier(2, fallback=False)
    assert result is None


# ------------------------------------------------------------------
# 5. Analytic backend returns dict with key_rate_bps > 0
# ------------------------------------------------------------------
def test_analytic_backend_simulate():
    ab = AnalyticBackend()
    out = ab.simulate("qkd_link", {"distance_km": 20})
    assert "key_rate_bps" in out
    assert out["key_rate_bps"] > 0
    assert "qber_total" in out
    assert "loss_db" in out
    assert "eta_channel" in out


# ------------------------------------------------------------------
# 6. Same seed produces identical stochastic key_rate_mean
# ------------------------------------------------------------------
def test_stochastic_backend_deterministic_seed():
    sb = StochasticBackend()
    inputs = {"distance_km": 30, "mc_samples": 50}
    r1 = sb.simulate("qkd_link", inputs, seed=42)
    r2 = sb.simulate("qkd_link", inputs, seed=42)
    assert r1["key_rate_mean"] == r2["key_rate_mean"]
    assert r1["key_rate_std"] == r2["key_rate_std"]


# ------------------------------------------------------------------
# 7. ComparisonResult has all required fields
# ------------------------------------------------------------------
def test_comparison_report_structure():
    scenario = {"distance_km": 40, "scenario_id": "test-40km"}
    result = run_cross_fidelity_comparison(scenario=scenario, seed=7)
    assert isinstance(result, ComparisonResult)
    assert result.scenario_id == "test-40km"
    assert len(result.backends_compared) >= 2
    assert isinstance(result.results, dict)
    assert isinstance(result.deltas, dict)
    assert result.consistency_verdict in {
        "consistent",
        "divergent",
        "inconclusive",
    }
    assert isinstance(result.max_relative_delta, float)
    assert isinstance(result.provenance, list)


# ------------------------------------------------------------------
# 8. Comparing analytic to itself yields "consistent"
# ------------------------------------------------------------------
def test_comparison_consistent_verdict():
    scenario = {"distance_km": 25}
    result = run_cross_fidelity_comparison(
        scenario=scenario,
        backends=["analytic", "analytic"],
        seed=1,
    )
    assert result.consistency_verdict == "consistent"
    assert result.max_relative_delta == 0.0


# ------------------------------------------------------------------
# 9. provenance() returns dict with name, tier, version
# ------------------------------------------------------------------
def test_provenance_tracking():
    for cls in (AnalyticBackend, StochasticBackend):
        prov = cls().provenance()
        assert "backend_name" in prov
        assert "tier" in prov
        assert "version" in prov


# ------------------------------------------------------------------
# 10. applicability({}) returns {"applicable": True}
# ------------------------------------------------------------------
def test_applicability_check():
    for cls in (AnalyticBackend, StochasticBackend):
        app = cls().applicability({})
        assert app["applicable"] is True


# ------------------------------------------------------------------
# 11. build_multifidelity_evidence returns valid result
# ------------------------------------------------------------------
def test_multifidelity_evidence_artifact():
    scenario = {"distance_km": 50}
    comp = run_cross_fidelity_comparison(scenario=scenario, seed=99)
    evidence = build_multifidelity_evidence(comp)
    assert isinstance(evidence, MultifidelityEvidence)
    assert isinstance(evidence.tier_coverage, dict)
    assert isinstance(evidence.recommendation, str)
    d = evidence.as_dict()
    assert "comparison" in d
    assert "tier_coverage" in d
    assert "recommendation" in d


# ------------------------------------------------------------------
# 12. BackendProvenance.as_dict() serialization round-trip
# ------------------------------------------------------------------
def test_backend_provenance_serialization():
    prov = BackendProvenance(
        backend_name="analytic",
        tier=0,
        version="1.0.0",
        seed=42,
        config_hash="abc123",
        timestamp="2026-03-23T00:00:00Z",
    )
    d = prov.as_dict()
    assert d["backend_name"] == "analytic"
    assert d["tier"] == 0
    assert d["version"] == "1.0.0"
    assert d["seed"] == 42
    assert d["config_hash"] == "abc123"
    assert d["timestamp"] == "2026-03-23T00:00:00Z"
