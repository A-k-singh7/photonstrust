from __future__ import annotations

from photonstrust.chipverify.types import ChipVerifyMetrics


def compute_insertion_loss_db(simulation_results: dict) -> float:
    """Extract total insertion loss from simulation results.

    Looks for chain_solver.total_loss_db first, then falls back to summing
    per-component losses.  Ensures the result is >= 0.
    """
    chain = simulation_results.get("chain_solver")
    if isinstance(chain, dict) and chain.get("applicable"):
        total = chain.get("total_loss_db")
        if total is not None:
            return max(0.0, float(total))

    # Fallback: sum per-component losses from chain solver.
    if isinstance(chain, dict) and chain.get("applicable"):
        per = chain.get("per_component")
        if isinstance(per, list) and per:
            total = sum(float(c.get("loss_db", 0.0)) for c in per if isinstance(c, dict))
            return max(0.0, total)

    # Fallback: use DAG solver external_outputs loss.
    dag = simulation_results.get("dag_solver")
    if isinstance(dag, dict):
        outs = dag.get("external_outputs")
        if isinstance(outs, list) and outs:
            max_loss = max(
                (float(o.get("loss_db", 0.0)) for o in outs if isinstance(o, dict)),
                default=0.0,
            )
            return max(0.0, max_loss)

    return 0.0


def compute_pic_metrics(
    *,
    simulation_results: dict,
    netlist: dict,
    wavelength_nm: float | None = None,
) -> ChipVerifyMetrics:
    """Build ChipVerifyMetrics from simulation results and the compiled netlist."""
    total_il = compute_insertion_loss_db(simulation_results)

    nodes = netlist.get("nodes")
    edges = netlist.get("edges")
    component_count = len(nodes) if isinstance(nodes, list) else 0
    edge_count = len(edges) if isinstance(edges, list) else 0

    return ChipVerifyMetrics(
        total_insertion_loss_db=total_il,
        bandwidth_3db_nm=None,
        crosstalk_isolation_db=None,
        component_count=component_count,
        edge_count=edge_count,
    )
