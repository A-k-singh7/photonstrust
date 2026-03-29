from __future__ import annotations

from photonstrust.chipverify.types import ChipVerifyGate, ChipVerifyMetrics


def default_gates() -> list[dict]:
    return [
        {
            "name": "max_insertion_loss",
            "metric": "total_insertion_loss_db",
            "threshold": 20.0,
            "comparator": "lt",
        },
        {
            "name": "min_component_count",
            "metric": "component_count",
            "threshold": 1,
            "comparator": "gt",
        },
    ]


_COMPARATORS = {
    "lt": lambda actual, threshold: actual < threshold,
    "gt": lambda actual, threshold: actual > threshold,
    "le": lambda actual, threshold: actual <= threshold,
    "ge": lambda actual, threshold: actual >= threshold,
}


def evaluate_gates(
    metrics: ChipVerifyMetrics,
    gate_configs: list[dict],
) -> list[ChipVerifyGate]:
    """Evaluate each gate config against the computed metrics."""
    gates: list[ChipVerifyGate] = []
    metrics_dict = metrics.as_dict()

    for cfg in gate_configs:
        name = str(cfg.get("name", ""))
        metric_key = str(cfg.get("metric", ""))
        threshold = float(cfg.get("threshold", 0.0))
        comparator = str(cfg.get("comparator", "lt"))

        actual_value = metrics_dict.get(metric_key)
        if actual_value is None:
            actual = 0.0
        else:
            actual = float(actual_value)

        cmp_fn = _COMPARATORS.get(comparator)
        if cmp_fn is None:
            status = "fail"
        else:
            status = "pass" if cmp_fn(actual, threshold) else "fail"

        gates.append(
            ChipVerifyGate(
                name=name,
                metric=metric_key,
                threshold=threshold,
                comparator=comparator,
                actual=actual,
                status=status,
            )
        )

    return gates


def overall_status(gates: list[ChipVerifyGate]) -> str:
    if not gates:
        return "pass"
    if any(g.status == "fail" for g in gates):
        return "fail"
    return "pass"
