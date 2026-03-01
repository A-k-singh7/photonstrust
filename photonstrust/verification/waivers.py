"""PIC waiver loading and validation utilities."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


class WaiverValidationError(ValueError):
    """Raised when a waiver document cannot be loaded or schema-validated."""


def pic_waivers_schema_path() -> Path:
    return (Path(__file__).resolve().parents[2] / "schemas" / "photonstrust.pic_waivers.v0.schema.json").resolve()


def load_pic_waiver_file(path: str | Path) -> dict[str, Any]:
    waiver_path = Path(path).resolve()
    if not waiver_path.exists():
        raise WaiverValidationError(f"Waiver file not found: {waiver_path}")

    try:
        payload = json.loads(waiver_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WaiverValidationError(f"Waiver file is not valid JSON: {waiver_path}") from exc

    if not isinstance(payload, dict):
        raise WaiverValidationError("Waiver file must be a JSON object")

    _validate_schema(payload, pic_waivers_schema_path())
    return payload


def validate_pic_waivers(payload: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    rows_raw = payload.get("waivers")
    rows: list[Any] = rows_raw if isinstance(rows_raw, list) else []
    ref_now = _utc_now_or(now)

    active = 0
    expired = 0
    invalid = 0
    active_rule_ids: list[str] = []
    issues: list[str] = []

    for i, row in enumerate(rows):
        row_label = f"waivers[{i}]"
        if not isinstance(row, dict):
            invalid += 1
            issues.append(f"{row_label}: entry must be an object")
            continue

        justification = str(row.get("justification", "")).strip()
        reviewer = str(row.get("reviewer", "")).strip()
        status = str(row.get("status", "")).strip().lower()

        row_invalid = False
        if not justification:
            row_invalid = True
            issues.append(f"{row_label}: missing justification")
        if not reviewer:
            row_invalid = True
            issues.append(f"{row_label}: missing reviewer")

        approved_at = _parse_datetime(row.get("approved_at"), label=f"{row_label}.approved_at", issues=issues)
        expires_at = _parse_datetime(row.get("expires_at"), label=f"{row_label}.expires_at", issues=issues)

        if approved_at is None or expires_at is None:
            row_invalid = True
        elif expires_at < approved_at:
            row_invalid = True
            issues.append(f"{row_label}: expires_at precedes approved_at")

        if row_invalid:
            invalid += 1
            continue

        is_expired = status == "expired" or (expires_at is not None and expires_at <= ref_now)
        if is_expired:
            expired += 1
            issues.append(f"{row_label}: waiver is expired")
            continue

        if status == "active":
            active += 1
            rule_id = str(row.get("rule_id", "")).strip()
            if rule_id:
                active_rule_ids.append(rule_id)

    summary = {
        "total": int(len(rows)),
        "active": int(active),
        "expired": int(expired),
        "invalid": int(invalid),
    }
    return {
        "ok": bool(expired == 0 and invalid == 0),
        "summary": summary,
        "active_rule_ids": sorted(set(active_rule_ids), key=lambda s: s.lower()),
        "issues": issues,
    }


def load_and_validate_pic_waivers(path: str | Path, *, now: datetime | None = None) -> dict[str, Any]:
    payload = load_pic_waiver_file(path)
    result = validate_pic_waivers(payload, now=now)
    result["path"] = str(Path(path).resolve())
    return result


def _validate_schema(instance: dict[str, Any], schema_path: Path) -> None:
    try:
        from jsonschema import validate
    except Exception as exc:  # pragma: no cover - dev dependency
        raise RuntimeError(
            "jsonschema is required for waiver schema validation. "
            "Install dev dependencies (e.g., photonstrust[dev])."
        ) from exc

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        validate(instance=instance, schema=schema)
    except Exception as exc:
        raise WaiverValidationError(str(exc)) from exc


def _parse_datetime(value: Any, *, label: str, issues: list[str]) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        issues.append(f"{label}: missing timestamp")
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        out = datetime.fromisoformat(text)
    except ValueError:
        issues.append(f"{label}: invalid datetime value")
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def _utc_now_or(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)
