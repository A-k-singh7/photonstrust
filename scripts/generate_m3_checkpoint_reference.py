"""Generate a deterministic M3 checkpoint reference fixture."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from photonstrust.pipeline.m3_checkpoint import run_m3_checkpoint


def _path_to_repo_rel_or_placeholder(raw: object, *, repo_root: Path) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "<MISSING_PATH>"
    try:
        rel = Path(raw).resolve().relative_to(repo_root.resolve())
        return rel.as_posix()
    except Exception:
        return "<ABS_PATH>"


def _round_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(float(obj), 15)
    if isinstance(obj, list):
        return [_round_floats(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): _round_floats(value) for key, value in obj.items()}
    return obj


def _canonicalize_report(report: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    payload = copy.deepcopy(report)
    payload["generated_at"] = "<GENERATED_AT>"

    inputs = payload.get("inputs")
    if isinstance(inputs, dict):
        inputs["qkd_config_path"] = _path_to_repo_rel_or_placeholder(inputs.get("qkd_config_path"), repo_root=repo_root)
        inputs["repeater_config_path"] = _path_to_repo_rel_or_placeholder(
            inputs.get("repeater_config_path"),
            repo_root=repo_root,
        )
        inputs["output_dir"] = "<OUTPUT_DIR>"

    qkd = payload.get("qkd")
    if isinstance(qkd, dict) and isinstance(qkd.get("bands"), list):
        qkd["bands"] = sorted(
            list(qkd["bands"]),
            key=lambda row: (
                str(row.get("scenario_id", "")) if isinstance(row, dict) else "",
                str(row.get("band", "")) if isinstance(row, dict) else "",
            ),
        )

    repeater = payload.get("repeater")
    if isinstance(repeater, dict) and isinstance(repeater.get("distances"), list):
        repeater["distances"] = sorted(
            list(repeater["distances"]),
            key=lambda row: float(row.get("total_distance_km", 0.0)) if isinstance(row, dict) else 0.0,
        )

    rounded = _round_floats(payload)
    assert isinstance(rounded, dict)
    return rounded


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "results" / "m3_checkpoint_reference"
    fixture_path = root / "tests" / "fixtures" / "m3_checkpoint_reference.json"

    report = run_m3_checkpoint(
        qkd_config_path=root / "configs" / "demo1_default.yml",
        repeater_config_path=root / "configs" / "demo2_repeater_spacing.yml",
        output_dir=output_dir,
        force_analytic_backend=True,
        perturbation_fraction=0.05,
    )
    canonical = _canonicalize_report(report, repo_root=root)

    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(canonical, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(str(fixture_path.relative_to(root)))


if __name__ == "__main__":
    main()
