from __future__ import annotations

import math

import pytest

from photonstrust.pipeline.pic_qkd_bridge import (
    build_qkd_scenario_from_pic,
    extract_eta_chip,
    pdk_coupler_efficiency,
)


def test_extract_eta_chip_prefers_dag_external_output_power_sum() -> None:
    sim_result = {
        "dag_solver": {
            "external_outputs": [
                {"node": "n1", "port": "out", "power": 0.30},
                {"node": "n2", "port": "out", "power": 0.25},
            ]
        },
        "chain_solver": {"eta_total": 0.11},
    }

    eta = extract_eta_chip(sim_result, wavelength_nm=1550.0)
    assert eta == pytest.approx(0.55)


def test_extract_eta_chip_falls_back_to_chain_eta_and_loss() -> None:
    sim_chain = {"chain_solver": {"eta_total": 0.42}}
    assert extract_eta_chip(sim_chain, wavelength_nm=1550.0) == pytest.approx(0.42)

    sim_loss = {"chain_solver": {"total_loss_db": 3.0}}
    assert extract_eta_chip(sim_loss, wavelength_nm=1550.0) == pytest.approx(10.0 ** (-3.0 / 10.0))


def test_pdk_coupler_efficiency_uses_component_cell_il_and_defaults_to_one() -> None:
    pdk = {
        "component_cells": [
            {"name": "grating_coupler_te", "nominal_il_db": 3.0},
            {"name": "edge_coupler_te", "insertion_loss_db": 1.0},
            {"name": "mmi_2x2", "nominal_il_db": 10.0},
        ]
    }

    expected = 10.0 ** (-((3.0 + 1.0) / 2.0) / 10.0)
    assert pdk_coupler_efficiency(pdk) == pytest.approx(expected)
    assert pdk_coupler_efficiency({}) == pytest.approx(1.0)


def test_build_qkd_scenario_from_pic_absorbs_chip_and_coupler_efficiency() -> None:
    scenario = build_qkd_scenario_from_pic(
        graph={"graph_id": "bridge_case"},
        distances_km=[50.0, 0.0, 25.0],
        wavelength_nm=1550.0,
        protocol="BB84_DECOY",
        eta_chip=0.5,
        eta_coupler=0.8,
    )

    assert scenario["scenario_id"] == "bridge_case_pic_qkd_certificate"
    assert scenario["protocol"]["name"] == "BB84_DECOY"
    assert scenario["distances_km"] == [0.0, 25.0, 50.0]
    assert scenario["source"]["coupling_efficiency"] == pytest.approx(0.4)
    assert math.isclose(float(scenario["wavelength_nm"]), 1550.0)
