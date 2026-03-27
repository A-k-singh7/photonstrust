"""Runtime PDK loader with aliasing and config-manifest precedence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from photonstrust.pdk.models import LoadedPDK, PDKRequest


DEFAULT_PDK_NAME = "generic_silicon_photonics"

_PDK_NAME_ALIASES: dict[str, str] = {
    "generic": "generic_silicon_photonics",
    "generic_silicon_photonics": "generic_silicon_photonics",
    "generic_sip": "generic_silicon_photonics",
    "generic_sip_corners": "generic_sip_corners",
    "siepic": "siepic_ebeam",
    "ebeam": "siepic_ebeam",
    "siepic_ebeam": "siepic_ebeam",
    "aim": "aim_photonics",
    "aim_photonics": "aim_photonics",
    "aim_300nm_sin": "aim_photonics_300nm_sin",
    "aim_photonics_300nm_sin": "aim_photonics_300nm_sin",
    "imec": "imec_isipp50g",
    "imec_isipp50g": "imec_isipp50g",
    "isipp50g": "imec_isipp50g",
    "ligentec": "ligentec_an800",
    "ligentec_an800": "ligentec_an800",
    "an800": "ligentec_an800",
    "gf_45clo": "gf_45clo",
    "gf45clo": "gf_45clo",
    "globalfoundries_45clo": "gf_45clo",
    "lionix": "lionix_triplex",
    "lionix_triplex": "lionix_triplex",
    "triplex": "lionix_triplex",
}

_BUILTIN_PDK_MANIFESTS: dict[str, dict[str, Any]] = {
    "generic_silicon_photonics": {
        "name": "generic_silicon_photonics",
        "version": "0",
        "design_rules": {
            "min_waveguide_width_um": 0.45,
            "min_waveguide_gap_um": 0.20,
            "min_bend_radius_um": 5.0,
        },
        "notes": [
            "Built-in demo PDK. Replace with a foundry PDK manifest for real tapeout workflows.",
        ],
    },
    "aim_photonics": {
        "name": "aim_photonics",
        "version": "0",
        "design_rules": {
            "min_waveguide_width_um": 0.50,
            "min_waveguide_gap_um": 0.25,
            "min_bend_radius_um": 10.0,
        },
        "notes": [
            "Built-in AIM-compatible fallback profile. Prefer runtime manifest configs for production use.",
        ],
        "interop": {
            "aim": {"enabled": True, "profile": "builtin_fallback"},
        },
    },
}


def normalize_pdk_name(name: str | None) -> str:
    raw = str(name or "").strip().lower()
    if not raw:
        return DEFAULT_PDK_NAME
    return _PDK_NAME_ALIASES.get(raw, raw)


def _repo_root() -> Path:
    # .../photonstrust/photonstrust/pic/pdk_loader.py -> repo root is two levels up from package root.
    return Path(__file__).resolve().parents[2]


def config_manifest_path_for_name(name: str) -> Path:
    canonical_name = normalize_pdk_name(name)
    return _repo_root() / "configs" / "pdks" / f"{canonical_name}.pdk.json"


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("PDK manifest must be a JSON object")
    return dict(payload)


def _load_from_manifest_path(
    path: Path,
    *,
    request: "PDKRequest",
) -> "LoadedPDK":
    from photonstrust.pdk.models import LoadedPDK

    payload = _read_manifest(path)
    return LoadedPDK.from_manifest(payload, request=request, source_manifest=path.resolve())


def _load_builtin(name: str, *, requested_name: str | None) -> "LoadedPDK":
    from photonstrust.pdk.models import LoadedPDK, PDKRequest

    payload = _BUILTIN_PDK_MANIFESTS.get(name)
    if payload is None:
        if requested_name is not None:
            raise KeyError(f"Unknown built-in PDK: {requested_name!r}")
        payload = _BUILTIN_PDK_MANIFESTS[DEFAULT_PDK_NAME]
        name = DEFAULT_PDK_NAME

    request_name = normalize_pdk_name(requested_name) if requested_name is not None else name
    request = PDKRequest(name=request_name, manifest_path=None)
    return LoadedPDK.from_manifest(payload, request=request, source_manifest=None)


def load_pdk(name: str | None = None, manifest_path: str | None = None) -> LoadedPDK:
    """Load a PDK using precedence: manifest_path > name > configs/pdks/<name> > built-in."""

    from photonstrust.pdk.models import PDKRequest

    request = PDKRequest.from_values(name=name, manifest_path=manifest_path)
    if request.manifest_path is not None:
        return _load_from_manifest_path(Path(request.manifest_path), request=request)

    requested_name = request.name
    canonical_name = normalize_pdk_name(requested_name)
    config_manifest = config_manifest_path_for_name(canonical_name)
    if config_manifest.exists():
        cfg_request = PDKRequest(name=canonical_name, manifest_path=None)
        return _load_from_manifest_path(config_manifest, request=cfg_request)

    return _load_builtin(canonical_name, requested_name=requested_name)


__all__ = [
    "DEFAULT_PDK_NAME",
    "config_manifest_path_for_name",
    "load_pdk",
    "normalize_pdk_name",
]
