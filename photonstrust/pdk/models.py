"""Typed models for runtime PDK loading and normalization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from photonstrust.pdk.adapters import default_pdk_capability_matrix


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_text_array(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value]


@dataclass(frozen=True)
class PDKRequest:
    name: str | None = None
    manifest_path: str | None = None

    @classmethod
    def from_values(cls, *, name: Any = None, manifest_path: Any = None) -> "PDKRequest":
        return cls(name=_coerce_optional_text(name), manifest_path=_coerce_optional_text(manifest_path))

    def to_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "manifest_path": self.manifest_path}


@dataclass(frozen=True)
class PDKIdentity:
    name: str
    version: str
    design_rules: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PDKIdentity":
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("PDK manifest missing required field: name")
        version = str(payload.get("version", "0")).strip() or "0"
        rules = payload.get("design_rules")
        if rules is None:
            rules = {}
        if not isinstance(rules, Mapping):
            raise ValueError("PDK manifest design_rules must be an object")
        notes = _coerce_text_array(payload.get("notes"))
        return cls(name=name, version=version, design_rules=dict(rules), notes=notes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "design_rules": dict(self.design_rules),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PDKCapabilities:
    supports_layout: bool
    supports_performance_drc: bool
    supports_lvs_lite_signoff: bool
    supports_spice_export: bool

    @classmethod
    def from_mapping(cls, payload: Any) -> "PDKCapabilities":
        defaults = default_pdk_capability_matrix()
        raw = payload if isinstance(payload, Mapping) else {}
        return cls(
            supports_layout=bool(raw.get("supports_layout", defaults["supports_layout"])),
            supports_performance_drc=bool(
                raw.get("supports_performance_drc", defaults["supports_performance_drc"])
            ),
            supports_lvs_lite_signoff=bool(
                raw.get("supports_lvs_lite_signoff", defaults["supports_lvs_lite_signoff"])
            ),
            supports_spice_export=bool(raw.get("supports_spice_export", defaults["supports_spice_export"])),
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "supports_layout": self.supports_layout,
            "supports_performance_drc": self.supports_performance_drc,
            "supports_lvs_lite_signoff": self.supports_lvs_lite_signoff,
            "supports_spice_export": self.supports_spice_export,
        }


@dataclass(frozen=True)
class PDKLayer:
    name: str
    gds_layer: int | None = None
    gds_datatype: int | None = None
    material: str | None = None
    thickness_um: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, fallback_name: str) -> "PDKLayer":
        name = _coerce_optional_text(payload.get("name")) or fallback_name
        metadata = dict(payload)
        for key in ("name", "gds_layer", "gds_datatype", "material", "thickness_um"):
            metadata.pop(key, None)
        gds_layer = payload.get("gds_layer")
        gds_datatype = payload.get("gds_datatype")
        thickness_um = payload.get("thickness_um")
        return cls(
            name=name,
            gds_layer=int(gds_layer) if isinstance(gds_layer, int) else None,
            gds_datatype=int(gds_datatype) if isinstance(gds_datatype, int) else None,
            material=_coerce_optional_text(payload.get("material")),
            thickness_um=float(thickness_um)
            if isinstance(thickness_um, (int, float)) and not isinstance(thickness_um, bool)
            else None,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name}
        if self.gds_layer is not None:
            out["gds_layer"] = self.gds_layer
        if self.gds_datatype is not None:
            out["gds_datatype"] = self.gds_datatype
        if self.material is not None:
            out["material"] = self.material
        if self.thickness_um is not None:
            out["thickness_um"] = self.thickness_um
        out.update(self.metadata)
        return out


@dataclass(frozen=True)
class PDKComponentCell:
    name: str
    library: str | None = None
    cell: str | None = None
    ports: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, fallback_name: str) -> "PDKComponentCell":
        name = _coerce_optional_text(payload.get("name")) or fallback_name
        metadata = dict(payload)
        for key in ("name", "library", "cell", "ports"):
            metadata.pop(key, None)
        return cls(
            name=name,
            library=_coerce_optional_text(payload.get("library")),
            cell=_coerce_optional_text(payload.get("cell")),
            ports=_coerce_text_array(payload.get("ports")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name}
        if self.library is not None:
            out["library"] = self.library
        if self.cell is not None:
            out["cell"] = self.cell
        if self.ports:
            out["ports"] = list(self.ports)
        out.update(self.metadata)
        return out


@dataclass(frozen=True)
class PDKInteropTarget:
    enabled: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Any) -> "PDKInteropTarget | None":
        if not isinstance(payload, Mapping):
            return None
        enabled_raw = payload.get("enabled")
        enabled = bool(enabled_raw) if isinstance(enabled_raw, bool) else None
        details = dict(payload)
        details.pop("enabled", None)
        return cls(enabled=enabled, details=details)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.details)
        if self.enabled is not None:
            out["enabled"] = self.enabled
        return out


@dataclass(frozen=True)
class PDKInterop:
    siepic: PDKInteropTarget | None = None
    aim: PDKInteropTarget | None = None

    @classmethod
    def from_mapping(cls, payload: Any) -> "PDKInterop | None":
        if not isinstance(payload, Mapping):
            return None
        siepic = PDKInteropTarget.from_mapping(payload.get("siepic"))
        aim = PDKInteropTarget.from_mapping(payload.get("aim"))
        if siepic is None and aim is None:
            return None
        return cls(siepic=siepic, aim=aim)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.siepic is not None:
            out["siepic"] = self.siepic.to_dict()
        if self.aim is not None:
            out["aim"] = self.aim.to_dict()
        return out


@dataclass(frozen=True)
class LoadedPDK:
    request: PDKRequest
    identity: PDKIdentity
    capabilities: PDKCapabilities
    layer_stack: list[PDKLayer] = field(default_factory=list)
    component_cells: list[PDKComponentCell] = field(default_factory=list)
    interop: PDKInterop | None = None
    source_manifest: Path | None = None

    @classmethod
    def from_manifest(
        cls,
        payload: Mapping[str, Any],
        *,
        request: PDKRequest,
        source_manifest: Path | None = None,
    ) -> "LoadedPDK":
        identity = PDKIdentity.from_mapping(payload)
        capabilities = PDKCapabilities.from_mapping(payload.get("capabilities"))

        layers: list[PDKLayer] = []
        raw_layers = payload.get("layer_stack")
        if isinstance(raw_layers, list):
            for idx, raw in enumerate(raw_layers):
                if isinstance(raw, Mapping):
                    layers.append(PDKLayer.from_mapping(raw, fallback_name=f"layer_{idx}"))

        cells: list[PDKComponentCell] = []
        raw_cells = payload.get("component_cells")
        if isinstance(raw_cells, list):
            for idx, raw in enumerate(raw_cells):
                if isinstance(raw, Mapping):
                    cells.append(PDKComponentCell.from_mapping(raw, fallback_name=f"cell_{idx}"))
        elif isinstance(raw_cells, Mapping):
            for idx, (name_hint, raw) in enumerate(raw_cells.items()):
                fallback_name = _coerce_optional_text(name_hint) or f"cell_{idx}"
                if isinstance(raw, Mapping):
                    raw_mapping = dict(raw)
                    raw_mapping.setdefault("name", fallback_name)
                    cells.append(PDKComponentCell.from_mapping(raw_mapping, fallback_name=fallback_name))
                elif isinstance(raw, str):
                    cells.append(
                        PDKComponentCell.from_mapping(
                            {"name": fallback_name, "cell": raw},
                            fallback_name=fallback_name,
                        )
                    )

        interop = PDKInterop.from_mapping(payload.get("interop"))

        return cls(
            request=request,
            identity=identity,
            capabilities=capabilities,
            layer_stack=layers,
            component_cells=cells,
            interop=interop,
            source_manifest=source_manifest,
        )

    def pdk_payload(self, *, include_optional: bool = True) -> dict[str, Any]:
        payload = self.identity.to_dict()
        if include_optional:
            if self.layer_stack:
                payload["layer_stack"] = [layer.to_dict() for layer in self.layer_stack]
            if self.component_cells:
                payload["component_cells"] = [cell.to_dict() for cell in self.component_cells]
            if self.interop is not None:
                interop_payload = self.interop.to_dict()
                if interop_payload:
                    payload["interop"] = interop_payload
        return payload

    def capabilities_payload(self) -> dict[str, bool]:
        return self.capabilities.to_dict()


__all__ = [
    "LoadedPDK",
    "PDKCapabilities",
    "PDKComponentCell",
    "PDKIdentity",
    "PDKInterop",
    "PDKInteropTarget",
    "PDKLayer",
    "PDKRequest",
]
