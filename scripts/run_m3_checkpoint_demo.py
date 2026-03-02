#!/usr/bin/env python3
"""Run the M3 checkpoint demo with default config inputs."""

from __future__ import annotations

import json
from pathlib import Path


def _summarize_result(result: object, *, output_dir: Path) -> dict:
    payload = result if isinstance(result, dict) else {}
    overall_status = str(payload.get("overall_status") or payload.get("status") or "UNKNOWN").strip().upper()
    qkd_status = None
    repeater_status = None

    qkd_pass_flags = payload.get("qkd_pass_flags")
    if not isinstance(qkd_pass_flags, dict):
        qkd_pass_flags = {}
        qkd_section = payload.get("qkd")
        if isinstance(qkd_section, dict):
            status_raw = qkd_section.get("status")
            if status_raw is not None:
                qkd_status = str(status_raw).strip().upper()
                qkd_pass_flags["status_pass"] = qkd_status == "PASS"

            bands = qkd_section.get("bands")
            if isinstance(bands, list):
                for row in bands:
                    if not isinstance(row, dict):
                        continue
                    scenario_id = str(row.get("scenario_id") or "").strip()
                    band = str(row.get("band") or "").strip()
                    if not scenario_id and not band:
                        continue
                    key = f"{scenario_id}:{band}".strip(":")
                    qkd_pass_flags[key] = str(row.get("status") or "").strip().upper() == "PASS"

    summary = payload.get("summary")
    if isinstance(summary, dict):
        all_qkd = summary.get("all_qkd_checks_pass")
        if isinstance(all_qkd, bool):
            qkd_pass_flags.setdefault("all_qkd_checks_pass", all_qkd)

    repeater_stability = payload.get("repeater_stability")
    if repeater_stability is None:
        repeater_section = payload.get("repeater")
        if isinstance(repeater_section, dict):
            status_raw = repeater_section.get("status")
            if status_raw is not None:
                repeater_status = str(status_raw).strip().upper()

            if "stability" in repeater_section:
                repeater_stability = repeater_section.get("stability")
            elif "stable" in repeater_section:
                repeater_stability = repeater_section.get("stable")
            elif "is_stable" in repeater_section:
                repeater_stability = repeater_section.get("is_stable")
            elif "distances" in repeater_section and isinstance(repeater_section.get("distances"), list):
                distances = repeater_section.get("distances") or []
                stable_flags = [bool(row.get("stable")) for row in distances if isinstance(row, dict)]
                if stable_flags:
                    repeater_stability = all(stable_flags)

    if repeater_stability is None and isinstance(summary, dict):
        stable_pass = summary.get("repeater_stability_pass")
        if isinstance(stable_pass, bool):
            repeater_stability = stable_pass

    output_path_raw = payload.get("output_path")
    if output_path_raw is None:
        output_path_raw = payload.get("output_dir")
    if output_path_raw is None and isinstance(payload.get("artifacts"), dict):
        output_path_raw = payload["artifacts"].get("output_dir")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "overall_status": overall_status,
        "output_path": output_path,
        "qkd_status": qkd_status,
        "repeater_status": repeater_status,
        "qkd_pass_flags": qkd_pass_flags,
        "repeater_stability": repeater_stability,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    qkd_config = repo_root / "configs" / "demo1_default.yml"
    repeater_config = repo_root / "configs" / "demo2_repeater_spacing.yml"
    output_dir = (repo_root / "results" / "m3_checkpoint_demo").resolve()

    try:
        from photonstrust.pipeline.m3_checkpoint import run_m3_checkpoint
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"m3_checkpoint_api_unavailable: {exc}",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    try:
        result = run_m3_checkpoint(
            qkd_config_path=qkd_config,
            repeater_config_path=repeater_config,
            output_dir=output_dir,
            force_analytic_backend=True,
            perturbation_fraction=0.05,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"m3_checkpoint_run_failed: {exc}",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    summary = _summarize_result(result, output_dir=output_dir)
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

