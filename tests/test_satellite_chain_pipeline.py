from __future__ import annotations

import copy

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.pipeline.satellite_chain import run_satellite_chain
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
    cert = payload.get("certificate") if isinstance(payload.get("certificate"), dict) else {}
    section = cert.get("pass") if isinstance(cert.get("pass"), dict) else {}
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
