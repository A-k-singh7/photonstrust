"""Core types for ETSI QKD compliance checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_WARNING = "WARNING"
STATUS_NOT_ASSESSED = "NOT_ASSESSED"
VALID_STATUSES = {
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_WARNING,
    STATUS_NOT_ASSESSED,
}


class CheckFn(Protocol):
    def __call__(
        self,
        sweep_result: Any,
        scenario: dict[str, Any],
        *,
        context: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ETSIRequirement:
    id: str
    standard: str
    version: str
    clause: str
    description: str
    check_fn: CheckFn
    inputs_required: tuple[str, ...]
    category: str


@dataclass(frozen=True)
class RequirementResult:
    req_id: str
    standard: str
    clause: str
    description: str
    status: str
    computed_value: Any
    threshold: Any
    unit: str | None
    notes: list[str]


def normalize_status(value: Any) -> str:
    candidate = str(value or "").strip().upper()
    if candidate in VALID_STATUSES:
        return candidate
    return STATUS_NOT_ASSESSED
