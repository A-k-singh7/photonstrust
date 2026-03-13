"""Verify release gate packet artifact hashes and approval structure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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


def _verify_approvals(approvals_payload: dict) -> list[str]:
    failures: list[str] = []
    approvers = approvals_payload.get("approvers")
    if not isinstance(approvers, list):
        return ["approvals must include an 'approvers' list"]

    for role in REQUIRED_APPROVER_ROLES:
        role_rows = [
            row
            for row in approvers
            if isinstance(row, dict) and str(row.get("role") or "").strip().upper() == role
        ]
        if not role_rows:
            failures.append(f"missing required approval role: {role}")
            continue
        if not any(bool(row.get("approved", False)) for row in role_rows):
            failures.append(f"approval role not approved: {role}")
    return failures


def verify_release_gate_packet(
    repo_root: Path,
    *,
    packet_path: Path,
    check_approvals: bool = True,
) -> tuple[bool, list[str], dict]:
    failures: list[str] = []
    resolved_packet = packet_path if packet_path.is_absolute() else (repo_root / packet_path)
    if not resolved_packet.exists():
        return False, [f"missing release gate packet: {resolved_packet}"], {}

    try:
        packet = json.loads(resolved_packet.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"failed to parse packet JSON: {exc}"], {}

    if not isinstance(packet, dict):
        return False, ["release gate packet must be a JSON object"], {}

    if str(packet.get("kind") or "") != "photonstrust.release_gate_packet":
        failures.append(f"unexpected packet kind: {packet.get('kind')}")

    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, list):
        failures.append("packet artifacts field must be a list")
        return False, failures, packet

    artifact_count = int(packet.get("artifact_count", -1))
    required_artifact_count = int(packet.get("required_artifact_count", -1))
    if artifact_count != len(artifacts):
        failures.append(f"artifact_count mismatch: header={artifact_count} actual={len(artifacts)}")
    if required_artifact_count < len(artifacts):
        failures.append(
            f"required_artifact_count smaller than actual artifacts: {required_artifact_count} < {len(artifacts)}"
        )

    for index, row in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(row, dict):
            failures.append(f"{label} must be an object")
            continue
        relpath = str(row.get("path") or "")
        expected_sha256 = str(row.get("sha256") or "")
        if not relpath:
            failures.append(f"{label} missing path")
            continue

        artifact_path = repo_root / Path(relpath)
        if not artifact_path.exists():
            failures.append(f"missing artifact file: {relpath}")
            continue

        actual_sha256 = _sha256_file(artifact_path)
        if expected_sha256 != actual_sha256:
            failures.append(f"artifact hash mismatch: {relpath}")

    if check_approvals:
        approvals = packet.get("approvals")
        if not isinstance(approvals, dict):
            failures.append("packet approvals section must be an object")
        else:
            failures.extend(_verify_approvals(approvals))

    return len(failures) == 0, failures, packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release gate packet integrity.")
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path("reports/specs/milestones/release_gate_packet_2026-02-16.json"),
        help="Path to release gate packet JSON file.",
    )
    parser.add_argument(
        "--check-approvals",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Verify required approval roles are present and approved (default: true).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    ok, failures, _packet = verify_release_gate_packet(
        repo_root,
        packet_path=args.packet,
        check_approvals=bool(args.check_approvals),
    )
    if ok:
        print("Release gate packet verify: PASS")
        print(str(args.packet if args.packet.is_absolute() else (repo_root / args.packet)))
        return 0

    print("Release gate packet verify: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
