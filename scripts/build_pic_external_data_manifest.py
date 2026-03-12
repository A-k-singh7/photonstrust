#!/usr/bin/env python3
"""Build manifest of external data needed for production PIC readiness closure."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_GATE_B = Path("results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json")
DEFAULT_GATE_E = Path("results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json")
DEFAULT_OUTPUT = Path("results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json")

ALLOWED_SOURCE_LICENSES: tuple[str, ...] = ("Apache-2.0", "MIT")

SOURCE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "source_id": "SRC-GDSFACTORY-CORE",
        "repository": "gdsfactory/gdsfactory",
        "url": "https://github.com/gdsfactory/gdsfactory",
        "license": "MIT",
        "areas": ["GateB"],
        "requirement_ids": ["EXT-B1", "EXT-B2", "EXT-B4"],
        "priority_by_requirement": {
            "EXT-B1": 1,
            "EXT-B2": 1,
            "EXT-B4": 1,
        },
        "role": "PIC flow primitives for deterministic model-vs-measurement correlation automation.",
        "artifacts": ["correlation tables", "lot split stats", "corner comparison reports"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-GDSFACTORY-GPLUGINS",
        "repository": "gdsfactory/gplugins",
        "url": "https://github.com/gdsfactory/gplugins",
        "license": "MIT",
        "areas": ["GateB"],
        "requirement_ids": ["EXT-B1", "EXT-B2", "EXT-B4", "EXT-B5"],
        "priority_by_requirement": {
            "EXT-B1": 2,
            "EXT-B2": 2,
            "EXT-B4": 2,
            "EXT-B5": 1,
        },
        "role": "Simulation and measurement plugin stack for extending Gate B packet evidence coverage.",
        "artifacts": ["post-processing utilities", "trend extracts", "batch regression helpers"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-SKYWATER-PDK",
        "repository": "google/skywater-pdk",
        "url": "https://github.com/google/skywater-pdk",
        "license": "Apache-2.0",
        "areas": ["GateB"],
        "requirement_ids": ["EXT-B4"],
        "priority_by_requirement": {
            "EXT-B4": 3,
        },
        "role": "Reference for process-corner and PDK data packaging conventions for delay/RC closure.",
        "artifacts": ["corner manifest patterns", "PDK metadata conventions"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-GF180MCU-PDK",
        "repository": "google/gf180mcu-pdk",
        "url": "https://github.com/google/gf180mcu-pdk",
        "license": "Apache-2.0",
        "areas": ["GateB"],
        "requirement_ids": ["EXT-B4"],
        "priority_by_requirement": {
            "EXT-B4": 4,
        },
        "role": "Additional open foundry collateral reference for RC/timing evidence normalization.",
        "artifacts": ["corner naming templates", "open PDK packaging patterns"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-APACHE-DEVLAKE",
        "repository": "apache/incubator-devlake",
        "url": "https://github.com/apache/incubator-devlake",
        "license": "Apache-2.0",
        "areas": ["GateE"],
        "requirement_ids": ["EXT-E1", "EXT-E3"],
        "priority_by_requirement": {
            "EXT-E1": 1,
            "EXT-E3": 1,
        },
        "role": "Ingest and normalize CI/issue telemetry into stable timeseries exports.",
        "artifacts": ["rolling pass-rate export", "flaky-rate export", "incident lead-time export"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-CHAOSS-AUGUR",
        "repository": "chaoss/augur",
        "url": "https://github.com/chaoss/augur",
        "license": "MIT",
        "areas": ["GateE"],
        "requirement_ids": ["EXT-E3"],
        "priority_by_requirement": {
            "EXT-E3": 2,
        },
        "role": "Issue and contribution analytics backbone for MTTR and triage-quality evidence.",
        "artifacts": ["MTTR distributions", "time-to-root-cause trends"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-DORA-FOURKEYS",
        "repository": "dora-team/fourkeys",
        "url": "https://github.com/dora-team/fourkeys",
        "license": "Apache-2.0",
        "areas": ["GateE"],
        "requirement_ids": ["EXT-E1", "EXT-E3"],
        "priority_by_requirement": {
            "EXT-E1": 4,
            "EXT-E3": 3,
        },
        "role": "Reference implementation for DORA-style CI and incident metric pipelines.",
        "artifacts": ["pipeline templates", "deployment/incident KPI aggregation"],
        "maintenance_status": "archived",
    },
    {
        "source_id": "SRC-OSSF-SCORECARD",
        "repository": "ossf/scorecard",
        "url": "https://github.com/ossf/scorecard",
        "license": "Apache-2.0",
        "areas": ["GateE"],
        "requirement_ids": ["EXT-E1"],
        "priority_by_requirement": {
            "EXT-E1": 2,
        },
        "role": "Supply-chain and CI hygiene signal source to strengthen CI stability evidence quality.",
        "artifacts": ["CI hygiene checks", "branch protection signal", "dependency policy checks"],
        "maintenance_status": "active",
    },
    {
        "source_id": "SRC-CHIPSALLIANCE-F4PGA",
        "repository": "chipsalliance/f4pga",
        "url": "https://github.com/chipsalliance/f4pga",
        "license": "Apache-2.0",
        "areas": ["GateE"],
        "requirement_ids": ["EXT-E1"],
        "priority_by_requirement": {
            "EXT-E1": 3,
        },
        "role": "Open hardware CI orchestration reference to reinforce deterministic automation patterns.",
        "artifacts": ["workflow templates", "reproducible CI stage breakdown"],
        "maintenance_status": "active",
    },
)

REQUIREMENT_EXECUTION_METADATA: dict[str, dict[str, str]] = {
    "EXT-B1": {
        "owner_role": "PIC Modeling Lead",
        "definition_of_done": "Measured insertion-loss bundle ingested and Gate B1 status is pass.",
    },
    "EXT-B2": {
        "owner_role": "PIC Device Characterization Lead",
        "definition_of_done": "Measured resonance bundle ingested and Gate B2 status is pass.",
    },
    "EXT-B4": {
        "owner_role": "PDK and Timing Correlation Lead",
        "definition_of_done": "Measured delay/RC bundle ingested and Gate B4 status is pass.",
    },
    "EXT-B5": {
        "owner_role": "Reliability and Drift Analytics Lead",
        "definition_of_done": "Measured drift history ingested and Gate B5 trend check status is pass.",
    },
    "EXT-E1": {
        "owner_role": "CI Platform and DevOps Lead",
        "definition_of_done": "Real CI history metrics ingested and Gate E1 status is pass (non-synthetic).",
    },
    "EXT-E3": {
        "owner_role": "Incident Response and SRE Lead",
        "definition_of_done": "Real triage analytics ingested and Gate E3 status is pass (non-synthetic).",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build external data manifest for PIC readiness closure")
    parser.add_argument("--gate-b", type=Path, default=DEFAULT_GATE_B, help="Gate B packet path")
    parser.add_argument("--gate-e", type=Path, default=DEFAULT_GATE_E, help="Gate E packet path")
    parser.add_argument("--rc-id", default="rc_next", help="Release candidate identifier for recommended paths")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output manifest path")
    return parser.parse_args()


def _resolve(path: Path, *, cwd: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _is_pending(status: str) -> bool:
    text = str(status or "").strip().lower()
    return text in {
        "pending",
        "pending_silicon_required",
        "pending_ci_history_required",
        "evidence_ready_pending_timeseries",
    }


def _priority_for_requirement(source: dict[str, Any], requirement_id: str) -> int:
    priority_by_requirement = _as_dict(source.get("priority_by_requirement"))
    raw_priority = priority_by_requirement.get(requirement_id)
    if isinstance(raw_priority, (int, float, str)):
        try:
            priority = int(raw_priority)
        except Exception:
            priority = 99
    else:
        priority = 99
    return max(1, priority)


def _build_source_candidates(
    *, requirements: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    requirement_ids = {
        str(row.get("id") or "")
        for row in requirements
        if isinstance(row, dict)
    }
    requirement_ids.discard("")

    by_requirement_pairs: dict[str, list[tuple[int, str]]] = {
        key: [] for key in sorted(requirement_ids)
    }
    by_requirement: dict[str, list[str]] = {key: [] for key in sorted(requirement_ids)}
    candidates: list[dict[str, Any]] = []

    allowed = set(ALLOWED_SOURCE_LICENSES)

    for source in SOURCE_CATALOG:
        source_license = str(source.get("license") or "")
        if source_license not in allowed:
            continue

        mapped = [
            requirement_id
            for requirement_id in source.get("requirement_ids", [])
            if isinstance(requirement_id, str) and requirement_id in requirement_ids
        ]
        if not mapped:
            continue

        source_id = str(source.get("source_id") or "")
        if not source_id:
            continue

        mapped_priorities: dict[str, int] = {}
        for requirement_id in mapped:
            mapped_priorities[requirement_id] = _priority_for_requirement(source, requirement_id)
            by_requirement_pairs.setdefault(requirement_id, []).append(
                (mapped_priorities[requirement_id], source_id)
            )

        integration_priority = min(mapped_priorities.values()) if mapped_priorities else 99

        candidates.append(
            {
                "source_id": source_id,
                "repository": str(source.get("repository") or ""),
                "url": str(source.get("url") or ""),
                "license": source_license,
                "areas": _as_str_list(source.get("areas")),
                "mapped_requirements": mapped,
                "priority_by_requirement": mapped_priorities,
                "integration_priority": int(integration_priority),
                "role": str(source.get("role") or ""),
                "artifacts": _as_str_list(source.get("artifacts")),
                "maintenance_status": str(source.get("maintenance_status") or "unknown"),
            }
        )

    for requirement_id, pairs in by_requirement_pairs.items():
        ordered = sorted(pairs, key=lambda item: (int(item[0]), item[1]))
        by_requirement[requirement_id] = [source_id for _, source_id in ordered]

    candidates.sort(
        key=lambda row: (
            int(row.get("integration_priority") or 99),
            str(row.get("repository") or ""),
            str(row.get("source_id") or ""),
        )
    )
    return candidates, by_requirement


def _build_integration_plan(
    *,
    requirements: list[dict[str, Any]],
    requirement_sources: dict[str, list[str]],
    source_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_by_id: dict[str, dict[str, Any]] = {}
    for candidate in source_candidates:
        source_id = str(candidate.get("source_id") or "")
        if source_id:
            source_by_id[source_id] = candidate

    plan: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        requirement_id = str(requirement.get("id") or "")
        ranked_ids = requirement_sources.get(requirement_id, [])
        ranked_sources: list[dict[str, Any]] = []

        for rank, source_id in enumerate(ranked_ids, start=1):
            source = source_by_id.get(source_id, {})
            ranked_sources.append(
                {
                    "rank": int(rank),
                    "source_id": source_id,
                    "repository": str(source.get("repository") or ""),
                    "license": str(source.get("license") or ""),
                    "maintenance_status": str(source.get("maintenance_status") or "unknown"),
                }
            )

        metadata = REQUIREMENT_EXECUTION_METADATA.get(requirement_id, {})
        plan.append(
            {
                "execution_order": int(index),
                "requirement_id": requirement_id,
                "area": str(requirement.get("area") or ""),
                "owner_role": str(metadata.get("owner_role") or "TBD"),
                "definition_of_done": str(
                    metadata.get("definition_of_done")
                    or "Replace synthetic inputs with production data and rerun the gate packet."
                ),
                "expected_path": str(requirement.get("expected_path") or ""),
                "primary_source_id": ranked_ids[0] if ranked_ids else None,
                "ranked_sources": ranked_sources,
            }
        )

    return plan


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()

    gate_b_path = _resolve(args.gate_b, cwd=cwd)
    gate_e_path = _resolve(args.gate_e, cwd=cwd)
    output_path = _resolve(args.output, cwd=cwd)

    gate_b = _load_json(gate_b_path)
    gate_e = _load_json(gate_e_path)

    gate_b_metrics = _as_dict(gate_b.get("metrics"))
    gate_e_metrics = _as_dict(gate_e.get("metrics"))

    rc_id = str(args.rc_id)
    recommended_root = f"datasets/measurements/private/{rc_id}"

    requirements: list[dict[str, Any]] = []

    b5 = _as_dict(gate_b_metrics.get("b5_drift"))
    if _is_pending(str(b5.get("status") or "")):
        requirements.extend(
            [
                {
                    "id": "EXT-B1",
                    "area": "GateB",
                    "description": "Measured insertion-loss bundle for production B1 correlation.",
                    "expected_path": f"{recommended_root}/b1_insertion_loss/measurement_bundle.json",
                },
                {
                    "id": "EXT-B2",
                    "area": "GateB",
                    "description": "Measured resonance bundle for production B2 correlation.",
                    "expected_path": f"{recommended_root}/b2_resonance/measurement_bundle.json",
                },
                {
                    "id": "EXT-B4",
                    "area": "GateB",
                    "description": "Measured delay/RC bundle for production B4 correlation.",
                    "expected_path": f"{recommended_root}/b4_delay_rc/measurement_bundle.json",
                },
                {
                    "id": "EXT-B5",
                    "area": "GateB",
                    "description": "Measured drift history bundle(s) for B5 trend stability validation.",
                    "expected_path": f"{recommended_root}/b5_drift/measurement_bundle.json",
                },
            ]
        )

    e1 = _as_dict(gate_e_metrics.get("e1_ci_stability"))
    e3 = _as_dict(gate_e_metrics.get("e3_failure_triage_quality"))

    e1_status = str(e1.get("status") or "")
    if _is_pending(e1_status) or str(e1.get("synthetic") or "").lower() == "true":
        requirements.append(
            {
                "id": "EXT-E1",
                "area": "GateE",
                "description": "Rolling CI stability export (pass-rate/flaky metrics).",
                "expected_path": "results/pic_readiness/governance/ci_history_metrics_real.json",
            }
        )

    e3_status = str(e3.get("status") or "")
    if _is_pending(e3_status) or str(e3.get("synthetic") or "").lower() == "true":
        requirements.append(
            {
                "id": "EXT-E3",
                "area": "GateE",
                "description": "Incident triage analytics export (MTTR/time-to-root-cause).",
                "expected_path": "results/pic_readiness/governance/triage_metrics_real.json",
            }
        )

    source_candidates, requirement_sources = _build_source_candidates(requirements=requirements)

    integration_plan = _build_integration_plan(
        requirements=requirements,
        requirement_sources=requirement_sources,
        source_candidates=source_candidates,
    )

    for requirement in requirements:
        requirement_id = str(requirement.get("id") or "")
        recommended_source_ids = requirement_sources.get(requirement_id, [])
        requirement["recommended_source_ids"] = recommended_source_ids
        requirement["primary_source_id"] = recommended_source_ids[0] if recommended_source_ids else None

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_external_data_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "gate_b": str(gate_b_path),
            "gate_e": str(gate_e_path),
            "rc_id": rc_id,
        },
        "requirements": requirements,
        "requirement_count": int(len(requirements)),
        "source_policy": {
            "allowed_licenses": list(ALLOWED_SOURCE_LICENSES),
            "license_policy": "allowlist_only",
            "notes": [
                "Only MIT and Apache-2.0 sources are included.",
                "Revalidate upstream repository license before operational adoption.",
            ],
        },
        "source_candidates": source_candidates,
        "source_candidate_count": int(len(source_candidates)),
        "requirement_to_source_ids": requirement_sources,
        "integration_plan": integration_plan,
        "integration_plan_count": int(len(integration_plan)),
        "note": "Provide these datasets/telemetry exports to replace preflight synthetic artifacts and close production readiness gates.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(output_path),
                "requirement_count": len(requirements),
                "source_candidate_count": len(source_candidates),
                "integration_plan_count": len(integration_plan),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
