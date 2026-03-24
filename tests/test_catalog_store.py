"""Tests for the component catalog store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.catalog.store import ComponentCatalog
from photonstrust.catalog.types import ComponentEntry


def _write_entry(base: Path, category: str, component_id: str, **extra) -> Path:
    d = base / category
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "component_id": component_id,
        "category": category,
        "subcategory": extra.get("subcategory", ""),
        "vendor": extra.get("vendor"),
        "model": extra.get("model"),
        "version": "1.0",
        "params": extra.get("params", {"pde": 0.5}),
        "tags": extra.get("tags", []),
        "notes": extra.get("notes", ""),
    }
    p = d / f"{component_id}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_builtin_entries_load():
    cat = ComponentCatalog()
    entries = cat.all_entries()
    assert len(entries) >= 7
    ids = {e.component_id for e in entries}
    assert "generic_snspd" in ids
    assert "generic_ingaas" in ids
    assert "generic_si_apd" in ids
    assert "c_1550" in ids
    assert "o_1310" in ids
    assert "nir_850" in ids
    assert "nir_795" in ids


def test_get_by_id():
    cat = ComponentCatalog()
    entry = cat.get("generic_snspd")
    assert entry.category == "detector"
    assert entry.subcategory == "snspd"
    assert entry.params["pde"] == 0.30


def test_get_missing_raises():
    cat = ComponentCatalog()
    with pytest.raises(KeyError, match="nonexistent"):
        cat.get("nonexistent")


def test_search_by_category():
    cat = ComponentCatalog()
    result = cat.search(category="detector")
    assert result.total_count == 3
    assert all(e.category == "detector" for e in result.matches)


def test_search_by_subcategory():
    cat = ComponentCatalog()
    result = cat.search(subcategory="nir")
    assert result.total_count == 2


def test_search_by_tags():
    cat = ComponentCatalog()
    result = cat.search(tags=["telecom"])
    assert result.total_count >= 2


def test_text_search():
    cat = ComponentCatalog()
    result = cat.search(text_query="snspd")
    assert result.total_count >= 1
    assert any(e.component_id == "generic_snspd" for e in result.matches)


def test_list_categories():
    cat = ComponentCatalog()
    cats = cat.list_categories()
    assert "detector" in cats
    assert "band" in cats


def test_add_user_entry(tmp_path):
    cat = ComponentCatalog(user_dir=tmp_path)
    entry = ComponentEntry(
        component_id="test_custom_det",
        category="detector",
        subcategory="snspd",
        vendor="TestVendor",
        model="TV-100",
        version="1.0",
        params={"pde": 0.90, "dark_counts_cps": 5},
        tags=("snspd", "custom"),
    )
    path = cat.add_entry(entry, catalog_dir=tmp_path)
    assert path.exists()
    retrieved = cat.get("test_custom_det")
    assert retrieved.vendor == "TestVendor"
    assert retrieved.params["pde"] == 0.90


def test_user_dir_entries(tmp_path):
    _write_entry(tmp_path, "source", "custom_source", subcategory="spdc",
                 params={"rep_rate_mhz": 80}, tags=["custom"])
    cat = ComponentCatalog(user_dir=tmp_path)
    entry = cat.get("custom_source")
    assert entry.category == "source"
    assert entry.params["rep_rate_mhz"] == 80


def test_search_limit():
    cat = ComponentCatalog()
    result = cat.search(limit=2)
    assert len(result.matches) <= 2
    assert result.total_count >= 7


def test_entry_round_trip():
    entry = ComponentEntry(
        component_id="rt_test",
        category="detector",
        subcategory="snspd",
        vendor="Acme",
        model="X1",
        version="2.0",
        params={"pde": 0.85},
        tags=("snspd",),
        notes="round-trip test",
    )
    d = entry.as_dict()
    restored = ComponentEntry.from_dict(d)
    assert restored.component_id == entry.component_id
    assert restored.params == entry.params
    assert restored.tags == entry.tags


def test_backward_compat_preset_bridge():
    from photonstrust.catalog.compat import get_band_preset, get_detector_preset

    band = get_band_preset("c_1550")
    assert band["wavelength_nm"] == 1550
    assert band["fiber_loss_db_per_km"] == 0.20

    det = get_detector_preset("snspd")
    assert det["pde"] == 0.30
    assert det["dark_counts_cps"] == 100

    det_adj = get_detector_preset("snspd", band="c_1550")
    assert det_adj["pde"] == pytest.approx(0.35)
