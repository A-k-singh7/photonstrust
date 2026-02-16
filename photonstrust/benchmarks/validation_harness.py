"""Canonical benchmark validation harness.

Provides repeatable drift checks over canonical scenarios with:
- explicit case definitions (config + baseline fixture)
- metric thresholds (relative + absolute)
- structured artifacts for CI/history inspection
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep
from photonstrust.validation import validate_scenarios_or_raise


@dataclass(frozen=True)
class MetricThreshold:
    rel_tol: float
    abs_tol: float


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    config_path: Path
    baseline_path: Path


def default_thresholds() -> dict[str, MetricThreshold]:
    return {
        "key_rate_bps": MetricThreshold(rel_tol=1e-6, abs_tol=1e-12),
        "qber": MetricThreshold(rel_tol=1e-6, abs_tol=1e-12),
        "raman_counts_cps": MetricThreshold(rel_tol=1e-6, abs_tol=1e-9),
        "background_counts_cps": MetricThreshold(rel_tol=1e-6, abs_tol=1e-9),
    }


def default_cases(repo_root: Path) -> list[ValidationCase]:
    """Build canonical case list from known baseline fixtures."""

    out: list[ValidationCase] = []

    demo_baseline = repo_root / "tests" / "fixtures" / "baselines.json"
    demo_config = repo_root / "configs" / "demo1_default.yml"
    if demo_baseline.exists() and demo_config.exists():
        out.append(
            ValidationCase(
                case_id="demo1_default_regression",
                config_path=demo_config,
                baseline_path=demo_baseline,
            )
        )

    canonical_baseline = repo_root / "tests" / "fixtures" / "canonical_phase41_baselines.json"
    if canonical_baseline.exists():
        payload = json.loads(canonical_baseline.read_text(encoding="utf-8"))
        for entry in payload.get("configs") or []:
            rel = str(entry.get("config_relpath") or "").strip()
            if not rel:
                continue
            cfg = repo_root / rel
            if not cfg.exists():
                continue
            case_id = f"phase41::{Path(rel).stem}"
            out.append(
                ValidationCase(
                    case_id=case_id,
                    config_path=cfg,
                    baseline_path=canonical_baseline,
                )
            )

    satellite_baseline = repo_root / "tests" / "fixtures" / "canonical_phase54_satellite_baselines.json"
    if satellite_baseline.exists():
        payload = json.loads(satellite_baseline.read_text(encoding="utf-8"))
        for entry in payload.get("configs") or []:
            rel = str(entry.get("config_relpath") or "").strip()
            if not rel:
                continue
            cfg = repo_root / rel
            if not cfg.exists():
                continue
            case_id = f"phase54::{Path(rel).stem}"
            out.append(
                ValidationCase(
                    case_id=case_id,
                    config_path=cfg,
                    baseline_path=satellite_baseline,
                )
            )

    return out


def run_validation_harness(
    *,
    repo_root: Path,
    output_root: Path,
    cases: list[ValidationCase] | None = None,
    thresholds: dict[str, MetricThreshold] | None = None,
) -> dict[str, Any]:
    cases = cases or default_cases(repo_root)
    thresholds = thresholds or default_thresholds()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    cases_dir = run_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    case_summaries: list[dict[str, Any]] = []
    total_failures = 0

    for case in cases:
        case_dir = cases_dir / _safe_case_id(case.case_id)
        case_dir.mkdir(parents=True, exist_ok=True)

        observed, expected_by_key = _collect_case_vectors(case)
        comparison = _compare_case(observed, expected_by_key, thresholds)
        failures = comparison["failures"]
        total_failures += len(failures)

        (case_dir / "observed.json").write_text(json.dumps(observed, indent=2), encoding="utf-8")
        (case_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

        case_summaries.append(
            {
                "case_id": case.case_id,
                "config_path": str(case.config_path),
                "baseline_path": str(case.baseline_path),
                "passed": len(failures) == 0,
                "failure_count": len(failures),
                "artifact_dir": str(case_dir),
            }
        )

    summary = {
        "schema_version": "0.1",
        "kind": "photonstrust.validation_harness",
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": total_failures == 0,
        "case_count": len(case_summaries),
        "failed_cases": sum(1 for c in case_summaries if not c["passed"]),
        "total_failures": total_failures,
        "thresholds": {k: asdict(v) for k, v in thresholds.items()},
        "cases": case_summaries,
        "artifacts": {
            "run_dir": str(run_dir),
            "cases_dir": str(cases_dir),
            "summary": str(run_dir / "summary.json"),
            "manifest": str(run_dir / "manifest.json"),
        },
    }

    manifest = {
        "schema_version": "0.1",
        "kind": "photonstrust.validation_harness.manifest",
        "run_id": run_id,
        "files": [
            "summary.json",
            "manifest.json",
            *[f"cases/{_safe_case_id(c['case_id'])}/observed.json" for c in case_summaries],
            *[f"cases/{_safe_case_id(c['case_id'])}/comparison.json" for c in case_summaries],
        ],
    }

    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return summary


def _collect_case_vectors(case: ValidationCase) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    config = load_config(case.config_path)
    scenarios = build_scenarios(config)
    validate_scenarios_or_raise(scenarios)

    expected_by_key = _load_expected_by_key(case)

    observed: list[dict[str, Any]] = []
    for scenario in scenarios:
        sweep = compute_sweep(scenario, include_uncertainty=False)
        results = sweep["results"]
        observed.append(
            {
                "scenario_id": scenario["scenario_id"],
                "band": scenario["band"],
                "distances_km": [float(r.distance_km) for r in results],
                "key_rate_bps": [float(r.key_rate_bps) for r in results],
                "qber": [float(r.qber_total) for r in results],
                "raman_counts_cps": [float(r.raman_counts_cps) for r in results],
                "background_counts_cps": [float(r.background_counts_cps) for r in results],
            }
        )
    return observed, expected_by_key


def _load_expected_by_key(case: ValidationCase) -> dict[tuple[str, str], dict[str, Any]]:
    payload = json.loads(case.baseline_path.read_text(encoding="utf-8"))

    # Fixture style A: tests/fixtures/baselines.json
    if isinstance(payload.get("baselines"), list):
        out = {}
        for row in payload["baselines"]:
            sid = str(row.get("scenario_id") or "").strip() or "scenario"
            band = str(row.get("band") or "").strip()
            out[(sid, band)] = row
        return out

    # Fixture style B: tests/fixtures/canonical_phase41_baselines.json
    if isinstance(payload.get("configs"), list):
        match = None
        case_rel = _as_relpath(case.config_path)
        for entry in payload["configs"]:
            rel = str(entry.get("config_relpath") or "").replace("\\", "/")
            if rel == case_rel or Path(rel).name == case.config_path.name:
                match = entry
                break
        if match is None:
            raise ValueError(f"No baseline entry for {case.config_path} in {case.baseline_path}")
        out = {}
        for row in match.get("baselines") or []:
            sid = str(row.get("scenario_id") or "").strip() or "scenario"
            band = str(row.get("band") or "").strip()
            out[(sid, band)] = row
        return out

    raise ValueError(f"Unsupported baseline fixture format: {case.baseline_path}")


def _compare_case(
    observed: list[dict[str, Any]],
    expected_by_key: dict[tuple[str, str], dict[str, Any]],
    thresholds: dict[str, MetricThreshold],
) -> dict[str, Any]:
    failures: list[str] = []
    metrics: list[dict[str, Any]] = []

    for row in observed:
        key = (str(row["scenario_id"]), str(row["band"]))
        expected = expected_by_key.get(key)
        if expected is None:
            failures.append(f"Missing baseline for scenario_id={key[0]} band={key[1]}")
            continue

        for metric, threshold in thresholds.items():
            obs_arr = row.get(metric)
            exp_arr = expected.get(metric)
            if exp_arr is None:
                continue
            if not isinstance(obs_arr, list) or not isinstance(exp_arr, list):
                failures.append(f"{key[0]}/{key[1]} {metric}: non-list data")
                continue
            if len(obs_arr) != len(exp_arr):
                failures.append(
                    f"{key[0]}/{key[1]} {metric}: length mismatch observed={len(obs_arr)} expected={len(exp_arr)}"
                )
                continue

            max_abs_delta = 0.0
            max_rel_delta = 0.0
            fail_count = 0
            for i, (obs, exp) in enumerate(zip(obs_arr, exp_arr)):
                obs_f = float(obs)
                exp_f = float(exp)
                abs_delta = abs(obs_f - exp_f)
                denom = max(abs(exp_f), abs(obs_f), 1e-30)
                rel_delta = abs_delta / denom
                max_abs_delta = max(max_abs_delta, abs_delta)
                max_rel_delta = max(max_rel_delta, rel_delta)
                tol = max(threshold.abs_tol, threshold.rel_tol * max(abs(exp_f), abs(obs_f)))
                if abs_delta > tol:
                    fail_count += 1
                    failures.append(
                        f"{key[0]}/{key[1]} {metric}[{i}] drift: observed={obs_f:.12g} expected={exp_f:.12g} "
                        f"abs_delta={abs_delta:.3g} tol={tol:.3g}"
                    )

            metrics.append(
                {
                    "scenario_id": key[0],
                    "band": key[1],
                    "metric": metric,
                    "samples": len(obs_arr),
                    "max_abs_delta": max_abs_delta,
                    "max_rel_delta": max_rel_delta,
                    "fail_count": fail_count,
                    "threshold": asdict(threshold),
                }
            )

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "metrics": metrics,
    }


def _safe_case_id(case_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in case_id)


def _as_relpath(path: Path) -> str:
    p = str(path).replace("\\", "/")
    marker = "/photonstrust/"
    idx = p.rfind(marker)
    if idx >= 0:
        return p[idx + len(marker) :]
    return Path(path).as_posix()
