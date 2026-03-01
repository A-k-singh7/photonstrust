from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from photonstrust.pdk import resolve_pdk_contract


def _schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pdk_manifest.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _manifest_from_contract(contract: dict, *, execution_mode: str) -> dict:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pdk_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": execution_mode,
        "source_run_id": None,
        "adapter": contract["adapter"],
        "request": contract["request"],
        "pdk": contract["pdk"],
        "capabilities": contract["capabilities"],
    }


def test_pdk_manifest_schema_builtin_contract() -> None:
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    manifest = _manifest_from_contract(contract, execution_mode="preview")
    validate(instance=manifest, schema=_schema())


def test_pdk_manifest_schema_manifest_based_contract() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "pdk" / "toy_pdk_manifest.json"
    contract = resolve_pdk_contract({"manifest_path": str(fixture_path)})
    manifest = _manifest_from_contract(contract, execution_mode="certification")
    validate(instance=manifest, schema=_schema())


def test_pdk_manifest_schema_allows_optional_layer_stack_and_component_cells() -> None:
    contract = resolve_pdk_contract({"name": "aim"})
    manifest = _manifest_from_contract(contract, execution_mode="preview")
    manifest["pdk"]["layer_stack"] = [
        {"name": "si_core", "gds_layer": 1, "gds_datatype": 0},
    ]
    manifest["pdk"]["component_cells"] = [
        {"name": "grating_coupler_te", "library": "aim", "cell": "GC_TE"},
    ]
    validate(instance=manifest, schema=_schema())


def test_pdk_manifest_schema_request_rejects_name_and_manifest_path_both_null() -> None:
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    manifest = _manifest_from_contract(contract, execution_mode="preview")
    manifest["request"] = {"name": None, "manifest_path": None}

    with pytest.raises(ValidationError):
        validate(instance=manifest, schema=_schema())
