"""Compliance portfolio tracking with JSONL persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.audit.types import CompliancePortfolioEntry, PortfolioSummary


class CompliancePortfolio:
    """Tracks compliance assessments across deployments."""

    def __init__(self, portfolio_dir: Path) -> None:
        self._portfolio_dir = Path(portfolio_dir)
        self._portfolio_path = self._portfolio_dir / "portfolio.jsonl"

    def record_assessment(
        self,
        *,
        deployment_id: str,
        standards_checked: list[str],
        results_summary: dict,
        overall_status: str,
        details_ref: str = "",
    ) -> CompliancePortfolioEntry:
        """Persist a new compliance assessment and return the entry."""
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        entry = CompliancePortfolioEntry(
            deployment_id=deployment_id,
            timestamp_iso=timestamp_iso,
            standards_checked=standards_checked,
            results_summary=results_summary,
            overall_status=overall_status,
            details_ref=details_ref,
        )
        self._portfolio_dir.mkdir(parents=True, exist_ok=True)
        with open(self._portfolio_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.as_dict(), sort_keys=True) + "\n")
        return entry

    def get_deployment_history(
        self, deployment_id: str
    ) -> list[CompliancePortfolioEntry]:
        """Return all assessments for a given deployment."""
        return [
            e for e in self._read_all() if e.deployment_id == deployment_id
        ]

    def summary(self) -> PortfolioSummary:
        """Compute an aggregated summary across all assessments."""
        entries = self._read_all()
        if not entries:
            return PortfolioSummary(
                total_deployments=0,
                compliant_deployments=0,
                non_compliant_deployments=0,
                last_assessment_iso="",
                standards_coverage={},
            )

        # Track latest status per deployment
        latest: dict[str, CompliancePortfolioEntry] = {}
        for e in entries:
            latest[e.deployment_id] = e

        compliant = sum(
            1 for e in latest.values() if e.overall_status == "compliant"
        )
        non_compliant = sum(
            1 for e in latest.values() if e.overall_status != "compliant"
        )

        # Standards coverage: count how many deployments checked each standard
        standards_coverage: dict[str, int] = {}
        for e in latest.values():
            for std in e.standards_checked:
                standards_coverage[std] = standards_coverage.get(std, 0) + 1

        last_assessment_iso = max(e.timestamp_iso for e in entries)

        return PortfolioSummary(
            total_deployments=len(latest),
            compliant_deployments=compliant,
            non_compliant_deployments=non_compliant,
            last_assessment_iso=last_assessment_iso,
            standards_coverage=standards_coverage,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _read_all(self) -> list[CompliancePortfolioEntry]:
        if not self._portfolio_path.exists():
            return []
        entries: list[CompliancePortfolioEntry] = []
        with open(self._portfolio_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entries.append(CompliancePortfolioEntry(**data))
        return entries
