from __future__ import annotations

from photonstrust.orbit.providers.base import OrbitTrace, OrbitTraceSample
from photonstrust.orbit.providers.parity import compare_provider_traces


def _trace(
    *,
    provider_id: str,
    samples: list[tuple[float, float, float]],
) -> OrbitTrace:
    rows = tuple(
        OrbitTraceSample(t_s=float(t), elevation_deg=float(el), slant_range_km=float(sr)) for t, el, sr in samples
    )
    return OrbitTrace(
        provider_id=provider_id,
        provider_version="test",
        execution_mode="preview",
        trusted=True,
        compatibility="native",
        samples=rows,
        metadata={},
    )


def test_compare_provider_traces_computes_expected_deltas() -> None:
    reference = _trace(
        provider_id="analytic",
        samples=[(0.0, 20.0, 1200.0), (10.0, 50.0, 800.0), (20.0, 40.0, 900.0)],
    )
    candidate = _trace(
        provider_id="skyfield",
        samples=[(2.0, 15.0, 1300.0), (12.0, 55.0, 750.0), (22.0, 45.0, 950.0), (32.0, 10.0, 1500.0)],
    )

    parity = compare_provider_traces(reference, candidate)

    assert parity.pass_start_s.delta == 2.0
    assert parity.pass_end_s.delta == 12.0
    assert parity.peak_elevation_deg.delta == 5.0
    assert parity.peak_slant_range_km.delta == -50.0
    assert parity.sample_count.delta == 1.0
    assert parity.sample_count.abs_delta == 1.0


def test_compare_provider_traces_to_dict_contains_required_metrics() -> None:
    left = _trace(provider_id="a", samples=[])
    right = _trace(provider_id="b", samples=[])
    payload = compare_provider_traces(left, right).to_dict()

    assert payload["reference_provider"] == "a"
    assert payload["candidate_provider"] == "b"
    assert set(payload.keys()) == {
        "reference_provider",
        "candidate_provider",
        "pass_start_s",
        "pass_end_s",
        "peak_elevation_deg",
        "peak_slant_range_km",
        "sample_count",
    }
