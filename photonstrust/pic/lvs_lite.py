"""M1 schematic-vs-compiled-netlist LVS-lite checks."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_netlist_payload(compiled_netlist: dict | object) -> dict[str, Any]:
    if isinstance(compiled_netlist, dict):
        if isinstance(compiled_netlist.get("nodes"), list) and isinstance(compiled_netlist.get("edges"), list):
            return dict(compiled_netlist)
        nested = compiled_netlist.get("compiled")
        if isinstance(nested, dict):
            return _extract_netlist_payload(nested)
        raise TypeError("compiled_netlist dict must include 'nodes' and 'edges'")

    nested = getattr(compiled_netlist, "compiled", None)
    if isinstance(nested, dict):
        return _extract_netlist_payload(nested)
    raise TypeError("compiled_netlist must be a dict or object with dict attribute .compiled")


def _normalize_nodes(raw_nodes: Any) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    if not isinstance(raw_nodes, list):
        return nodes
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        node_id = _clean_text(raw.get("id"))
        if not node_id:
            continue
        nodes.append({"id": node_id, "kind": _clean_text(raw.get("kind")).lower()})
    nodes.sort(key=lambda row: (row["id"].lower(), row["id"], row["kind"].lower(), row["kind"]))
    return nodes


def _normalize_edges(raw_edges: Any) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    if not isinstance(raw_edges, list):
        return edges
    for raw in raw_edges:
        if not isinstance(raw, dict):
            continue
        src = _clean_text(raw.get("from"))
        dst = _clean_text(raw.get("to"))
        if not src or not dst:
            continue
        from_port = _clean_text(raw.get("from_port")) or "out"
        to_port = _clean_text(raw.get("to_port")) or "in"
        key = f"{src}.{from_port}->{dst}.{to_port}"
        edges.append(
            {
                "from": src,
                "from_port": from_port,
                "to": dst,
                "to_port": to_port,
                "key": key,
            }
        )
    edges.sort(key=lambda row: (row["key"].lower(), row["key"]))
    return edges


def _node_kind_map(nodes: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in nodes:
        node_id = row["id"]
        if node_id not in out:
            out[node_id] = row["kind"]
    return out


def _counter_diff_rows(expected: Counter[str], observed: Counter[str], *, prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = sorted(set(expected.keys()).union(observed.keys()), key=lambda t: (t.lower(), t))
    for key in keys:
        expected_count = int(expected.get(key, 0))
        observed_count = int(observed.get(key, 0))
        if expected_count > observed_count:
            for idx in range(expected_count - observed_count):
                rows.append(
                    {
                        "id": f"{prefix}:missing:{key}:{idx + 1}",
                        "type": "missing",
                        "edge": key,
                        "expected_count": expected_count,
                        "observed_count": observed_count,
                    }
                )
        elif observed_count > expected_count:
            for idx in range(observed_count - expected_count):
                rows.append(
                    {
                        "id": f"{prefix}:unexpected:{key}:{idx + 1}",
                        "type": "unexpected",
                        "edge": key,
                        "expected_count": expected_count,
                        "observed_count": observed_count,
                    }
                )
    rows.sort(key=lambda row: (str(row.get("id", "")).lower(), str(row.get("id", ""))))
    return rows


def run_lvs_lite(graph: dict, compiled_netlist: dict | object) -> dict:
    if not isinstance(graph, dict):
        raise TypeError("graph must be an object")

    netlist = _extract_netlist_payload(compiled_netlist)

    graph_nodes = _normalize_nodes(graph.get("nodes"))
    compiled_nodes = _normalize_nodes(netlist.get("nodes"))
    graph_edges = _normalize_edges(graph.get("edges"))
    compiled_edges = _normalize_edges(netlist.get("edges"))

    graph_kind_by_id = _node_kind_map(graph_nodes)
    compiled_kind_by_id = _node_kind_map(compiled_nodes)

    graph_edge_counter = Counter(edge["key"] for edge in graph_edges)
    compiled_edge_counter = Counter(edge["key"] for edge in compiled_edges)

    graph_node_ids = sorted(graph_kind_by_id.keys(), key=lambda t: (t.lower(), t))
    compiled_node_ids = sorted(compiled_kind_by_id.keys(), key=lambda t: (t.lower(), t))

    block_count_pass = len(graph_nodes) == len(compiled_nodes)
    block_count_mismatches: list[dict[str, Any]] = []
    if not block_count_pass:
        missing_ids = sorted(set(graph_node_ids) - set(compiled_node_ids), key=lambda t: (t.lower(), t))
        extra_ids = sorted(set(compiled_node_ids) - set(graph_node_ids), key=lambda t: (t.lower(), t))
        for node_id in missing_ids:
            block_count_mismatches.append(
                {
                    "id": f"block_count:missing:{node_id}",
                    "type": "missing",
                    "instance_id": node_id,
                }
            )
        for node_id in extra_ids:
            block_count_mismatches.append(
                {
                    "id": f"block_count:unexpected:{node_id}",
                    "type": "unexpected",
                    "instance_id": node_id,
                }
            )
        if not block_count_mismatches:
            block_count_mismatches.append(
                {
                    "id": "block_count:count_mismatch",
                    "type": "count_mismatch",
                    "graph_count": int(len(graph_nodes)),
                    "compiled_count": int(len(compiled_nodes)),
                }
            )
        block_count_mismatches.sort(key=lambda row: (str(row.get("id", "")).lower(), str(row.get("id", ""))))

    connection_count_pass = len(graph_edges) == len(compiled_edges)
    connection_count_mismatches = (
        _counter_diff_rows(graph_edge_counter, compiled_edge_counter, prefix="connection_count")
        if not connection_count_pass
        else []
    )

    port_mapping_mismatches = _counter_diff_rows(graph_edge_counter, compiled_edge_counter, prefix="port_mapping")
    port_mapping_pass = len(port_mapping_mismatches) == 0

    kind_preservation_mismatches: list[dict[str, Any]] = []
    instance_ids = sorted(set(graph_node_ids).union(compiled_node_ids), key=lambda t: (t.lower(), t))
    for node_id in instance_ids:
        in_graph = node_id in graph_kind_by_id
        in_compiled = node_id in compiled_kind_by_id
        if not in_compiled:
            kind_preservation_mismatches.append(
                {
                    "id": f"kind_preservation:missing_compiled:{node_id}",
                    "type": "missing_compiled_instance",
                    "instance_id": node_id,
                    "expected_kind": graph_kind_by_id.get(node_id),
                    "compiled_kind": None,
                }
            )
            continue
        if not in_graph:
            kind_preservation_mismatches.append(
                {
                    "id": f"kind_preservation:unexpected_compiled:{node_id}",
                    "type": "unexpected_compiled_instance",
                    "instance_id": node_id,
                    "expected_kind": None,
                    "compiled_kind": compiled_kind_by_id.get(node_id),
                }
            )
            continue

        expected_kind = graph_kind_by_id.get(node_id, "")
        compiled_kind = compiled_kind_by_id.get(node_id, "")
        if expected_kind != compiled_kind:
            kind_preservation_mismatches.append(
                {
                    "id": f"kind_preservation:kind_mismatch:{node_id}",
                    "type": "kind_mismatch",
                    "instance_id": node_id,
                    "expected_kind": expected_kind,
                    "compiled_kind": compiled_kind,
                }
            )

    kind_preservation_mismatches.sort(key=lambda row: (str(row.get("id", "")).lower(), str(row.get("id", ""))))
    kind_preservation_pass = len(kind_preservation_mismatches) == 0

    checks = {
        "block_count": {
            "pass": bool(block_count_pass),
            "graph_count": int(len(graph_nodes)),
            "compiled_count": int(len(compiled_nodes)),
        },
        "connection_count": {
            "pass": bool(connection_count_pass),
            "graph_count": int(len(graph_edges)),
            "compiled_count": int(len(compiled_edges)),
        },
        "port_mapping": {
            "pass": bool(port_mapping_pass),
            "checked_edges": int(len(graph_edges)),
            "mismatch_count": int(len(port_mapping_mismatches)),
        },
        "kind_preservation": {
            "pass": bool(kind_preservation_pass),
            "checked_instances": int(len(set(graph_node_ids).union(compiled_node_ids))),
            "mismatch_count": int(len(kind_preservation_mismatches)),
        },
    }

    failed_checks = [name for name in ("block_count", "connection_count", "port_mapping", "kind_preservation") if not checks[name]["pass"]]

    return {
        "schema_version": "0.1",
        "kind": "pic.lvs_lite_m1",
        "pass": len(failed_checks) == 0,
        "checks": checks,
        "mismatches": {
            "block_count": block_count_mismatches,
            "connection_count": connection_count_mismatches,
            "port_mapping": port_mapping_mismatches,
            "kind_preservation": kind_preservation_mismatches,
        },
        "summary": {
            "failed_checks": failed_checks,
            "failure_count": int(len(failed_checks)),
        },
    }
