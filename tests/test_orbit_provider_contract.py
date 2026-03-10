from __future__ import annotations

import json

import pytest

from photonstrust.orbit.providers import (
    AnalyticOrbitProvider,
    OrbitProviderError,
    OrbitProviderRequest,
    OrbitProviderUnavailableError,
    OrekitReferenceProvider,
    PoliastroOrbitProvider,
    SkyfieldOrbitProvider,
    get_orbit_provider,
)


def _request(mode: str = "preview") -> OrbitProviderRequest:
    return OrbitProviderRequest(
        altitude_km=600.0,
        elevation_min_deg=20.0,
        dt_s=10.0,
        execution_mode=mode,
        tle_line1="1 25544U 98067A   24060.50000000  .00016717  00000+0  10270-3 0  9003",
        tle_line2="2 25544  51.6416 115.3534 0003470  54.4278  41.0895 15.50000123 12345",
        satellite_name="ISS",
    )


def test_analytic_provider_contract_is_deterministic() -> None:
    provider = AnalyticOrbitProvider()
    trace_a = provider.build_trace(_request())
    trace_b = provider.build_trace(_request())

    assert trace_a.to_dict() == trace_b.to_dict()
    assert trace_a.provider_id == "analytic"
    assert trace_a.trusted is True
    assert trace_a.compatibility == "native"
    assert trace_a.sample_count > 0
    assert trace_a.pass_end_s >= trace_a.pass_start_s
    assert trace_a.peak_elevation_deg >= 0.0
    assert trace_a.peak_slant_range_km > 0.0


def test_provider_registry_rejects_unknown_provider() -> None:
    with pytest.raises(OrbitProviderError):
        get_orbit_provider("missing-provider")


def test_provider_registry_resolves_orekit_provider() -> None:
    provider = get_orbit_provider("orekit")
    assert isinstance(provider, OrekitReferenceProvider)


def test_skyfield_missing_dependency_falls_back_only_in_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = SkyfieldOrbitProvider()
    monkeypatch.setattr("photonstrust.orbit.providers.skyfield_provider._import_skyfield", lambda: None)

    preview_trace = provider.build_trace(_request(mode="preview"))
    assert preview_trace.provider_id == "skyfield"
    assert preview_trace.trusted is False
    assert preview_trace.compatibility == "preview_fallback"
    assert "skyfield_dependency_unavailable" in preview_trace.untrusted_reasons

    with pytest.raises(OrbitProviderUnavailableError):
        provider.build_trace(_request(mode="certification"))


def test_skyfield_provider_uses_native_path_when_dependency_available(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = SkyfieldOrbitProvider()

    class FakeSkyfield:
        __version__ = "9.9.9"

    monkeypatch.setattr("photonstrust.orbit.providers.skyfield_provider._import_skyfield", lambda: FakeSkyfield)
    monkeypatch.setattr(
        "photonstrust.orbit.providers.skyfield_provider._derive_altitude_from_tle",
        lambda **_: {
            "provider_version": "9.9.9",
            "tle_hash": "abc123",
            "tle_epoch": "2026-01-01T00:00:00Z",
            "altitude_km": 605.0,
        },
    )

    trace = provider.build_trace(_request())
    assert trace.provider_id == "skyfield"
    assert trace.trusted is True
    assert trace.compatibility == "native"
    assert trace.metadata["tle_hash"] == "abc123"
    assert trace.sample_count > 0


def test_poliastro_missing_dependency_is_explicitly_untrusted(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = PoliastroOrbitProvider()
    monkeypatch.setattr("photonstrust.orbit.providers.poliastro_provider._import_poliastro", lambda: None)

    trace = provider.build_trace(_request(mode="certification"))
    assert trace.provider_id == "poliastro"
    assert trace.trusted is False
    assert trace.compatibility == "dependency_unavailable"
    assert "poliastro_dependency_unavailable" in trace.untrusted_reasons


def test_orekit_provider_without_sidecar_falls_back_untrusted() -> None:
    provider = OrekitReferenceProvider()
    trace = provider.build_trace(_request(mode="certification"))

    assert trace.provider_id == "orekit"
    assert trace.trusted is False
    assert trace.compatibility == "reference_fallback"
    assert "orekit_reference_sidecar_unavailable" in trace.untrusted_reasons
    assert trace.sample_count > 0


def test_orekit_provider_uses_sidecar_when_present(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sidecar_path = tmp_path / "orekit_reference.json"
    sidecar_path.write_text(
        json.dumps(
            {
                "provider_version": "orekit-13.0",
                "source_hash": "sha256:demo",
                "samples": [
                    {"t_s": 10.0, "elevation_deg": 30.0, "distance_km": 1400.0},
                    {"t_s": 0.0, "elevation_deg": 10.0, "distance_km": 1600.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHOTONTRUST_OREKIT_REFERENCE_JSON", str(sidecar_path))

    provider = OrekitReferenceProvider()
    trace = provider.build_trace(_request(mode="certification"))

    assert trace.provider_id == "orekit"
    assert trace.trusted is True
    assert trace.compatibility == "sidecar"
    assert trace.provider_version == "orekit-13.0"
    assert trace.samples[0].t_s == 0.0
    assert trace.samples[1].t_s == 10.0
