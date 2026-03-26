# 02 - Test Coverage Gaps & Proposed Tests

Current state: **145 passed, 2 skipped** (2026-02-14).
Estimated line coverage: ~60-70% (no `pytest-cov` integration yet).

---

## Research Anchors (Test Strategy Tooling)

- pytest documentation: https://docs.pytest.org/
- pytest-cov coverage plugin: https://pytest-cov.readthedocs.io/
- Hypothesis (property-based testing; useful for config + numeric invariants): https://hypothesis.readthedocs.io/

## Gap 1: Untested modules

### `photonstrust/presets.py`

No direct tests for band/detector preset logic. Boundary values for PDE
adjustments and band-detector compatibility are unchecked.

**Proposed test:** `tests/test_presets.py`

```python
import pytest
from photonstrust.presets import BAND_PRESETS, DETECTOR_PRESETS, get_band_preset, get_detector_preset

@pytest.mark.parametrize("band", list(BAND_PRESETS.keys()))
def test_band_preset_has_required_keys(band):
    preset = get_band_preset(band)
    assert "wavelength_nm" in preset
    assert "fiber_loss_db_per_km" in preset
    assert preset["wavelength_nm"] > 0

@pytest.mark.parametrize("detector_class", list(DETECTOR_PRESETS.keys()))
@pytest.mark.parametrize("band", list(BAND_PRESETS.keys()))
def test_detector_preset_pde_in_range(detector_class, band):
    preset = get_detector_preset(detector_class, band)
    assert 0.0 <= preset["pde"] <= 1.0
    assert preset["dark_counts_cps"] >= 0.0
    assert preset["jitter_ps_fwhm"] >= 0.0

def test_unknown_band_raises():
    with pytest.raises(ValueError):
        get_band_preset("nonexistent_band")
```

---

### `photonstrust/utils.py`

`binary_entropy()`, `clamp()`, `hash_dict()` lack any tests.

**Proposed test:** `tests/test_utils.py`

```python
import math
import pytest
from photonstrust.utils import binary_entropy, clamp, hash_dict

class TestBinaryEntropy:
    def test_zero_returns_zero(self):
        assert binary_entropy(0.0) == 0.0

    def test_one_returns_zero(self):
        assert binary_entropy(1.0) == 0.0

    def test_half_returns_one(self):
        assert abs(binary_entropy(0.5) - 1.0) < 1e-12

    def test_negative_returns_zero(self):
        assert binary_entropy(-0.1) == 0.0

    def test_above_one_returns_zero(self):
        assert binary_entropy(1.1) == 0.0

    def test_symmetric(self):
        assert abs(binary_entropy(0.2) - binary_entropy(0.8)) < 1e-12

class TestClamp:
    def test_within_range(self):
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_range(self):
        assert clamp(-1.0, 0.0, 1.0) == 0.0

    def test_above_range(self):
        assert clamp(2.0, 0.0, 1.0) == 1.0

class TestHashDict:
    def test_deterministic(self):
        d = {"a": 1, "b": 2}
        assert hash_dict(d) == hash_dict(d)

    def test_order_independent(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert hash_dict(d1) == hash_dict(d2)

    def test_different_values_differ(self):
        assert hash_dict({"a": 1}) != hash_dict({"a": 2})
```

---

### `photonstrust/events/` (kernel.py, topology.py)

Event serialization/deserialization has no tests. The `EventKernel` class and
topology builder helpers are untested.

**Proposed test:** `tests/test_events.py`

```python
# Minimal smoke tests for the event subsystem.
# Expand once the event API stabilizes.

def test_event_kernel_import():
    from photonstrust.events.kernel import Event, EventKernel
    kernel = EventKernel()
    kernel.schedule(Event(time_ns=1.0, priority=0, event_type="ping", node_id="n1"))
    out = kernel.run()
    assert len(out) == 1
    assert out[0].node_id == "n1"

def test_topology_import():
    from photonstrust.events.topology import build_chain, build_link, build_star

    channel_cfg = {"model": "fiber", "fiber_loss_db_per_km": 0.2, "connector_loss_db": 1.5, "dispersion_ps_per_km": 0.0}
    assert build_link("a", "b", channel_cfg)["nodes"] == ["a", "b"]
    assert len(build_chain(["a", "b", "c"], channel_cfg)["links"]) == 2
    assert len(build_star("hub", ["a", "b"], channel_cfg)["links"]) == 2
```

---

### `photonstrust/comparison.py`

No tests for heralding comparison runner.

---

## Gap 2: Missing edge cases

### Distance = 0

At zero distance (fiber), the path loss should reduce to connector loss (if any),
and the key rate should be >= longer distances given identical noise.

```python
def test_zero_distance_has_min_loss_and_max_rate(base_scenario):
    r0 = compute_point(base_scenario, 0.0)
    r10 = compute_point(base_scenario, 10.0)
    assert abs(r0.loss_db - float(base_scenario["channel"]["connector_loss_db"])) < 1e-9
    assert r0.key_rate_bps >= r10.key_rate_bps
```

### Extreme parameter combinations

```python
@pytest.mark.parametrize("dark_cps,pde", [
    (1e6, 0.01),   # Very high dark counts, very low PDE
    (0.0, 0.99),   # No dark counts, high PDE
    (100, 0.0),    # Non-zero dark counts, zero PDE
])
def test_extreme_detector_parameters(base_scenario, dark_cps, pde):
    base_scenario["detector"]["dark_counts_cps"] = dark_cps
    base_scenario["detector"]["pde"] = pde
    result = compute_point(base_scenario, 50.0)
    assert result.key_rate_bps >= 0.0
    assert 0.0 <= result.qber_total <= 0.5
```

### Numerical stability near underflow

```python
def test_very_long_distance_no_nan(base_scenario):
    result = compute_point(base_scenario, 500.0)  # ~100 dB loss
    assert math.isfinite(result.key_rate_bps)
    assert math.isfinite(result.qber_total)
    assert result.key_rate_bps >= 0.0
```

---

## Gap 3: No end-to-end integration test

No single test exercises: config load -> build scenarios -> compute sweep ->
write results -> generate report.

**Proposed test:** `tests/test_integration_pipeline.py`

```python
"""End-to-end integration test: config -> sweep -> output."""

from pathlib import Path
from photonstrust.config import load_config, build_scenarios
from photonstrust.qkd import compute_sweep

def test_full_pipeline_quick_smoke(tmp_path):
    config = load_config("configs/quickstart/qkd_quick_smoke.yml")
    scenarios = build_scenarios(config)
    assert len(scenarios) > 0

    for scenario in scenarios:
        result = compute_sweep(scenario, include_uncertainty=False)
        assert len(result["results"]) > 0
        for r in result["results"]:
            assert r.key_rate_bps >= 0.0
            assert 0.0 <= r.qber_total <= 0.5
```

---

## Gap 4: No shared test fixtures

Many test files recreate the same `cfg` dictionaries. This leads to drift
between test configs and real configs.

**Correction:** Create `tests/conftest.py` with shared fixtures:

```python
"""Shared test fixtures for PhotonTrust test suite."""

import pytest
from photonstrust.config import load_config, build_scenarios

@pytest.fixture
def base_scenario():
    """A minimal valid scenario for unit tests."""
    return {
        "scenario_id": "test_base",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [10, 50, 100],
        "source": {
            "type": "spdc",
            "mu": 0.05,
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.60,
            "physics_backend": "analytic",
            "emission_mode": "steady_state",
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "dispersion_ps_per_km": 17.0,
            "connector_loss_db": 1.5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.85,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 50,
            "dead_time_ns": 20,
            "afterpulsing_prob": 0.01,
            "afterpulse_delay_ns": 50.0,
            "physics_backend": "analytic",
            "sample_count": 500,
            "time_bin_ps": 10.0,
            "background_counts_cps": 0.0,
        },
        "timing": {"sync_drift_ps_rms": 10},
        "protocol": {"sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
        "finite_key": {},
    }

@pytest.fixture
def quick_smoke_scenarios():
    """Scenarios from the quick smoke demo config."""
    config = load_config("configs/quickstart/qkd_quick_smoke.yml")
    return build_scenarios(config)
```

---

## Gap 5: No parametrized band/detector matrix tests

The project has multiple bands and detector presets, but no test systematically
sweeps all combinations.

```python
from photonstrust.presets import BAND_PRESETS, DETECTOR_PRESETS, get_band_preset, get_detector_preset

@pytest.mark.parametrize("band", list(BAND_PRESETS.keys()))
@pytest.mark.parametrize("detector_class", list(DETECTOR_PRESETS.keys()))
def test_all_band_detector_combinations_produce_positive_rate(band, detector_class, base_scenario):
    bp = get_band_preset(band)
    dp = get_detector_preset(detector_class, band)

    base_scenario["band"] = band
    base_scenario["wavelength_nm"] = bp["wavelength_nm"]
    base_scenario["channel"]["fiber_loss_db_per_km"] = bp["fiber_loss_db_per_km"]
    base_scenario["detector"].update(dp)

    result = compute_point(base_scenario, 10.0)
    assert result.key_rate_bps >= 0.0
```

---

## Summary: Coverage improvement roadmap

| Priority | Action | Files | Estimated new tests |
|----------|--------|-------|---------------------|
| 1 | Add `conftest.py` with shared fixtures | tests/conftest.py | 0 (enables others) |
| 2 | Add `test_utils.py` | tests/test_utils.py | ~10 |
| 3 | Add `test_presets.py` | tests/test_presets.py | ~8 |
| 4 | Add edge case tests to `test_qkd_smoke.py` | tests/test_qkd_smoke.py | ~6 |
| 5 | [DONE] Add PLOB bound test (PLOB sanity gate) | tests/test_qkd_plob_bound.py | Implemented (5 param cases) |
| 6 | Add integration pipeline test | tests/test_integration_pipeline.py | ~2 |
| 7 | Add parametrized band/detector matrix | tests/test_band_detector_matrix.py | ~6 |
| 8 | Add `pytest-cov` to CI with 70% floor | ci.yml | 0 (enforcement) |

**Total: ~37 new tests, targeting 80%+ coverage on core physics modules.**
