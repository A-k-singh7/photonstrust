#!/usr/bin/env python3
"""Build a PIC Gate B correlation packet from available measurement bundles."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any

from photonstrust.calibrate.pic_crosstalk import fit_parallel_waveguide_crosstalk_model, load_pic_crosstalk_sweep
from photonstrust.measurements import ingest_measurement_bundle_file, publish_artifact_pack


DEFAULT_RUN_DIR = Path("results/pic_readiness/run_pkg")
DEFAULT_OPEN_ROOT = Path("results/pic_readiness/measurements_open")
DEFAULT_ARTIFACT_ROOT = Path("results/pic_readiness/artifact_packs")
DEFAULT_OUTPUT = Path("results/pic_readiness/gate_b/packet_auto.json")

DEFAULT_B1_BUNDLE = Path("tests/fixtures/measurement_bundle_demo/measurement_bundle.json")
DEFAULT_B3_BUNDLE = Path("tests/fixtures/measurement_bundle_pic_crosstalk/measurement_bundle.json")
DEFAULT_B3_BASELINE = Path("tests/fixtures/pic_crosstalk_calibration_baseline.json")

B1_MAE_DB_MAX = 0.30
B1_P95_DB_MAX = 0.60
B2_MAE_PM_MAX = 10.0
B2_P95_PM_MAX = 25.0
B3_MAE_DB_MAX = 3.0
B3_P95_DB_MAX = 6.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PIC Gate B correlation packet from measurement bundles")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR, help="PIC candidate run directory")
    parser.add_argument("--release-candidate", default="preflight_auto", help="Release candidate identifier")
    parser.add_argument("--open-root", type=Path, default=DEFAULT_OPEN_ROOT, help="Measurement open registry root")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT, help="Artifact pack output root")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output packet JSON path")

    parser.add_argument("--b1-bundle", type=Path, default=DEFAULT_B1_BUNDLE, help="B1 insertion-loss measurement bundle")
    parser.add_argument("--b2-bundle", type=Path, default=None, help="B2 resonance measurement bundle")
    parser.add_argument("--b3-bundle", type=Path, default=DEFAULT_B3_BUNDLE, help="B3 crosstalk measurement bundle")
    parser.add_argument("--b4-bundle", type=Path, default=None, help="B4 delay/RC measurement bundle")
    parser.add_argument("--b5-bundle", type=Path, default=None, help="B5 drift measurement bundle")
    parser.add_argument("--b3-baseline", type=Path, default=DEFAULT_B3_BASELINE, help="Optional B3 drift baseline JSON")

    parser.add_argument("--overwrite-ingest", action="store_true", help="Overwrite dataset entry if already ingested")
    parser.add_argument("--allow-risk-pack", action="store_true", help="Allow artifact pack even if redaction scan flags issues")
    parser.add_argument(
        "--zip-pack",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create zip archive for artifact pack (default: true)",
    )
    return parser.parse_args()


def _resolve_cli_path(path: Path | None, *, cwd: Path) -> Path | None:
    if path is None:
        return None
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _text_contains_synthetic(value: str) -> bool:
    return "synthetic" in value.lower()


def _is_synthetic_bundle(bundle: dict[str, Any]) -> bool:
    fields: list[str] = []
    title = bundle.get("title")
    if isinstance(title, str):
        fields.append(title)

    restrictions = bundle.get("restrictions")
    if isinstance(restrictions, dict):
        notes = restrictions.get("notes")
        if isinstance(notes, str):
            fields.append(notes)

    provenance = bundle.get("provenance")
    if isinstance(provenance, dict):
        description = provenance.get("description")
        if isinstance(description, str):
            fields.append(description)

    return any(_text_contains_synthetic(text) for text in fields)


def _rel_err(observed: float, expected: float) -> float:
    if expected == 0.0:
        return float("inf") if observed != 0.0 else 0.0
    return abs(observed - expected) / abs(expected)


def _ingest_and_publish(
    bundle_path: Path,
    *,
    open_root: Path,
    artifact_root: Path,
    overwrite_ingest: bool,
    allow_risk_pack: bool,
    zip_pack: bool,
) -> dict[str, Any]:
    bundle = _load_json_object(bundle_path)
    dataset_id = str(bundle.get("dataset_id") or "").strip()
    if not dataset_id:
        raise ValueError(f"measurement bundle missing dataset_id: {bundle_path}")

    ingested_manifest = ingest_measurement_bundle_file(bundle_path, open_root=open_root, overwrite=overwrite_ingest)
    pack_root = publish_artifact_pack(
        bundle_path,
        artifact_root,
        pack_id=f"{dataset_id}_pack",
        allow_risk=allow_risk_pack,
        zip_pack=zip_pack,
    )

    return {
        "bundle_path": str(bundle_path),
        "dataset_id": dataset_id,
        "kind": str(bundle.get("kind") or ""),
        "bundle": bundle,
        "ingested_manifest_path": str(ingested_manifest),
        "artifact_pack_manifest_path": str((pack_root / "artifact_pack_manifest.json").resolve()),
        "artifact_pack_root": str(pack_root.resolve()),
    }


def _resolve_bundle_data_file(bundle_path: Path, bundle: dict[str, Any], *, suffix_hint: str | None = None) -> Path | None:
    files = bundle.get("files")
    if not isinstance(files, list):
        return None

    bundle_dir = bundle_path.parent
    preferred: Path | None = None
    fallback_csv: Path | None = None
    fallback_json: Path | None = None
    fallback_any: Path | None = None
    for row in files:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("path") or "").replace("\\", "/")
        if not rel:
            continue
        candidate = (bundle_dir / rel).resolve()
        if not candidate.exists() or not candidate.is_file():
            continue
        if suffix_hint and rel.endswith(suffix_hint):
            preferred = candidate
            break
        if fallback_any is None:
            fallback_any = candidate
        lower = rel.lower()
        if fallback_csv is None and lower.endswith(".csv"):
            fallback_csv = candidate
        if fallback_json is None and lower.endswith(".json"):
            fallback_json = candidate
    return preferred or fallback_csv or fallback_json or fallback_any


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _pick_float(row: dict[str, str], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        raw = row.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        try:
            value = float(text)
        except Exception:
            continue
        if math.isfinite(value):
            return value
    return None


def _abs_error_stats(errors: list[float]) -> tuple[float, float]:
    if not errors:
        return 0.0, 0.0
    values = sorted(float(v) for v in errors if math.isfinite(float(v)))
    if not values:
        return 0.0, 0.0
    mae = sum(values) / float(len(values))
    p95_index = max(0, min(len(values) - 1, math.ceil(0.95 * len(values)) - 1))
    p95 = float(values[p95_index])
    return float(mae), float(p95)


def _evaluate_csv_metric(
    *,
    metric_name: str,
    bundle_path: Path,
    bundle_meta: dict[str, Any],
    suffix_hint: str,
    observed_keys: tuple[str, ...],
    predicted_keys: tuple[str, ...],
    error_scale: float,
    mae_max: float,
    p95_max: float,
    enforce_thresholds: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    bundle = bundle_meta["bundle"]
    data_path = _resolve_bundle_data_file(bundle_path, bundle, suffix_hint=suffix_hint)
    evidence = [
        bundle_meta["bundle_path"],
        bundle_meta["ingested_manifest_path"],
        bundle_meta["artifact_pack_manifest_path"],
    ]

    if data_path is None:
        notes.append(f"{metric_name}: data file not found in bundle.")
        return (
            {
                "status": "evidence_ready_pending_correlation",
                "mae": None,
                "p95": None,
                "sample_count": 0,
                "evidence": evidence,
            },
            notes,
        )

    evidence.append(str(data_path))
    if data_path.suffix.lower() != ".csv":
        notes.append(f"{metric_name}: expected CSV data for correlation, found {data_path.suffix}.")
        return (
            {
                "status": "evidence_ready_pending_correlation",
                "mae": None,
                "p95": None,
                "sample_count": 0,
                "evidence": evidence,
            },
            notes,
        )

    rows = _read_csv_rows(data_path)
    errors: list[float] = []
    for row in rows:
        observed = _pick_float(row, observed_keys)
        predicted = _pick_float(row, predicted_keys)
        if observed is None or predicted is None:
            continue
        errors.append(abs(observed - predicted) * float(error_scale))

    if not errors:
        notes.append(f"{metric_name}: no comparable rows with measured+model columns.")
        return (
            {
                "status": "evidence_ready_pending_correlation",
                "mae": None,
                "p95": None,
                "sample_count": 0,
                "evidence": evidence,
            },
            notes,
        )

    mae, p95 = _abs_error_stats(errors)
    synthetic = _is_synthetic_bundle(bundle)
    if not enforce_thresholds:
        status = "preflight_pass_synthetic" if synthetic else "evidence_ready_pending_threshold_policy"
    elif mae <= float(mae_max) and p95 <= float(p95_max):
        status = "preflight_pass_synthetic" if synthetic else "pass"
    else:
        status = "fail"
        notes.append(
            f"{metric_name}: thresholds exceeded (mae={mae:.6g}, p95={p95:.6g}, limits={mae_max:.6g}/{p95_max:.6g})."
        )

    return (
        {
            "status": status,
            "mae": float(mae),
            "p95": float(p95),
            "sample_count": int(len(errors)),
            "evidence": evidence,
            "comparator": {
                "observed_keys": list(observed_keys),
                "predicted_keys": list(predicted_keys),
                "error_scale": float(error_scale),
                "thresholds_enforced": bool(enforce_thresholds),
            },
        },
        notes,
    )


def _evaluate_b3(
    *,
    bundle_path: Path,
    bundle_meta: dict[str, Any],
    baseline_path: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    bundle = bundle_meta["bundle"]
    sweep_path = _resolve_bundle_data_file(bundle_path, bundle, suffix_hint="pic_crosstalk_sweep.json")
    if sweep_path is None:
        return (
            {
                "status": "fail",
                "rmse_db": None,
                "max_abs_error_db": None,
                "fit_params": {},
                "sample_count": 0,
                "drift_gate": "not_run",
                "evidence": [
                    bundle_meta["bundle_path"],
                    bundle_meta["ingested_manifest_path"],
                    bundle_meta["artifact_pack_manifest_path"],
                ],
            },
            ["B3 sweep file not found inside bundle files list."],
        )

    sweep = load_pic_crosstalk_sweep(sweep_path)
    report = fit_parallel_waveguide_crosstalk_model(sweep)
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    fit = report.get("fit") if isinstance(report.get("fit"), dict) else {}
    params = fit.get("params") if isinstance(fit.get("params"), dict) else {}
    sample_count = len(sweep.gaps_um) * len(sweep.wavelengths_nm)

    drift_gate = "not_run"
    drift_failures: list[str] = []
    if baseline_path is not None and baseline_path.exists() and baseline_path.is_file():
        baseline = _load_json_object(baseline_path)
        expected = baseline.get("expected") if isinstance(baseline.get("expected"), dict) else {}
        expected_params = expected.get("params") if isinstance(expected.get("params"), dict) else {}
        tolerances = baseline.get("tolerances") if isinstance(baseline.get("tolerances"), dict) else {}

        try:
            kappa0 = float(params.get("kappa0_per_um"))
            gap_decay = float(params.get("gap_decay_um"))
            lambda_exp = float(params.get("lambda_exp"))
            expected_kappa0 = float(expected_params.get("kappa0_per_um"))
            expected_gap_decay = float(expected_params.get("gap_decay_um"))
            expected_lambda_exp = float(expected_params.get("lambda_exp"))

            kappa0_rel_tol = float(tolerances.get("kappa0_rel_tol", 1e-6))
            gap_decay_rel_tol = float(tolerances.get("gap_decay_rel_tol", 1e-6))
            lambda_exp_abs_tol = float(tolerances.get("lambda_exp_abs_tol", 1e-6))

            if not math.isfinite(kappa0) or not math.isfinite(gap_decay) or not math.isfinite(lambda_exp):
                drift_failures.append("non-finite fitted parameters")
            if _rel_err(kappa0, expected_kappa0) > kappa0_rel_tol:
                drift_failures.append("kappa0_per_um outside tolerance")
            if _rel_err(gap_decay, expected_gap_decay) > gap_decay_rel_tol:
                drift_failures.append("gap_decay_um outside tolerance")
            if abs(lambda_exp - expected_lambda_exp) > lambda_exp_abs_tol:
                drift_failures.append("lambda_exp outside tolerance")

            rmse_db = float(metrics.get("rmse_db") or 0.0)
            rmse_max = float(expected.get("rmse_db_max", 1e-6))
            if rmse_db > rmse_max:
                drift_failures.append("rmse_db exceeds baseline max")
        except Exception as exc:
            drift_failures.append(f"baseline evaluation failed: {exc}")

        drift_gate = "pass" if not drift_failures else "fail"

    if drift_failures:
        notes.extend(f"B3 drift: {msg}" for msg in drift_failures)

    synthetic = _is_synthetic_bundle(bundle)
    status = "fail" if drift_gate == "fail" else ("preflight_pass_synthetic" if synthetic else "pass")

    evidence = [
        bundle_meta["bundle_path"],
        bundle_meta["ingested_manifest_path"],
        bundle_meta["artifact_pack_manifest_path"],
        str(sweep_path),
    ]
    if baseline_path is not None and baseline_path.exists() and baseline_path.is_file():
        evidence.append(str(baseline_path))

    return (
        {
            "status": status,
            "rmse_db": float(metrics.get("rmse_db")) if metrics.get("rmse_db") is not None else None,
            "max_abs_error_db": float(metrics.get("max_abs_error_db")) if metrics.get("max_abs_error_db") is not None else None,
            "fit_params": {
                "kappa0_per_um": float(params.get("kappa0_per_um")) if params.get("kappa0_per_um") is not None else None,
                "gap_decay_um": float(params.get("gap_decay_um")) if params.get("gap_decay_um") is not None else None,
                "lambda_ref_nm": float(params.get("lambda_ref_nm")) if params.get("lambda_ref_nm") is not None else None,
                "lambda_exp": float(params.get("lambda_exp")) if params.get("lambda_exp") is not None else None,
            },
            "sample_count": int(sample_count),
            "drift_gate": drift_gate,
            "evidence": evidence,
        },
        notes,
    )


def _default_metric_entry() -> dict[str, Any]:
    return {
        "status": "pending",
        "mae": None,
        "p95": None,
        "sample_count": 0,
        "evidence": [],
    }


def _derive_overall_status(metrics: dict[str, dict[str, Any]]) -> str:
    statuses = [str((row or {}).get("status") or "pending").strip().lower() for row in metrics.values()]
    if any(status == "fail" for status in statuses):
        return "fail"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "pending"


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    cwd = Path.cwd()

    run_dir = _resolve_cli_path(args.run_dir, cwd=cwd)
    open_root = _resolve_cli_path(args.open_root, cwd=cwd)
    artifact_root = _resolve_cli_path(args.artifact_root, cwd=cwd)
    output_path = _resolve_cli_path(args.output, cwd=cwd)

    b1_bundle = _resolve_cli_path(args.b1_bundle, cwd=cwd)
    b2_bundle = _resolve_cli_path(args.b2_bundle, cwd=cwd)
    b3_bundle = _resolve_cli_path(args.b3_bundle, cwd=cwd)
    b4_bundle = _resolve_cli_path(args.b4_bundle, cwd=cwd)
    b5_bundle = _resolve_cli_path(args.b5_bundle, cwd=cwd)
    b3_baseline = _resolve_cli_path(args.b3_baseline, cwd=cwd)

    open_root.parent.mkdir(parents=True, exist_ok=True)
    artifact_root.parent.mkdir(parents=True, exist_ok=True)

    metrics: dict[str, dict[str, Any]] = {
        "b1_insertion_loss": _default_metric_entry(),
        "b2_resonance_alignment": _default_metric_entry(),
        "b3_crosstalk": {
            "status": "pending",
            "rmse_db": None,
            "max_abs_error_db": None,
            "fit_params": {},
            "sample_count": 0,
            "drift_gate": "not_run",
            "evidence": [],
        },
        "b4_delay_rc": _default_metric_entry(),
        "b5_drift": {
            "status": "pending",
            "drift_pass": None,
            "delta_summary": {},
            "evidence": [],
        },
    }

    notes: list[str] = []

    bundle_map = {
        "b1_insertion_loss": b1_bundle,
        "b2_resonance_alignment": b2_bundle,
        "b3_crosstalk": b3_bundle,
        "b4_delay_rc": b4_bundle,
        "b5_drift": b5_bundle,
    }

    ingested: dict[str, dict[str, Any]] = {}
    for metric_name, bundle_path in bundle_map.items():
        if bundle_path is None:
            continue
        if not bundle_path.exists() or not bundle_path.is_file():
            notes.append(f"{metric_name}: bundle not found at {bundle_path}")
            continue
        try:
            bundle_meta = _ingest_and_publish(
                bundle_path,
                open_root=open_root,
                artifact_root=artifact_root,
                overwrite_ingest=bool(args.overwrite_ingest),
                allow_risk_pack=bool(args.allow_risk_pack),
                zip_pack=bool(args.zip_pack),
            )
        except Exception as exc:
            metrics[metric_name]["status"] = "fail"
            notes.append(f"{metric_name}: ingest/publish failed ({exc})")
            continue

        ingested[metric_name] = bundle_meta
        metrics[metric_name]["evidence"] = [
            bundle_meta["bundle_path"],
            bundle_meta["ingested_manifest_path"],
            bundle_meta["artifact_pack_manifest_path"],
        ]

        if metric_name != "b3_crosstalk":
            metrics[metric_name]["status"] = "evidence_ready_pending_correlation"

    if "b1_insertion_loss" in ingested:
        try:
            b1_entry, b1_notes = _evaluate_csv_metric(
                metric_name="b1_insertion_loss",
                bundle_path=b1_bundle,
                bundle_meta=ingested["b1_insertion_loss"],
                suffix_hint=".csv",
                observed_keys=("measured_loss_db", "loss_db"),
                predicted_keys=("model_loss_db", "predicted_loss_db", "sim_loss_db"),
                error_scale=1.0,
                mae_max=B1_MAE_DB_MAX,
                p95_max=B1_P95_DB_MAX,
            )
            metrics["b1_insertion_loss"] = b1_entry
            notes.extend(b1_notes)
        except Exception as exc:
            metrics["b1_insertion_loss"]["status"] = "fail"
            notes.append(f"b1_insertion_loss: evaluation failed ({exc})")

    if "b2_resonance_alignment" in ingested:
        try:
            b2_entry, b2_notes = _evaluate_csv_metric(
                metric_name="b2_resonance_alignment",
                bundle_path=b2_bundle,
                bundle_meta=ingested["b2_resonance_alignment"],
                suffix_hint=".csv",
                observed_keys=("measured_resonance_nm", "resonance_center_nm", "resonance_nm"),
                predicted_keys=("model_resonance_nm", "predicted_resonance_nm", "sim_resonance_nm"),
                error_scale=1000.0,
                mae_max=B2_MAE_PM_MAX,
                p95_max=B2_P95_PM_MAX,
            )
            metrics["b2_resonance_alignment"] = b2_entry
            notes.extend(b2_notes)
        except Exception as exc:
            metrics["b2_resonance_alignment"]["status"] = "fail"
            notes.append(f"b2_resonance_alignment: evaluation failed ({exc})")

    if "b4_delay_rc" in ingested:
        try:
            b4_entry, b4_notes = _evaluate_csv_metric(
                metric_name="b4_delay_rc",
                bundle_path=b4_bundle,
                bundle_meta=ingested["b4_delay_rc"],
                suffix_hint=".csv",
                observed_keys=("measured_delay_ps", "delay_ps"),
                predicted_keys=("model_delay_ps", "predicted_delay_ps", "sim_delay_ps"),
                error_scale=1.0,
                mae_max=0.0,
                p95_max=0.0,
                enforce_thresholds=False,
            )
            metrics["b4_delay_rc"] = b4_entry
            notes.extend(b4_notes)
        except Exception as exc:
            metrics["b4_delay_rc"]["status"] = "fail"
            notes.append(f"b4_delay_rc: evaluation failed ({exc})")

    if "b3_crosstalk" in ingested:
        try:
            b3_entry, b3_notes = _evaluate_b3(
                bundle_path=b3_bundle,
                bundle_meta=ingested["b3_crosstalk"],
                baseline_path=b3_baseline,
            )
            metrics["b3_crosstalk"] = b3_entry
            notes.extend(b3_notes)
        except Exception as exc:
            metrics["b3_crosstalk"]["status"] = "fail"
            notes.append(f"b3_crosstalk: evaluation failed ({exc})")

    b3_status = str(metrics["b3_crosstalk"].get("status") or "pending").lower()
    if b3_status == "fail":
        metrics["b5_drift"] = {
            "status": "fail",
            "drift_pass": False,
            "delta_summary": {"source": "b3_crosstalk", "reason": "b3 failed"},
            "evidence": list(metrics["b3_crosstalk"].get("evidence") or []),
        }
    elif b3_status in {"pass", "preflight_pass_synthetic"}:
        drift_gate = str(metrics["b3_crosstalk"].get("drift_gate") or "not_run").lower()
        drift_pass = drift_gate == "pass"
        b5_status = "pending_silicon_required"
        if not drift_pass and drift_gate != "not_run":
            b5_status = "fail"
        metrics["b5_drift"] = {
            "status": b5_status,
            "drift_pass": drift_pass if drift_gate != "not_run" else None,
            "delta_summary": {
                "source": "b3_crosstalk",
                "scope": "synthetic_fixture_only" if b3_status == "preflight_pass_synthetic" else "bundle_scope",
            },
            "evidence": list(metrics["b3_crosstalk"].get("evidence") or []),
        }

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_gate_b_correlation_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "run_dir": str(run_dir),
            "release_candidate": str(args.release_candidate),
        },
        "tolerances": {
            "b1_mae_db_max": B1_MAE_DB_MAX,
            "b1_p95_db_max": B1_P95_DB_MAX,
            "b2_mae_pm_max": B2_MAE_PM_MAX,
            "b2_p95_pm_max": B2_P95_PM_MAX,
            "b3_mae_db_max": B3_MAE_DB_MAX,
            "b3_p95_db_max": B3_P95_DB_MAX,
        },
        "metrics": metrics,
        "overall_gate_b_status": _derive_overall_status(metrics),
        "notes": notes,
        "provenance": {
            "script": str((repo_root / "scripts" / "build_pic_gate_b_packet.py").resolve()),
            "python": sys.version.split()[0],
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    print(f"gate_b_packet: {str(output_path.resolve())}")
    print(f"gate_b_status: {packet['overall_gate_b_status']}")
    return 0 if packet["overall_gate_b_status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
