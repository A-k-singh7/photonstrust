from __future__ import annotations

import copy

import pytest

from photonstrust.benchmarks.schema import SchemaValidationError, validate_instance
from photonstrust.workflow.schema import (
    satellite_qkd_chain_certificate_schema_path,
    satellite_qkd_chain_schema_path,
)


def _minimal_chain_config() -> dict:
    return {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": "m5_minimal",
            "satellite": {
                "altitude_km": 600.0,
                "orbit_inclination_deg": 70.0,
                "tx_aperture_m": 0.15,
                "wavelength_nm": 785.0,
                "source_type": "bb84_wcp",
                "rep_rate_mhz": 100.0,
                "mu_signal": 0.5,
                "mu_decoy": 0.1,
                "source_qber_contribution": 0.005,
            },
            "atmosphere": {
                "model": "effective_thickness",
                "extinction_db_per_km": 0.05,
                "effective_thickness_km": 20.0,
                "turbulence_scintillation_index": 0.15,
                "pointing_jitter_urad": 2.0,
            },
            "ground_station": {
                "latitude_deg": 52.5,
                "rx_aperture_m": 0.40,
                "telescope_efficiency": 0.80,
                "fibre_coupling_efficiency": 0.45,
                "eta_chip": 0.60,
                "detector_type": "ingaas_apd",
                "detector_pde": 0.25,
                "detector_dcr_cps": 1000.0,
                "detector_jitter_ps_fwhm": 500.0,
                "coincidence_window_ps": 1000.0,
                "bandpass_filter_nm": 0.5,
                "clear_sky_probability": 0.40,
            },
            "pass_geometry": {
                "elevation_min_deg": 15.0,
                "dt_s": 5.0,
                "day_night": "night",
            },
            "protocol": "BB84_decoy",
            "output": {
                "key_per_pass": True,
                "annual_estimate": True,
                "sign_certificate": False,
            },
        },
    }


def _minimal_chain_certificate() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_certificate",
        "run_id": "abcd1234ef56",
        "generated_at": "2026-03-02T00:00:00Z",
        "mission": "m5_minimal",
        "ground_station": {
            "latitude_deg": 52.5,
            "pic_cert_run_id": None,
            "eta_chip": 0.60,
            "eta_ground_terminal": 0.216,
        },
        "pass": {
            "altitude_km": 600.0,
            "elevation_min_deg": 15.0,
            "pass_duration_s": 420.0,
            "samples_evaluated": 84,
            "samples_with_positive_key_rate": 70,
            "key_bits_accumulated": 41234.0,
            "mean_key_rate_bps": 98.2,
            "peak_key_rate_bps": 740.0,
            "peak_elevation_deg": 72.0,
        },
        "annual_estimate": {
            "passes_per_day": 4.3,
            "clear_sky_probability": 0.4,
            "key_bits_per_year": 25874000.0,
            "key_mbits_per_year": 25.874,
            "notes": "night passes only",
        },
        "signoff": {
            "decision": "GO",
            "key_rate_positive_at_zenith": True,
            "annual_key_above_1mbit": True,
        },
        "signature": None,
    }


def test_satellite_chain_schema_accepts_minimal_valid_instance() -> None:
    validate_instance(_minimal_chain_config(), satellite_qkd_chain_schema_path())


def test_satellite_chain_schema_rejects_missing_required_field() -> None:
    bad = copy.deepcopy(_minimal_chain_config())
    bad["satellite_qkd_chain"].pop("pass_geometry")
    with pytest.raises(SchemaValidationError):
        validate_instance(bad, satellite_qkd_chain_schema_path())


def test_satellite_chain_certificate_schema_accepts_minimal_valid_instance() -> None:
    validate_instance(_minimal_chain_certificate(), satellite_qkd_chain_certificate_schema_path())


def test_satellite_chain_certificate_schema_rejects_missing_pass_object() -> None:
    bad = copy.deepcopy(_minimal_chain_certificate())
    bad.pop("pass")
    with pytest.raises(SchemaValidationError):
        validate_instance(bad, satellite_qkd_chain_certificate_schema_path())

