"""Backward-compatibility bridge from catalog to legacy preset API."""

from __future__ import annotations

from photonstrust.catalog.store import ComponentCatalog

_catalog: ComponentCatalog | None = None


def _get_catalog() -> ComponentCatalog:
    global _catalog
    if _catalog is None:
        _catalog = ComponentCatalog()
    return _catalog


def get_band_preset(band: str) -> dict:
    """Drop-in replacement for ``presets.get_band_preset()``.

    Looks up band entries in the catalog by matching component_id to the band
    key.  Falls back to the legacy presets module if not found in catalog.
    """
    cat = _get_catalog()
    try:
        entry = cat.get(band)
        return dict(entry.params)
    except KeyError:
        from photonstrust.presets import get_band_preset as _legacy
        return _legacy(band)


def get_detector_preset(detector_class: str, band: str | None = None) -> dict:
    """Drop-in replacement for ``presets.get_detector_preset()``.

    Looks up by ``generic_<detector_class>`` in the catalog.  Falls back to the
    legacy presets module if not found.  Band adjustments are applied the same
    way as the legacy code.
    """
    cat = _get_catalog()
    catalog_id = f"generic_{detector_class}"
    try:
        entry = cat.get(catalog_id)
        preset = dict(entry.params)
    except KeyError:
        from photonstrust.presets import get_detector_preset as _legacy
        return _legacy(detector_class, band)

    if band:
        from photonstrust.presets import DETECTOR_ADJUSTMENTS
        band_adjustments = DETECTOR_ADJUSTMENTS.get(band, {})
        adj = band_adjustments.get(detector_class)
        if adj:
            preset["pde"] = max(0.0, min(1.0, preset["pde"] + adj.get("pde_delta", 0.0)))
            preset["dark_counts_cps"] *= adj.get("dark_scale", 1.0)
    return preset
