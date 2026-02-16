"""Connectivity extraction from layout sidecars (v0.1).

This is intentionally conservative:
- v0.1 extracts connectivity by snapping route endpoints to the nearest known
  port coordinate (from ports.json), within a tolerance.

This enables LVS-lite style checks without requiring a full GDS extraction flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConnectivityExtractResult:
    edges: list[dict[str, Any]]
    dangling_routes: list[dict[str, Any]]
    warnings: list[str]


def extract_connectivity_from_routes(
    routes: dict[str, Any],
    ports: dict[str, Any],
    *,
    tol_um: float,
) -> ConnectivityExtractResult:
    if tol_um <= 0.0:
        raise ValueError("tol_um must be > 0")

    port_rows = ports.get("ports") if isinstance(ports, dict) else None
    route_rows = routes.get("routes") if isinstance(routes, dict) else None
    if not isinstance(port_rows, list):
        raise TypeError("ports.ports must be a list")
    if not isinstance(route_rows, list):
        raise TypeError("routes.routes must be a list")

    port_points: list[tuple[float, float, str, str]] = []
    for p in port_rows:
        if not isinstance(p, dict):
            continue
        node = str(p.get("node", "")).strip()
        port = str(p.get("port", "")).strip()
        if not node or not port:
            continue
        try:
            x = float(p.get("x_um"))
            y = float(p.get("y_um"))
        except Exception:
            continue
        port_points.append((x, y, node, port))

    tol2 = float(tol_um) ** 2

    def nearest(pt: tuple[float, float]) -> tuple[str, str] | None:
        best = None
        best_d2 = None
        for x, y, node, port in port_points:
            dx = float(pt[0]) - float(x)
            dy = float(pt[1]) - float(y)
            d2 = dx * dx + dy * dy
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = (node, port)
        if best is None or best_d2 is None:
            return None
        if best_d2 > tol2:
            return None
        return best

    edges: list[dict[str, Any]] = []
    dangling: list[dict[str, Any]] = []
    warnings: list[str] = []

    for r in route_rows:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("route_id", "")).strip() or "route"
        pts = r.get("points_um") or []
        if not isinstance(pts, list) or len(pts) < 2:
            continue
        try:
            a = (float(pts[0][0]), float(pts[0][1]))
            b = (float(pts[-1][0]), float(pts[-1][1]))
        except Exception:
            continue

        pa = nearest(a)
        pb = nearest(b)
        if pa is None or pb is None:
            dangling.append(
                {
                    "route_id": rid,
                    "a_um": [float(a[0]), float(a[1])],
                    "b_um": [float(b[0]), float(b[1])],
                    "a_port": {"node": pa[0], "port": pa[1]} if pa else None,
                    "b_port": {"node": pb[0], "port": pb[1]} if pb else None,
                }
            )
            continue
        if pa == pb:
            warnings.append(f"{rid}: route endpoint snaps to the same port on both ends: {pa[0]}.{pa[1]}")
            continue

        edges.append(
            {
                "route_id": rid,
                "a": {"node": pa[0], "port": pa[1]},
                "b": {"node": pb[0], "port": pb[1]},
            }
        )

    edges.sort(key=lambda e: (str(e.get("a", {}).get("node", "")).lower(), str(e.get("route_id", "")).lower()))
    return ConnectivityExtractResult(edges=edges, dangling_routes=dangling, warnings=warnings)

