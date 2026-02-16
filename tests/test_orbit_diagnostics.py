from __future__ import annotations


from photonstrust.orbit.diagnostics import validate_orbit_pass_semantics


def _good_config() -> dict:
    return {
        "orbit_pass": {
            "id": "test_orbit_pass",
            "band": "c_1550",
            "dt_s": 30,
            "samples": [
                {"t_s": 0, "distance_km": 1200, "elevation_deg": 20, "background_counts_cps": 5000},
                {"t_s": 30, "distance_km": 900, "elevation_deg": 40, "background_counts_cps": 2000},
                {"t_s": 60, "distance_km": 600, "elevation_deg": 70, "background_counts_cps": 300},
            ],
        },
        "source": {"type": "emitter_cavity"},
        "channel": {"model": "free_space"},
        "detector": {"class": "snspd"},
        "timing": {},
        "protocol": {"name": "BBM92"},
        "uncertainty": {},
    }


def test_orbit_diagnostics_good_config_has_no_errors() -> None:
    d = validate_orbit_pass_semantics(_good_config())
    assert d["summary"]["error_count"] == 0


def test_orbit_diagnostics_catches_missing_orbit_pass_block() -> None:
    d = validate_orbit_pass_semantics({"source": {"type": "emitter_cavity"}, "channel": {"model": "free_space"}, "detector": {"class": "snspd"}})
    assert d["summary"]["error_count"] >= 1
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.block" in codes


def test_orbit_diagnostics_catches_sample_elevation_out_of_range() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["samples"][0]["elevation_deg"] = 120
    d = validate_orbit_pass_semantics(cfg)
    assert d["summary"]["error_count"] >= 1
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.sample.elevation_deg" in codes


def test_orbit_diagnostics_warns_on_dt_s_spacing_mismatch() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["dt_s"] = 10
    d = validate_orbit_pass_semantics(cfg)
    codes = {x["code"] for x in d["warnings"]}
    assert "orbit_pass.dt_s.spacing" in codes


def test_orbit_diagnostics_catches_availability_clear_fraction_out_of_range() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["availability"] = {"clear_fraction": 1.5}
    d = validate_orbit_pass_semantics(cfg)
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.availability.clear_fraction" in codes


def test_orbit_diagnostics_validates_execution_mode() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["execution_mode"] = "invalid_mode"
    d = validate_orbit_pass_semantics(cfg)
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.execution_mode" in codes


def test_orbit_diagnostics_certification_warns_for_deterministic_models() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["execution_mode"] = "certification"
    cfg["channel"]["pointing_model"] = "deterministic"
    cfg["channel"]["turbulence_model"] = "deterministic"
    d = validate_orbit_pass_semantics(cfg)
    warn_codes = {x["code"] for x in d["warnings"]}
    assert "channel.pointing_model" in warn_codes
    assert "channel.turbulence_model" in warn_codes


def test_orbit_diagnostics_rejects_invalid_radiance_day_night_flag() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["background_model"] = "radiance_proxy"
    cfg["channel"]["background_model"] = "radiance_proxy"
    cfg["orbit_pass"]["samples"][0]["background_counts_cps"] = None
    cfg["orbit_pass"]["samples"][0]["day_night"] = "twilight"
    d = validate_orbit_pass_semantics(cfg)
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.sample.day_night" in codes


def test_orbit_diagnostics_finite_key_enforcement_warning_when_disabled() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["finite_key"] = {"enabled": False}
    d = validate_orbit_pass_semantics(cfg)
    warn_codes = {x["code"] for x in d["warnings"]}
    assert "orbit_pass.finite_key.enforced" in warn_codes


def test_orbit_diagnostics_rejects_invalid_finite_key_detection_probability() -> None:
    cfg = _good_config()
    cfg["orbit_pass"]["finite_key"] = {"detection_probability": 1.2}
    d = validate_orbit_pass_semantics(cfg)
    codes = {x["code"] for x in d["errors"]}
    assert "orbit_pass.finite_key.detection_probability" in codes
