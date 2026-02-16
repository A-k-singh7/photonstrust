"""GraphSpec helpers for TOML/JSON round-tripping."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback for older runtimes
    import tomli as tomllib  # type: ignore[no-redef]


_TOP_KEY_ORDER = [
    "schema_version",
    "graph_id",
    "profile",
    "metadata",
    "scenario",
    "circuit",
    "uncertainty",
    "finite_key",
    "ui",
]


def parse_graphspec_toml(text: str) -> dict[str, Any]:
    """Parse GraphSpec TOML and return canonical graph JSON dict.

    GraphSpec TOML cannot represent explicit null values. Canonicalization treats
    null and missing fields as equivalent by dropping null dictionary entries.
    """

    raw = tomllib.loads(str(text))
    if not isinstance(raw, dict):
        raise ValueError("GraphSpec TOML root must be an object")
    return canonicalize_graph(raw)


def load_graph_file(path: str | Path) -> dict[str, Any]:
    """Load a graph from JSON or GraphSpec TOML."""

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    lower = p.name.lower()
    if lower.endswith(".toml"):
        return parse_graphspec_toml(text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Graph JSON root must be an object")
    return canonicalize_graph(payload)


def stable_graph_hash(graph: dict[str, Any]) -> str:
    """Return a stable semantic hash for a graph."""

    canonical = canonicalize_graph(graph)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def format_graphspec_toml(graph: dict[str, Any]) -> str:
    """Serialize graph as deterministic GraphSpec TOML."""

    canonical = canonicalize_graph(graph)
    lines: list[str] = []

    for key in _TOP_KEY_ORDER:
        if key not in canonical:
            continue
        if key in {"nodes", "edges"}:
            continue
        lines.append(f"{_toml_key(key)} = {_toml_inline(canonical[key])}")

    for key in sorted(k for k in canonical.keys() if k not in set(_TOP_KEY_ORDER) | {"nodes", "edges"}):
        lines.append(f"{_toml_key(key)} = {_toml_inline(canonical[key])}")

    nodes = canonical.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            lines.append("")
            lines.append("[[nodes]]")
            _append_table_kv(lines, node, preferred=["id", "kind", "label", "params", "ui"])

    edges = canonical.get("edges")
    if isinstance(edges, list) and edges:
        for edge in edges:
            lines.append("")
            lines.append("[[edges]]")
            _append_table_kv(lines, edge, preferred=["id", "from", "from_port", "to", "to_port", "kind", "label", "params"])

    return "\n".join(lines).rstrip() + "\n"


def canonicalize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Normalize graph for deterministic formatting/hashing/round-trip checks."""

    if not isinstance(graph, dict):
        raise TypeError("canonicalize_graph expects a graph dict")

    raw = _strip_null_dict_entries(_normalize_jsonish(graph))
    profile = str(raw.get("profile", "")).strip().lower()

    raw["schema_version"] = str(raw.get("schema_version", "0.1") or "0.1")
    if "graph_id" in raw:
        raw["graph_id"] = str(raw.get("graph_id", "")).strip()

    nodes = raw.get("nodes")
    if isinstance(nodes, list):
        normalized_nodes: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            n = _strip_null_dict_entries(_normalize_jsonish(node))
            if "id" in n:
                n["id"] = str(n.get("id", "")).strip()
            if "kind" in n:
                n["kind"] = str(n.get("kind", "")).strip()
            params = n.get("params")
            if params is None or not isinstance(params, dict):
                n["params"] = {}
            normalized_nodes.append(n)
        raw["nodes"] = sorted(normalized_nodes, key=lambda n: str(n.get("id", "")).lower())

    edges = raw.get("edges")
    if isinstance(edges, list):
        normalized_edges: list[dict[str, Any]] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            e = _strip_null_dict_entries(_normalize_jsonish(edge))
            if "from" in e:
                e["from"] = str(e.get("from", "")).strip()
            if "to" in e:
                e["to"] = str(e.get("to", "")).strip()
            if profile == "pic_circuit":
                e["kind"] = str(e.get("kind", "optical") or "optical")
                e["from_port"] = str(e.get("from_port", "out") or "out")
                e["to_port"] = str(e.get("to_port", "in") or "in")
                params = e.get("params")
                e["params"] = params if isinstance(params, dict) else {}
            normalized_edges.append(e)
        raw["edges"] = sorted(
            normalized_edges,
            key=lambda e: (
                str(e.get("from", "")).lower(),
                str(e.get("from_port", "")).lower(),
                str(e.get("to", "")).lower(),
                str(e.get("to_port", "")).lower(),
                str(e.get("kind", "")).lower(),
                str(e.get("id", "")).lower(),
            ),
        )

    return _sort_object(raw)


def _append_table_kv(lines: list[str], payload: Any, *, preferred: list[str]) -> None:
    if not isinstance(payload, dict):
        return
    preferred_set = set(preferred)
    ordered_keys = [k for k in preferred if k in payload] + sorted(k for k in payload.keys() if k not in preferred_set)
    for key in ordered_keys:
        lines.append(f"{_toml_key(key)} = {_toml_inline(payload[key])}")


def _sort_object(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sort_object(value[k]) for k in sorted(value.keys(), key=lambda s: str(s).lower())}
    if isinstance(value, list):
        return [_sort_object(v) for v in value]
    return value


def _normalize_jsonish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_jsonish(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_jsonish(v) for v in value]
    return value


def _strip_null_dict_entries(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            vv = _strip_null_dict_entries(v)
            if vv is None:
                continue
            out[str(k)] = vv
        return out
    if isinstance(value, list):
        return [_strip_null_dict_entries(v) for v in value]
    return value


_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(key: Any) -> str:
    k = str(key)
    if _BARE_KEY_RE.match(k):
        return k
    return _toml_string(k)


def _toml_inline(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("GraphSpec formatter does not support non-finite floats")
        out = repr(value)
        if out == "-0.0":
            return "0.0"
        return out
    if isinstance(value, str):
        return _toml_string(value)
    if value is None:
        raise ValueError("GraphSpec TOML cannot encode null values")
    if isinstance(value, list):
        return "[" + ", ".join(_toml_inline(v) for v in value) + "]"
    if isinstance(value, dict):
        items: list[str] = []
        for k in sorted(value.keys(), key=lambda s: str(s).lower()):
            items.append(f"{_toml_key(k)} = {_toml_inline(value[k])}")
        return "{" + ", ".join(items) + "}"
    raise ValueError(f"Unsupported GraphSpec value type: {type(value).__name__}")


def _toml_string(value: str) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'
