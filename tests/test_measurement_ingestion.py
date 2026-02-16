from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.measurements import ingest_measurement_bundle_file


def test_measurement_bundle_ingestion_copies_files_and_updates_index(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_demo" / "measurement_bundle.json"
    out = ingest_measurement_bundle_file(bundle_path, open_root=tmp_path)
    assert out.exists()

    target_dir = tmp_path / "meas_demo_001"
    assert (target_dir / "measurement_bundle.json").exists()
    assert (target_dir / "data" / "demo_measurements.csv").exists()

    index_path = tmp_path / "index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert any(str(r.get("dataset_id")) == "meas_demo_001" for r in index)


def test_measurement_bundle_ingestion_refuses_overwrite_by_default(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_demo" / "measurement_bundle.json"
    ingest_measurement_bundle_file(bundle_path, open_root=tmp_path)

    with pytest.raises(FileExistsError):
        ingest_measurement_bundle_file(bundle_path, open_root=tmp_path, overwrite=False)


def test_measurement_bundle_ingestion_pic_crosstalk_sweep_fixture(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_pic_crosstalk" / "measurement_bundle.json"
    out = ingest_measurement_bundle_file(bundle_path, open_root=tmp_path)
    assert out.exists()

    target_dir = tmp_path / "meas_pic_xt_synth_001"
    assert (target_dir / "measurement_bundle.json").exists()
    assert (target_dir / "data" / "pic_crosstalk_sweep.json").exists()
