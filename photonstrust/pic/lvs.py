"""Netlist-level LVS connectivity compare helpers for PIC routes."""

from __future__ import annotations

from typing import Any

from photonstrust.components.pic.library import component_ports
from photonstrust.graph.compiler import compile_graph
from photonstrust.layout.pic.extract_connectivity import extract_connectivity_from_routes


def compare_schematic_vs_routes(
    graph: dict[str, Any],
    routes: dict[str, Any],
    ports: dict[str, Any] | None = None,
    coord_tol_um: float = 1e-6,
) -> dict[str, Any]:
    """Compare compiled schematic connectivity against observed routed connectivity.

    Args:
      graph: PIC graph (profile=pic_circuit).
      routes: routes sidecar object.
      ports: optional ports sidecar object. When provided, observed connectivity is
        extracted by snapping route endpoints to ports within coord_tol_um.
      coord_tol_um: endpoint snap tolerance in um.

    Returns:
      Deterministic diff summary with mismatch buckets:
      - missing_connections
      - extra_connections
      - port_mapping_mismatches
      - unconnected_ports
    """

    if not isinstance(graph, dict):
        raise TypeError("graph must be an object")
    if not isinstance(routes, dict):
        raise TypeError("routes must be an object")
    if ports is not None and not isinstance(ports, dict):
        raise TypeError("ports must be an object when provided")

    tol = float(coord_tol_um)
    if tol <= 0.0:
        raise ValueError("coord_tol_um must be > 0")

    compiled = compile_graph(graph, require_schema=False)
    netlist = compiled.compiled

    expected_connections = _collect_expected_connections(netlist)
    expected_by_undirected_key = _to_undirected_map(expected_connections)

    observed_connections, dangling_routes, warnings = _collect_observed_connections(
        routes=routes,
        ports=ports,
        coord_tol_um=tol,
    )
    observed_by_undirected_key = _to_undirected_map(observed_connections)

    roles_by_ref = _collect_port_roles(netlist)

    missing_connections = _missing_connections(expected_by_undirected_key, observed_by_undirected_key)
    extra_connections = _extra_connections(expected_by_undirected_key, observed_by_undirected_key)
    port_mapping_mismatches = _port_mapping_mismatches(
        expected_by_undirected_key=expected_by_undirected_key,
        observed_by_undirected_key=observed_by_undirected_key,
        roles_by_ref=roles_by_ref,
    )
    unconnected_ports = _unconnected_ports(
        expected_connections=expected_connections,
        observed_connections=observed_connections,
        dangling_routes=dangling_routes,
    )

    summary = {
        "pass": (
            len(missing_connections) == 0
            and len(extra_connections) == 0
            and len(port_mapping_mismatches) == 0
            and len(unconnected_ports) == 0
        ),
        "missing_connections": int(len(missing_connections)),
        "extra_connections": int(len(extra_connections)),
        "port_mapping_mismatches": int(len(port_mapping_mismatches)),
        "unconnected_ports": int(len(unconnected_ports)),
    }

    return {
        "schema_version": "0.1",
        "kind": "pic.local_lvs_compare",
        "settings": {
            "coord_tol_um": tol,
            "ports_provided": bool(ports is not None),
        },
        "expected": {
            "connections": expected_connections,
            "connections_count": int(len(expected_connections)),
        },
        "observed": {
            "connections": observed_connections,
            "connections_count": int(len(observed_connections)),
            "dangling_routes": dangling_routes,
            "warnings": warnings,
        },
        "mismatches": {
            "missing_connections": missing_connections,
            "extra_connections": extra_connections,
            "port_mapping_mismatches": port_mapping_mismatches,
            "unconnected_ports": unconnected_ports,
        },
        "summary": summary,
    }


def _collect_expected_connections(netlist: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for edge in (netlist.get("edges") or []):
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from", "")).strip()
        dst = str(edge.get("to", "")).strip()
        if not src or not dst:
            continue
        out.append(
            {
                "from": src,
                "from_port": str(edge.get("from_port", "out")).strip() or "out",
                "to": dst,
                "to_port": str(edge.get("to_port", "in")).strip() or "in",
            }
        )

    out.sort(key=lambda e: (e["from"].lower(), e["from_port"].lower(), e["to"].lower(), e["to_port"].lower()))
    return out


def _collect_observed_connections(
    *,
    routes: dict[str, Any],
    ports: dict[str, Any] | None,
    coord_tol_um: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if ports is not None:
        extracted = extract_connectivity_from_routes(routes, ports, tol_um=coord_tol_um)
        observed = list(extracted.edges)
        dangling = list(extracted.dangling_routes)
        warnings = list(extracted.warnings)
        observed.sort(
            key=lambda e: (
                str((e.get("a") or {}).get("node", "")).lower(),
                str((e.get("a") or {}).get("port", "")).lower(),
                str((e.get("b") or {}).get("node", "")).lower(),
                str((e.get("b") or {}).get("port", "")).lower(),
                str(e.get("route_id", "")).lower(),
            )
        )
        dangling.sort(key=lambda d: str(d.get("route_id", "")).lower())
        warnings.sort(key=lambda w: str(w).lower())
        return observed, dangling, warnings

    route_rows = routes.get("routes") if isinstance(routes, dict) else None
    if not isinstance(route_rows, list):
        raise TypeError("routes.routes must be a list")

    observed: list[dict[str, Any]] = []
    warnings: list[str] = []

    for idx, route in enumerate(route_rows):
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "")).strip() or f"route_{idx}"
        parsed = _parse_route_connection(route)
        if parsed is None:
            warnings.append(f"{route_id}: could not infer endpoints from route metadata")
            continue
        a, b = parsed
        if a == b:
            warnings.append(f"{route_id}: route endpoints resolve to the same node/port")
            continue
        observed.append(
            {
                "route_id": route_id,
                "a": {"node": a[0], "port": a[1]},
                "b": {"node": b[0], "port": b[1]},
            }
        )

    observed.sort(
        key=lambda e: (
            str((e.get("a") or {}).get("node", "")).lower(),
            str((e.get("a") or {}).get("port", "")).lower(),
            str((e.get("b") or {}).get("node", "")).lower(),
            str((e.get("b") or {}).get("port", "")).lower(),
            str(e.get("route_id", "")).lower(),
        )
    )
    warnings.sort(key=lambda w: str(w).lower())
    return observed, [], warnings


def _parse_route_connection(route: dict[str, Any]) -> tuple[tuple[str, str], tuple[str, str]] | None:
    source = route.get("source")
    if isinstance(source, dict):
        edge = source.get("edge")
        if isinstance(edge, dict):
            src = str(edge.get("from", "")).strip()
            dst = str(edge.get("to", "")).strip()
            if src and dst:
                from_port = str(edge.get("from_port", "out")).strip() or "out"
                to_port = str(edge.get("to_port", "in")).strip() or "in"
                return (src, from_port), (dst, to_port)

    a = route.get("a")
    b = route.get("b")
    if isinstance(a, dict) and isinstance(b, dict):
        a_node = str(a.get("node", "")).strip()
        a_port = str(a.get("port", "")).strip()
        b_node = str(b.get("node", "")).strip()
        b_port = str(b.get("port", "")).strip()
        if a_node and a_port and b_node and b_port:
            return (a_node, a_port), (b_node, b_port)

    src = str(route.get("from", "")).strip()
    dst = str(route.get("to", "")).strip()
    if src and dst:
        from_port = str(route.get("from_port", "out")).strip() or "out"
        to_port = str(route.get("to_port", "in")).strip() or "in"
        return (src, from_port), (dst, to_port)

    return None


def _collect_port_roles(netlist: dict[str, Any]) -> dict[tuple[str, str], str]:
    kind_by_node: dict[str, str] = {}
    params_by_node: dict[str, dict[str, Any]] = {}

    for node in (netlist.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            continue
        kind_by_node[node_id] = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {})
        params_by_node[node_id] = params if isinstance(params, dict) else {}

    roles: dict[tuple[str, str], str] = {}
    for node_id in sorted(kind_by_node.keys(), key=lambda n: n.lower()):
        kind = kind_by_node[node_id]
        try:
            ports = component_ports(kind, params=params_by_node.get(node_id) or {})
        except Exception:
            continue
        for port in list(getattr(ports, "in_ports", []) or []):
            roles[(node_id, str(port))] = "in"
        for port in list(getattr(ports, "out_ports", []) or []):
            roles[(node_id, str(port))] = "out"
    return roles


def _missing_connections(
    expected_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
    observed_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for key in sorted(expected_by_undirected_key.keys(), key=_undirected_sort_key):
        if key in observed_by_undirected_key:
            continue
        edge = expected_by_undirected_key[key]
        out.append(
            {
                "from": str(edge.get("from", "")),
                "from_port": str(edge.get("from_port", "")),
                "to": str(edge.get("to", "")),
                "to_port": str(edge.get("to_port", "")),
            }
        )
    return out


def _extra_connections(
    expected_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
    observed_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in sorted(observed_by_undirected_key.keys(), key=_undirected_sort_key):
        if key in expected_by_undirected_key:
            continue
        obs = observed_by_undirected_key[key]
        a = obs.get("a") if isinstance(obs.get("a"), dict) else {}
        b = obs.get("b") if isinstance(obs.get("b"), dict) else {}
        out.append(
            {
                "a": {"node": str(a.get("node", "")), "port": str(a.get("port", ""))},
                "b": {"node": str(b.get("node", "")), "port": str(b.get("port", ""))},
                "route_id": str(obs.get("route_id", "")).strip() or None,
            }
        )
    return out


def _port_mapping_mismatches(
    *,
    expected_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
    observed_by_undirected_key: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]],
    roles_by_ref: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    shared_keys = [key for key in expected_by_undirected_key.keys() if key in observed_by_undirected_key]

    for key in sorted(shared_keys, key=_undirected_sort_key):
        expected = expected_by_undirected_key[key]
        observed = observed_by_undirected_key[key]

        a = observed.get("a") if isinstance(observed.get("a"), dict) else {}
        b = observed.get("b") if isinstance(observed.get("b"), dict) else {}
        an = str(a.get("node", "")).strip()
        ap = str(a.get("port", "")).strip()
        bn = str(b.get("node", "")).strip()
        bp = str(b.get("port", "")).strip()

        role_a = roles_by_ref.get((an, ap))
        role_b = roles_by_ref.get((bn, bp))

        oriented: dict[str, str] | None
        reason: str
        if role_a == "out" and role_b == "in":
            oriented = {"from": an, "from_port": ap, "to": bn, "to_port": bp}
            reason = ""
        elif role_a == "in" and role_b == "out":
            oriented = {"from": bn, "from_port": bp, "to": an, "to_port": ap}
            reason = ""
        elif role_a is None or role_b is None:
            oriented = None
            reason = "unknown_port"
        else:
            oriented = None
            reason = "ambiguous_or_invalid_port_roles"

        if oriented is None:
            out.append(
                {
                    "expected": {
                        "from": str(expected.get("from", "")),
                        "from_port": str(expected.get("from_port", "")),
                        "to": str(expected.get("to", "")),
                        "to_port": str(expected.get("to_port", "")),
                    },
                    "observed": {
                        "a": {"node": an, "port": ap},
                        "b": {"node": bn, "port": bp},
                        "route_id": str(observed.get("route_id", "")).strip() or None,
                    },
                    "reason": reason,
                }
            )
            continue

        if (
            oriented["from"] != str(expected.get("from", ""))
            or oriented["from_port"] != str(expected.get("from_port", ""))
            or oriented["to"] != str(expected.get("to", ""))
            or oriented["to_port"] != str(expected.get("to_port", ""))
        ):
            out.append(
                {
                    "expected": {
                        "from": str(expected.get("from", "")),
                        "from_port": str(expected.get("from_port", "")),
                        "to": str(expected.get("to", "")),
                        "to_port": str(expected.get("to_port", "")),
                    },
                    "observed": {
                        "a": {"node": an, "port": ap},
                        "b": {"node": bn, "port": bp},
                        "route_id": str(observed.get("route_id", "")).strip() or None,
                    },
                    "oriented": oriented,
                    "reason": "direction_mismatch",
                }
            )

    out.sort(
        key=lambda row: (
            str((row.get("expected") or {}).get("from", "")).lower(),
            str((row.get("expected") or {}).get("from_port", "")).lower(),
            str((row.get("expected") or {}).get("to", "")).lower(),
            str((row.get("expected") or {}).get("to_port", "")).lower(),
            str(row.get("reason", "")).lower(),
            str(((row.get("observed") or {}).get("route_id") or "")).lower(),
        )
    )
    return out


def _unconnected_ports(
    *,
    expected_connections: list[dict[str, str]],
    observed_connections: list[dict[str, Any]],
    dangling_routes: list[dict[str, Any]],
) -> list[dict[str, str]]:
    expected_ports: set[tuple[str, str]] = set()
    for edge in expected_connections:
        expected_ports.add((str(edge.get("from", "")), str(edge.get("from_port", ""))))
        expected_ports.add((str(edge.get("to", "")), str(edge.get("to_port", ""))))

    observed_ports: set[tuple[str, str]] = set()
    for edge in observed_connections:
        a = edge.get("a") if isinstance(edge.get("a"), dict) else {}
        b = edge.get("b") if isinstance(edge.get("b"), dict) else {}
        observed_ports.add((str(a.get("node", "")), str(a.get("port", ""))))
        observed_ports.add((str(b.get("node", "")), str(b.get("port", ""))))

    for dangling in dangling_routes:
        if not isinstance(dangling, dict):
            continue
        a_port = dangling.get("a_port")
        b_port = dangling.get("b_port")
        if isinstance(a_port, dict):
            observed_ports.add((str(a_port.get("node", "")), str(a_port.get("port", ""))))
        if isinstance(b_port, dict):
            observed_ports.add((str(b_port.get("node", "")), str(b_port.get("port", ""))))

    out: list[dict[str, str]] = []
    for node, port in sorted(expected_ports - observed_ports, key=lambda t: (t[0].lower(), t[1].lower())):
        out.append({"node": node, "port": port})
    return out


def _to_undirected_map(
    connections: list[dict[str, Any]],
) -> dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]]:
    out: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]] = {}
    for row in connections:
        if not isinstance(row, dict):
            continue
        if "from" in row and "to" in row:
            a = (str(row.get("from", "")).strip(), str(row.get("from_port", "")).strip())
            b = (str(row.get("to", "")).strip(), str(row.get("to_port", "")).strip())
        else:
            a_raw = row.get("a") if isinstance(row.get("a"), dict) else {}
            b_raw = row.get("b") if isinstance(row.get("b"), dict) else {}
            a = (str(a_raw.get("node", "")).strip(), str(a_raw.get("port", "")).strip())
            b = (str(b_raw.get("node", "")).strip(), str(b_raw.get("port", "")).strip())
        if not a[0] or not a[1] or not b[0] or not b[1]:
            continue
        key = _undirected_key(a[0], a[1], b[0], b[1])
        existing = out.get(key)
        if existing is None:
            out[key] = row
            continue
        existing_route_id = str(existing.get("route_id", "")).lower()
        row_route_id = str(row.get("route_id", "")).lower()
        if row_route_id and (not existing_route_id or row_route_id < existing_route_id):
            out[key] = row
    return out


def _undirected_key(a_node: str, a_port: str, b_node: str, b_port: str) -> tuple[tuple[str, str], tuple[str, str]]:
    a = (a_node, a_port)
    b = (b_node, b_port)
    if (a[0].lower(), a[1].lower()) <= (b[0].lower(), b[1].lower()):
        return a, b
    return b, a


def _undirected_sort_key(key: tuple[tuple[str, str], tuple[str, str]]) -> tuple[str, str, str, str]:
    return (key[0][0].lower(), key[0][1].lower(), key[1][0].lower(), key[1][1].lower())
