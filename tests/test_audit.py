"""Tests for the audit trail and compliance governance framework."""

from __future__ import annotations

import json

from photonstrust.audit.log import AuditLog
from photonstrust.audit.portfolio import CompliancePortfolio
from photonstrust.audit.types import AuditEntry, AuditQuery


def test_audit_log_append_and_query(tmp_path):
    """Append 3 entries and verify query returns all 3."""
    log = AuditLog(tmp_path / "audit.jsonl")

    for i in range(3):
        log.append(
            actor=f"user-{i}",
            action="create",
            resource_type="key",
            resource_id=f"key-{i}",
            details={"index": i},
        )

    entries = log.query()
    assert len(entries) == 3
    assert entries[0].actor == "user-0"
    assert entries[2].resource_id == "key-2"


def test_audit_log_hash_chain_valid(tmp_path):
    """Append 5 entries and verify the chain is valid."""
    log = AuditLog(tmp_path / "audit.jsonl")

    for i in range(5):
        log.append(
            actor="system",
            action="rotate",
            resource_type="key",
            resource_id=f"key-{i}",
        )

    result = log.verify_chain()
    assert result["valid"] is True
    assert result["entries_checked"] == 5
    assert result["first_broken_at"] is None


def test_audit_log_tamper_detection(tmp_path):
    """Tamper with a middle entry and verify chain detects it."""
    log_path = tmp_path / "audit.jsonl"
    log = AuditLog(log_path)

    for i in range(3):
        log.append(
            actor="admin",
            action="deploy",
            resource_type="node",
            resource_id=f"node-{i}",
            details={"version": i},
        )

    # Tamper with the middle line (index 1)
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[1])
    data["details"]["version"] = 999  # tamper
    lines[1] = json.dumps(data, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Re-create log object so it re-reads from disk
    log2 = AuditLog(log_path)
    result = log2.verify_chain()
    assert result["valid"] is False
    assert result["first_broken_at"] == 1


def test_audit_log_query_by_actor(tmp_path):
    """Filter entries by a specific actor."""
    log = AuditLog(tmp_path / "audit.jsonl")

    log.append(actor="alice", action="read", resource_type="key", resource_id="k1")
    log.append(actor="bob", action="write", resource_type="key", resource_id="k2")
    log.append(actor="alice", action="delete", resource_type="key", resource_id="k3")

    q = AuditQuery(actor="alice")
    entries = log.query(q)
    assert len(entries) == 2
    assert all(e.actor == "alice" for e in entries)


def test_audit_log_query_by_time_range(tmp_path):
    """Verify start_iso / end_iso filtering path executes correctly."""
    log = AuditLog(tmp_path / "audit.jsonl")

    for i in range(3):
        log.append(
            actor="system",
            action="check",
            resource_type="link",
            resource_id=f"link-{i}",
        )

    # Use a wide time range that includes all entries
    q_all = AuditQuery(start_iso="2000-01-01T00:00:00", end_iso="2099-12-31T23:59:59")
    entries = log.query(q_all)
    assert len(entries) == 3

    # Use a time range far in the past that excludes everything
    q_none = AuditQuery(start_iso="2000-01-01T00:00:00", end_iso="2000-01-02T00:00:00")
    entries_none = log.query(q_none)
    assert len(entries_none) == 0


def test_compliance_portfolio_record_and_summary(tmp_path):
    """Record 3 assessments for 2 deployments and verify summary."""
    portfolio = CompliancePortfolio(tmp_path)

    portfolio.record_assessment(
        deployment_id="dep-1",
        standards_checked=["ETSI-QKD-005", "ISO-27001"],
        results_summary={"passed": 10, "failed": 0},
        overall_status="compliant",
    )
    portfolio.record_assessment(
        deployment_id="dep-2",
        standards_checked=["ETSI-QKD-005"],
        results_summary={"passed": 8, "failed": 2},
        overall_status="non_compliant",
    )
    portfolio.record_assessment(
        deployment_id="dep-1",
        standards_checked=["ETSI-QKD-005", "ISO-27001"],
        results_summary={"passed": 11, "failed": 0},
        overall_status="compliant",
        details_ref="report-001",
    )

    summary = portfolio.summary()
    assert summary.total_deployments == 2
    assert summary.compliant_deployments == 1
    assert summary.non_compliant_deployments == 1
    assert summary.standards_coverage["ETSI-QKD-005"] == 2
    assert summary.standards_coverage["ISO-27001"] == 1

    # Verify deployment history
    history = portfolio.get_deployment_history("dep-1")
    assert len(history) == 2


def test_audit_entry_serialization():
    """AuditEntry.as_dict() should contain all expected keys."""
    entry = AuditEntry(
        entry_id="abc-123",
        timestamp_iso="2026-03-23T12:00:00+00:00",
        actor="tester",
        action="test",
        resource_type="unit",
        resource_id="t-1",
        details={"foo": "bar"},
        previous_hash="0" * 64,
        entry_hash="a" * 64,
    )
    d = entry.as_dict()
    expected_keys = {
        "entry_id",
        "timestamp_iso",
        "actor",
        "action",
        "resource_type",
        "resource_id",
        "details",
        "previous_hash",
        "entry_hash",
    }
    assert set(d.keys()) == expected_keys
    assert d["actor"] == "tester"
    assert d["details"] == {"foo": "bar"}


def test_genesis_hash_is_zeros(tmp_path):
    """The first entry should have previous_hash equal to 64 zeros."""
    log = AuditLog(tmp_path / "audit.jsonl")
    entry = log.append(
        actor="genesis",
        action="init",
        resource_type="system",
        resource_id="boot",
    )
    assert entry.previous_hash == "0" * 64
