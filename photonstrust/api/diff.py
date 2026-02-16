"""JSON diff helpers for run manifests (local-dev).

We intentionally keep this bounded and stable:
- Paths use JSON Pointer escaping (RFC 6901).
- Only leaf changes are recorded for nested dicts.
- Lists are treated as atomic values to avoid large diffs.
"""

from __future__ import annotations

from typing import Any


def json_pointer_escape(token: str) -> str:
    """Escape a token for inclusion in a JSON Pointer path (RFC 6901)."""

    return str(token).replace("~", "~0").replace("/", "~1")


def json_pointer_join(prefix: str, token: str) -> str:
    """Join a JSON Pointer prefix and a token."""

    p = str(prefix or "")
    if p and not p.startswith("/"):
        # Defensive: treat non-empty non-root prefixes as already tokenized.
        p = "/" + p
    return f"{p}/{json_pointer_escape(token)}"


def diff_json(
    lhs: Any,
    rhs: Any,
    *,
    limit: int = 200,
) -> dict[str, Any]:
    """Compute a bounded diff between two JSON-like objects.

    Returns:
      {"changes": [{"path": str, "lhs": Any, "rhs": Any}, ...], "truncated": bool}
    """

    if limit < 1:
        limit = 1
    if limit > 2000:
        limit = 2000

    changes: list[dict[str, Any]] = []
    truncated = False

    def rec(a: Any, b: Any, ptr: str) -> None:
        nonlocal truncated
        if truncated:
            return

        if a == b:
            return

        if isinstance(a, dict) and isinstance(b, dict):
            keys = sorted(set(a.keys()) | set(b.keys()), key=lambda x: str(x))
            for k in keys:
                if truncated:
                    return
                p2 = json_pointer_join(ptr, str(k))
                in_a = k in a
                in_b = k in b
                if in_a and in_b:
                    rec(a.get(k), b.get(k), p2)
                elif in_a and not in_b:
                    changes.append({"path": p2, "lhs": a.get(k), "rhs": None})
                else:
                    changes.append({"path": p2, "lhs": None, "rhs": b.get(k)})

                if len(changes) >= limit:
                    truncated = True
                    return
            return

        # Lists are treated as atomic to keep diffs bounded and stable.
        changes.append({"path": ptr, "lhs": a, "rhs": b})
        if len(changes) >= limit:
            truncated = True

    rec(lhs, rhs, "")
    return {"changes": changes, "truncated": truncated}


def _violation_key(violation: dict[str, Any]) -> str | None:
    """Return a stable key for a violation row.

    Preference order:
    1) explicit `id`
    2) derived key from (`code`, `entity_ref`, `message`)
    """

    if not isinstance(violation, dict):
        return None

    rid = str(violation.get("id", "")).strip()
    if rid:
        return f"id:{rid}"

    code = str(violation.get("code", "")).strip().lower()
    entity_ref = str(violation.get("entity_ref", "")).strip().lower()
    message = str(violation.get("message", "")).strip().lower()
    if not (code or entity_ref or message):
        return None
    return f"derived:{code}|{entity_ref}|{message}"


def diff_violations(lhs: list[dict[str, Any]], rhs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute semantic violation diff buckets for two violation lists."""

    lhs_by_key: dict[str, dict[str, Any]] = {}
    rhs_by_key: dict[str, dict[str, Any]] = {}

    for item in lhs:
        if not isinstance(item, dict):
            continue
        key = _violation_key(item)
        if key and key not in lhs_by_key:
            lhs_by_key[key] = item

    for item in rhs:
        if not isinstance(item, dict):
            continue
        key = _violation_key(item)
        if key and key not in rhs_by_key:
            rhs_by_key[key] = item

    lhs_keys = set(lhs_by_key.keys())
    rhs_keys = set(rhs_by_key.keys())

    new_items = [rhs_by_key[k] for k in sorted(rhs_keys - lhs_keys)]
    resolved_items = [lhs_by_key[k] for k in sorted(lhs_keys - rhs_keys)]

    applicability_changed: list[dict[str, Any]] = []
    for key in sorted(lhs_keys & rhs_keys):
        lhs_item = lhs_by_key[key]
        rhs_item = rhs_by_key[key]
        lhs_app = str(lhs_item.get("applicability", "")).strip().lower()
        rhs_app = str(rhs_item.get("applicability", "")).strip().lower()
        if lhs_app != rhs_app:
            applicability_changed.append(
                {
                    "key": key,
                    "lhs_applicability": lhs_item.get("applicability"),
                    "rhs_applicability": rhs_item.get("applicability"),
                    "lhs": lhs_item,
                    "rhs": rhs_item,
                }
            )

    return {
        "new": new_items,
        "resolved": resolved_items,
        "applicability_changed": applicability_changed,
        "summary": {
            "new_count": len(new_items),
            "resolved_count": len(resolved_items),
            "applicability_changed_count": len(applicability_changed),
        },
    }
