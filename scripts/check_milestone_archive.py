"""Check milestone archive completeness for a release cycle date."""

from __future__ import annotations

import argparse
from pathlib import Path


def required_archive_paths(cycle_date: str) -> tuple[str, ...]:
    prefix = f"reports/specs/milestones"
    return (
        f"{prefix}/milestone_readiness_ga_{cycle_date}.md",
        f"{prefix}/regression_baseline_gate_{cycle_date}.md",
        f"{prefix}/reliability_card_quality_review_{cycle_date}.md",
        f"{prefix}/external_reviewer_dry_run_{cycle_date}.md",
        f"{prefix}/external_reviewer_dry_run_{cycle_date}.json",
        f"{prefix}/external_reviewer_severity_closure_plan_{cycle_date}.md",
        f"{prefix}/release_approvals_{cycle_date}.json",
        f"{prefix}/rc_baseline_lock_{cycle_date}.json",
        f"{prefix}/release_gate_packet_{cycle_date}.json",
        f"{prefix}/release_gate_packet_{cycle_date}.ed25519.sig.json",
        f"{prefix}/ga_release_bundle_manifest_{cycle_date}.json",
        f"{prefix}/ga_replay_matrix_{cycle_date}.json",
        f"{prefix}/release_gate_v1_0_{cycle_date}.md",
        f"reports/specs/release_notes_v0.1.0_ga_{cycle_date}.md",
    )


def check_milestone_archive(repo_root: Path, *, cycle_date: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for relpath in required_archive_paths(cycle_date):
        full_path = repo_root / Path(relpath)
        if not full_path.exists():
            failures.append(f"missing archive artifact: {relpath}")
    return len(failures) == 0, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release milestone archive completeness.")
    parser.add_argument(
        "--cycle-date",
        default="2026-02-16",
        help="Release cycle date suffix used in archived artifact filenames.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ok, failures = check_milestone_archive(repo_root, cycle_date=str(args.cycle_date))
    if ok:
        print("Milestone archive check: PASS")
        print(f"cycle_date={args.cycle_date}")
        return 0

    print("Milestone archive check: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
