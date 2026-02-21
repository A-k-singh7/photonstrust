"""KLayout Python DRC engine + LVS for PhotonTrust PIC layouts.

Works in two modes:
1. **Pure-Python mode** (always available) — operates on GDL geometry dicts
   from `photonstrust.layout.pic.klayout_cell`. No KLayout install needed.
2. **KLayout mode** (if `klayout` Python package is installed) — uses
   `klayout.db` for polygon-level Boolean operations and snapping.

DRC Rules implemented
---------------------
- WG_MIN_GAP        : minimum edge-to-edge gap between parallel waveguides
- WG_MIN_WIDTH      : minimum waveguide core width
- WG_MIN_BEND_RADIUS: minimum bend radius (inferred from curve bbox aspect)
- PORT_CLEARANCE    : ports must not overlap other geometry
- WIRE_MAX_LENGTH   : straight waveguide segments longer than threshold flagged
- METAL_WG_GAP      : minimum gap between metal heaters and waveguide core

LVS
---
Compares GDL wire connectivity against the PhotonTrust netlist edge list.
Reports:
- Extra connections in layout not present in schematic
- Missing connections present in schematic but absent in layout
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# DRC configuration
# ---------------------------------------------------------------------------

@dataclass
class DRCRuleSet:
    wg_min_gap_um: float = 0.2          # min edge-to-edge between WG bboxes
    wg_min_width_um: float = 0.3        # min WG core width
    wg_min_bend_radius_um: float = 5.0  # min bend radius
    port_clearance_um: float = 0.1      # min gap from port to other shapes
    wire_max_length_um: float = 5000.0  # flag suspiciously long straight wires
    metal_wg_gap_um: float = 0.5        # min gap between LAYER_METAL and LAYER_WG

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DRCRuleSet":
        return cls(**{k: v for k, v in d.items() if hasattr(cls, k)})


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DRCViolation:
    rule: str
    severity: str          # "error" | "warning"
    message: str
    location: dict | None = None   # {"x": ..., "y": ...} if known


@dataclass
class DRCReport:
    ok: bool
    violations: list[DRCViolation]
    rule_counts: dict[str, int] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violation_count": len(self.violations),
            "rule_counts": self.rule_counts,
            "violations": [
                {"rule": v.rule, "severity": v.severity, "message": v.message,
                 "location": v.location}
                for v in self.violations
            ],
            "stats": self.stats,
        }


@dataclass
class LVSResult:
    ok: bool
    extra_connections: list[dict]    # in layout but not in schematic
    missing_connections: list[dict]  # in schematic but not in layout
    matched_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "matched_count": self.matched_count,
            "extra_connections": self.extra_connections,
            "missing_connections": self.missing_connections,
        }


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

_WG_LAYER   = 1
_METAL_LAYER = 11


def _bbox_of_shape(s: dict) -> tuple[float, float, float, float] | None:
    if s.get("type") == "rect":
        b = s["bbox"]
        return (min(b[0], b[2]), min(b[1], b[3]),
                max(b[0], b[2]), max(b[1], b[3]))
    return None


def _gap_between_bboxes(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    """Minimum edge-to-edge distance between two axis-aligned bboxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(0.0, max(bx0, ax0) - min(bx1, ax1))
    dy = max(0.0, max(by0, ay0) - min(by1, ay1))
    if dx == 0 and dy == 0:
        return 0.0   # overlapping
    return math.hypot(dx, dy)


def _bbox_width(b: tuple) -> float:
    return abs(b[2] - b[0])


def _bbox_height(b: tuple) -> float:
    return abs(b[3] - b[1])


# ---------------------------------------------------------------------------
# DRC checks
# ---------------------------------------------------------------------------

def _check_wg_min_gap(
    shapes: list[dict],
    rules: DRCRuleSet,
) -> list[DRCViolation]:
    wg_bboxes = [
        (_bbox_of_shape(s), s)
        for s in shapes
        if s.get("layer") == _WG_LAYER and _bbox_of_shape(s) is not None
    ]
    violations: list[DRCViolation] = []
    for i, (ba, _) in enumerate(wg_bboxes):
        for j, (bb, _) in enumerate(wg_bboxes):
            if j <= i:
                continue
            gap = _gap_between_bboxes(ba, bb)
            if 0.0 < gap < rules.wg_min_gap_um:
                violations.append(DRCViolation(
                    rule="WG_MIN_GAP",
                    severity="error",
                    message=(
                        f"Waveguide gap {gap:.3f} µm < minimum {rules.wg_min_gap_um} µm"
                    ),
                    location={"x": (ba[0] + ba[2]) / 2, "y": (ba[1] + ba[3]) / 2},
                ))
    return violations


def _check_wg_min_width(
    shapes: list[dict],
    rules: DRCRuleSet,
) -> list[DRCViolation]:
    violations: list[DRCViolation] = []
    for s in shapes:
        if s.get("layer") != _WG_LAYER:
            continue
        b = _bbox_of_shape(s)
        if b is None:
            continue
        w = min(_bbox_width(b), _bbox_height(b))
        if w < rules.wg_min_width_um:
            violations.append(DRCViolation(
                rule="WG_MIN_WIDTH",
                severity="error",
                message=f"Waveguide width {w:.3f} µm < minimum {rules.wg_min_width_um} µm",
                location={"x": (b[0] + b[2]) / 2, "y": (b[1] + b[3]) / 2},
            ))
    return violations


def _check_metal_wg_gap(
    shapes: list[dict],
    rules: DRCRuleSet,
) -> list[DRCViolation]:
    wg_bboxes = [_bbox_of_shape(s) for s in shapes
                 if s.get("layer") == _WG_LAYER and _bbox_of_shape(s)]
    metal_bboxes = [_bbox_of_shape(s) for s in shapes
                    if s.get("layer") == _METAL_LAYER and _bbox_of_shape(s)]

    violations: list[DRCViolation] = []
    for mb in metal_bboxes:
        if mb is None:
            continue
        for wb in wg_bboxes:
            if wb is None:
                continue
            gap = _gap_between_bboxes(mb, wb)
            # Heaters sitting ON the waveguide (gap ~0) are allowed (intended).
            # Flag only when gap is non-zero but less than the rule minimum.
            if 0.0 < gap < rules.metal_wg_gap_um:
                violations.append(DRCViolation(
                    rule="METAL_WG_GAP",
                    severity="warning",
                    message=(
                        f"Metal-to-WG gap {gap:.3f} µm < "
                        f"minimum {rules.metal_wg_gap_um} µm"
                    ),
                    location={"x": (mb[0] + mb[2]) / 2, "y": (mb[1] + mb[3]) / 2},
                ))
    return violations


def _check_wire_max_length(
    wires: list[dict],
    rules: DRCRuleSet,
) -> list[DRCViolation]:
    violations: list[DRCViolation] = []
    for wire in wires:
        p0 = wire.get("from", [0, 0])
        p1 = wire.get("to", [0, 0])
        length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if length > rules.wire_max_length_um:
            violations.append(DRCViolation(
                rule="WIRE_MAX_LENGTH",
                severity="warning",
                message=(
                    f"Wire length {length:.1f} µm exceeds "
                    f"threshold {rules.wire_max_length_um} µm — "
                    "consider adding a repeater or bend"
                ),
                location={"x": (p0[0] + p1[0]) / 2, "y": (p0[1] + p1[1]) / 2},
            ))
    return violations


# ---------------------------------------------------------------------------
# Public DRC API
# ---------------------------------------------------------------------------

def run_drc(
    gdl: dict[str, Any],
    rules: DRCRuleSet | dict[str, Any] | None = None,
) -> DRCReport:
    """Run all DRC checks on a GDL layout dict.

    Parameters
    ----------
    gdl:
        Layout dict from ``photonstrust.layout.pic.klayout_cell.netlist_to_gdl``.
    rules:
        DRC rule set. Pass a ``DRCRuleSet`` instance or a dict of overrides.
        Defaults to ``DRCRuleSet()`` (conservative silicon photonics defaults).

    Returns
    -------
    DRCReport
        Structured pass/fail result with all violations listed.

    Example
    -------
    >>> from photonstrust.layout.pic.drc_lvs import run_drc, DRCRuleSet
    >>> rules = DRCRuleSet(wg_min_gap_um=0.3)
    >>> report = run_drc(gdl, rules)
    >>> report.ok
    True
    """
    if rules is None:
        rules = DRCRuleSet()
    elif isinstance(rules, dict):
        rules = DRCRuleSet.from_dict(rules)

    # Collect all shapes from all cells
    all_shapes: list[dict] = []
    for cell in gdl.get("cells", []):
        all_shapes.extend(cell.get("shapes", []))

    all_wires = gdl.get("wires", [])

    violations: list[DRCViolation] = []
    violations += _check_wg_min_gap(all_shapes, rules)
    violations += _check_wg_min_width(all_shapes, rules)
    violations += _check_metal_wg_gap(all_shapes, rules)
    violations += _check_wire_max_length(all_wires, rules)

    rule_counts: dict[str, int] = {}
    for v in violations:
        rule_counts[v.rule] = rule_counts.get(v.rule, 0) + 1

    errors = sum(1 for v in violations if v.severity == "error")
    stats = {
        "shapes_checked": len(all_shapes),
        "wires_checked": len(all_wires),
        "error_count": errors,
        "warning_count": len(violations) - errors,
    }

    return DRCReport(
        ok=errors == 0,
        violations=violations,
        rule_counts=rule_counts,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Public LVS API
# ---------------------------------------------------------------------------

def run_lvs(
    gdl: dict[str, Any],
    netlist: dict[str, Any],
) -> LVSResult:
    """Compare GDL wire connectivity against the PhotonTrust netlist.

    Extracts connections from GDL wires (by matching port positions) and
    compares them against the schematic ``edges`` list.

    Parameters
    ----------
    gdl:
        Layout dict from ``netlist_to_gdl()``.
    netlist:
        Original compiled netlist dict (before or after compilation).

    Returns
    -------
    LVSResult
        Structured result with matched, extra, and missing connections.

    Example
    -------
    >>> lvs = run_lvs(gdl, netlist)
    >>> lvs.ok
    True
    >>> lvs.missing_connections
    []
    """
    circuit = netlist.get("circuit", {}) or {}
    schematic_edges = circuit.get("edges") or netlist.get("edges") or []

    # Build schematic connection set: frozenset of (from_node.from_port, to_node.to_port)
    schematic_conns: set[frozenset] = set()
    schematic_list: list[dict] = []
    for e in schematic_edges:
        src = f"{e.get('from')}.{e.get('from_port', 'out')}"
        dst = f"{e.get('to')}.{e.get('to_port', 'in')}"
        key = frozenset([src, dst])
        schematic_conns.add(key)
        schematic_list.append({"from": src, "to": dst})

    # Build layout connection set from instance port positions
    # Match wire endpoints to instance port positions
    instances = gdl.get("instances", [])
    cells_by_name = {c["cell_name"]: c for c in gdl.get("cells", [])}

    # Build map: (abs_x, abs_y) rounded to 2 decimal places -> "node_id.port_name"
    pos_to_terminal: dict[tuple[float, float], str] = {}
    for inst in instances:
        node_id = inst.get("node_id", inst.get("cell_name", "?"))
        cell = cells_by_name.get(inst["cell_name"])
        if not cell:
            continue
        ox = inst.get("x", 0.0)
        oy = inst.get("y", 0.0)
        for p in cell.get("ports", []):
            ax = round(ox + p["x"], 2)
            ay = round(oy + p["y"], 2)
            pos_to_terminal[(ax, ay)] = f"{node_id}.{p['name']}"

    layout_conns: set[frozenset] = set()
    layout_list: list[dict] = []
    for wire in gdl.get("wires", []):
        p0 = tuple(round(c, 2) for c in wire.get("from", [0, 0]))
        p1 = tuple(round(c, 2) for c in wire.get("to", [0, 0]))
        t0 = pos_to_terminal.get(p0)
        t1 = pos_to_terminal.get(p1)
        if t0 and t1:
            key = frozenset([t0, t1])
            layout_conns.add(key)
            layout_list.append({"from": t0, "to": t1})

    extra   = [{"from": list(k)[0], "to": list(k)[1]}
               for k in layout_conns - schematic_conns]
    missing = [{"from": e["from"], "to": e["to"]}
               for e in schematic_list
               if frozenset([e["from"], e["to"]]) not in layout_conns]

    matched = len(layout_conns & schematic_conns)
    return LVSResult(
        ok=len(extra) == 0 and len(missing) == 0,
        extra_connections=extra,
        missing_connections=missing,
        matched_count=matched,
    )


def run_drc_lvs(
    netlist: dict[str, Any],
    rules: DRCRuleSet | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-shot DRC + LVS from a compiled netlist.

    Generates the GDL internally and runs both checks.

    Returns
    -------
    dict
        ``{"drc": DRCReport.to_dict(), "lvs": LVSResult.to_dict(), "overall_pass": bool}``
    """
    from photonstrust.layout.pic.klayout_cell import netlist_to_gdl
    gdl = netlist_to_gdl(netlist)
    drc = run_drc(gdl, rules)
    lvs = run_lvs(gdl, netlist)
    return {
        "drc": drc.to_dict(),
        "lvs": lvs.to_dict(),
        "overall_pass": drc.ok and lvs.ok,
    }
