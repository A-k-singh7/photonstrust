from __future__ import annotations

import pytest

from photonstrust.protocols.engines.base import ProtocolEngine, ProtocolPrimitiveResult
from photonstrust.protocols.engines.parity import run_protocol_engine_parity


class _FixedEngine(ProtocolEngine):
    def __init__(self, *, engine_id: str, value: float, available: bool = True) -> None:
        self.engine_id = engine_id
        self._value = float(value)
        self._available = bool(available)

    def supported_primitives(self) -> tuple[str, ...]:
        return ("swap_bsm_equal_bits",)

    def availability(self) -> tuple[bool, str | None]:
        if self._available:
            return True, None
        return False, "dependency unavailable"

    def run_primitive(self, primitive: str, *, seed: int | None = None) -> ProtocolPrimitiveResult:
        _ = seed
        return ProtocolPrimitiveResult(
            engine_id=self.engine_id,
            primitive=primitive,
            metrics={"success_probability": self._value},
            metadata={},
        )


def test_parity_harness_reports_deltas_and_violations(monkeypatch: pytest.MonkeyPatch) -> None:
    engines = {
        "analytic": _FixedEngine(engine_id="analytic", value=0.5),
        "candidate": _FixedEngine(engine_id="candidate", value=0.6),
    }
    monkeypatch.setattr(
        "photonstrust.protocols.engines.parity.get_protocol_engine",
        lambda engine_id: engines[str(engine_id)],
    )

    report = run_protocol_engine_parity(
        primitive="swap_bsm_equal_bits",
        engine_ids=["analytic", "candidate"],
        baseline_engine_id="analytic",
        threshold_policy={"swap_bsm_equal_bits": {"success_probability": 0.05}},
        seed=1,
    )

    assert report["baseline_available"] is True
    assert report["summary"]["violations_total"] == 1
    candidate_row = [row for row in report["engine_results"] if row["engine_id"] == "candidate"][0]
    assert candidate_row["metrics"]["success_probability"] == pytest.approx(0.6)
    assert candidate_row["delta_abs_vs_baseline"]["success_probability"] == pytest.approx(0.1)


def test_parity_harness_marks_unavailable_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    engines = {
        "qiskit": _FixedEngine(engine_id="qiskit", value=0.5, available=False),
        "analytic": _FixedEngine(engine_id="analytic", value=0.5),
    }
    monkeypatch.setattr(
        "photonstrust.protocols.engines.parity.get_protocol_engine",
        lambda engine_id: engines[str(engine_id)],
    )

    report = run_protocol_engine_parity(
        primitive="swap_bsm_equal_bits",
        engine_ids=["qiskit", "analytic"],
        baseline_engine_id="qiskit",
        seed=1,
    )

    assert report["baseline_available"] is False
    assert report["summary"]["status_counts"]["unavailable"] == 1
    assert report["summary"]["violations_total"] == 0
