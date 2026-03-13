"""Check benchmark drift against canonical baseline fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.benchmarks.validation_harness import (
    MetricThreshold,
    ValidationCase,
    default_thresholds,
    run_validation_harness,
)


def _build_thresholds(*, rel_tol: float | None, abs_tol: float | None) -> dict[str, MetricThreshold]:
    thresholds = default_thresholds()
    if rel_tol is None and abs_tol is None:
        return thresholds

    out: dict[str, MetricThreshold] = {}
    for metric, current in thresholds.items():
        out[metric] = MetricThreshold(
            rel_tol=float(rel_tol) if rel_tol is not None else float(current.rel_tol),
            abs_tol=float(abs_tol) if abs_tol is not None else float(current.abs_tol),
        )
    return out


def _collect_failure_lines(summary: dict) -> list[str]:
    lines: list[str] = []
    for case in summary.get("cases") or []:
        if bool(case.get("passed", False)):
            continue
        case_id = str(case.get("case_id") or "case")
        artifact_dir = Path(str(case.get("artifact_dir") or ""))
        comparison_path = artifact_dir / "comparison.json"
        if comparison_path.exists():
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
            failures = comparison.get("failures") or []
            if failures:
                lines.extend([f"{case_id}: {msg}" for msg in failures])
                continue
        lines.append(f"{case_id}: drift check failed")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PhotonTrust benchmark drift.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Config path for single-case drift checks.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Baseline fixture path for single-case drift checks.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/benchmark_drift"),
        help="Output root for drift-comparison artifacts.",
    )
    parser.add_argument(
        "--rel-tol",
        type=float,
        default=None,
        help="Optional relative tolerance override applied to tracked metrics.",
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=None,
        help="Optional absolute tolerance override applied to tracked metrics.",
    )
    args = parser.parse_args()

    if (args.config is None) != (args.baseline is None):
        parser.error("--config and --baseline must be provided together for single-case mode")

    repo_root = Path(__file__).resolve().parents[2]
    thresholds = _build_thresholds(rel_tol=args.rel_tol, abs_tol=args.abs_tol)
    cases = None
    if args.config is not None and args.baseline is not None:
        cfg = args.config if args.config.is_absolute() else (repo_root / args.config)
        baseline = args.baseline if args.baseline.is_absolute() else (repo_root / args.baseline)
        cases = [
            ValidationCase(
                case_id="single_case_drift",
                config_path=cfg,
                baseline_path=baseline,
            )
        ]

    summary = run_validation_harness(
        repo_root=repo_root,
        output_root=(args.output_root if args.output_root.is_absolute() else (repo_root / args.output_root)),
        cases=cases,
        thresholds=thresholds,
    )

    if bool(summary.get("ok", False)):
        print("Benchmark drift check: PASS")
        print(f"Artifacts: {summary.get('artifacts', {}).get('run_dir', '')}")
        return 0

    print("Benchmark drift check: FAIL")
    for line in _collect_failure_lines(summary):
        print(f" - {line}")
    print(f"Artifacts: {summary.get('artifacts', {}).get('run_dir', '')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
