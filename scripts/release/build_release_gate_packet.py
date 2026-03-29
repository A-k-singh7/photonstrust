"""Build a machine-readable release gate packet manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from release_gate_paths import DEFAULT_APPROVALS_PATH, DEFAULT_PACKET_PATH
from photonstrust.utils import hash_dict


DEFAULT_REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "reports/specs/milestones/rc_baseline_lock_2026-02-16.json",
    "reports/specs/milestones/milestone_readiness_ga_2026-02-16.md",
    "reports/specs/milestones/regression_baseline_gate_2026-02-16.md",
    "reports/specs/milestones/reliability_card_quality_review_2026-02-16.md",
    "reports/specs/milestones/external_reviewer_dry_run_2026-02-16.md",
    "reports/specs/milestones/external_reviewer_dry_run_2026-02-16.json",
    "reports/specs/milestones/external_reviewer_severity_closure_plan_2026-02-16.md",
    "reports/specs/milestones/release_gate_v1_0_2026-02-16.md",
    "reports/specs/milestones/release_approvals_2026-02-16.json",
    "reports/specs/release_notes_v0.1.0_ga_2026-02-16.md",
    "CHANGELOG.md",
    "results/release_gate/release_gate_report.json",
)

DEFAULT_APPROVALS_RELPATH = str(DEFAULT_APPROVALS_PATH)
REQUIRED_APPROVER_ROLES: tuple[str, ...] = ("TL", "QA", "DOC")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_relpath(path: str) -> str:
    return str(Path(path)).replace("\\", "/")


def _validate_approvals_payload(approvals_payload: dict) -> list[str]:
    failures: list[str] = []
    approvers = approvals_payload.get("approvers")
    if not isinstance(approvers, list):
        return ["approvals file must contain an 'approvers' list"]

    for role in REQUIRED_APPROVER_ROLES:
        role_matches = [
            item
            for item in approvers
            if isinstance(item, dict) and str(item.get("role") or "").strip().upper() == role
        ]
        if not role_matches:
            failures.append(f"missing required approver role: {role}")
            continue
        approved = any(bool(item.get("approved", False)) for item in role_matches)
        if not approved:
            failures.append(f"required approver role not approved: {role}")

    return failures


def build_release_gate_packet(
    repo_root: Path,
    *,
    required_artifacts: Sequence[str] = DEFAULT_REQUIRED_ARTIFACTS,
    approvals_relpath: str = DEFAULT_APPROVALS_RELPATH,
    generated_at: str | None = None,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    artifacts: list[dict] = []

    for relpath in required_artifacts:
        normalized = _normalize_relpath(relpath)
        full_path = repo_root / Path(relpath)
        if not full_path.exists():
            failures.append(f"missing required artifact: {normalized}")
            continue
        artifacts.append(
            {
                "path": normalized,
                "sha256": _sha256_file(full_path),
                "bytes": int(full_path.stat().st_size),
            }
        )

    approvals_path = repo_root / Path(approvals_relpath)
    approvals_payload: dict = {}
    approvals_sha256 = ""
    if approvals_path.exists():
        try:
            approvals_payload = json.loads(approvals_path.read_text(encoding="utf-8"))
            if isinstance(approvals_payload, dict):
                failures.extend(_validate_approvals_payload(approvals_payload))
            else:
                failures.append("approvals file must be a JSON object")
                approvals_payload = {}
        except Exception as exc:
            failures.append(f"failed to parse approvals file: {exc}")
            approvals_payload = {}
        approvals_sha256 = _sha256_file(approvals_path)
    else:
        failures.append(f"missing approvals file: {_normalize_relpath(approvals_relpath)}")

    artifacts.sort(key=lambda row: str(row["path"]).lower())
    artifact_set_hash = hash_dict(
        {
            "artifacts": [
                {"path": str(row["path"]), "sha256": str(row["sha256"])} for row in artifacts
            ],
            "approvals_sha256": approvals_sha256,
        }
    )

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.release_gate_packet",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "required_artifact_count": len(tuple(required_artifacts)),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "approvals": approvals_payload,
        "artifact_set_sha256": artifact_set_hash,
    }
    return packet, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build release gate packet manifest.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PACKET_PATH,
        help="Path to write release gate packet JSON.",
    )
    parser.add_argument(
        "--approvals",
        type=Path,
        default=DEFAULT_APPROVALS_PATH,
        help="Path to approvals JSON file.",
    )
    parser.add_argument(
        "--required-artifact",
        dest="required_artifacts",
        action="append",
        default=None,
        help="Additional required artifact relpath. Repeat to override defaults.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    required_artifacts: Sequence[str]
    if args.required_artifacts:
        required_artifacts = tuple(str(item) for item in args.required_artifacts)
    else:
        required_artifacts = DEFAULT_REQUIRED_ARTIFACTS

    packet, failures = build_release_gate_packet(
        repo_root,
        required_artifacts=required_artifacts,
        approvals_relpath=str(args.approvals),
    )

    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(packet, indent=2))

    if failures:
        print("Release gate packet: FAIL")
        for line in failures:
            print(f" - {line}")
        print(str(output_path))
        return 1

    print("Release gate packet: PASS")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
