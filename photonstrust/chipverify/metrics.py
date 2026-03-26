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


def compute_bandwidth_3db_nm(simulation_results: dict) -> float | None:
    """Extract 3-dB bandwidth from simulation results (ring/filter structures)."""
    chain = simulation_results.get("chain_solver")
    if isinstance(chain, dict) and chain.get("applicable"):
        per = chain.get("per_component")
        if isinstance(per, list):
            for comp in per:
                if isinstance(comp, dict) and comp.get("kind", "").startswith("pic.ring"):
                    bw = comp.get("bandwidth_3db_nm")
                    if bw is not None:
                        return max(0.0, float(bw))
    return None


def compute_crosstalk_isolation_db(simulation_results: dict) -> float | None:
    """Extract crosstalk isolation from simulation results."""
    dag = simulation_results.get("dag_solver")
    if isinstance(dag, dict):
        outs = dag.get("external_outputs")
        if isinstance(outs, list) and len(outs) >= 2:
            powers = [float(o.get("power_fraction", 0)) for o in outs if isinstance(o, dict)]
            if len(powers) >= 2:
                powers_sorted = sorted(powers, reverse=True)
                main = max(1e-15, powers_sorted[0])
                cross = max(1e-15, powers_sorted[1])
                import math
                return abs(10.0 * math.log10(cross / main))
    return None


def compute_phase_error_sensitivity(simulation_results: dict) -> float | None:
    """Estimate phase error sensitivity (rad/nm) from simulation results."""
    chain = simulation_results.get("chain_solver")
    if isinstance(chain, dict) and chain.get("applicable"):
        per = chain.get("per_component")
        if isinstance(per, list):
            total_phase_sens = 0.0
            count = 0
            for comp in per:
                if isinstance(comp, dict):
                    ps = comp.get("phase_sensitivity_rad_per_nm")
                    if ps is not None:
                        total_phase_sens += abs(float(ps))
                        count += 1
            if count > 0:
                return total_phase_sens
    return None


def compute_group_delay_variation_ps(simulation_results: dict) -> float | None:
    """Estimate group delay variation (ps) from simulation results."""
    chain = simulation_results.get("chain_solver")
    if isinstance(chain, dict) and chain.get("applicable"):
        per = chain.get("per_component")
        if isinstance(per, list):
            total_gdv = 0.0
            count = 0
            for comp in per:
                if isinstance(comp, dict):
                    gdv = comp.get("group_delay_ps")
                    if gdv is not None:
                        total_gdv += float(gdv)
                        count += 1
            if count > 0:
                return total_gdv
    return None


def estimate_process_yield_pct(
    simulation_results: dict,
    netlist: dict,
    *,
    loss_variation_pct: float = 10.0,
    n_trials: int = 200,
    max_loss_threshold_db: float = 20.0,
) -> float | None:
    """Estimate process yield via Monte Carlo variation of component losses.

    For each trial, varies each component's loss by +-loss_variation_pct%
    (uniform distribution) and checks if total IL stays below threshold.
    Returns the fraction of trials that pass as a percentage.
    """
    chain = simulation_results.get("chain_solver")
    if not isinstance(chain, dict) or not chain.get("applicable"):
        return None
    per = chain.get("per_component")
    if not isinstance(per, list) or not per:
        return None

    import numpy as np
    rng = np.random.default_rng(42)
    losses = []
    for comp in per:
        if isinstance(comp, dict):
            losses.append(max(0.0, float(comp.get("loss_db", 0.0))))
    if not losses:
        return None

    losses_arr = np.array(losses)
    pass_count = 0
    var_frac = loss_variation_pct / 100.0

    for _ in range(n_trials):
        scale = rng.uniform(1.0 - var_frac, 1.0 + var_frac, len(losses_arr))
        trial_total = float(np.sum(losses_arr * scale))
        if trial_total < max_loss_threshold_db:
            pass_count += 1

    return 100.0 * pass_count / n_trials


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

    bw_3db = compute_bandwidth_3db_nm(simulation_results)
    crosstalk = compute_crosstalk_isolation_db(simulation_results)
    phase_sens = compute_phase_error_sensitivity(simulation_results)
    gdv = compute_group_delay_variation_ps(simulation_results)
    yield_pct = estimate_process_yield_pct(simulation_results, netlist)

    return ChipVerifyMetrics(
        total_insertion_loss_db=total_il,
        bandwidth_3db_nm=bw_3db,
        crosstalk_isolation_db=crosstalk,
        component_count=component_count,
        edge_count=edge_count,
        phase_error_sensitivity_rad_per_nm=phase_sens,
        group_delay_variation_ps=gdv,
        process_yield_estimate_pct=yield_pct,
    )
