"""Foundry PEX sealed runner seam (metadata-safe summary only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from photonstrust.layout.pic.generic_cli_sealed_runner import run_generic_cli_backend
from photonstrust.utils import hash_dict

_ALLOWED_CHECK_STATUSES = {"pass", "fail", "error"}
_ALLOWED_RUN_STATUSES = {"pass", "fail", "error"}
_GENERIC_CLI_EMPTY_CHECKS_ERROR_CODE = "generic_cli_empty_checks"
_GENERIC_CLI_STATUS_CHECKS_CONFLICT_ERROR_CODE = "generic_cli_status_checks_conflict"


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


def _harden_generic_cli_outcome(
    *,
    status: str,
    checks: list[dict[str, str]],
    error_code: str | None,
) -> tuple[str, str | None]:
    normalized_status = _normalize_status(status, default="error")
    normalized_error_code = _clean_text(error_code) or None
    if normalized_status != "pass":
        return normalized_status, normalized_error_code
    if not checks:
        return "error", normalized_error_code or _GENERIC_CLI_EMPTY_CHECKS_ERROR_CODE
    if any(_clean_text(check.get("status")).lower() in {"fail", "error"} for check in checks):
        return "error", normalized_error_code or _GENERIC_CLI_STATUS_CHECKS_CONFLICT_ERROR_CODE
    return normalized_status, normalized_error_code


def _deterministic_run_id(*, execution_backend: str, deck_fingerprint: str | None, checks: list[dict[str, str]]) -> str:
    seed = {
        "execution_backend": execution_backend,
        "deck_fingerprint": deck_fingerprint,
        "checks": checks,
    }
    return f"pexs_{hash_dict(seed)[:12]}"


@dataclass(frozen=True)
class FoundryPEXSealedSummary:
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


def run_foundry_pex_sealed(
    request: dict[str, Any] | None = None,
    *,
    now_fn: Callable[[], str] = _utc_now_iso,
) -> dict[str, Any]:
    req = dict(request or {})
    started_at = now_fn()

    requested_backend = _clean_text(req.get("backend") or "mock") or "mock"
    execution_backend = requested_backend if requested_backend in {"mock", "generic_cli"} else "mock"
    deck_fingerprint_raw = req.get("deck_fingerprint")
    deck_fingerprint = _clean_text(deck_fingerprint_raw) if deck_fingerprint_raw is not None else None

    backend_error_code: str | None = None
    checks: list[dict[str, str]] = []
    status: str

    if requested_backend == "mock":
        raw_mock_result = req.get("mock_result")
        if isinstance(raw_mock_result, dict):
            mock_result: dict[str, Any] = dict(raw_mock_result)
        else:
            mock_result = {}
        checks = _normalize_checks(mock_result.get("checks"))
        status = _normalize_status(mock_result.get("status"), default=_derived_status(checks))
    elif requested_backend == "generic_cli":
        generic_result = run_generic_cli_backend(
            req,
            normalize_status=_normalize_status,
            normalize_checks=_normalize_checks,
            derive_status=_derived_status,
        )
        checks = generic_result.checks
        status = generic_result.status
        backend_error_code = generic_result.error_code
        status, backend_error_code = _harden_generic_cli_outcome(
            status=status,
            checks=checks,
            error_code=backend_error_code,
        )
    else:
        checks = []
        status = "error"
        backend_error_code = "unsupported_backend"

    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    errored = sum(1 for c in checks if c["status"] == "error")

    failed_checks = [c for c in checks if c["status"] == "fail"]
    failed_check_ids = [c["id"] for c in failed_checks]
    failed_check_names = [c["name"] for c in failed_checks]

    run_id = _clean_text(req.get("run_id")) or _deterministic_run_id(
        execution_backend=requested_backend,
        deck_fingerprint=deck_fingerprint,
        checks=checks,
    )

    summary = FoundryPEXSealedSummary(
        schema_version="0.1",
        kind="pic.foundry_pex_sealed_summary",
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
