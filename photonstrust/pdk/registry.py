"""PDK registry and loader helpers (v0).

The goal is to keep this small but useful:
- Built-in "generic" PDK for demos and tests.
- Ability to load a private PDK manifest from disk (JSON).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from photonstrust.pdk.adapters import (
    PDKAdapterContract,
    PDKPayloadResolver,
    default_pdk_capability_matrix,
    validate_pdk_adapter_contract,
)


@dataclass(frozen=True)
class PDK:
    name: str
    version: str
    design_rules: dict[str, Any]
    notes: list[str]


def get_pdk(name: str | None) -> PDK:
    """Return a built-in PDK by name (or a default)."""

    n = str(name or "").strip().lower()
    if not n:
        n = "generic_silicon_photonics"

    if n in {"generic", "generic_silicon_photonics", "generic_sip"}:
        return PDK(
            name="generic_silicon_photonics",
            version="0",
            design_rules={
                # Keep these conservative; real PDKs should override via manifest.
                "min_waveguide_width_um": 0.45,
                "min_waveguide_gap_um": 0.20,
                "min_bend_radius_um": 5.0,
            },
            notes=[
                "Built-in demo PDK. Replace with a foundry PDK manifest for real tapeout workflows.",
            ],
        )

    raise KeyError(f"Unknown built-in PDK: {name!r}")


def load_pdk_manifest(path: str | Path) -> PDK:
    """Load a PDK manifest from a JSON file."""

    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("PDK manifest must be a JSON object")

    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("PDK manifest missing required field: name")
    version = str(data.get("version", "0")).strip() or "0"
    rules = data.get("design_rules", {}) or {}
    if not isinstance(rules, dict):
        raise ValueError("PDK manifest design_rules must be an object")
    notes = data.get("notes", []) or []
    if not isinstance(notes, list):
        notes = []
    notes_s = [str(n) for n in notes]

    return PDK(name=name, version=version, design_rules=rules, notes=notes_s)


def _manifest_capabilities(path: str | Path) -> dict[str, bool]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return default_pdk_capability_matrix()
    raw_caps = data.get("capabilities")
    defaults = default_pdk_capability_matrix()
    if not isinstance(raw_caps, dict):
        return defaults
    out = dict(defaults)
    for key in defaults.keys():
        if key in raw_caps:
            out[key] = bool(raw_caps[key])
    return out


class RegistryPDKAdapter(PDKPayloadResolver):
    """Adapter implementation backed by built-in/manifest PDK registry."""

    def resolve(self, pdk_request: Mapping[str, Any] | None) -> PDKAdapterContract:
        if pdk_request is None:
            pdk_request = {}
        if not isinstance(pdk_request, Mapping):
            raise TypeError("pdk_request must be an object")

        name_raw = pdk_request.get("name")
        manifest_path_raw = pdk_request.get("manifest_path")

        name = str(name_raw).strip() if name_raw is not None else None
        manifest_path = str(manifest_path_raw).strip() if manifest_path_raw is not None else None

        if name == "":
            name = None
        if manifest_path == "":
            manifest_path = None

        if manifest_path is not None:
            pdk = load_pdk_manifest(manifest_path)
            capabilities = _manifest_capabilities(manifest_path)
        else:
            pdk = get_pdk(name)
            capabilities = default_pdk_capability_matrix()

        return validate_pdk_adapter_contract(
            {
                "schema_version": "0",
                "adapter": "registry.v0",
                "request": {
                    "name": name,
                    "manifest_path": manifest_path,
                },
                "pdk": {
                    "name": pdk.name,
                    "version": pdk.version,
                    "design_rules": dict(pdk.design_rules or {}),
                    "notes": list(pdk.notes or []),
                },
                "capabilities": capabilities,
            }
        )


def resolve_pdk_contract(pdk_request: Mapping[str, Any] | None) -> PDKAdapterContract:
    """Resolve a normalized PDK adapter contract.

    Accepted request forms:
      - {"name": "generic_silicon_photonics"}
      - {"manifest_path": "/path/to/manifest.json"}
    """

    adapter = RegistryPDKAdapter()
    return adapter.resolve(pdk_request)


def pdk_capability_matrix(pdk_requests: Iterable[Mapping[str, Any] | None]) -> list[dict[str, Any]]:
    """Resolve many requests and return their capability matrix rows."""

    rows: list[dict[str, Any]] = []
    for req in pdk_requests:
        contract = resolve_pdk_contract(req)
        rows.append(
            {
                "request": dict(contract["request"]),
                "name": contract["pdk"]["name"],
                "version": contract["pdk"]["version"],
                "capabilities": dict(contract["capabilities"]),
            }
        )
    return rows
