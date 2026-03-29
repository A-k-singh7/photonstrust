from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import validate

from photonstrust.benchmarks.open_benchmarks import check_bundle_file
from photonstrust.benchmarks.repro_pack import generate_repro_pack


def test_generate_repro_pack_creates_expected_files(tmp_path: Path):
    cfg = {
        "scenario": {"id": "repro_demo", "distance_km": {"start": 0.0, "stop": 10.0, "step": 10.0}, "band": "c_1550", "wavelength_nm": 1550},
        "source": {"type": "emitter_cavity", "physics_backend": "analytic"},
        "channel": {"fiber_loss_db_per_km": 0.2, "connector_loss_db": 1.5, "dispersion_ps_per_km": 5.0},
        "detector": {"class": "snspd"},
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    pack_dir = tmp_path / "pack"
    generate_repro_pack(config_path, pack_dir)

    assert (pack_dir / "README.md").exists()
    assert (pack_dir / "config.yml").exists()
    assert (pack_dir / "benchmark_bundle.json").exists()
    assert (pack_dir / "repro_pack_manifest.json").exists()
    assert (pack_dir / "env" / "pip_freeze.txt").exists()
    assert (pack_dir / "env" / "python_info.json").exists()
    assert (pack_dir / "reference_outputs" / "run_registry.json").exists()

    # Schema-validate the bundle and manifest.
    bundle = json.loads((pack_dir / "benchmark_bundle.json").read_text(encoding="utf-8"))
    bundle_schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "photonstrust.benchmark_bundle.v0.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=bundle, schema=bundle_schema)

    manifest = json.loads((pack_dir / "repro_pack_manifest.json").read_text(encoding="utf-8"))
    manifest_schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "photonstrust.repro_pack_manifest.v0.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=manifest, schema=manifest_schema)

    # Bundle check should pass.
    ok, failures = check_bundle_file(pack_dir / "benchmark_bundle.json")
    assert ok, "\n".join(failures)
