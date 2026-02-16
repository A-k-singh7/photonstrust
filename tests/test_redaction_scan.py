from __future__ import annotations

from pathlib import Path

import pytest

from photonstrust.measurements import publish_artifact_pack
from photonstrust.measurements.redaction import scan_measurement_bundle


def test_redaction_scan_detects_secret_like_patterns(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_dir = root / "tests" / "fixtures" / "measurement_bundle_bad_secret"
    issues = scan_measurement_bundle(bundle_dir, file_paths=["measurement_bundle.json", "data/leak.txt"])
    assert any("aws_access_key_id" in i for i in issues)


def test_publish_artifact_pack_blocks_bad_secret_by_default(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_bad_secret" / "measurement_bundle.json"
    with pytest.raises(ValueError, match="Redaction scan failed"):
        publish_artifact_pack(bundle_path, tmp_path)


def test_publish_artifact_pack_allows_override_with_flag(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_bad_secret" / "measurement_bundle.json"
    pack_root = publish_artifact_pack(bundle_path, tmp_path, allow_risk=True, zip_pack=False)
    assert (Path(pack_root) / "artifact_pack_manifest.json").exists()


def test_publish_artifact_pack_demo_bundle_succeeds(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    bundle_path = root / "tests" / "fixtures" / "measurement_bundle_demo" / "measurement_bundle.json"
    pack_root = publish_artifact_pack(bundle_path, tmp_path, zip_pack=True)
    pack_root = Path(pack_root)
    assert (pack_root / "measurement_bundle.json").exists()
    assert (pack_root / "data" / "demo_measurements.csv").exists()
    assert (pack_root / "artifact_pack_manifest.json").exists()
    assert (tmp_path / f"{pack_root.name}.zip").exists()
