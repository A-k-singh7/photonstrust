from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.klayout_artifact_pack import (
    build_klayout_run_artifact_pack,
    klayout_run_artifact_pack_schema_path,
)
from photonstrust.layout.pic.klayout_runner import find_klayout_exe


def test_klayout_artifact_pack_schema_validates_and_writes_pack(tmp_path: Path) -> None:
    dummy_gds = tmp_path / "dummy.gds"
    dummy_gds.write_bytes(b"PHOTONTRUST_DUMMY_GDS")

    out_dir = tmp_path / "klayout_pack"
    pack = build_klayout_run_artifact_pack(
        input_gds_path=dummy_gds,
        output_dir=out_dir,
        allow_missing_tool=True,
        timeout_s=5.0,
    )

    validate_instance(pack, klayout_run_artifact_pack_schema_path())

    pack_path = out_dir / "klayout_run_artifact_pack.json"
    assert pack_path.exists()
    disk = json.loads(pack_path.read_text(encoding="utf-8"))
    assert disk["schema_version"] == "0.1"
    assert disk["pack_id"] == pack["pack_id"]


def test_klayout_artifact_pack_optional_real_run(tmp_path: Path) -> None:
    exe = find_klayout_exe()
    if not exe:
        pytest.skip("KLayout executable not available (PATH or PHOTONTRUST_KLAYOUT_EXE)")

    try:
        import gdstk  # type: ignore
    except Exception:
        pytest.skip("gdstk not available; cannot generate a real GDS fixture for KLayout macro")

    # Generate a minimal GDS fixture with a PATH + one port label matching PhotonTrust conventions.
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("TOP")
    cell.add(gdstk.FlexPath([(0.0, 0.0), (100.0, 0.0)], 0.5, layer=1, datatype=0))
    cell.add(gdstk.Label("PTPORT:n1:out", (0.0, 0.0), layer=10, texttype=0))
    cell.add(gdstk.Label("PTPORT:n2:in", (100.0, 0.0), layer=10, texttype=0))

    gds_path = tmp_path / "fixture.gds"
    lib.write_gds(gds_path)

    out_dir = tmp_path / "klayout_pack_real"
    pack = build_klayout_run_artifact_pack(
        input_gds_path=gds_path,
        output_dir=out_dir,
        klayout_exe=exe,
        allow_missing_tool=False,
        timeout_s=30.0,
    )

    validate_instance(pack, klayout_run_artifact_pack_schema_path())
    assert pack["status"] in ("pass", "fail", "error")
    assert (out_dir / "drc_lite.json").exists() or pack["status"] == "skipped"
