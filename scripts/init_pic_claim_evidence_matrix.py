#!/usr/bin/env python3
"""Initialize a machine-readable PIC claim-to-evidence matrix for Gate E4."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("results/pic_readiness/governance/claim_evidence_matrix_2026-03-03.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize PIC claim-evidence matrix JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output matrix JSON path")
    parser.add_argument("--release-candidate", default="rc_missing_data_2026_03_03", help="Release candidate identifier")
    parser.add_argument("--force", action="store_true", help="Overwrite output file if it exists")
    return parser.parse_args()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_claims() -> list[dict[str, Any]]:
    boundary_doc = "docs/operations/pilot_readiness_packet/03_claim_boundaries_summary.md"
    return [
        {
            "claim_id": "CLM-EXT-001",
            "claim_text": "PhotonTrust provides simulation-and-evidence-based reliability assessments for scoped pilot scenarios.",
            "external": True,
            "status": "supported",
            "boundary_source_path": boundary_doc,
            "evidence_ids": ["EV-PIC-TAPEOUT-GATE", "EV-PIC-CD5-PACKET"],
            "evidence_paths": [
                "results/pic_readiness/tapeout_gate_report.json",
                "results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json",
            ],
            "notes": "Claim aligns with boundary document section 4 safe wording.",
        },
        {
            "claim_id": "CLM-EXT-002",
            "claim_text": "Results are valid within the documented operating envelope and evidence tier.",
            "external": True,
            "status": "supported",
            "boundary_source_path": boundary_doc,
            "evidence_ids": ["EV-PIC-GATE-B", "EV-PIC-GATE-CD5"],
            "evidence_paths": [
                "results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json",
                "results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json",
            ],
            "notes": "Gate B preflight is synthetic; production replacement with measured silicon required.",
        },
        {
            "claim_id": "CLM-EXT-003",
            "claim_text": "Pilot outputs support engineering decisions and are not formal certification.",
            "external": True,
            "status": "supported",
            "boundary_source_path": boundary_doc,
            "evidence_ids": ["EV-CLAIM-BOUNDARY", "EV-RELEASE-SIGNATURE"],
            "evidence_paths": [
                "docs/operations/pilot_readiness_packet/03_claim_boundaries_summary.md",
                "reports/specs/milestones/release_gate_packet_2026-02-16.ed25519.sig.json",
            ],
            "notes": "Boundary and governance controls explicitly prohibit over-claiming.",
        },
        {
            "claim_id": "CLM-EXT-004",
            "claim_text": "No hardware performance guarantee is asserted without customer measurement calibration.",
            "external": True,
            "status": "out_of_scope",
            "boundary_source_path": boundary_doc,
            "evidence_ids": ["EV-CLAIM-BOUNDARY"],
            "evidence_paths": [
                "docs/operations/pilot_readiness_packet/03_claim_boundaries_summary.md",
            ],
            "notes": "Explicitly treated as exclusion boundary in customer communication.",
        },
    ]


def _build_coverage(claims: list[dict[str, Any]]) -> dict[str, int]:
    external_claims = [row for row in claims if bool(row.get("external"))]
    mapped_external = [
        row
        for row in external_claims
        if isinstance(row.get("evidence_paths"), list) and len(row.get("evidence_paths") or []) > 0
    ]
    unmapped_external = len(external_claims) - len(mapped_external)
    return {
        "total_claims": int(len(claims)),
        "external_claims": int(len(external_claims)),
        "mapped_external_claims": int(len(mapped_external)),
        "unmapped_external_claims": int(unmapped_external),
    }


def main() -> int:
    args = parse_args()
    output = args.output.resolve() if args.output.is_absolute() else (Path.cwd() / args.output).resolve()
    if output.exists() and not bool(args.force):
        raise SystemExit(f"output exists, use --force to overwrite: {output}")

    claims = _make_claims()
    coverage = _build_coverage(claims)
    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_claim_evidence_matrix",
        "generated_at": _now_iso(),
        "release_candidate": str(args.release_candidate),
        "claims": claims,
        "coverage": coverage,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"matrix": str(output), "coverage": coverage}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
