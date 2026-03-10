from __future__ import annotations

import copy

import pytest

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.pipeline.satellite_chain import run_satellite_chain
from photonstrust.workflow.runtime_models import validate_satellite_chain_certificate
from photonstrust.workflow.schema import satellite_qkd_chain_certificate_schema_path


def _base_config() -> dict:
    return {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": "pipeline_unit_chain",
            "satellite": {
                "altitude_km": 500.0,
                "orbit_inclination_deg": 70.0,
                "tx_aperture_m": 0.30,
                "wavelength_nm": 850.0,
                "source_type": "bb84_wcp",
                "rep_rate_mhz": 200.0,
                "mu_signal": 0.5,
                "mu_decoy": 0.1,
                "source_qber_contribution": 0.005,
            },
            "atmosphere": {
                "model": "effective_thickness",
                "extinction_db_per_km": 0.02,
                "effective_thickness_km": 20.0,
                "turbulence_scintillation_index": 0.08,
                "pointing_jitter_urad": 1.0,
            },
            "ground_station": {
                "latitude_deg": 52.5,
                "rx_aperture_m": 1.2,
                "telescope_efficiency": 0.9,
                "fibre_coupling_efficiency": 0.7,
                "eta_chip": 0.9,
                "detector_type": "ingaas_apd",
                "detector_pde": 0.35,
                "detector_dcr_cps": 300.0,
                "detector_jitter_ps_fwhm": 200.0,
                "coincidence_window_ps": 400.0,
            },
            "pass_geometry": {
                "elevation_min_deg": 15.0,
                "dt_s": 5.0,
                "day_night": "night",
            },
            "protocol": "BB84_decoy",
            "output": {
                "annual_estimate": True,
                "clear_sky_probability": 0.5,
            },
        },
    }


def _key_bits(payload: dict) -> float:
    cert_raw = payload.get("certificate")
    cert = cert_raw if isinstance(cert_raw, dict) else {}
    section_raw = cert.get("pass")
    section = section_raw if isinstance(section_raw, dict) else {}
    return float(section.get("key_bits_accumulated", 0.0) or 0.0)


def test_satellite_chain_k_pass_positive_for_reasonable_scenario() -> None:
    result = run_satellite_chain(_base_config())
    assert _key_bits(result) > 0.0


def test_satellite_chain_snspd_outperforms_ingaas_for_same_geometry() -> None:
    ingaas_cfg = _base_config()
    ingaas_cfg["satellite_qkd_chain"]["ground_station"]["detector_type"] = "ingaas_apd"
    ingaas_cfg["satellite_qkd_chain"]["ground_station"]["detector_pde"] = 0.25
    ingaas_cfg["satellite_qkd_chain"]["ground_station"]["detector_dcr_cps"] = 1000.0

    snspd_cfg = copy.deepcopy(ingaas_cfg)
    snspd_cfg["satellite_qkd_chain"]["ground_station"]["detector_type"] = "snspd"
    snspd_cfg["satellite_qkd_chain"]["ground_station"]["detector_pde"] = 0.85
    snspd_cfg["satellite_qkd_chain"]["ground_station"]["detector_dcr_cps"] = 10.0

    ingaas = run_satellite_chain(ingaas_cfg)
    snspd = run_satellite_chain(snspd_cfg)
    assert _key_bits(snspd) >= _key_bits(ingaas)


def test_satellite_chain_annual_estimate_sane_positive() -> None:
    result = run_satellite_chain(_base_config())
    cert = result["certificate"]
    annual = cert.get("annual_estimate") if isinstance(cert.get("annual_estimate"), dict) else {}

    bits = float(annual.get("key_bits_per_year", 0.0) or 0.0)
    assert bits > 0.0
    assert bits < 1.0e12


def test_satellite_chain_certificate_validates_against_schema_helper() -> None:
    result = run_satellite_chain(_base_config())
    schema_path = satellite_qkd_chain_certificate_schema_path()
    validate_instance(result["certificate"], schema_path)


def test_satellite_chain_certificate_includes_seed_lineage_and_model_metadata() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["runtime"] = {
        "execution_mode": "certification",
        "rng_seed": 17,
    }

    result = run_satellite_chain(cfg)
    certificate = result["certificate"]
    inputs = certificate["inputs"]

    assert inputs["execution_mode"] == "certification"
    assert inputs["seed_lineage"] == {
        "seed": 17,
        "source": "satellite_qkd_chain.runtime.rng_seed",
        "deterministic": True,
    }
    assert "qkd.bb84_decoy_asymptotic" in inputs["model_metadata"]
    provider = inputs["orbit_provider"]
    assert provider["provider_name"] == "analytic"
    assert provider["trust_status"] == "trusted"
    assert provider["source_hash"]
    assert certificate["provenance"]["orbit_provider"] == provider
    budget = certificate["uncertainty_budget"]
    assert budget["rollup_method"] == "rss"
    assert budget["required_components"] == ["orbit_provider_sigma_cps", "parity_derived_sigma_cps"]
    assert budget["missing_components"] == []
    assert budget["is_complete"] is True
    assert budget["within_threshold"] is True
    assert budget["pass"] is True
    assert len(budget["components"]) == 2
    assert certificate["signoff"]["provider_trusted"] is True
    assert certificate["signoff"]["provider_parity_ok"] is True
    assert certificate["signoff"]["provider_uncertainty_ok"] is True
    assert certificate["signoff"]["uncertainty_budget_complete"] is True
    assert certificate["signoff"]["uncertainty_budget_within_threshold"] is True
    assert certificate["signoff"]["uncertainty_budget_ok"] is True
    assert certificate["signoff"]["hold_reasons"] == []
    validate_satellite_chain_certificate(certificate)


def test_satellite_chain_certification_requires_trusted_compute_backend() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["compute"] = {"accumulate_backend": "jax"}
    cfg["satellite_qkd_chain"]["runtime"] = {
        "execution_mode": "certification",
        "trusted_backends": ["numpy"],
    }

    with pytest.raises(ValueError, match="trusted accumulate backend"):
        run_satellite_chain(cfg)


def test_satellite_chain_certification_fail_closed_when_provider_unavailable() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["runtime"] = {
        "execution_mode": "certification",
    }
    cfg["satellite_qkd_chain"]["orbit_provider"] = {
        "name": "provider_that_does_not_exist",
        "allow_fallback": True,
        "trusted_providers": ["analytic"],
    }

    result = run_satellite_chain(cfg)
    cert = result["certificate"]
    signoff = cert["signoff"]
    assert signoff["decision"] == "HOLD"
    assert signoff["orbit_provider_trust_status"] == "unavailable"
    assert "provider_not_trusted" in signoff["hold_reasons"]
    assert "provider_parity_check_failed" in signoff["hold_reasons"]
    assert "provider_uncertainty_out_of_bounds" in signoff["hold_reasons"]


def test_satellite_chain_certification_fail_closed_when_provider_untrusted() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["runtime"] = {
        "execution_mode": "certification",
    }
    cfg["satellite_qkd_chain"]["orbit_provider"] = {
        "name": "analytic",
        "trusted_providers": ["external_provider"],
    }

    result = run_satellite_chain(cfg)
    cert = result["certificate"]
    signoff = cert["signoff"]
    assert signoff["decision"] == "HOLD"
    assert signoff["provider_trusted"] is False
    assert signoff["orbit_provider_trust_status"] == "untrusted"
    assert "provider_not_trusted" in signoff["hold_reasons"]


def test_satellite_chain_signoff_holds_when_uncertainty_budget_over_threshold() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["runtime"] = {
        "uncertainty_budget": {
            "max_total_sigma_cps": 40.0,
        }
    }
    cfg["satellite_qkd_chain"]["orbit_provider"] = {
        "name": "analytic",
        "reference_provider": "provider_that_does_not_exist",
        "require_parity": True,
    }

    result = run_satellite_chain(cfg)
    cert = result["certificate"]
    budget = cert["uncertainty_budget"]
    signoff = cert["signoff"]

    assert budget["is_complete"] is True
    assert budget["within_threshold"] is False
    assert budget["pass"] is False
    assert signoff["decision"] == "HOLD"
    assert signoff["uncertainty_budget_within_threshold"] is False
    assert signoff["uncertainty_budget_ok"] is False
    assert "uncertainty_budget_over_threshold" in signoff["hold_reasons"]


def test_satellite_chain_signoff_holds_when_uncertainty_budget_incomplete() -> None:
    cfg = _base_config()
    cfg["satellite_qkd_chain"]["runtime"] = {
        "uncertainty_budget": {
            "required_components": ["orbit_provider_sigma_cps", "unknown_component"],
        }
    }

    result = run_satellite_chain(cfg)
    cert = result["certificate"]
    budget = cert["uncertainty_budget"]
    signoff = cert["signoff"]

    assert budget["is_complete"] is False
    assert budget["pass"] is False
    assert "unknown_component" in budget["missing_components"]
    assert signoff["decision"] == "HOLD"
    assert signoff["uncertainty_budget_complete"] is False
    assert signoff["uncertainty_budget_ok"] is False
    assert "uncertainty_budget_incomplete" in signoff["hold_reasons"]
