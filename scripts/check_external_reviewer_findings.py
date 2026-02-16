"""Validate external reviewer dry-run findings for release readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_SEVERITIES = frozenset({"critical", "major", "minor"})
ALLOWED_STATUSES = frozenset({"open", "in_progress", "resolved", "accepted_risk"})
PASSING_RECOMMENDATIONS = frozenset({"go", "conditional_go"})


def evaluate_external_reviewer_report(report: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    recommendation = str(report.get("go_recommendation") or "").strip().lower()
    if recommendation not in PASSING_RECOMMENDATIONS.union({"no_go"}):
        failures.append("go_recommendation must be one of: go, conditional_go, no_go")
    elif recommendation == "no_go":
        failures.append("go_recommendation is no_go")

    findings = report.get("findings")
    if not isinstance(findings, list):
        failures.append("findings must be a JSON list")
        return False, failures

    for index, finding in enumerate(findings):
        label = f"finding[{index}]"
        if not isinstance(finding, dict):
            failures.append(f"{label} must be an object")
            continue

        severity = str(finding.get("severity") or "").strip().lower()
        status = str(finding.get("status") or "").strip().lower()
        if severity not in ALLOWED_SEVERITIES:
            failures.append(f"{label} has invalid severity '{severity}'")
            continue
        if status not in ALLOWED_STATUSES:
            failures.append(f"{label} has invalid status '{status}'")
            continue

        if severity == "critical" and status not in {"resolved", "accepted_risk"}:
            finding_id = str(finding.get("id") or label)
            failures.append(f"critical finding unresolved: {finding_id}")

    return len(failures) == 0, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check external reviewer dry-run findings.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/specs/milestones/external_reviewer_dry_run_2026-02-16.json"),
        help="Path to structured external reviewer report JSON.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report_path = args.report if args.report.is_absolute() else (repo_root / args.report)

    if not report_path.exists():
        print("External reviewer findings: FAIL")
        print(f" - missing report: {report_path}")
        return 1

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("External reviewer findings: FAIL")
        print(f" - failed to parse JSON: {exc}")
        return 1

    ok, failures = evaluate_external_reviewer_report(report)
    if ok:
        print("External reviewer findings: PASS")
        print(str(report_path))
        return 0

    print("External reviewer findings: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
