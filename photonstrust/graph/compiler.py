"""Graph compiler (drag-drop UI graph -> engine configs or netlists)."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from photonstrust.components.pic.library import component_ports, supported_component_kinds
from photonstrust.graph.schema import validate_graph
from photonstrust.graph.spec import stable_graph_hash
from photonstrust.registry.kinds import build_kinds_registry


QKD_REQUIRED_KINDS = [
    "qkd.source",
    "qkd.channel",
    "qkd.detector",
    "qkd.timing",
    "qkd.protocol",
]


@dataclass(frozen=True)
class CompiledGraph:
    profile: str
    compiled: dict
    warnings: list[str]
    assumptions_md: str


def compile_graph(graph: dict, *, require_schema: bool = False) -> CompiledGraph:
    """Compile a graph dict.

    Profiles:
    - qkd_link: returns a PhotonTrust config dict consumable by `build_scenarios`.
    - pic_circuit: returns a normalized netlist dict (Phase 09 will execute it).
    """

    validate_graph(graph, require_jsonschema=require_schema)

    profile = str(graph.get("profile", "")).strip().lower()
    if profile == "qkd_link":
        return _compile_qkd_link(graph)
    if profile == "pic_circuit":
        return _compile_pic_circuit(graph)
    raise ValueError(f"Unsupported graph profile: {profile!r}")


def compile_graph_artifacts(
    graph: dict,
    output_dir: str | Path,
    *,
    require_schema: bool = False,
) -> dict:
    """Compile and write a set of artifacts to `output_dir`."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    compiled = compile_graph(graph, require_schema=require_schema)
    graph_id = str(graph.get("graph_id", "graph")).strip() or "graph"
    schema_version = str(graph.get("schema_version", "")).strip()
    graph_hash = stable_graph_hash(graph)

    # Always copy the input graph for provenance/replay.
    graph_path = output_dir / "graph.json"
    graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    compiled_path = None
    if compiled.profile == "qkd_link":
        compiled_path = output_dir / "compiled_config.yml"
        compiled_path.write_text(
            yaml.safe_dump(compiled.compiled, sort_keys=True),
            encoding="utf-8",
        )
    elif compiled.profile == "pic_circuit":
        compiled_path = output_dir / "compiled_netlist.json"
        compiled_path.write_text(json.dumps(compiled.compiled, indent=2), encoding="utf-8")

    assumptions_path = output_dir / "assumptions.md"
    assumptions_path.write_text(compiled.assumptions_md, encoding="utf-8")

    provenance = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": graph_id,
        "graph_schema_version": schema_version,
        "profile": compiled.profile,
        "graph_hash": graph_hash,
        "compiler": {
            "photonstrust_version": _photonstrust_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "artifacts": {
            "graph_path": str(graph_path.name),
            "compiled_path": str(compiled_path.name) if compiled_path else None,
            "assumptions_path": str(assumptions_path.name),
        },
        "warnings": compiled.warnings,
    }
    provenance_path = output_dir / "compile_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    return {
        "output_dir": str(output_dir),
        "graph_path": str(graph_path),
        "compiled_path": str(compiled_path) if compiled_path else None,
        "assumptions_path": str(assumptions_path),
        "provenance_path": str(provenance_path),
        "warnings": compiled.warnings,
    }


def _compile_qkd_link(graph: dict) -> CompiledGraph:
    warnings: list[str] = []
    schema_version = str(graph.get("schema_version", "")).strip()

    scenario = graph.get("scenario")
    if not isinstance(scenario, dict):
        raise ValueError("qkd_link graphs must include a top-level 'scenario' object.")

    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("graph.nodes must be a list")

    by_kind: dict[str, list[dict]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind", "")).strip().lower()
        by_kind.setdefault(kind, []).append(node)

    missing = [kind for kind in QKD_REQUIRED_KINDS if kind not in by_kind]
    if missing:
        raise ValueError(f"qkd_link graph missing required nodes: {missing}")

    dupes = [kind for kind in QKD_REQUIRED_KINDS if len(by_kind.get(kind, [])) != 1]
    if dupes:
        raise ValueError(f"qkd_link graph must contain exactly one of each required kind: {dupes}")

    def params(kind: str) -> dict:
        node = by_kind[kind][0]
        payload = node.get("params", {})
        if not isinstance(payload, dict):
            raise ValueError(f"node.params must be an object for kind={kind}")
        return payload

    config = {
        "scenario": scenario,
        "source": params("qkd.source"),
        "channel": params("qkd.channel"),
        "detector": params("qkd.detector"),
        "timing": params("qkd.timing"),
        "protocol": params("qkd.protocol"),
        "uncertainty": graph.get("uncertainty", {}) or {},
        "finite_key": graph.get("finite_key", {}) or {},
    }

    if config["uncertainty"] is None:
        config["uncertainty"] = {}
    if not isinstance(config["uncertainty"], dict):
        raise ValueError("graph.uncertainty must be an object when present")

    assumptions = (
        "# Graph Compile Assumptions\n\n"
        f"- profile: qkd_link\n"
        f"- graph_schema_version: {schema_version or 'unknown'}\n"
        "- Compilation output is a PhotonTrust YAML config dict consumable by `photonstrust run`.\n"
        "- Node params are passed through without physics interpretation at compile time.\n"
        "- Engine defaults/presets are applied later by `photonstrust.config.build_scenarios`.\n"
        "- Edges are currently informational only for qkd_link graphs (not required for compilation).\n"
    )
    return CompiledGraph(profile="qkd_link", compiled=config, warnings=warnings, assumptions_md=assumptions)


def _compile_pic_circuit(graph: dict) -> CompiledGraph:
    warnings: list[str] = []
    schema_version = str(graph.get("schema_version", "")).strip()

    circuit = graph.get("circuit")
    if not isinstance(circuit, dict):
        raise ValueError("pic_circuit graphs must include a top-level 'circuit' object.")

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("pic_circuit graphs must include 'nodes' and 'edges' lists.")

    node_by_id: dict[str, dict] = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("graph.nodes entries must be objects")
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            raise ValueError("node.id is required")
        if node_id in node_by_id:
            raise ValueError(f"Duplicate node id: {node_id}")
        node_by_id[node_id] = node

    kind_registry = build_kinds_registry()
    kind_meta: dict[str, dict[str, Any]] = {}
    for entry in kind_registry.get("kinds", []) or []:
        if isinstance(entry, dict) and str(entry.get("kind", "")).strip():
            kind_meta[str(entry.get("kind", "")).strip()] = entry

    supported = supported_component_kinds()
    ports_by_node: dict[str, Any] = {}
    port_domains_by_node: dict[str, dict[str, dict[str, str]]] = {}
    kind_by_node: dict[str, str] = {}

    for node_id, node in node_by_id.items():
        kind = str(node.get("kind", "")).strip().lower()
        kind_by_node[node_id] = kind
        if kind not in supported:
            raise ValueError(f"Unsupported PIC component kind: {kind!r}")

        params = node.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"node.params must be an object for node_id={node_id}")

        try:
            ports = component_ports(kind, params=params)
        except Exception as exc:
            raise ValueError(f"Could not resolve ports for node {node_id!r} kind {kind!r}: {exc}") from exc

        meta = kind_meta.get(kind, {})
        domain_map = _resolve_kind_port_domains(meta, kind=kind, ports=ports)
        ports_by_node[node_id] = ports
        port_domains_by_node[node_id] = domain_map

    normalized_edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("graph.edges entries must be objects")
        src = str(edge.get("from", "")).strip()
        dst = str(edge.get("to", "")).strip()
        if not src or not dst:
            raise ValueError("edge.from and edge.to are required")
        if src not in node_by_id:
            raise ValueError(f"edge.from refers to missing node: {src}")
        if dst not in node_by_id:
            raise ValueError(f"edge.to refers to missing node: {dst}")
        kind = edge.get("kind")
        if kind is None:
            kind = "optical"
        from_port = edge.get("from_port")
        to_port = edge.get("to_port")
        if from_port is None:
            from_port = "out"
        if to_port is None:
            to_port = "in"
        params = edge.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ValueError("edge.params must be an object when present")

        src_ports = ports_by_node[src]
        dst_ports = ports_by_node[dst]
        from_port_name = str(from_port)
        to_port_name = str(to_port)
        if from_port_name not in src_ports.out_ports:
            raise ValueError(
                f"Unknown from_port {from_port_name!r} for node {src!r} ({kind_by_node.get(src,'')})."
            )
        if to_port_name not in dst_ports.in_ports:
            raise ValueError(
                f"Unknown to_port {to_port_name!r} for node {dst!r} ({kind_by_node.get(dst,'')})."
            )

        edge_kind = str(kind).strip().lower()
        src_domain = port_domains_by_node[src]["out"].get(from_port_name, "optical")
        dst_domain = port_domains_by_node[dst]["in"].get(to_port_name, "optical")
        if src_domain != dst_domain:
            raise ValueError(
                f"Port domain mismatch for edge {src}:{from_port_name} -> {dst}:{to_port_name}: "
                f"{src_domain!r} -> {dst_domain!r}."
            )
        expected_domain = _expected_domain_for_edge_kind(edge_kind)
        if expected_domain is not None and src_domain != expected_domain:
            raise ValueError(
                f"Edge kind {edge_kind!r} is incompatible with port domain {src_domain!r} "
                f"for edge {src}:{from_port_name} -> {dst}:{to_port_name}."
            )

        normalized_edges.append(
            {
                "id": edge.get("id"),
                "from": src,
                "from_port": from_port_name,
                "to": dst,
                "to_port": to_port_name,
                "kind": str(kind),
                "label": edge.get("label"),
                "params": params,
            }
        )

    circuit_solver = str((circuit.get("solver") or "")).strip().lower()
    if not circuit_solver:
        circuit_solver = "dag"

    order: list[str] | None
    topology: dict
    try:
        order = _topological_order(node_by_id.keys(), normalized_edges)
        topology = {"is_dag": True, "topological_order": order}
    except ValueError as exc:
        msg = str(exc)
        if "cycle" in msg.lower() and circuit_solver in {"scattering", "scattering_network", "bidirectional_scattering"}:
            warnings.append("PIC graph contains a cycle; allowing because circuit.solver='scattering'.")
            topology = {"is_dag": False, "topological_order": []}
        else:
            raise

    normalized_nodes = []
    for node_id in sorted(node_by_id.keys(), key=lambda x: x.lower()):
        node = node_by_id[node_id]
        kind = str(node.get("kind", "")).strip()
        params = node.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"node.params must be an object for node_id={node_id}")
        normalized_nodes.append(
            {
                "id": node_id,
                "kind": kind,
                "label": node.get("label"),
                "params": params,
            }
        )

    normalized_edges.sort(
        key=lambda e: (
            str(e["from"]).lower(),
            str(e.get("from_port", "")).lower(),
            str(e["to"]).lower(),
            str(e.get("to_port", "")).lower(),
            str(e.get("kind", "")).lower(),
        )
    )

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": graph.get("graph_id"),
        "circuit": circuit,
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "topology": topology,
    }

    assumptions = (
        "# Graph Compile Assumptions\n\n"
        f"- profile: pic_circuit\n"
        f"- graph_schema_version: {schema_version or 'unknown'}\n"
        "- Compilation output is a normalized netlist only (no PIC physics executed in Phase 08).\n"
        "- The compiler enforces:\n"
        "  - unique node IDs\n"
        "  - valid edge endpoints\n"
        "  - deterministic topological ordering (tie-break by node id)\n"
        "- Phase 09 will define component models and execute this netlist.\n"
    )
    return CompiledGraph(profile="pic_circuit", compiled=netlist, warnings=warnings, assumptions_md=assumptions)


def _topological_order(node_ids, edges: list[dict]) -> list[str]:
    node_ids = [str(n) for n in node_ids]
    adjacency: dict[str, set[str]] = {node: set() for node in node_ids}
    indegree: dict[str, int] = {node: 0 for node in node_ids}

    for edge in edges:
        src = str(edge["from"])
        dst = str(edge["to"])
        if dst not in adjacency[src]:
            adjacency[src].add(dst)
            indegree[dst] += 1

    ready = sorted([node for node in node_ids if indegree[node] == 0], key=lambda x: x.lower())
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in sorted(adjacency[node], key=lambda x: x.lower()):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort(key=lambda x: x.lower())

    if len(order) != len(node_ids):
        raise ValueError("PIC graph has a cycle (topological sort failed).")
    return order


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


def _resolve_kind_port_domains(meta: dict[str, Any], *, kind: str, ports: Any) -> dict[str, dict[str, str]]:
    default_domain = "optical" if str(kind).startswith("pic.") else "control"
    out = {
        "in": {str(name): default_domain for name in list(getattr(ports, "in_ports", []) or [])},
        "out": {str(name): default_domain for name in list(getattr(ports, "out_ports", []) or [])},
    }

    pd = meta.get("port_domains") if isinstance(meta, dict) else None
    if not isinstance(pd, dict):
        return out

    for direction in ("in", "out"):
        maybe = pd.get(direction)
        if not isinstance(maybe, dict):
            continue
        for port_name, domain in maybe.items():
            port = str(port_name)
            if port in out[direction]:
                out[direction][port] = str(domain)
    return out


def _expected_domain_for_edge_kind(kind: str) -> str | None:
    key = str(kind or "").strip().lower()
    if key == "optical":
        return "optical"
    if key == "electrical":
        return "electrical"
    if key == "control":
        return "control"
    return None
