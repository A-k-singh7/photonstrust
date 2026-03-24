from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChipVerifyGate:
    name: str
    metric: str
    threshold: float
    comparator: str  # "lt" | "gt" | "le" | "ge"
    actual: float
    status: str  # "pass" | "fail"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "metric": self.metric,
            "threshold": self.threshold,
            "comparator": self.comparator,
            "actual": self.actual,
            "status": self.status,
        }


@dataclass(frozen=True)
class ChipVerifyMetrics:
    total_insertion_loss_db: float
    bandwidth_3db_nm: float | None
    crosstalk_isolation_db: float | None
    component_count: int
    edge_count: int

    def as_dict(self) -> dict:
        return {
            "total_insertion_loss_db": self.total_insertion_loss_db,
            "bandwidth_3db_nm": self.bandwidth_3db_nm,
            "crosstalk_isolation_db": self.crosstalk_isolation_db,
            "component_count": self.component_count,
            "edge_count": self.edge_count,
        }


@dataclass(frozen=True)
class ChipVerifyReport:
    report_id: str
    netlist_hash: str
    timestamp: str
    simulation_results: dict
    drc_results: dict
    lvs_results: dict | None
    performance_metrics: ChipVerifyMetrics
    gates: list[ChipVerifyGate]
    overall_status: str  # "pass" | "fail" | "conditional"
    warnings: list[str]

    def as_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "netlist_hash": self.netlist_hash,
            "timestamp": self.timestamp,
            "simulation_results": self.simulation_results,
            "drc_results": self.drc_results,
            "lvs_results": self.lvs_results,
            "performance_metrics": self.performance_metrics.as_dict(),
            "gates": [g.as_dict() for g in self.gates],
            "overall_status": self.overall_status,
            "warnings": list(self.warnings),
        }
