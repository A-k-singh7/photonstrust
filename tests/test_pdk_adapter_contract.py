from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.pdk import pdk_capability_matrix, resolve_pdk_contract, validate_pdk_adapter_contract


def _toy_manifest_path() -> Path:
    return Path(__file__).parent / "fixtures" / "pdk" / "toy_pdk_manifest.json"


def _contract_schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pdk_adapter_contract.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_resolve_pdk_contract_by_name_validates_against_schema():
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    validate(instance=contract, schema=_contract_schema())

    assert contract["pdk"]["name"] == "generic_silicon_photonics"
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
