"""Route-level layout feature extraction (v0.1).

Scope (v0.1):
- Input is a list of Manhattan (axis-aligned) polylines representing waveguide
  centerlines in microns.
- Output is a list of "parallel run" features between pairs of routes:
  (gap_um, parallel_length_um) + provenance.

This is intentionally deterministic and dependency-free so it can run in CI and
inside the web/API hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class _Route:
    route_id: str
    width_um: float
    points_um: list[tuple[float, float]]


@dataclass(frozen=True)
class _Seg:
    route_id: str
    width_um: float
    seg_index: int
    x0_um: float
    y0_um: float
    x1_um: float
    y1_um: float
    orientation: str  # "h" or "v"

    @property
    def length_um(self) -> float:
        if self.orientation == "h":
            return abs(self.x1_um - self.x0_um)
        return abs(self.y1_um - self.y0_um)


def extract_parallel_run_segments(
    routes: list[dict[str, Any]],
    *,
    max_gap_um: float | None = None,
    min_parallel_length_um: float = 0.0,
    coord_tol_um: float = 1e-9,
) -> list[dict[str, Any]]:
    """Extract parallel run segments between Manhattan-routed waveguides.

    Args:
      routes: list of route dicts:
        - route_id (or id): str
        - width_um: float (>0)
        - points_um: [[x_um, y_um], ...] (>=2 points)
      max_gap_um: optional filter on extracted *edge-to-edge* gap (um).
      min_parallel_length_um: optional filter on overlap length (um).
      coord_tol_um: tolerance used for Manhattan/colinear checks.
    """

    if not isinstance(routes, list):
        raise TypeError("routes must be a list")
    if max_gap_um is not None:
        max_gap_um = float(max_gap_um)
        if max_gap_um < 0.0:
            raise ValueError("max_gap_um must be >= 0")
    min_parallel_length_um = float(min_parallel_length_um)
    if min_parallel_length_um < 0.0:
        raise ValueError("min_parallel_length_um must be >= 0")
    coord_tol_um = float(coord_tol_um)
    if coord_tol_um <= 0.0:
        raise ValueError("coord_tol_um must be > 0")

    parsed = [_parse_route(r, index=i, tol=coord_tol_um) for i, r in enumerate(routes)]
    segs_by_route = {r.route_id: _segments_for_route(r, tol=coord_tol_um) for r in parsed}

    runs: list[dict[str, Any]] = []
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            a = parsed[i]
            b = parsed[j]
            for sa in segs_by_route[a.route_id]:
                for sb in segs_by_route[b.route_id]:
                    if sa.orientation != sb.orientation:
                        continue
                    if sa.orientation == "h":
                        run = _overlap_h(sa, sb, tol=coord_tol_um)
                    else:
                        run = _overlap_v(sa, sb, tol=coord_tol_um)
                    if run is None:
                        continue
                    if run["parallel_length_um"] < min_parallel_length_um:
                        continue
                    if max_gap_um is not None and run["gap_um"] > max_gap_um:
                        continue
                    runs.append(run)

    # Deterministic ordering (helps diffs and stable UI).
    runs.sort(
        key=lambda r: (
            str(r.get("route_a")),
            str(r.get("route_b")),
            str(r.get("orientation")),
            float(r.get("parallel_length_um", 0.0)),
            float(r.get("gap_um", 0.0)),
            str(r.get("a_seg_index")),
            str(r.get("b_seg_index")),
        )
    )
    return runs


def _parse_route(obj: dict[str, Any], *, index: int, tol: float) -> _Route:
    if not isinstance(obj, dict):
        raise TypeError("each route must be an object")

    route_id = obj.get("route_id")
    if route_id is None:
        route_id = obj.get("id")
    route_id_s = str(route_id or "").strip()
    if not route_id_s:
        raise ValueError(f"route[{index}] missing route_id")

    width_um = obj.get("width_um")
    if width_um is None:
        raise ValueError(f"route[{index}] missing width_um")
    width_um_f = float(width_um)
    if width_um_f <= 0.0:
        raise ValueError(f"route[{index}] width_um must be > 0")

    pts = obj.get("points_um")
    if not isinstance(pts, list) or len(pts) < 2:
        raise ValueError(f"route[{index}] points_um must be a list with >= 2 points")
    points = []
    for k, p in enumerate(pts):
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError(f"route[{index}].points_um[{k}] must be [x_um, y_um]")
        x = float(p[0])
        y = float(p[1])
        points.append((x, y))

    canon = _canonicalize_points(points, tol=tol)
    if len(canon) < 2:
        raise ValueError(f"route[{index}] points_um must contain at least 2 distinct points")

    return _Route(route_id=route_id_s, width_um=width_um_f, points_um=canon)


def _canonicalize_points(points: Iterable[tuple[float, float]], *, tol: float) -> list[tuple[float, float]]:
    pts = list(points)
    if not pts:
        return []

    # Remove consecutive duplicates.
    out: list[tuple[float, float]] = []
    for x, y in pts:
        if out and abs(x - out[-1][0]) <= tol and abs(y - out[-1][1]) <= tol:
            continue
        out.append((float(x), float(y)))

    # Remove colinear interior points (Manhattan-only check).
    if len(out) <= 2:
        return out
    canon = [out[0]]
    for i in range(1, len(out) - 1):
        a = canon[-1]
        b = out[i]
        c = out[i + 1]
        if _colinear_manhattan(a, b, c, tol=tol):
            continue
        canon.append(b)
    canon.append(out[-1])
    return canon


def _colinear_manhattan(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], *, tol: float) -> bool:
    ax, ay = a
    bx, by = b
    cx, cy = c
    if abs(ax - bx) <= tol and abs(bx - cx) <= tol:
        return True
    if abs(ay - by) <= tol and abs(by - cy) <= tol:
        return True
    return False


def _segments_for_route(route: _Route, *, tol: float) -> list[_Seg]:
    segs: list[_Seg] = []
    pts = route.points_um
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        if abs(dx) <= tol and abs(dy) <= tol:
            continue
        if abs(dy) <= tol and abs(dx) > tol:
            segs.append(
                _Seg(
                    route_id=route.route_id,
                    width_um=route.width_um,
                    seg_index=i,
                    x0_um=x0,
                    y0_um=y0,
                    x1_um=x1,
                    y1_um=y1,
                    orientation="h",
                )
            )
            continue
        if abs(dx) <= tol and abs(dy) > tol:
            segs.append(
                _Seg(
                    route_id=route.route_id,
                    width_um=route.width_um,
                    seg_index=i,
                    x0_um=x0,
                    y0_um=y0,
                    x1_um=x1,
                    y1_um=y1,
                    orientation="v",
                )
            )
            continue
        raise ValueError(
            f"route_id={route.route_id!r} contains a non-Manhattan segment at index {i}: "
            f"({x0},{y0})->({x1},{y1})"
        )
    return segs


def _overlap_h(a: _Seg, b: _Seg, *, tol: float) -> dict[str, Any] | None:
    # Horizontal segments: y is constant.
    if a.orientation != "h" or b.orientation != "h":
        return None
    ya = float(a.y0_um)
    yb = float(b.y0_um)
    if abs(a.y1_um - a.y0_um) > tol:
        return None
    if abs(b.y1_um - b.y0_um) > tol:
        return None

    ax0, ax1 = sorted([float(a.x0_um), float(a.x1_um)])
    bx0, bx1 = sorted([float(b.x0_um), float(b.x1_um)])
    ox0 = max(ax0, bx0)
    ox1 = min(ax1, bx1)
    overlap = ox1 - ox0
    if overlap <= 0.0:
        return None

    center_sep = abs(ya - yb)
    edge_gap = center_sep - 0.5 * (float(a.width_um) + float(b.width_um))
    return {
        "route_a": a.route_id,
        "route_b": b.route_id,
        "a_seg_index": int(a.seg_index),
        "b_seg_index": int(b.seg_index),
        "orientation": "horizontal",
        "gap_um": float(edge_gap),
        "centerline_sep_um": float(center_sep),
        "parallel_length_um": float(overlap),
        "width_a_um": float(a.width_um),
        "width_b_um": float(b.width_um),
        "overlap": {"x0_um": float(ox0), "x1_um": float(ox1), "y_a_um": float(ya), "y_b_um": float(yb)},
    }


def _overlap_v(a: _Seg, b: _Seg, *, tol: float) -> dict[str, Any] | None:
    # Vertical segments: x is constant.
    if a.orientation != "v" or b.orientation != "v":
        return None
    xa = float(a.x0_um)
    xb = float(b.x0_um)
    if abs(a.x1_um - a.x0_um) > tol:
        return None
    if abs(b.x1_um - b.x0_um) > tol:
        return None

    ay0, ay1 = sorted([float(a.y0_um), float(a.y1_um)])
    by0, by1 = sorted([float(b.y0_um), float(b.y1_um)])
    oy0 = max(ay0, by0)
    oy1 = min(ay1, by1)
    overlap = oy1 - oy0
    if overlap <= 0.0:
        return None

    center_sep = abs(xa - xb)
    edge_gap = center_sep - 0.5 * (float(a.width_um) + float(b.width_um))
    return {
        "route_a": a.route_id,
        "route_b": b.route_id,
        "a_seg_index": int(a.seg_index),
        "b_seg_index": int(b.seg_index),
        "orientation": "vertical",
        "gap_um": float(edge_gap),
        "centerline_sep_um": float(center_sep),
        "parallel_length_um": float(overlap),
        "width_a_um": float(a.width_um),
        "width_b_um": float(b.width_um),
        "overlap": {"y0_um": float(oy0), "y1_um": float(oy1), "x_a_um": float(xa), "x_b_um": float(xb)},
    }

