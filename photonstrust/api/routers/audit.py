"""Audit trail and compliance governance API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/v1/audit", tags=["audit"])

_DEFAULT_AUDIT_LOG_PATH = Path("data/audit/audit.jsonl")
_DEFAULT_PORTFOLIO_DIR = Path("data/audit/")


def _get_audit_log():
    from photonstrust.audit.log import AuditLog

    return AuditLog(_DEFAULT_AUDIT_LOG_PATH)


def _get_portfolio():
    from photonstrust.audit.portfolio import CompliancePortfolio

    return CompliancePortfolio(_DEFAULT_PORTFOLIO_DIR)


@router.get("/log")
def query_audit_log(
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 100,
) -> dict:
    """Query the audit log with optional filters."""
    from photonstrust.audit.types import AuditQuery

    log = _get_audit_log()
    q = AuditQuery(
        actor=actor,
        action=action,
        resource_type=resource_type,
        limit=limit,
    )
    entries = log.query(q)
    return {"entries": [e.as_dict() for e in entries], "count": len(entries)}


@router.get("/log/verify")
def verify_audit_chain() -> dict:
    """Verify the integrity of the hash-chained audit log."""
    log = _get_audit_log()
    return log.verify_chain()


@router.get("/portfolio")
def portfolio_summary() -> dict:
    """Return aggregated compliance portfolio summary."""
    portfolio = _get_portfolio()
    return portfolio.summary().as_dict()


@router.get("/portfolio/{deployment_id}")
def deployment_compliance_history(deployment_id: str) -> dict:
    """Return the compliance assessment history for a specific deployment."""
    portfolio = _get_portfolio()
    entries = portfolio.get_deployment_history(deployment_id)
    return {"deployment_id": deployment_id, "entries": [e.as_dict() for e in entries]}
