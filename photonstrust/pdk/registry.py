"""PDK registry facade backed by runtime PDK loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from photonstrust.pdk.adapters import (
    PDKAdapterContract,
    PDKPayloadResolver,
    validate_pdk_adapter_contract,
)
from photonstrust.pdk.models import LoadedPDK


@dataclass(frozen=True)
class PDK:
    name: str
    version: str
    design_rules: dict[str, Any]
    notes: list[str]
    layer_stack: list[dict[str, Any]] | None = None
    component_cells: list[dict[str, Any]] | None = None
    interop: dict[str, Any] | None = None
    process_corners: dict[str, Any] | None = None
    sensitivity_coefficients: dict[str, Any] | None = None

    def to_payload(self, *, include_optional: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "design_rules": dict(self.design_rules or {}),
            "notes": list(self.notes or []),
        }
        if include_optional:
            if self.layer_stack:
                payload["layer_stack"] = [dict(layer) for layer in self.layer_stack]
            if self.component_cells:
                payload["component_cells"] = [dict(cell) for cell in self.component_cells]
            if self.interop:
                payload["interop"] = dict(self.interop)
            if self.process_corners is not None:
                payload["process_corners"] = dict(self.process_corners)
            if self.sensitivity_coefficients is not None:
                payload["sensitivity_coefficients"] = dict(self.sensitivity_coefficients)
        return payload

def _to_registry_pdk(loaded: LoadedPDK) -> PDK:
    layer_stack = [layer.to_dict() for layer in loaded.layer_stack] or None
    component_cells = [cell.to_dict() for cell in loaded.component_cells] or None
    interop = loaded.interop.to_dict() if loaded.interop is not None else None
    if interop == {}:
        interop = None
    return PDK(
        name=loaded.identity.name,
        version=loaded.identity.version,
        design_rules=dict(loaded.identity.design_rules),
        notes=list(loaded.identity.notes),
        layer_stack=layer_stack,
        component_cells=component_cells,
        interop=interop,
        process_corners=(
            dict(loaded.identity.process_corners)
            if loaded.identity.process_corners is not None
            else None
        ),
        sensitivity_coefficients=(
            dict(loaded.identity.sensitivity_coefficients)
            if loaded.identity.sensitivity_coefficients is not None
            else None
        ),
    )


def _runtime_load_pdk(*, name: str | None, manifest_path: str | None) -> LoadedPDK:
    # Lazily import runtime loader to avoid package-level circular import edges.
    from photonstrust.pic.pdk_loader import load_pdk

    return load_pdk(name=name, manifest_path=manifest_path)


def get_pdk(name: str | None) -> PDK:
    """Return a PDK by name, including alias and runtime-config resolution."""

    loaded = _runtime_load_pdk(name=name, manifest_path=None)
    return _to_registry_pdk(loaded)


def load_pdk_manifest(path: str | Path) -> PDK:
    """Load a PDK manifest from a JSON file."""

    loaded = _runtime_load_pdk(name=None, manifest_path=str(path))
    return _to_registry_pdk(loaded)


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

        loaded = _runtime_load_pdk(name=name, manifest_path=manifest_path)
        pdk = _to_registry_pdk(loaded)
        capabilities = loaded.capabilities_payload()

        return validate_pdk_adapter_contract(
            {
                "schema_version": "0",
                "adapter": "registry.v0",
                "request": {
                    "name": name,
                    "manifest_path": manifest_path,
                },
                "pdk": pdk.to_payload(include_optional=False),
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
