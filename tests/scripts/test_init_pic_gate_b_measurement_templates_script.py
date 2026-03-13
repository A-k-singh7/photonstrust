from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from photonstrust.measurements.schema import measurement_bundle_schema_path, validate_instance


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "init_pic_gate_b_measurement_templates.py"
    spec = importlib.util.spec_from_file_location("init_pic_gate_b_measurement_templates_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_init_pic_gate_b_measurement_templates_writes_valid_bundles(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    root = tmp_path / "measurements_private"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_pic_gate_b_measurement_templates.py",
            "--root",
            str(root),
            "--rc-id",
            "rc_test_001",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())

    manifest_path = Path(payload["manifest"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundles = manifest.get("bundles") if isinstance(manifest.get("bundles"), dict) else {}

    assert set(bundles.keys()) == {"b1_insertion_loss", "b2_resonance_alignment", "b4_delay_rc"}

    for key in ("b1_insertion_loss", "b2_resonance_alignment", "b4_delay_rc"):
        bundle_path = Path(str(bundles[key]))
        assert bundle_path.exists()
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        validate_instance(bundle, measurement_bundle_schema_path())
        files = bundle.get("files") if isinstance(bundle.get("files"), list) else []
        assert len(files) == 1
        rel = str((files[0] or {}).get("path", ""))
        assert rel
        data_path = (bundle_path.parent / rel).resolve()
        assert data_path.exists()
