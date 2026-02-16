from __future__ import annotations

from pathlib import Path

import pytest

from photonstrust.layout.gds_extract import OptionalDependencyError, extract_routes_from_gds


def test_gds_extract_requires_optional_dep(tmp_path: Path):
    # gdstk is optional; in the minimal CI environment this should raise a clear error.
    try:
        import gdstk  # noqa: F401
        pytest.skip("gdstk is installed; this test covers the missing-dep path")
    except ImportError:
        pass
    with pytest.raises(OptionalDependencyError, match="gdstk"):
        extract_routes_from_gds(tmp_path / "dummy.gds")


def test_gds_extract_roundtrip_when_gdstk_available(tmp_path: Path):
    gdstk = pytest.importorskip("gdstk")

    # Create a minimal GDS with 2 parallel horizontal FlexPaths (width=0.5 um, sep=1.0 um).
    # Note: gdstk converts FlexPaths to boundary (polygon) records on GDS
    # round-trip, so include_rectangles=True is needed to recover them.
    cell = gdstk.Cell("TOP")
    cell.add(
        gdstk.FlexPath([(0, 0), (100, 0)], 0.5, layer=1, datatype=0),
        gdstk.FlexPath([(0, 1), (100, 1)], 0.5, layer=1, datatype=0),
    )
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    lib.add(cell)

    gds_path = tmp_path / "demo.gds"
    lib.write_gds(gds_path)

    routes, stats = extract_routes_from_gds(gds_path, filter_layers=[(1, 0)], include_rectangles=True)
    assert stats.routes == 2
    assert len(routes) == 2
    assert all(r.get("width_um") == 0.5 for r in routes)

