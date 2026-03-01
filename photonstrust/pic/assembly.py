"""PIC chip assembly core helpers."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.spec import stable_graph_hash
from photonstrust.utils import hash_dict

_HEX_CHARS = set("0123456789abcdef")


def assemble_pic_chip(
    request: dict[str, Any],
    *,
    assembly_run_id: str | None = None,
    require_schema: bool = False,
) -> dict[str, Any]:
    """Compile + assemble a PIC graph into a normalized netlist and report."""

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    graph = request.get("graph")
    if not isinstance(graph, dict):
        raise TypeError("request.graph must be an object")

    compiled = compile_graph(graph, require_schema=require_schema)
    if str(compiled.profile).strip().lower() != "pic_circuit":
        raise ValueError("assemble_pic_chip requires graph.profile=pic_circuit")

    assembled_netlist = json.loads(json.dumps(compiled.compiled))
    graph_hash = stable_graph_hash(graph)
    output_hash = hash_dict(assembled_netlist)
    block_refs = _build_block_refs(graph=graph, assembled_netlist=assembled_netlist, graph_hash=graph_hash)

    stitched_links = _stitched_links(graph=graph, assembled_netlist=assembled_netlist)
    failed_links = 0
    status = "pass" if failed_links == 0 else "partial"

    report = {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "pic.chip_assembly",
        "assembly_run_id": _resolve_assembly_run_id(
            assembly_run_id=assembly_run_id,
            graph_hash=graph_hash,
            output_hash=output_hash,
        ),
        "inputs": {
            "graph_hash": graph_hash,
            "block_refs": block_refs,
        },
        "outputs": {
            "summary": {
                "status": status,
                "assembled_blocks": int(len(block_refs)),
                "output_hash": output_hash,
            }
        },
        "stitch": {
            "summary": {
                "status": status,
                "stitched_links": int(stitched_links),
                "failed_links": int(failed_links),
                "warnings": list(compiled.warnings or []),
            }
        },
        "provenance": {
            "photonstrust_version": _photonstrust_version() or "unknown",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    return {
        "report": report,
        "assembled_netlist": assembled_netlist,
    }


def _build_block_refs(
    *,
    graph: dict[str, Any],
    assembled_netlist: dict[str, Any],
    graph_hash: str,
) -> list[dict[str, Any]]:
    blocks = graph.get("blocks")
    instances = graph.get("instances")

    if isinstance(blocks, list) and isinstance(instances, list):
        block_by_id: dict[str, dict[str, Any]] = {}
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_id = str(block.get("id", "")).strip()
            if not block_id:
                continue
            block_by_id[block_id] = block

        refs: list[dict[str, Any]] = []
        ordered_instances = sorted(
            [row for row in instances if isinstance(row, dict)],
            key=lambda row: str(row.get("id", "")).strip().lower(),
        )
        for instance in ordered_instances:
            instance_id = str(instance.get("id", "")).strip()
            block_id = str(instance.get("block", "")).strip()
            if not instance_id or not block_id:
                continue

            block_payload = block_by_id.get(block_id, {"id": block_id})
            instance_params = instance.get("params")
            if not isinstance(instance_params, dict):
                instance_params = {}
            artifact_hash = hash_dict(
                {
                    "block_id": block_id,
                    "instance_id": instance_id,
                    "block": block_payload,
                    "instance_params": instance_params,
                }
            )
            run_id = hash_dict(
                {
                    "graph_hash": graph_hash,
                    "block_id": block_id,
                    "instance_id": instance_id,
                }
            )[:12]
            refs.append(
                {
                    "block_id": f"{block_id}::{instance_id}",
                    "run_id": run_id,
                    "artifact_hash": artifact_hash,
                    "status": "ready",
                    "kind": "pic.block_instance",
                    "note": f"instance={instance_id}",
                }
            )
        if refs:
            return refs

    flat_artifact_hash = hash_dict(
        {
            "graph_hash": graph_hash,
            "assembled_netlist": assembled_netlist,
        }
    )
    flat_run_id = hash_dict({"graph_hash": graph_hash, "mode": "flat"})[:12]
    return [
        {
            "block_id": "flat_graph",
            "run_id": flat_run_id,
            "artifact_hash": flat_artifact_hash,
            "status": "ready",
            "kind": "pic.flat",
            "note": "legacy nodes/edges graph synthesized as one flat block",
        }
    ]


def _stitched_links(*, graph: dict[str, Any], assembled_netlist: dict[str, Any]) -> int:
    nets = graph.get("nets")
    if isinstance(nets, list):
        return int(sum(1 for row in nets if isinstance(row, dict)))
    edges = assembled_netlist.get("edges")
    if isinstance(edges, list):
        return int(sum(1 for row in edges if isinstance(row, dict)))
    return 0


def _resolve_assembly_run_id(*, assembly_run_id: str | None, graph_hash: str, output_hash: str) -> str:
    rid = str(assembly_run_id or "").strip().lower()
    if 8 <= len(rid) <= 64 and all(ch in _HEX_CHARS for ch in rid):
        return rid
    return hash_dict({"kind": "pic_chip_assembly", "graph_hash": graph_hash, "output_hash": output_hash})[:12]


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        # Source checkout fallback.
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None
