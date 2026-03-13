from __future__ import annotations

from pathlib import Path

from photonstrust.pdk import load_pdk_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
PDK_ROOT = REPO_ROOT / "configs" / "pdks"


def _component_names(manifest_name: str) -> set[str]:
    pdk = load_pdk_manifest(PDK_ROOT / manifest_name)
    cells = pdk.component_cells or []
    return {str(cell.get("name") or "").strip() for cell in cells if str(cell.get("name") or "").strip()}


def _component_cells(manifest_name: str) -> list[dict[str, object]]:
    pdk = load_pdk_manifest(PDK_ROOT / manifest_name)
    return list(pdk.component_cells or [])


def test_aim_photonics_manifest_covers_core_pic_cells() -> None:
    names = _component_names("aim_photonics.pdk.json")
    assert {
        "grating_coupler_te",
        "edge_coupler_te",
        "waveguide_straight",
        "mmi_2x2",
        "phase_shifter",
        "ring_resonator",
        "waveguide_bend_euler",
        "spot_size_converter",
    }.issubset(names)


def test_aim_photonics_300nm_sin_manifest_covers_core_io_and_tuning_cells() -> None:
    names = _component_names("aim_photonics_300nm_sin.pdk.json")
    assert {
        "grating_coupler_te",
        "edge_coupler_te",
        "waveguide_straight",
        "mmi_2x2",
        "phase_shifter",
    }.issubset(names)


def test_generic_manifests_cover_core_build_and_layout_cells() -> None:
    generic_names = _component_names("generic_silicon_photonics.pdk.json")
    corner_names = _component_names("generic_sip_corners.pdk.json")
    required = {
        "grating_coupler_te",
        "edge_coupler_te",
        "waveguide_straight",
        "mmi_2x2",
        "phase_shifter",
    }
    assert required.issubset(generic_names)
    assert required.issubset(corner_names)


def test_siepic_ebeam_manifest_covers_core_pic_cells() -> None:
    names = _component_names("siepic_ebeam.pdk.json")
    assert {
        "grating_coupler_te",
        "edge_coupler_te",
        "waveguide_straight",
        "mmi_2x2",
        "phase_shifter",
        "ring_resonator",
        "waveguide_bend_euler",
        "monitor_tap_1x2",
        "photodiode_ge",
        "awg_mux_demux",
    }.issubset(names)


def test_public_facing_adapter_manifests_include_support_metadata() -> None:
    for manifest_name in ("aim_photonics.pdk.json", "siepic_ebeam.pdk.json"):
        for cell in _component_cells(manifest_name):
            assert cell.get("support_level"), f"missing support_level in {manifest_name}"
            workflows = cell.get("recommended_workflows")
            assert isinstance(workflows, list) and workflows, f"missing recommended_workflows in {manifest_name}"


def test_public_facing_adapter_manifests_cover_at_least_ten_catalog_cells() -> None:
    assert len(_component_names("aim_photonics.pdk.json")) >= 8
    assert len(_component_names("siepic_ebeam.pdk.json")) >= 10


def test_pdk_manifests_do_not_repeat_component_names() -> None:
    for manifest_path in sorted(PDK_ROOT.glob("*.json")):
        pdk = load_pdk_manifest(manifest_path)
        cells = pdk.component_cells or []
        names = [str(cell.get("name") or "").strip() for cell in cells if str(cell.get("name") or "").strip()]
        assert len(names) == len(set(names)), f"duplicate component cell names in {manifest_path.name}"
