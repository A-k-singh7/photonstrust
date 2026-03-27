"""Tests for Phase C2 PDK manifests: new foundry PDKs, enhancements, and DRC rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_CONFIGS_DIR = Path(__file__).resolve().parents[1] / "configs" / "pdks"

_NEW_PDKS = [
    "imec_isipp50g",
    "ligentec_an800",
    "gf_45clo",
    "lionix_triplex",
]

_REQUIRED_DESIGN_RULES = [
    "min_waveguide_width_um",
    "min_waveguide_gap_um",
    "min_bend_radius_um",
]

# Known internal component kinds from the PIC library.
_KNOWN_KINDS = {
    "pic.waveguide",
    "pic.grating_coupler",
    "pic.edge_coupler",
    "pic.phase_shifter",
    "pic.isolator_2port",
    "pic.ring",
    "pic.coupler",
    "pic.touchstone_2port",
    "pic.touchstone_nport",
    "pic.mmi",
    "pic.y_branch",
    "pic.crossing",
    "pic.mzm",
    "pic.photodetector",
    "pic.awg",
    "pic.heater",
    "pic.ssc",
}


def _load_manifest(name: str) -> dict:
    path = _CONFIGS_DIR / f"{name}.pdk.json"
    assert path.exists(), f"PDK manifest not found: {path}"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict), "PDK manifest must be a JSON object"
    return data


# ------------------------------------------------------------------
# Step 2 tests: new PDK manifests load and validate
# ------------------------------------------------------------------

def test_imec_manifest_loads():
    data = _load_manifest("imec_isipp50g")
    assert data["name"] == "imec_isipp50g"
    assert data["version"] == "0.1"
    assert isinstance(data["layer_stack"], list) and len(data["layer_stack"]) >= 5
    assert isinstance(data["component_cells"], list) and len(data["component_cells"]) >= 6


def test_ligentec_manifest_loads():
    data = _load_manifest("ligentec_an800")
    assert data["name"] == "ligentec_an800"
    assert data["version"] == "0.1"
    assert isinstance(data["layer_stack"], list) and len(data["layer_stack"]) >= 3
    assert isinstance(data["component_cells"], list) and len(data["component_cells"]) >= 4


def test_gf45clo_manifest_loads():
    data = _load_manifest("gf_45clo")
    assert data["name"] == "gf_45clo"
    assert data["version"] == "0.1"
    assert isinstance(data["layer_stack"], list) and len(data["layer_stack"]) >= 2
    assert isinstance(data["component_cells"], list) and len(data["component_cells"]) >= 3


def test_lionix_manifest_loads():
    data = _load_manifest("lionix_triplex")
    assert data["name"] == "lionix_triplex"
    assert data["version"] == "0.1"
    assert isinstance(data["layer_stack"], list) and len(data["layer_stack"]) >= 3
    assert isinstance(data["component_cells"], list) and len(data["component_cells"]) >= 3


# ------------------------------------------------------------------
# Step 3 tests: existing PDK enhancements
# ------------------------------------------------------------------

def test_siepic_has_phase_c_components():
    data = _load_manifest("siepic_ebeam")
    cells = data["component_cells"]
    kinds = {c.get("maps_to_internal_kind") for c in cells if c.get("maps_to_internal_kind")}
    assert "pic.mmi" in kinds, "siepic_ebeam should have pic.mmi after Phase C enhancement"
    assert "pic.y_branch" in kinds, "siepic_ebeam should have pic.y_branch after Phase C enhancement"
    assert "pic.crossing" in kinds, "siepic_ebeam should have pic.crossing after Phase C enhancement"


def test_aim_has_phase_c_components():
    data = _load_manifest("aim_photonics")
    cells = data["component_cells"]
    kinds = {c.get("maps_to_internal_kind") for c in cells if c.get("maps_to_internal_kind")}
    assert "pic.mzm" in kinds, "aim_photonics should have pic.mzm after Phase C enhancement"
    assert "pic.photodetector" in kinds, "aim_photonics should have pic.photodetector"
    assert "pic.heater" in kinds, "aim_photonics should have pic.heater"
    assert "pic.awg" in kinds, "aim_photonics should have pic.awg"


# ------------------------------------------------------------------
# Cross-PDK validation
# ------------------------------------------------------------------

def _all_pdk_names() -> list[str]:
    return sorted(
        p.stem.replace(".pdk", "")
        for p in _CONFIGS_DIR.glob("*.pdk.json")
    )


@pytest.mark.parametrize("pdk_name", _all_pdk_names())
def test_all_pdks_have_design_rules(pdk_name: str):
    data = _load_manifest(pdk_name)
    rules = data.get("design_rules", {})
    for key in _REQUIRED_DESIGN_RULES:
        assert key in rules, f"{pdk_name} missing design rule: {key}"
        assert isinstance(rules[key], (int, float)), f"{pdk_name} design rule {key} must be numeric"
        assert rules[key] > 0, f"{pdk_name} design rule {key} must be > 0"


@pytest.mark.parametrize("pdk_name", _all_pdk_names())
def test_component_cells_map_to_known_kinds(pdk_name: str):
    data = _load_manifest(pdk_name)
    cells = data.get("component_cells", [])
    for cell in cells:
        kind = cell.get("maps_to_internal_kind")
        if kind is not None:
            assert kind in _KNOWN_KINDS, (
                f"{pdk_name} component '{cell.get('name')}' maps to unknown kind: {kind}"
            )


# ------------------------------------------------------------------
# Platform-specific property tests
# ------------------------------------------------------------------

def test_ligentec_ultra_low_loss():
    data = _load_manifest("ligentec_an800")
    wg_cells = [
        c for c in data["component_cells"]
        if c.get("maps_to_internal_kind") == "pic.waveguide"
    ]
    assert len(wg_cells) >= 1
    for wg in wg_cells:
        loss = wg.get("default_params", {}).get("loss_db_per_cm", 999)
        assert loss < 0.1, (
            f"Ligentec AN800 waveguide '{wg['name']}' loss {loss} dB/cm should be < 0.1 dB/cm"
        )


def test_lionix_ultra_low_loss():
    data = _load_manifest("lionix_triplex")
    wg_cells = [
        c for c in data["component_cells"]
        if c.get("maps_to_internal_kind") == "pic.waveguide"
    ]
    assert len(wg_cells) >= 1
    # At least one waveguide must have ultra-low loss < 0.05 dB/cm
    min_loss = min(
        c.get("default_params", {}).get("loss_db_per_cm", 999) for c in wg_cells
    )
    assert min_loss < 0.05, (
        f"LioniX TriPleX best waveguide loss {min_loss} dB/cm should be < 0.05 dB/cm"
    )


def test_imec_has_modulator():
    data = _load_manifest("imec_isipp50g")
    kinds = {
        c.get("maps_to_internal_kind")
        for c in data["component_cells"]
        if c.get("maps_to_internal_kind")
    }
    assert "pic.mzm" in kinds, "IMEC iSiPP50G must have a pic.mzm modulator component"
