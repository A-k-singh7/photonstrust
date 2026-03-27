"""Audit trail and compliance governance data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuditEntry:
    """Single tamper-evident audit log entry."""

    entry_id: str
    timestamp_iso: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: dict = field(default_factory=dict)
    previous_hash: str = ""
    entry_hash: str = ""

    def as_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "timestamp_iso": self.timestamp_iso,
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass
class AuditQuery:
    """Mutable query filter for audit log searches."""

    actor: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    start_iso: str | None = None
    end_iso: str | None = None
    limit: int = 100


@dataclass(frozen=True)
class CompliancePortfolioEntry:
    """Record of a single compliance assessment."""

    deployment_id: str
    timestamp_iso: str
    standards_checked: list[str] = field(default_factory=list)
    results_summary: dict = field(default_factory=dict)
    overall_status: str = ""
    details_ref: str = ""

    def as_dict(self) -> dict:
        return {
            "deployment_id": self.deployment_id,
            "timestamp_iso": self.timestamp_iso,
            "standards_checked": list(self.standards_checked),
            "results_summary": self.results_summary,
            "overall_status": self.overall_status,
            "details_ref": self.details_ref,
        }


@dataclass(frozen=True)
class PortfolioSummary:
    """Aggregated compliance portfolio summary."""

    total_deployments: int
    compliant_deployments: int
    non_compliant_deployments: int
    last_assessment_iso: str
    standards_coverage: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "total_deployments": self.total_deployments,
            "compliant_deployments": self.compliant_deployments,
            "non_compliant_deployments": self.non_compliant_deployments,
            "last_assessment_iso": self.last_assessment_iso,
            "standards_coverage": self.standards_coverage,
        }
