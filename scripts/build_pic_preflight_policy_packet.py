#!/usr/bin/env python3
"""Build a PIC preflight policy packet manifest with deterministic hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from photonstrust.utils import hash_dict


DEFAULT_ARTIFACTS: tuple[str, ...] = (
    "results/pic_readiness/tapeout_gate_report.json",
    "results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json",
    "results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json",
    "results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json",
    "results/pic_readiness/scorecard/pic_readiness_scorecard_2026-03-03.json",
)

DEFAULT_POLICY_DOCS: tuple[str, ...] = (
    "docs/operations/pic_foundry_readiness_95_checklist.md",
    "docs/operations/pic_foundry_readiness_95_execution_2026-03-03.md",
    "docs/operations/pic_gate_b_correlation_packet_template.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PIC preflight policy packet")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.json"),
        help="Output packet path",
    )
    parser.add_argument(
        "--artifact",
        dest="artifacts",
        action="append",
        default=None,
        help="Artifact relpath to include. Repeat; overrides defaults when provided.",
    )
    parser.add_argument(
        "--policy-doc",
        dest="policy_docs",
        action="append",
        default=None,
        help="Policy document relpath to include. Repeat; overrides defaults when provided.",
    )
    parser.add_argument(
        "--run-id",
        default="pic_preflight_2026-03-03",
        help="Logical run identifier embedded in packet",
    )
    return parser.parse_args()


def _normalize(path: str) -> str:
    return str(Path(path)).replace("\\", "/")


def _resolve(path: str, *, repo_root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_entries(paths: Sequence[str], *, repo_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for rel in paths:
        normalized = _normalize(rel)
        full = _resolve(rel, repo_root=repo_root)
        if not full.exists():
            failures.append(f"missing artifact: {normalized}")
            continue
        rows.append(
            {
                "path": normalized,
                "sha256": _sha256(full),
                "bytes": int(full.stat().st_size),
            }
        )
    rows.sort(key=lambda row: str(row["path"]).lower())
    return rows, failures


def build_packet(
    *,
    repo_root: Path,
    artifacts: Sequence[str],
    policy_docs: Sequence[str],
    run_id: str,
) -> tuple[dict[str, Any], list[str]]:
    artifact_rows, artifact_failures = _collect_entries(artifacts, repo_root=repo_root)
    policy_rows, policy_failures = _collect_entries(policy_docs, repo_root=repo_root)
    failures = artifact_failures + policy_failures

    policy_hash = hash_dict(
        {
            "artifacts": [{"path": row["path"], "sha256": row["sha256"]} for row in artifact_rows],
            "policy_docs": [{"path": row["path"], "sha256": row["sha256"]} for row in policy_rows],
        }
    )

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_preflight_policy_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": str(run_id),
        "artifact_count": int(len(artifact_rows)),
        "policy_doc_count": int(len(policy_rows)),
        "artifacts": artifact_rows,
        "policy_docs": policy_rows,
        "policy_hash_sha256": policy_hash,
    }
    return packet, failures


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    artifacts = tuple(str(item) for item in (args.artifacts or DEFAULT_ARTIFACTS))
    policy_docs = tuple(str(item) for item in (args.policy_docs or DEFAULT_POLICY_DOCS))

    packet, failures = build_packet(
        repo_root=repo_root,
        artifacts=artifacts,
        policy_docs=policy_docs,
        run_id=str(args.run_id),
    )

    output = args.output if args.output.is_absolute() else (repo_root / args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    if failures:
        print("PIC preflight policy packet: FAIL")
        for row in failures:
            print(f" - {row}")
        print(str(output))
        return 1

    print("PIC preflight policy packet: PASS")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
