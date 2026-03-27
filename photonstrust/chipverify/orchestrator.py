from __future__ import annotations

import uuid
from datetime import datetime, timezone

from photonstrust.chipverify.gates import default_gates, evaluate_gates, overall_status
from photonstrust.chipverify.metrics import compute_pic_metrics
from photonstrust.chipverify.types import ChipVerifyReport
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.spec import stable_graph_hash
from photonstrust.pic.simulate import simulate_pic_netlist
from photonstrust.pic.drc import run_graph_drc
from photonstrust.pic.lvs_lite import run_lvs_lite


def _normalize_graph(graph: dict) -> dict:
    """Ensure nodes and edges live at the top level of the graph dict.

    The graph compiler expects ``graph["nodes"]`` and ``graph["edges"]`` at the
    top level. Callers may pass them nested inside ``graph["circuit"]``, so we
    hoist them up when necessary.
    """
    out = dict(graph)
    circuit = out.get("circuit")
    if isinstance(circuit, dict):
        if not isinstance(out.get("nodes"), list) and isinstance(circuit.get("nodes"), list):
            out["nodes"] = circuit["nodes"]
        if not isinstance(out.get("edges"), list) and isinstance(circuit.get("edges"), list):
            out["edges"] = circuit["edges"]
    return out


def run_chipverify(
    *,
    graph: dict,
    gates: list[dict] | None = None,
    wavelength_nm: float | None = None,
) -> ChipVerifyReport:
    """Run the full ChipVerify alpha pipeline.

    Steps:
    1. Compile the graph using the existing compiler.
    2. Run PIC simulation on the compiled netlist.
    3. Run DRC checks.
    4. Run LVS-lite checks.
    5. Compute performance metrics.
    6. Evaluate quality gates.
    7. Build and return the report.
    """
    # Validate profile
    profile = str(graph.get("profile", "")).strip().lower()
    if profile != "pic_circuit":
        raise ValueError(
            f"ChipVerify requires profile='pic_circuit', got {profile!r}"
        )

    warnings: list[str] = []

    # Normalize the graph so nodes/edges are at top level
    normalized_graph = _normalize_graph(graph)

    # Step 1: Compile graph
    compiled = compile_graph(normalized_graph)
    netlist = compiled.compiled
    warnings.extend(compiled.warnings)

    netlist_hash = stable_graph_hash(normalized_graph)

    # Step 2: Run PIC simulation
    simulation_results: dict = {}
    try:
        simulation_results = simulate_pic_netlist(
            netlist, wavelength_nm=wavelength_nm
        )
    except Exception as exc:
        warnings.append(f"Simulation failed: {exc}")
        simulation_results = {"error": str(exc)}

    # Step 3: Run DRC
    drc_results: dict = {}
    try:
        drc_results = run_graph_drc(netlist, pdk={})
    except Exception as exc:
        warnings.append(f"DRC failed: {exc}")
        drc_results = {"error": str(exc)}

    # Step 4: Run LVS-lite
    lvs_results: dict | None = None
    try:
        lvs_results = run_lvs_lite(normalized_graph, netlist)
    except Exception as exc:
        warnings.append(f"LVS-lite failed: {exc}")
        lvs_results = {"error": str(exc)}

    # Step 5: Compute metrics
    metrics = compute_pic_metrics(
        simulation_results=simulation_results,
        netlist=netlist,
        wavelength_nm=wavelength_nm,
    )

    # Step 6: Evaluate gates
    gate_configs = gates if gates is not None else default_gates()
    evaluated_gates = evaluate_gates(metrics, gate_configs)
    status = overall_status(evaluated_gates)

    # Step 7: Build report
    report = ChipVerifyReport(
        report_id=str(uuid.uuid4()),
        netlist_hash=netlist_hash,
        timestamp=datetime.now(timezone.utc).isoformat(),
        simulation_results=simulation_results,
        drc_results=drc_results,
        lvs_results=lvs_results,
        performance_metrics=metrics,
        gates=evaluated_gates,
        overall_status=status,
        warnings=warnings,
    )

    return report
