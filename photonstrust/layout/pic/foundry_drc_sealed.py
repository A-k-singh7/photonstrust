"""Foundry DRC sealed runner seam (metadata-safe summary only).

This module intentionally exposes a minimal, non-proprietary contract for
foundry DRC outcomes. It must never emit deck paths, deck content, or rule text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from photonstrust.utils import hash_dict

_ALLOWED_CHECK_STATUSES = {"pass", "fail", "error"}
_ALLOWED_RUN_STATUSES = {"pass", "fail", "error"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_status(value: Any, *, default: str = "error") -> str:
    status = _clean_text(value).lower()
    if status in _ALLOWED_RUN_STATUSES:
        return status
    return default


def _normalize_checks(raw_checks: Any) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    if not isinstance(raw_checks, list):
        return checks

    for i, raw in enumerate(raw_checks):
        if not isinstance(raw, dict):
            continue
        check_id = _clean_text(raw.get("id")) or f"check_{i}"
        check_name = _clean_text(raw.get("name")) or check_id
        status_raw = _clean_text(raw.get("status")).lower()
        status = status_raw if status_raw in _ALLOWED_CHECK_STATUSES else "error"
        checks.append({"id": check_id, "name": check_name, "status": status})

    checks.sort(key=lambda c: (c["id"].lower(), c["name"].lower()))
    return checks


def _derived_status(checks: list[dict[str, str]]) -> str:
    if any(c["status"] == "error" for c in checks):
        return "error"
    if any(c["status"] == "fail" for c in checks):
        return "fail"
    return "pass"


def _deterministic_run_id(*, execution_backend: str, deck_fingerprint: str | None, checks: list[dict[str, str]]) -> str:
    seed = {
        "execution_backend": execution_backend,
        "deck_fingerprint": deck_fingerprint,
        "checks": checks,
    }
    return f"drcs_{hash_dict(seed)[:12]}"


@dataclass(frozen=True)
class FoundryDRCSealedSummary:
    schema_version: str
    kind: str
    run_id: str
    status: str
    execution_backend: str
    started_at: str
    finished_at: str
    check_counts: dict[str, int]
    failed_check_ids: list[str]
    failed_check_names: list[str]
    deck_fingerprint: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "run_id": self.run_id,
            "status": self.status,
            "execution_backend": self.execution_backend,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "check_counts": {
                "total": int(self.check_counts.get("total", 0)),
                "passed": int(self.check_counts.get("passed", 0)),
                "failed": int(self.check_counts.get("failed", 0)),
                "errored": int(self.check_counts.get("errored", 0)),
            },
            "failed_check_ids": list(self.failed_check_ids),
            "failed_check_names": list(self.failed_check_names),
            "deck_fingerprint": self.deck_fingerprint,
            "error_code": self.error_code,
        }


def run_foundry_drc_sealed(
    request: dict[str, Any] | None = None,
    *,
    now_fn: Callable[[], str] = _utc_now_iso,
) -> dict[str, Any]:
    """Run a sealed foundry DRC backend and return metadata-safe summary.

    Supported request fields:
      - run_id?: str
      - backend?: str (only "mock" is available in open-core)
      - deck_fingerprint?: str
      - mock_result?:
          {
            status?: "pass"|"fail"|"error",
            checks?: [{id, name, status}],
          }

    Notes:
      - Deck paths/content/rule text are intentionally ignored.
      - Output is constrained to safe metadata for API-facing summaries.
    """

    req = dict(request or {})
    started_at = now_fn()

    execution_backend = _clean_text(req.get("backend") or "mock") or "mock"
    deck_fingerprint_raw = req.get("deck_fingerprint")
    deck_fingerprint = _clean_text(deck_fingerprint_raw) if deck_fingerprint_raw is not None else None

    backend_error_code: str | None = None
    checks: list[dict[str, str]] = []
    status: str

    if execution_backend == "mock":
        mock_result = req.get("mock_result") if isinstance(req.get("mock_result"), dict) else {}
        checks = _normalize_checks(mock_result.get("checks"))
        status = _normalize_status(mock_result.get("status"), default=_derived_status(checks))
    else:
        # Sealed proprietary backends are not implemented in open-core.
        checks = []
        status = "error"
        backend_error_code = "backend_unavailable"

    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    errored = sum(1 for c in checks if c["status"] == "error")

    failed_checks = [c for c in checks if c["status"] == "fail"]
    failed_check_ids = [c["id"] for c in failed_checks]
    failed_check_names = [c["name"] for c in failed_checks]

    run_id = _clean_text(req.get("run_id")) or _deterministic_run_id(
        execution_backend=execution_backend,
        deck_fingerprint=deck_fingerprint,
        checks=checks,
    )

    summary = FoundryDRCSealedSummary(
        schema_version="0.1",
        kind="pic.foundry_drc_sealed_summary",
        run_id=run_id,
        status=status,
        execution_backend=execution_backend,
        started_at=started_at,
        finished_at=now_fn(),
        check_counts={
            "total": int(len(checks)),
            "passed": int(passed),
            "failed": int(failed),
            "errored": int(errored),
        },
        failed_check_ids=failed_check_ids,
        failed_check_names=failed_check_names,
        deck_fingerprint=deck_fingerprint,
        error_code=backend_error_code,
    )
    return summary.to_dict()
