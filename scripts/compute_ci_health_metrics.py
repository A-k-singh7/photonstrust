#!/usr/bin/env python3
"""Compute CI pass-rate and MTTR metrics from GitHub Actions runs."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import subprocess
from typing import Any, NamedTuple


DEFAULT_OUTPUT_JSON = Path("results/ci_health/ci_history_metrics_real.json")
DEFAULT_OUTPUT_MD = Path("results/ci_health/ci_health_summary.md")
DEFAULT_WORKFLOWS = (
    "ci-smoke",
    "Web Playwright Tests",
    "security-baseline",
)
FAILURE_CONCLUSIONS = {
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "startup_failure",
}


class RunRecord(NamedTuple):
    name: str
    conclusion: str
    run_attempt: int
    created_at: datetime
    updated_at: datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute CI health metrics from workflow runs")
    parser.add_argument("--repo", default=None, help="GitHub repo slug in owner/repo format")
    parser.add_argument("--branch", default="main", help="Branch name to analyze")
    parser.add_argument(
        "--workflow",
        dest="workflows",
        action="append",
        default=None,
        help="Workflow name to include. Repeat for multiple workflows.",
    )
    parser.add_argument("--window-days", type=int, default=14, help="Trailing analysis window in days")
    parser.add_argument("--per-page", type=int, default=100, help="Runs per API page when fetching")
    parser.add_argument("--max-pages", type=int, default=5, help="Max API pages when fetching")
    parser.add_argument(
        "--runs-json",
        type=Path,
        default=None,
        help="Optional path to GitHub Actions runs JSON (for offline computation)",
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output JSON path")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Output markdown path")
    parser.add_argument(
        "--min-pass-rate-percent",
        type=float,
        default=95.0,
        help="Pass-rate threshold for red/green status",
    )
    parser.add_argument(
        "--max-flaky-rate-percent",
        type=float,
        default=3.0,
        help="Flaky-rate threshold for red/green status",
    )
    parser.add_argument(
        "--max-mttr-hours",
        type=float,
        default=24.0,
        help="MTTR threshold (hours) for red/green status",
    )
    parser.add_argument(
        "--fail-on-threshold-breach",
        action="store_true",
        help="Return non-zero if any threshold is red",
    )
    return parser.parse_args()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_gh_api(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"gh api failed ({proc.returncode}): {stderr}")

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {}
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise ValueError("gh api response must be a JSON object")
    return payload


def _load_runs_from_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        runs_obj = payload.get("workflow_runs")
        if isinstance(runs_obj, list):
            return [row for row in runs_obj if isinstance(row, dict)]
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _fetch_runs_from_github(*, repo: str, branch: str, per_page: int, max_pages: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        command = [
            "gh",
            "api",
            f"repos/{repo}/actions/runs",
            "-f",
            f"branch={branch}",
            "-f",
            "status=completed",
            "-f",
            f"per_page={max(1, per_page)}",
            "-f",
            f"page={page}",
        ]
        payload = _run_gh_api(command)
        page_runs_obj = payload.get("workflow_runs")
        page_runs = [row for row in page_runs_obj if isinstance(row, dict)] if isinstance(page_runs_obj, list) else []
        if not page_runs:
            break
        runs.extend(page_runs)
        if len(page_runs) < max(1, per_page):
            break
    return runs


def _to_record(raw: dict[str, Any]) -> RunRecord | None:
    created_at = _parse_iso_utc(raw.get("created_at"))
    if created_at is None:
        return None
    updated_at = _parse_iso_utc(raw.get("updated_at")) or created_at

    name = str(raw.get("name") or "unknown-workflow")
    conclusion = str(raw.get("conclusion") or "").strip().lower()
    run_attempt_raw = raw.get("run_attempt", 1)
    try:
        run_attempt = max(1, int(run_attempt_raw))
    except Exception:
        run_attempt = 1

    return RunRecord(
        name=name,
        conclusion=conclusion,
        run_attempt=run_attempt,
        created_at=created_at,
        updated_at=updated_at,
    )


def _select_records(
    runs: list[dict[str, Any]],
    *,
    workflows: tuple[str, ...],
    window_start: datetime,
    window_end: datetime,
) -> list[RunRecord]:
    allowed = {item.strip() for item in workflows if item.strip()}
    selected: list[RunRecord] = []
    for row in runs:
        record = _to_record(row)
        if record is None:
            continue
        if allowed and record.name not in allowed:
            continue
        if record.created_at < window_start or record.created_at > window_end:
            continue
        if not record.conclusion:
            continue
        selected.append(record)
    selected.sort(key=lambda item: item.updated_at)
    return selected


def _compute_mttr(records: list[RunRecord]) -> dict[str, Any]:
    by_workflow: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        by_workflow[record.name].append(record)

    recoveries: list[float] = []
    failures_total = 0
    unresolved_failures = 0
    for workflow_records in by_workflow.values():
        workflow_records.sort(key=lambda row: row.updated_at)
        for index, row in enumerate(workflow_records):
            if row.conclusion not in FAILURE_CONCLUSIONS:
                continue
            failures_total += 1
            next_success = next(
                (candidate for candidate in workflow_records[index + 1 :] if candidate.conclusion == "success"),
                None,
            )
            if next_success is None:
                unresolved_failures += 1
                continue
            delta_hours = (next_success.updated_at - row.updated_at).total_seconds() / 3600.0
            recoveries.append(max(0.0, float(delta_hours)))

    mean_hours = float(statistics.mean(recoveries)) if recoveries else None
    return {
        "failure_count": int(failures_total),
        "recovered_failure_count": int(len(recoveries)),
        "unresolved_failure_count": int(unresolved_failures),
        "mean_time_to_recovery_hours": mean_hours,
    }


def _status_word(status: str) -> str:
    if status == "pass":
        return "GREEN"
    if status == "fail":
        return "RED"
    return "YELLOW"


def _render_markdown(payload: dict[str, Any]) -> str:
    metrics_obj = payload.get("metrics")
    metrics = metrics_obj if isinstance(metrics_obj, dict) else {}
    thresholds_obj = payload.get("thresholds")
    thresholds = thresholds_obj if isinstance(thresholds_obj, dict) else {}
    status_obj = payload.get("status")
    status = status_obj if isinstance(status_obj, dict) else {}

    rows = [
        (
            "Build pass rate",
            f"{float(metrics.get('pass_rate_percent', 0.0)):.2f}%",
            f">= {float(thresholds.get('min_pass_rate_percent', 0.0)):.2f}%",
            _status_word(str(status.get("pass_rate") or "pending")),
        ),
        (
            "Flaky rerun rate",
            f"{float(metrics.get('flaky_rate_percent', 0.0)):.2f}%",
            f"<= {float(thresholds.get('max_flaky_rate_percent', 0.0)):.2f}%",
            _status_word(str(status.get("flaky_rate") or "pending")),
        ),
        (
            "MTTR",
            (
                "n/a"
                if metrics.get("mean_time_to_recovery_hours") is None
                else f"{float(metrics.get('mean_time_to_recovery_hours', 0.0)):.2f} h"
            ),
            f"<= {float(thresholds.get('max_mttr_hours', 0.0)):.2f} h",
            _status_word(str(status.get("mttr") or "pending")),
        ),
    ]

    lines = [
        "# CI Health Scoreboard",
        "",
        f"Generated: `{payload.get('generated_at', '')}`",
        f"Window: `{payload.get('window', {}).get('start', '')}` -> `{payload.get('window', {}).get('end', '')}`",
        f"Overall: `{str(status.get('overall') or 'pending').upper()}`",
        "",
        "| Metric | Value | Threshold | Status |",
        "| --- | --- | --- | --- |",
    ]
    for name, value, threshold, row_status in rows:
        lines.append(f"| {name} | {value} | {threshold} | {row_status} |")
    lines.append("")
    return "\n".join(lines)


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (Path.cwd() / path)


def main() -> int:
    args = parse_args()
    now = _now_utc()
    window_days = max(1, int(args.window_days))
    window_start = now - timedelta(days=window_days)
    workflows = tuple(args.workflows) if args.workflows else tuple(DEFAULT_WORKFLOWS)

    if args.runs_json is not None:
        runs = _load_runs_from_json(_resolve(args.runs_json))
        source = "runs_json"
    else:
        if not args.repo:
            raise SystemExit("--repo is required when --runs-json is not provided")
        try:
            runs = _fetch_runs_from_github(
                repo=str(args.repo),
                branch=str(args.branch),
                per_page=max(1, int(args.per_page)),
                max_pages=max(1, int(args.max_pages)),
            )
        except Exception as exc:
            raise SystemExit(f"failed to fetch workflow runs for {args.repo}: {exc}") from exc
        source = "github_api"

    records = _select_records(
        runs,
        workflows=workflows,
        window_start=window_start,
        window_end=now,
    )

    total_runs = len(records)
    passed_runs = sum(1 for row in records if row.conclusion == "success")
    flaky_runs = sum(1 for row in records if row.run_attempt > 1)
    pass_rate = (100.0 * passed_runs / total_runs) if total_runs else 0.0
    flaky_rate = (100.0 * flaky_runs / total_runs) if total_runs else 0.0

    mttr_block = _compute_mttr(records)
    mttr_hours = mttr_block.get("mean_time_to_recovery_hours")
    mttr_failure_count = int(mttr_block.get("failure_count", 0))

    min_pass = float(args.min_pass_rate_percent)
    max_flaky = float(args.max_flaky_rate_percent)
    max_mttr = float(args.max_mttr_hours)

    pass_status = "pass" if pass_rate >= min_pass else "fail"
    flaky_status = "pass" if flaky_rate <= max_flaky else "fail"

    if mttr_failure_count == 0:
        mttr_status = "pending_no_failures"
    elif mttr_hours is None:
        mttr_status = "fail"
    else:
        mttr_status = "pass" if float(mttr_hours) <= max_mttr else "fail"

    if total_runs == 0:
        overall = "pending_no_runs"
    elif pass_status == "fail" or flaky_status == "fail" or mttr_status == "fail":
        overall = "fail"
    else:
        overall = "pass"

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.ci_history_metrics",
        "generated_at": _iso_utc(now),
        "synthetic": False,
        "source": {
            "mode": source,
            "repo": args.repo,
            "branch": args.branch,
            "workflows": list(workflows),
            "window_days": window_days,
        },
        "window": {
            "start": _iso_utc(window_start),
            "end": _iso_utc(now),
        },
        "metrics": {
            "run_count": int(total_runs),
            "pass_rate_percent": round(float(pass_rate), 3),
            "flaky_rate_percent": round(float(flaky_rate), 3),
            "mean_time_to_recovery_hours": None if mttr_hours is None else round(float(mttr_hours), 3),
            "failure_count": int(mttr_block.get("failure_count", 0)),
            "recovered_failure_count": int(mttr_block.get("recovered_failure_count", 0)),
            "unresolved_failure_count": int(mttr_block.get("unresolved_failure_count", 0)),
            "pass_count": int(passed_runs),
            "flaky_run_count": int(flaky_runs),
        },
        "thresholds": {
            "min_pass_rate_percent": float(min_pass),
            "max_flaky_rate_percent": float(max_flaky),
            "max_mttr_hours": float(max_mttr),
        },
        "status": {
            "pass_rate": pass_status,
            "flaky_rate": flaky_status,
            "mttr": mttr_status,
            "overall": overall,
        },
    }

    output_json = _resolve(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    output_md = _resolve(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(_render_markdown(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "output_json": str(output_json),
                "output_md": str(output_md),
                "run_count": total_runs,
                "overall": overall,
            },
            separators=(",", ":"),
        )
    )

    if bool(args.fail_on_threshold_breach) and overall == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
