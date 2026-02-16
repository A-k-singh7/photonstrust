"""Graph semantic diagnostics (beyond JSON Schema).

This module provides backend-owned validation of:
- parameter schemas (types, ranges, enums) using `photonstrust.registry`, and
- PIC port correctness using the PIC component library as the source of truth.

It is intentionally deterministic and side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from photonstrust.components.pic.library import component_ports, supported_component_kinds
from photonstrust.graph.compiler import QKD_REQUIRED_KINDS
from photonstrust.registry.kinds import build_kinds_registry


@dataclass(frozen=True)
class Diagnostic:
    level: str  # "error" | "warning"
    code: str
    message: str
    ref: dict[str, Any]


def _diag(level: str, code: str, message: str, ref: dict[str, Any] | None = None) -> Diagnostic:
    return Diagnostic(level=str(level), code=str(code), message=str(message), ref=dict(ref or {}))


def validate_graph_semantics(graph: dict) -> dict[str, Any]:
    """Return semantic diagnostics for a graph dict.

    Output format:
    - errors: list[dict]
    - warnings: list[dict]
    - summary: dict
    """

    if not isinstance(graph, dict):
        raise TypeError("validate_graph_semantics expects a graph dict")

    profile = str(graph.get("profile", "")).strip().lower()
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    registry = build_kinds_registry()
    kind_meta: dict[str, dict] = {}
    for entry in registry.get("kinds", []) or []:
        if not isinstance(entry, dict):
            continue
        k = str(entry.get("kind", "")).strip()
        if not k:
            continue
        kind_meta[k] = entry

    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []

    # Node parameter checks (registry-owned).
    for node in nodes:
        if not isinstance(node, dict):
            warnings.append(_diag("warning", "node.type", "graph.nodes entry is not an object", {"node": node}))
            continue
        node_id = str(node.get("id", "")).strip()
        kind = str(node.get("kind", "")).strip()
        params = node.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            errors.append(
                _diag(
                    "error",
                    "param.type",
                    "node.params must be an object",
                    {"node_id": node_id, "kind": kind},
                )
            )
            continue

        meta = kind_meta.get(kind)
        if not meta:
            warnings.append(
                _diag(
                    "warning",
                    "kind.unknown",
                    "No registry entry for kind (cannot validate params).",
                    {"node_id": node_id, "kind": kind},
                )
            )
            continue

        schema = meta.get("params", []) or []
        if not isinstance(schema, list):
            schema = []

        by_name: dict[str, dict] = {}
        for p in schema:
            if not isinstance(p, dict):
                continue
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            by_name[name] = p

        # Unknown params
        for key in params.keys():
            if str(key) not in by_name:
                warnings.append(
                    _diag(
                        "warning",
                        "param.unknown",
                        f"Unknown param {key!r} for kind {kind!r}.",
                        {"node_id": node_id, "kind": kind, "param": str(key)},
                    )
                )

        # Validate known params
        for name, p in by_name.items():
            required = bool(p.get("required", False))
            typ = str(p.get("type", "")).strip().lower()
            enum = p.get("enum") if isinstance(p.get("enum"), list) else None
            has_min = "min" in p
            has_max = "max" in p
            min_v = p.get("min")
            max_v = p.get("max")

            applies_when = p.get("applies_when") if isinstance(p.get("applies_when"), dict) else None

            present = name in params
            value = params.get(name)

            if not present:
                if required:
                    errors.append(
                        _diag(
                            "error",
                            "param.missing",
                            f"Missing required param {name!r}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
                continue

            if value is None:
                if required:
                    errors.append(
                        _diag(
                            "error",
                            "param.null",
                            f"Required param {name!r} must not be null.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
                continue

            # Applies-when (best-effort).
            if applies_when:
                mismatch = False
                for k, v in applies_when.items():
                    if params.get(k) != v:
                        mismatch = True
                        break
                if mismatch:
                    warnings.append(
                        _diag(
                            "warning",
                            "param.applies_when",
                            f"Param {name!r} may not apply given {applies_when}.",
                            {"node_id": node_id, "kind": kind, "param": name, "applies_when": applies_when},
                        )
                    )

            # Type validation.
            if typ in {"number", "integer"}:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be {typ}, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
                    continue
                if typ == "integer" and not isinstance(value, int):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be integer, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
                    continue
                num = float(value)
                if has_min and min_v is not None and num < float(min_v):
                    errors.append(
                        _diag(
                            "error",
                            "param.range",
                            f"Param {name!r} must be >= {min_v}, got {value}.",
                            {"node_id": node_id, "kind": kind, "param": name, "min": min_v},
                        )
                    )
                if has_max and max_v is not None and num > float(max_v):
                    errors.append(
                        _diag(
                            "error",
                            "param.range",
                            f"Param {name!r} must be <= {max_v}, got {value}.",
                            {"node_id": node_id, "kind": kind, "param": name, "max": max_v},
                        )
                    )
                if enum is not None and value not in enum:
                    errors.append(
                        _diag(
                            "error",
                            "param.enum",
                            f"Param {name!r} must be one of {enum}, got {value!r}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
            elif typ == "string":
                if not isinstance(value, str):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be string, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
                    continue
                if enum is not None and value not in enum:
                    errors.append(
                        _diag(
                            "error",
                            "param.enum",
                            f"Param {name!r} must be one of {enum}, got {value!r}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
            elif typ == "boolean":
                if not isinstance(value, bool):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be boolean, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
            elif typ == "object":
                if not isinstance(value, dict):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be object, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
            elif typ == "array":
                if not isinstance(value, list):
                    errors.append(
                        _diag(
                            "error",
                            "param.type",
                            f"Param {name!r} must be array, got {type(value).__name__}.",
                            {"node_id": node_id, "kind": kind, "param": name},
                        )
                    )
            else:
                # Unknown param type in registry - warn, but do not block.
                warnings.append(
                    _diag(
                        "warning",
                        "registry.param_type_unknown",
                        f"Registry param {name!r} has unknown type {typ!r}.",
                        {"node_id": node_id, "kind": kind, "param": name, "registry_type": typ},
                    )
                )

    # PIC execution checks (engine-owned).
    if profile == "pic_circuit":
        supported = supported_component_kinds()
        ports_by_node: dict[str, Any] = {}
        kind_by_node: dict[str, str] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id", "")).strip()
            kind = str(node.get("kind", "")).strip().lower()
            if not node_id:
                continue
            kind_by_node[node_id] = kind
            if kind not in supported:
                errors.append(
                    _diag(
                        "error",
                        "kind.unsupported",
                        f"Unsupported PIC component kind {kind!r}.",
                        {"node_id": node_id, "kind": kind},
                    )
                )
                continue
            try:
                params = node.get("params", {}) or {}
                ports_by_node[node_id] = component_ports(kind, params=params)
            except Exception as exc:
                errors.append(
                    _diag(
                        "error",
                        "kind.ports",
                        f"Could not resolve ports for kind {kind!r}: {exc}",
                        {"node_id": node_id, "kind": kind},
                    )
                )

        def _resolve_port_domains(kind: str, node_id: str) -> dict[str, dict[str, str]]:
            default_domain = "optical" if str(kind).startswith("pic.") else "control"
            ports = ports_by_node.get(node_id)
            out = {
                "in": {str(name): default_domain for name in list(getattr(ports, "in_ports", []) or [])},
                "out": {str(name): default_domain for name in list(getattr(ports, "out_ports", []) or [])},
            }

            meta = kind_meta.get(kind, {})
            pd = meta.get("port_domains") if isinstance(meta, dict) else None
            if not isinstance(pd, dict):
                return out

            for direction in ("in", "out"):
                mapping = pd.get(direction)
                if not isinstance(mapping, dict):
                    continue
                for name, domain in mapping.items():
                    port_name = str(name)
                    if port_name in out[direction]:
                        out[direction][port_name] = str(domain)
            return out

        def _expected_domain_for_edge_kind(edge_kind: str) -> str | None:
            kind_norm = str(edge_kind or "").strip().lower()
            if kind_norm == "optical":
                return "optical"
            if kind_norm == "electrical":
                return "electrical"
            if kind_norm == "control":
                return "control"
            return None

        for edge in edges:
            if not isinstance(edge, dict):
                warnings.append(_diag("warning", "edge.type", "graph.edges entry is not an object", {"edge": edge}))
                continue
            edge_id = edge.get("id")
            src = str(edge.get("from", "")).strip()
            dst = str(edge.get("to", "")).strip()
            fp = edge.get("from_port")
            tp = edge.get("to_port")
            from_port = str(fp if fp is not None else "out")
            to_port = str(tp if tp is not None else "in")

            if src not in ports_by_node:
                errors.append(
                    _diag(
                        "error",
                        "edge.from_unknown",
                        f"edge.from refers to missing/invalid node {src!r}.",
                        {"edge_id": edge_id, "from": src, "to": dst},
                    )
                )
                continue
            if dst not in ports_by_node:
                errors.append(
                    _diag(
                        "error",
                        "edge.to_unknown",
                        f"edge.to refers to missing/invalid node {dst!r}.",
                        {"edge_id": edge_id, "from": src, "to": dst},
                    )
                )
                continue

            src_ports = ports_by_node[src]
            dst_ports = ports_by_node[dst]
            if from_port not in src_ports.out_ports:
                errors.append(
                    _diag(
                        "error",
                        "edge.from_port",
                        f"Unknown from_port {from_port!r} for node {src!r} ({kind_by_node.get(src,'')}).",
                        {"edge_id": edge_id, "from": src, "from_port": from_port},
                    )
                )
            if to_port not in dst_ports.in_ports:
                errors.append(
                    _diag(
                        "error",
                        "edge.to_port",
                        f"Unknown to_port {to_port!r} for node {dst!r} ({kind_by_node.get(dst,'')}).",
                        {"edge_id": edge_id, "to": dst, "to_port": to_port},
                    )
                )

            src_domains = _resolve_port_domains(kind_by_node.get(src, ""), src)
            dst_domains = _resolve_port_domains(kind_by_node.get(dst, ""), dst)
            src_domain = str(src_domains["out"].get(from_port, "optical"))
            dst_domain = str(dst_domains["in"].get(to_port, "optical"))

            if src_domain != dst_domain:
                errors.append(
                    _diag(
                        "error",
                        "edge.port_domain",
                        (
                            f"Port domain mismatch for edge {src}:{from_port} -> "
                            f"{dst}:{to_port}: {src_domain!r} -> {dst_domain!r}."
                        ),
                        {
                            "edge_id": edge_id,
                            "from": src,
                            "from_port": from_port,
                            "to": dst,
                            "to_port": to_port,
                            "from_domain": src_domain,
                            "to_domain": dst_domain,
                        },
                    )
                )

            edge_kind = str(edge.get("kind") if edge.get("kind") is not None else "optical")
            expected_domain = _expected_domain_for_edge_kind(edge_kind)
            if expected_domain is not None and src_domain != expected_domain:
                errors.append(
                    _diag(
                        "error",
                        "edge.kind_domain",
                        (
                            f"Edge kind {edge_kind!r} is incompatible with port "
                            f"domain {src_domain!r} for {src}:{from_port} -> {dst}:{to_port}."
                        ),
                        {
                            "edge_id": edge_id,
                            "kind": edge_kind,
                            "from": src,
                            "from_port": from_port,
                            "to": dst,
                            "to_port": to_port,
                            "domain": src_domain,
                        },
                    )
                )

    # QKD required node checks (compile-like, but non-throwing).
    if profile == "qkd_link":
        by_kind: dict[str, int] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            k = str(node.get("kind", "")).strip().lower()
            if not k:
                continue
            by_kind[k] = by_kind.get(k, 0) + 1

        missing = [k for k in QKD_REQUIRED_KINDS if by_kind.get(k, 0) == 0]
        for k in missing:
            errors.append(
                _diag(
                    "error",
                    "qkd.missing_kind",
                    f"Missing required node kind {k!r} for qkd_link graphs.",
                    {"kind": k},
                )
            )

        dupes = [k for k in QKD_REQUIRED_KINDS if by_kind.get(k, 0) > 1]
        for k in dupes:
            errors.append(
                _diag(
                    "error",
                    "qkd.duplicate_kind",
                    f"Multiple nodes of required kind {k!r} (expected exactly one).",
                    {"kind": k, "count": by_kind.get(k, 0)},
                )
            )

    # Stable ordering for UI and tests.
    def sort_key(d: Diagnostic) -> tuple:
        ref = d.ref or {}
        return (
            str(d.level),
            str(d.code),
            str(ref.get("node_id", "")),
            str(ref.get("edge_id", "")),
            str(ref.get("param", "")),
            str(ref.get("from", "")),
            str(ref.get("to", "")),
            str(d.message),
        )

    errors.sort(key=sort_key)
    warnings.sort(key=sort_key)

    return {
        "profile": profile,
        "errors": [d.__dict__ for d in errors],
        "warnings": [d.__dict__ for d in warnings],
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }
