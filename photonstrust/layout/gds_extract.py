"""GDS-level route extraction (v0.2, optional dependency).

This module provides a thin bridge from GDS geometry to the route-level contract
used by `photonstrust.layout.route_extract`:

  routes[*] = {route_id, width_um, points_um}

Design goals:
- Keep core install lightweight: `gdstk` is optional.
- Be explicit about limitations (v0.2 is intentionally conservative).

Notes:
- gdstk stores geometry in a user unit (meters). We import with `unit=1e-6` so
  coordinates and widths are returned in microns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class OptionalDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class GdsExtractStats:
    cell_name: str
    routes: int
    paths_seen: int
    polygons_seen: int
    polygons_used_as_rect_routes: int
    skipped_non_manhattan_spines: int


def extract_routes_from_gds(
    gds_path: str | Path,
    *,
    cell: str | None = None,
    filter_layers: Iterable[tuple[int, int]] | None = None,
    include_rectangles: bool = True,
    route_id_prefix: str = "gds",
    manhattan_only: bool = True,
    tol_um: float = 1e-9,
) -> tuple[list[dict[str, Any]], GdsExtractStats]:
    """Extract routes from a GDS file into the PhotonTrust route contract.

    This extractor is conservative:
    - It primarily extracts from GDS PATH elements (FlexPath/RobustPath).
    - Optionally, axis-aligned rectangle polygons can be converted to 2-point routes.

    Args:
      gds_path: Path to a GDS file.
      cell: Optional cell name. If omitted, requires exactly 1 top-level cell.
      filter_layers: Optional list/set of (layer, datatype) to restrict input.
      include_rectangles: If True, attempt to convert axis-aligned rectangle polygons to routes.
      route_id_prefix: Prefix for generated route IDs.
      manhattan_only: If True, skip path spines that contain non-Manhattan segments.
      tol_um: Tolerance for Manhattan checks (um).

    Returns:
      (routes, stats)
    """

    gdstk = _import_gdstk()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    filter_set = None
    if filter_layers is not None:
        filter_set = {(int(l), int(d)) for (l, d) in filter_layers}

    # Import and convert geometry to microns.
    lib = gdstk.read_gds(path, unit=1e-6, filter=filter_set)

    cell_obj = None
    if cell is not None:
        name = str(cell).strip()
        if not name:
            raise ValueError("cell must be a non-empty string when provided")
        try:
            cell_obj = lib[name]
        except Exception as exc:
            raise KeyError(f"Cell not found in GDS: {name!r}") from exc
    else:
        tops = list(lib.top_level())
        if len(tops) != 1:
            names = [getattr(c, "name", "?") for c in tops]
            raise ValueError(f"Expected exactly 1 top-level cell, found {len(tops)}: {names}. Provide cell=...")
        cell_obj = tops[0]

    cell_name = str(getattr(cell_obj, "name", "") or "TOP")

    routes: list[dict[str, Any]] = []
    stats = {
        "paths_seen": 0,
        "polygons_seen": 0,
        "polygons_used_as_rect_routes": 0,
        "skipped_non_manhattan_spines": 0,
    }

    # Paths.
    for p_idx, p in enumerate(getattr(cell_obj, "paths", []) or []):
        stats["paths_seen"] += 1
        for route in _routes_from_gdstk_path(
            p,
            route_id_prefix=f"{route_id_prefix}:{cell_name}:path{p_idx}",
            filter_set=filter_set,
            manhattan_only=manhattan_only,
            tol_um=tol_um,
            stats=stats,
        ):
            routes.append(route)

    # Rectangle polygons (optional).
    if include_rectangles:
        for poly_idx, poly in enumerate(getattr(cell_obj, "polygons", []) or []):
            stats["polygons_seen"] += 1
            route = _route_from_rectangle_polygon(
                poly,
                route_id=f"{route_id_prefix}:{cell_name}:rect{poly_idx}",
                filter_set=filter_set,
                tol_um=tol_um,
            )
            if route is None:
                continue
            stats["polygons_used_as_rect_routes"] += 1
            routes.append(route)
    else:
        stats["polygons_seen"] = int(len(getattr(cell_obj, "polygons", []) or []))

    out_stats = GdsExtractStats(
        cell_name=cell_name,
        routes=int(len(routes)),
        paths_seen=int(stats["paths_seen"]),
        polygons_seen=int(stats["polygons_seen"]),
        polygons_used_as_rect_routes=int(stats["polygons_used_as_rect_routes"]),
        skipped_non_manhattan_spines=int(stats["skipped_non_manhattan_spines"]),
    )
    return routes, out_stats


def _import_gdstk():
    try:
        import gdstk  # type: ignore
    except Exception as exc:
        raise OptionalDependencyError(
            "GDS extraction requires optional dependency 'gdstk'. "
            "Install with: pip install 'photonstrust[layout]'"
        ) from exc
    return gdstk


def _routes_from_gdstk_path(
    path_obj: Any,
    *,
    route_id_prefix: str,
    filter_set: set[tuple[int, int]] | None,
    manhattan_only: bool,
    tol_um: float,
    stats: dict[str, int],
) -> list[dict[str, Any]]:
    # gdstk FlexPath / RobustPath both provide path_spines().
    try:
        spines = path_obj.path_spines()
    except Exception:
        return []

    def _normalize_per_spine(value: Any, n: int) -> list[Any]:
        # gdstk uses tuples for layers/datatypes (even for a single path).
        if isinstance(value, (list, tuple)):
            seq = list(value)
            if len(seq) == n:
                return seq
            if len(seq) == 1 and n > 1:
                return seq * n
            if not seq:
                return [None] * n
            # Best-effort: truncate/pad with last value.
            out = seq[:n]
            if len(out) < n:
                out.extend([out[-1]] * (n - len(out)))
            return out
        return [value] * n

    # Layers/datatypes can be a list/tuple (per parallel path) or a single value.
    layers = _normalize_per_spine(getattr(path_obj, "layers", None), len(spines))
    datatypes = _normalize_per_spine(getattr(path_obj, "datatypes", None), len(spines))

    widths_um = _path_widths_um(path_obj, len(spines))

    routes: list[dict[str, Any]] = []
    for i, spine in enumerate(spines):
        layer = int(layers[i] or 0)
        datatype = int(datatypes[i] or 0)
        if filter_set is not None and (layer, datatype) not in filter_set:
            continue

        points = _spine_points_um(spine)
        if len(points) < 2:
            continue
        if manhattan_only and not _is_manhattan(points, tol=tol_um):
            stats["skipped_non_manhattan_spines"] += 1
            continue

        w_um = float(widths_um[i])
        if w_um <= 0.0:
            continue

        routes.append(
            {
                "route_id": f"{route_id_prefix}:{i}",
                "width_um": w_um,
                "points_um": [[float(x), float(y)] for (x, y) in points],
                "source": {"kind": "gds_path", "layer": layer, "datatype": datatype},
            }
        )
    return routes


def _path_widths_um(path_obj: Any, n_paths: int) -> list[float]:
    # FlexPath.widths() returns widths for each path at every point.
    # RobustPath.widths(u) returns widths for each path at u in [0, size].
    widths = None
    try:
        widths = path_obj.widths()  # FlexPath
        # widths shape: (n_paths, n_points)
        out = []
        for i in range(n_paths):
            row = widths[i]
            # Conservative: use max width along spine.
            out.append(float(max(row)) if len(row) else 0.0)
        return out
    except TypeError:
        # RobustPath widths(u, ...)
        pass
    except Exception:
        pass

    # RobustPath: sample u at endpoints and midpoints of sections.
    try:
        size = int(getattr(path_obj, "size", 0) or 0)
    except Exception:
        size = 0
    u_samples = [0.0]
    if size > 0:
        u_samples.append(float(size))
        for k in range(size):
            u_samples.append(float(k) + 0.5)

    # If this fails, fall back to unknown/zero.
    per_path_max = [0.0 for _ in range(n_paths)]
    for u in u_samples:
        try:
            row = path_obj.widths(u)
        except Exception:
            continue
        for i in range(min(n_paths, len(row))):
            try:
                per_path_max[i] = max(per_path_max[i], float(row[i]))
            except Exception:
                continue
    return per_path_max


def _spine_points_um(spine: Any) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for p in list(spine):
        # gdstk points can be tuple pairs or complex.
        if isinstance(p, complex):
            pts.append((float(p.real), float(p.imag)))
            continue
        try:
            x = float(p[0])
            y = float(p[1])
        except Exception:
            continue
        pts.append((x, y))
    return pts


def _is_manhattan(points: list[tuple[float, float]], *, tol: float) -> bool:
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx = abs(float(x1) - float(x0))
        dy = abs(float(y1) - float(y0))
        if dx <= tol and dy <= tol:
            continue
        if dx <= tol and dy > tol:
            continue
        if dy <= tol and dx > tol:
            continue
        return False
    return True


def _route_from_rectangle_polygon(
    poly_obj: Any,
    *,
    route_id: str,
    filter_set: set[tuple[int, int]] | None,
    tol_um: float,
) -> dict[str, Any] | None:
    layer = int(getattr(poly_obj, "layer", 0) or 0)
    datatype = int(getattr(poly_obj, "datatype", 0) or 0)
    if filter_set is not None and (layer, datatype) not in filter_set:
        return None

    pts = getattr(poly_obj, "points", None)
    if pts is None:
        return None

    # Convert to a list of unique vertices.
    raw = []
    for p in list(pts):
        try:
            raw.append((float(p[0]), float(p[1])))
        except Exception:
            continue
    if len(raw) < 4:
        return None

    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)

    dx = float(maxx - minx)
    dy = float(maxy - miny)
    if dx <= tol_um or dy <= tol_um:
        return None

    # Rectangle test: all vertices must lie on the bbox edges, and the polygon
    # must have exactly 4 corners within tolerance.
    corners = {(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)}
    matched = set()
    for x, y in raw:
        on_edge = abs(x - minx) <= tol_um or abs(x - maxx) <= tol_um or abs(y - miny) <= tol_um or abs(y - maxy) <= tol_um
        if not on_edge:
            return None
        for cx, cy in corners:
            if abs(x - cx) <= tol_um and abs(y - cy) <= tol_um:
                matched.add((cx, cy))
                break
    if len(matched) != 4:
        return None

    # Build a 2-point centerline route.
    if dx >= dy:
        width_um = dy
        y = 0.5 * (miny + maxy)
        points = [(minx, y), (maxx, y)]
    else:
        width_um = dx
        x = 0.5 * (minx + maxx)
        points = [(x, miny), (x, maxy)]

    if not _is_manhattan(points, tol=tol_um):
        return None

    return {
        "route_id": route_id,
        "width_um": float(width_um),
        "points_um": [[float(x), float(y)] for (x, y) in points],
        "source": {"kind": "gds_rectangle", "layer": layer, "datatype": datatype},
    }
