"""Graph/netlist-level PIC DRC checks (no layout geometry assumptions)."""

from __future__ import annotations

from typing import Any

from photonstrust.components.pic.library import component_ports


_DEFAULT_RULES = {
    "min_waveguide_width_um": 0.45,
    "min_waveguide_gap_um": 0.20,
    "min_bend_radius_um": 5.0,
}
_IO_KINDS = {"pic.grating_coupler", "pic.edge_coupler"}
_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def run_graph_drc(compiled_or_netlist: Any, *, pdk: Any) -> dict[str, Any]:
    """Run deterministic graph/netlist DRC checks for PIC."""

    netlist = _extract_netlist(compiled_or_netlist)
    rules = _resolve_rules(pdk)

    raw_nodes = netlist.get("nodes") if isinstance(netlist.get("nodes"), list) else []
    raw_edges = netlist.get("edges") if isinstance(netlist.get("edges"), list) else []

    nodes: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("id", "")).strip() or f"node_{idx}"
        kind = str(raw.get("kind", "")).strip().lower()
        params = raw.get("params")
        nodes.append(
            {
                "node_id": node_id,
                "kind": kind,
                "params": params if isinstance(params, dict) else {},
                "index": idx,
            }
        )
    nodes.sort(key=lambda n: (str(n["node_id"]).lower(), int(n["index"])))

    edges: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_edges):
        if not isinstance(raw, dict):
            continue
        edge_id = str(raw.get("id", "")).strip() or f"edge_{idx}"
        edges.append({"edge_id": edge_id, "raw": raw, "index": idx})
    edges.sort(
        key=lambda e: (
            str(e["edge_id"]).lower(),
            str((e["raw"] or {}).get("from", "")).lower(),
            str((e["raw"] or {}).get("from_port", "")).lower(),
            str((e["raw"] or {}).get("to", "")).lower(),
            str((e["raw"] or {}).get("to_port", "")).lower(),
            int(e["index"]),
        )
    )

    items: list[dict[str, Any]] = []

    def add_item(
        *,
        code: str,
        severity: str,
        message: str,
        node_id: str | None = None,
        edge_id: str | None = None,
    ) -> None:
        row: dict[str, Any] = {
            "code": str(code),
            "severity": str(severity),
            "message": str(message),
        }
        if node_id is not None:
            row["node_id"] = str(node_id)
        if edge_id is not None:
            row["edge_id"] = str(edge_id)
        items.append(row)

    node_by_id: dict[str, dict[str, Any]] = {}
    port_map_by_node: dict[str, dict[str, tuple[str, ...]]] = {}

    for node in nodes:
        node_id = str(node["node_id"])
        kind = str(node["kind"])
        params = node["params"] if isinstance(node["params"], dict) else {}
        if node_id not in node_by_id:
            node_by_id[node_id] = node

        try:
            ports = component_ports(kind, params=params)
            in_ports = tuple(str(p) for p in (ports.in_ports or ()))
            out_ports = tuple(str(p) for p in (ports.out_ports or ()))
            port_map_by_node[node_id] = {"in": in_ports, "out": out_ports}
        except Exception:
            continue

        width_um = _first_float(params, ("width_um", "waveguide_width_um"))
        if width_um is not None and width_um < rules["min_waveguide_width_um"]:
            add_item(
                code="PIC.DRC.MIN_WIDTH",
                severity="error",
                message=(
                    f"width_um={width_um:.6g} is below "
                    f"min_waveguide_width_um={rules['min_waveguide_width_um']:.6g}"
                ),
                node_id=node_id,
            )

        gap_um = _safe_float(params.get("gap_um"))
        if gap_um is not None:
            if gap_um < rules["min_waveguide_gap_um"]:
                add_item(
                    code="PIC.DRC.MIN_GAP",
                    severity="error",
                    message=(
                        f"gap_um={gap_um:.6g} is below "
                        f"min_waveguide_gap_um={rules['min_waveguide_gap_um']:.6g}"
                    ),
                    node_id=node_id,
                )

        bend_radius_um = _first_float(params, ("bend_radius_um", "radius_um"))
        if bend_radius_um is not None and bend_radius_um < rules["min_bend_radius_um"]:
            add_item(
                code="PIC.DRC.MIN_BEND_RADIUS",
                severity="error",
                message=(
                    f"bend_radius_um={bend_radius_um:.6g} is below "
                    f"min_bend_radius_um={rules['min_bend_radius_um']:.6g}"
                ),
                node_id=node_id,
            )

    connected_refs: set[tuple[str, str]] = set()

    for edge in edges:
        edge_id = str(edge["edge_id"])
        raw = edge["raw"] if isinstance(edge["raw"], dict) else {}
        src = str(raw.get("from", "")).strip()
        dst = str(raw.get("to", "")).strip()
        from_port = str(raw.get("from_port", "out")).strip() or "out"
        to_port = str(raw.get("to_port", "in")).strip() or "in"

        src_ok = src in node_by_id
        dst_ok = dst in node_by_id
        if not src_ok:
            add_item(
                code="PIC.DRC.EDGE_NODE_MISSING",
                severity="error",
                message=f"edge.from refers to unknown node: {src or '<empty>'}",
                edge_id=edge_id,
            )
        if not dst_ok:
            add_item(
                code="PIC.DRC.EDGE_NODE_MISSING",
                severity="error",
                message=f"edge.to refers to unknown node: {dst or '<empty>'}",
                edge_id=edge_id,
            )

        if src_ok and src in port_map_by_node:
            out_ports = set(port_map_by_node[src]["out"])
            if from_port not in out_ports:
                add_item(
                    code="PIC.DRC.EDGE_PORT_INVALID",
                    severity="error",
                    message=f"from_port '{from_port}' is not valid for node '{src}'",
                    edge_id=edge_id,
                )
            else:
                connected_refs.add((src, from_port))

        if dst_ok and dst in port_map_by_node:
            in_ports = set(port_map_by_node[dst]["in"])
            if to_port not in in_ports:
                add_item(
                    code="PIC.DRC.EDGE_PORT_INVALID",
                    severity="error",
                    message=f"to_port '{to_port}' is not valid for node '{dst}'",
                    edge_id=edge_id,
                )
            else:
                connected_refs.add((dst, to_port))

    for node in nodes:
        node_id = str(node["node_id"])
        kind = str(node["kind"])
        node_ports = port_map_by_node.get(node_id)
        if not isinstance(node_ports, dict):
            continue

        for port_name in tuple(node_ports.get("in", ())) + tuple(node_ports.get("out", ())):
            ref = (node_id, str(port_name))
            if ref in connected_refs:
                continue
            if kind in _IO_KINDS:
                continue
            add_item(
                code="PIC.DRC.FLOATING_PORT",
                severity="warning",
                message=f"port '{port_name}' on node '{node_id}' is not connected",
                node_id=node_id,
            )

    # ---- Phase C2 DRC rules ------------------------------------------------

    # PIC.DRC.MIN_HEATER_SPACING — warn if heater nodes are placed too close.
    min_heater_spacing_um = float(rules.get("min_heater_spacing_um", 100.0) or 100.0)
    heater_nodes = [
        n for n in nodes
        if str(n["kind"]) == "pic.heater"
    ]
    for i in range(len(heater_nodes)):
        for j in range(i + 1, len(heater_nodes)):
            n_i = heater_nodes[i]
            n_j = heater_nodes[j]
            p_i = n_i["params"] if isinstance(n_i["params"], dict) else {}
            p_j = n_j["params"] if isinstance(n_j["params"], dict) else {}
            x_i = _safe_float(p_i.get("x_um"))
            y_i = _safe_float(p_i.get("y_um"))
            x_j = _safe_float(p_j.get("x_um"))
            y_j = _safe_float(p_j.get("y_um"))
            if x_i is not None and y_i is not None and x_j is not None and y_j is not None:
                import math as _math
                dist = _math.sqrt((x_i - x_j) ** 2 + (y_i - y_j) ** 2)
                if dist < min_heater_spacing_um:
                    add_item(
                        code="PIC.DRC.MIN_HEATER_SPACING",
                        severity="warning",
                        message=(
                            f"heater nodes '{n_i['node_id']}' and '{n_j['node_id']}' "
                            f"are {dist:.6g} um apart, below min_heater_spacing_um="
                            f"{min_heater_spacing_um:.6g}"
                        ),
                        node_id=str(n_i["node_id"]),
                    )

    # PIC.DRC.MAX_CROSSINGS — warn if crossing count exceeds threshold.
    max_crossings = int(rules.get("max_crossings", 20) or 20)
    crossing_count = sum(1 for n in nodes if str(n["kind"]) == "pic.crossing")
    if crossing_count > max_crossings:
        add_item(
            code="PIC.DRC.MAX_CROSSINGS",
            severity="warning",
            message=(
                f"number of pic.crossing nodes ({crossing_count}) exceeds "
                f"max_crossings={max_crossings}"
            ),
        )

    # PIC.DRC.MODULATOR_LENGTH — check MZM phase_shifter_length_mm bounds.
    max_modulator_length_mm = float(rules.get("max_modulator_length_mm", 10.0) or 10.0)
    min_modulator_length_mm = float(rules.get("min_modulator_length_mm", 0.1) or 0.1)
    for node in nodes:
        if str(node["kind"]) != "pic.mzm":
            continue
        node_id = str(node["node_id"])
        params = node["params"] if isinstance(node["params"], dict) else {}
        ps_len = _safe_float(params.get("phase_shifter_length_mm"))
        if ps_len is not None:
            if ps_len > max_modulator_length_mm:
                add_item(
                    code="PIC.DRC.MODULATOR_LENGTH",
                    severity="warning",
                    message=(
                        f"phase_shifter_length_mm={ps_len:.6g} exceeds "
                        f"max_modulator_length_mm={max_modulator_length_mm:.6g}"
                    ),
                    node_id=node_id,
                )
            elif ps_len < min_modulator_length_mm:
                add_item(
                    code="PIC.DRC.MODULATOR_LENGTH",
                    severity="warning",
                    message=(
                        f"phase_shifter_length_mm={ps_len:.6g} is below "
                        f"min_modulator_length_mm={min_modulator_length_mm:.6g}"
                    ),
                    node_id=node_id,
                )

    # ---- end Phase C2 DRC rules --------------------------------------------

    items.sort(
        key=lambda row: (
            _SEVERITY_RANK.get(str(row.get("severity", "info")).lower(), 99),
            str(row.get("code", "")).lower(),
            str(row.get("node_id", "")).lower(),
            str(row.get("edge_id", "")).lower(),
            str(row.get("message", "")).lower(),
        )
    )
    for idx, row in enumerate(items, start=1):
        row["id"] = f"item_{idx:04d}"

    error_count = sum(1 for row in items if str(row.get("severity", "")).lower() == "error")
    warning_count = sum(1 for row in items if str(row.get("severity", "")).lower() == "warning")
    info_count = sum(1 for row in items if str(row.get("severity", "")).lower() == "info")

    return {
        "kind": "pic.graph_drc",
        "graph_id": str(netlist.get("graph_id", "") or ""),
        "rules": dict(rules),
        "summary": {
            "pass": error_count == 0,
            "error_count": int(error_count),
            "warning_count": int(warning_count),
            "info_count": int(info_count),
        },
        "items": items,
    }


def _extract_netlist(compiled_or_netlist: Any) -> dict[str, Any]:
    if isinstance(compiled_or_netlist, dict):
        compiled = compiled_or_netlist.get("compiled")
        if isinstance(compiled, dict):
            return dict(compiled)
        return dict(compiled_or_netlist)

    compiled_attr = getattr(compiled_or_netlist, "compiled", None)
    if isinstance(compiled_attr, dict):
        return dict(compiled_attr)

    raise TypeError("compiled_or_netlist must be a netlist dict or object with .compiled dict")


def _resolve_rules(pdk: Any) -> dict[str, float]:
    design_rules: dict[str, Any] = {}
    if isinstance(pdk, dict):
        if isinstance(pdk.get("design_rules"), dict):
            design_rules = dict(pdk.get("design_rules") or {})
        elif isinstance(pdk.get("pdk"), dict) and isinstance((pdk.get("pdk") or {}).get("design_rules"), dict):
            design_rules = dict((pdk.get("pdk") or {}).get("design_rules") or {})
    else:
        maybe_design_rules = getattr(pdk, "design_rules", None)
        if isinstance(maybe_design_rules, dict):
            design_rules = dict(maybe_design_rules)

    return {
        "min_waveguide_width_um": _rule_value(
            design_rules,
            key="min_waveguide_width_um",
            default=_DEFAULT_RULES["min_waveguide_width_um"],
        ),
        "min_waveguide_gap_um": _rule_value(
            design_rules,
            key="min_waveguide_gap_um",
            default=_DEFAULT_RULES["min_waveguide_gap_um"],
        ),
        "min_bend_radius_um": _rule_value(
            design_rules,
            key="min_bend_radius_um",
            default=_DEFAULT_RULES["min_bend_radius_um"],
        ),
    }


def _rule_value(design_rules: dict[str, Any], *, key: str, default: float) -> float:
    parsed = _safe_float(design_rules.get(key))
    if parsed is None or parsed <= 0.0:
        return float(default)
    return float(parsed)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN check
        return None
    return out


def _first_float(params: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        parsed = _safe_float(params.get(key))
        if parsed is not None:
            return parsed
    return None
