from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.pdk import (
    get_pdk,
    load_pdk_manifest,
    pdk_capability_matrix,
    resolve_pdk_contract,
    validate_pdk_adapter_contract,
)


def _toy_manifest_path() -> Path:
    return Path(__file__).parent / "fixtures" / "pdk" / "toy_pdk_manifest.json"


def _contract_schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pdk_adapter_contract.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_resolve_pdk_contract_by_name_validates_against_schema():
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    validate(instance=contract, schema=_contract_schema())

    assert contract["pdk"]["name"] == "generic_silicon_photonics"
    assert contract["pdk"]["version"] == "0.1"
    assert contract["request"]["name"] == "generic_silicon_photonics"
    assert contract["request"]["manifest_path"] is None
    assert contract["capabilities"]["supports_layout"] is True


def test_resolve_pdk_contract_by_manifest_path_uses_fixture_capabilities():
    manifest_path = _toy_manifest_path()
    contract = resolve_pdk_contract({"manifest_path": str(manifest_path)})
    validate(instance=contract, schema=_contract_schema())

    assert contract["pdk"]["name"] == "toy_pdk"
    assert contract["request"]["name"] is None
    assert contract["request"]["manifest_path"] == str(manifest_path)
    assert contract["capabilities"]["supports_lvs_lite_signoff"] is False
    assert contract["capabilities"]["supports_spice_export"] is False


def test_resolve_pdk_contract_prefers_manifest_path_over_name(tmp_path: Path):
    manifest_path = tmp_path / "override_manifest.json"
    manifest_payload = {
        "name": "override_pdk",
        "version": "42",
        "design_rules": {"min_waveguide_width_um": 0.33},
        "notes": ["manifest path should win over name"],
        "capabilities": {
            "supports_layout": True,
            "supports_performance_drc": True,
            "supports_lvs_lite_signoff": False,
            "supports_spice_export": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

    contract = resolve_pdk_contract({"name": "aim", "manifest_path": str(manifest_path)})
    validate(instance=contract, schema=_contract_schema())

    assert contract["request"]["name"] == "aim"
    assert contract["request"]["manifest_path"] == str(manifest_path)
    assert contract["pdk"]["name"] == "override_pdk"
    assert contract["pdk"]["version"] == "42"
    assert contract["capabilities"]["supports_lvs_lite_signoff"] is False
    assert contract["capabilities"]["supports_spice_export"] is False


def test_pdk_capability_matrix_mixed_requests():
    rows = pdk_capability_matrix(
        [
            {"name": "generic_silicon_photonics"},
            {"manifest_path": str(_toy_manifest_path())},
        ]
    )

    assert len(rows) == 2
    assert rows[0]["name"] == "generic_silicon_photonics"
    assert rows[1]["name"] == "toy_pdk"
    assert rows[1]["capabilities"]["supports_spice_export"] is False


def test_resolve_pdk_contract_supports_aim_alias_names():
    contract = resolve_pdk_contract({"name": "aim"})
    validate(instance=contract, schema=_contract_schema())

    assert contract["request"]["name"] == "aim"
    assert contract["request"]["manifest_path"] is None
    assert contract["pdk"]["name"] == "aim_photonics"
    assert contract["capabilities"]["supports_lvs_lite_signoff"] is True


@pytest.mark.parametrize("alias_name", ["siepic", "ebeam"])
def test_resolve_pdk_contract_supports_siepic_alias_names(alias_name: str):
    contract = resolve_pdk_contract({"name": alias_name})
    validate(instance=contract, schema=_contract_schema())

    assert contract["request"]["name"] == alias_name
    assert contract["request"]["manifest_path"] is None
    assert contract["pdk"]["name"] == "generic_silicon_photonics"
    assert contract["pdk"]["version"] == "0.1"


def test_get_pdk_alias_includes_richer_optional_payload():
    pdk = get_pdk("aim_photonics")

    assert pdk.name == "aim_photonics"
    assert isinstance(pdk.layer_stack, list) and len(pdk.layer_stack) >= 1
    assert isinstance(pdk.component_cells, list) and len(pdk.component_cells) >= 1
    assert isinstance(pdk.interop, dict) and "aim" in pdk.interop


def test_resolve_pdk_contract_from_runtime_config_manifest_path():
    manifest_path = Path("configs") / "pdks" / "aim_photonics.pdk.json"
    contract = resolve_pdk_contract({"manifest_path": str(manifest_path)})
    validate(instance=contract, schema=_contract_schema())

    assert contract["pdk"]["name"] == "aim_photonics"
    assert contract["request"]["name"] is None
    assert contract["request"]["manifest_path"] == str(manifest_path)


def test_load_pdk_manifest_accepts_component_cells_dict(tmp_path: Path):
    manifest_path = tmp_path / "dict_cells_manifest.json"
    manifest_payload = {
        "name": "dict_cells_pdk",
        "version": "1",
        "design_rules": {"min_waveguide_width_um": 0.40},
        "notes": ["component cells defined as object map"],
        "component_cells": {
            "grating_coupler_te": {
                "library": "siepic",
                "cell": "GC_TE",
                "ports": ["o1", "o2"],
            },
            "mmi_2x2": "MMI_2X2",
        },
    }
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

    pdk = load_pdk_manifest(manifest_path)

    assert pdk.component_cells is not None
    assert [cell["name"] for cell in pdk.component_cells] == ["grating_coupler_te", "mmi_2x2"]
    assert pdk.component_cells[0]["library"] == "siepic"
    assert pdk.component_cells[0]["cell"] == "GC_TE"
    assert pdk.component_cells[1]["cell"] == "MMI_2X2"


@pytest.mark.parametrize(
    ("first_import", "second_import"),
    [
        ("photonstrust.pic.pdk_loader", "photonstrust.pdk.registry"),
        ("photonstrust.pdk.registry", "photonstrust.pic.pdk_loader"),
    ],
)
def test_pdk_loader_and_registry_import_order_is_safe(
    first_import: str,
    second_import: str,
):
    repo_root = Path(__file__).resolve().parents[1]
    script = (
        f"import importlib; "
        f"importlib.import_module({first_import!r}); "
        f"importlib.import_module({second_import!r}); "
        "from photonstrust.pic.pdk_loader import load_pdk; "
        "from photonstrust.pdk.registry import get_pdk; "
        "assert load_pdk('generic').identity.name == 'generic_silicon_photonics'; "
        "assert get_pdk('aim').name == 'aim_photonics'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"import order failed: {first_import} -> {second_import}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert result.stdout.strip() == "ok"


def test_validate_pdk_adapter_contract_rejects_missing_pdk_name():
    with pytest.raises(ValueError, match="pdk missing required field: name"):
        validate_pdk_adapter_contract(
            {
                "schema_version": "0",
                "adapter": "registry.v0",
                "request": {"name": "generic_silicon_photonics", "manifest_path": None},
                "pdk": {"version": "0", "design_rules": {}, "notes": []},
                "capabilities": {
                    "supports_layout": True,
                    "supports_performance_drc": True,
                    "supports_lvs_lite_signoff": True,
                    "supports_spice_export": True,
                },
            }
        )


def test_validate_pdk_adapter_contract_rejects_non_bool_capability():
    with pytest.raises(ValueError, match="capabilities.supports_layout"):
        validate_pdk_adapter_contract(
            {
                "schema_version": "0",
                "adapter": "registry.v0",
                "request": {"name": "generic_silicon_photonics", "manifest_path": None},
                "pdk": {
                    "name": "generic_silicon_photonics",
                    "version": "0",
                    "design_rules": {},
                    "notes": [],
                },
                "capabilities": {
                    "supports_layout": "yes",
                    "supports_performance_drc": True,
                    "supports_lvs_lite_signoff": True,
                    "supports_spice_export": True,
                },
            }
        )
