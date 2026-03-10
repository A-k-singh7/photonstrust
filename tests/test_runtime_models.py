from __future__ import annotations

from photonstrust.pipeline.satellite_chain import run_satellite_chain
from photonstrust.workflow.runtime_models import (
    validate_satellite_chain_certificate,
    validate_satellite_chain_config,
)


def _base_config() -> dict:
    return {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": "runtime_model_chain",
            "satellite": {
                "altitude_km": 550.0,
                "orbit_inclination_deg": 70.0,
                "tx_aperture_m": 0.30,
                "wavelength_nm": 850.0,
                "source_type": "bb84_wcp",
                "rep_rate_mhz": 150.0,
            },
            "atmosphere": {
                "model": "effective_thickness",
                "extinction_db_per_km": 0.02,
                "effective_thickness_km": 20.0,
                "turbulence_scintillation_index": 0.1,
                "pointing_jitter_urad": 1.2,
            },
            "ground_station": {
                "latitude_deg": 45.0,
                "rx_aperture_m": 1.0,
                "telescope_efficiency": 0.9,
                "fibre_coupling_efficiency": 0.65,
                "detector_type": "ingaas_apd",
                "detector_pde": 0.3,
                "detector_dcr_cps": 350.0,
                "detector_jitter_ps_fwhm": 250.0,
                "coincidence_window_ps": 400.0,
            },
            "pass_geometry": {
                "elevation_min_deg": 15.0,
                "dt_s": 5.0,
                "day_night": "night",
            },
            "protocol": "BB84_decoy",
        },
    }


def test_runtime_config_model_applies_day30_defaults() -> None:
    model = validate_satellite_chain_config({"schema_version": "0.1", "satellite_qkd_chain": {"id": "x"}})
    assert model.satellite_qkd_chain.compute.accumulate_backend == "numpy"
    assert model.satellite_qkd_chain.runtime.execution_mode == "preview"
    assert model.satellite_qkd_chain.runtime.rng_seed == 0
    assert model.satellite_qkd_chain.runtime.uncertainty_budget.rollup_method == "rss"
    assert model.satellite_qkd_chain.runtime.uncertainty_budget.required_components == (
        "orbit_provider_sigma_cps",
        "parity_derived_sigma_cps",
    )


def test_runtime_certificate_model_validates_pipeline_payload() -> None:
    result = run_satellite_chain(_base_config())
    cert_model = validate_satellite_chain_certificate(result["certificate"])
    assert cert_model.inputs.execution_mode == "preview"
    assert cert_model.inputs.seed_lineage.seed == 0
