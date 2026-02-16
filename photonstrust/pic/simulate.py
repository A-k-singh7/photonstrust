"""PIC netlist simulation (v1).

Two solvers are provided:
- A fast chain solver for simple 2-port component chains (loss budgets).
- A general DAG solver for feed-forward circuits (supports interference via
  multiport mixing nodes like couplers). This is an explicitly unidirectional
  model (no back-reflections).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from photonstrust.components.pic.library import (
    component_all_ports,
    component_forward_matrix,
    component_ports,
    component_scattering_matrix,
)
from photonstrust.utils import clamp


@dataclass(frozen=True)
class PICPortRef:
    node: str
    port: str


def simulate_pic_netlist(
    netlist: dict,
    *,
    wavelength_nm: float | None = None,
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
) -> dict:
    """Simulate a compiled PIC netlist dict."""

    if str(netlist.get("profile", "")).strip().lower() != "pic_circuit":
        raise ValueError("simulate_pic_netlist expects a netlist with profile=pic_circuit")

    circuit = netlist.get("circuit", {}) or {}
    if wavelength_nm is None:
        wavelength_nm = circuit.get("wavelength_nm")
    wavelength_nm = float(wavelength_nm) if wavelength_nm is not None else None

    chain = simulate_chain(netlist, wavelength_nm=wavelength_nm)

    circuit_solver = str((circuit.get("solver") or "")).strip().lower()
    if not circuit_solver:
        circuit_solver = "dag"

    if circuit_solver in {"scattering", "scattering_network", "bidirectional_scattering"}:
        dag = {"applicable": False, "reason": "skipped (circuit.solver='scattering')"}
        scattering = simulate_scattering(netlist, wavelength_nm=wavelength_nm, inputs=inputs, outputs=outputs)
    else:
        dag = simulate_dag(netlist, wavelength_nm=wavelength_nm, inputs=inputs, outputs=outputs)
        scattering = {"applicable": False, "reason": "circuit.solver is not 'scattering'"}

    return {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": netlist.get("graph_id"),
        "circuit_id": circuit.get("id"),
        "wavelength_nm": wavelength_nm,
        "chain_solver": chain,
        "dag_solver": dag,
        "scattering_solver": scattering,
        "assumptions": {
            "model": "bidirectional_scattering" if scattering.get("applicable") else "unidirectional_dag",
            "notes": [
                "The default v1 PIC simulator assumes forward-only propagation (no back-reflections).",
                "When circuit.solver='scattering', a bidirectional scattering-network linear solve is used.",
                "DAG cycles are rejected by the forward solver; scattering mode can support feedback loops.",
                "Component models are minimal and intended for early-stage loss/phase budgeting; validate against EM/SPICE for signoff.",
            ],
        },
    }


def simulate_pic_netlist_sweep(
    netlist: dict,
    *,
    wavelengths_nm: list[float],
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
) -> dict:
    """Simulate the same netlist across multiple wavelengths (nm).

    This is intended for compact-model inspection (e.g., ring/filter response)
    and Touchstone-imported components.
    """

    if not wavelengths_nm:
        raise ValueError("wavelengths_nm must be non-empty")

    points = []
    for w in wavelengths_nm:
        r = simulate_pic_netlist(netlist, wavelength_nm=float(w), inputs=inputs, outputs=outputs)
        points.append(
            {
                "wavelength_nm": float(w),
                "chain_solver": r["chain_solver"],
                "dag_solver": r["dag_solver"],
                "scattering_solver": r.get("scattering_solver"),
            }
        )

    circuit = netlist.get("circuit", {}) or {}
    return {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": netlist.get("graph_id"),
        "circuit_id": circuit.get("id"),
        "sweep": {
            "wavelength_nm": [float(w) for w in wavelengths_nm],
            "points": points,
        },
        "assumptions": {
            "model": "unidirectional_dag",
            "notes": [
                "This sweep reuses the v1 forward-only PIC solver (no back-reflections).",
                "If circuit.solver='scattering', each point also includes a scattering-network solve.",
            ],
        },
    }


def simulate_scattering(
    netlist: dict,
    *,
    wavelength_nm: float | None,
    inputs: list[dict] | None,
    outputs: list[dict] | None,
) -> dict:
    """Solve a bidirectional PIC netlist using a scattering-network linear system.

    This mode supports back-reflections and graph cycles, assuming edges represent
    ideal, lossless, zero-delay connections between ports.
    """

    nodes = netlist.get("nodes", [])
    edges = [_normalize_edge(e) for e in (netlist.get("edges", []) or [])]
    node_by_id = {str(n.get("id")): n for n in nodes}

    # Build global port indexing.
    port_list: list[tuple[str, str]] = []
    node_ports: dict[str, tuple[str, ...]] = {}
    for node_id in sorted(node_by_id.keys(), key=lambda x: x.lower()):
        node = node_by_id[node_id]
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}
        ports = component_all_ports(kind, params=params)
        node_ports[node_id] = tuple([str(p) for p in ports])
        for p in ports:
            port_list.append((node_id, str(p)))
    if not port_list:
        return {"applicable": False, "reason": "no ports"}

    idx_of = {ref: i for i, ref in enumerate(port_list)}
    n = len(port_list)

    # Assemble global block-diagonal scattering matrix S.
    S = np.zeros((n, n), dtype=np.complex128)
    for node_id in sorted(node_by_id.keys(), key=lambda x: x.lower()):
        node = node_by_id[node_id]
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}

        ports = list(node_ports.get(node_id) or component_all_ports(kind, params=params))
        s_local = component_scattering_matrix(kind, params, wavelength_nm=wavelength_nm)
        if s_local.shape != (len(ports), len(ports)):
            raise ValueError(f"{node_id} ({kind}) scattering matrix has wrong shape: {s_local.shape}")

        for i_local, p_i in enumerate(ports):
            gi = idx_of[(node_id, str(p_i))]
            for j_local, p_j in enumerate(ports):
                gj = idx_of[(node_id, str(p_j))]
                S[gi, gj] = complex(s_local[i_local, j_local])

    # Build ideal connection matrix C such that a = C @ b + a_ext
    # Each port can connect to at most one other port.
    partner: dict[int, int] = {}
    edge_g: dict[tuple[int, int], complex] = {}
    for e in edges:
        a_ref = (str(e["from"]), str(e["from_port"]))
        b_ref = (str(e["to"]), str(e["to_port"]))
        if a_ref not in idx_of:
            raise ValueError(f"edge refers to missing port: {a_ref[0]}.{a_ref[1]}")
        if b_ref not in idx_of:
            raise ValueError(f"edge refers to missing port: {b_ref[0]}.{b_ref[1]}")
        ia = idx_of[a_ref]
        ib = idx_of[b_ref]
        if ia in partner:
            raise ValueError(f"port connected multiple times: {a_ref[0]}.{a_ref[1]}")
        if ib in partner:
            raise ValueError(f"port connected multiple times: {b_ref[0]}.{b_ref[1]}")
        if ia == ib:
            raise ValueError(f"self-connection on a single port is not supported: {a_ref[0]}.{a_ref[1]}")

        g = _edge_transfer(e.get("params") or {}, wavelength_nm=wavelength_nm)
        partner[ia] = ib
        partner[ib] = ia
        edge_g[(ia, ib)] = complex(g)
        edge_g[(ib, ia)] = complex(g)

    C = np.zeros((n, n), dtype=np.complex128)
    for i, j in partner.items():
        C[i, j] = edge_g.get((i, j), 1.0 + 0.0j)

    # External IO: reuse the v1 input/output resolution based on directed edges.
    incoming_by_port: dict[tuple[str, str], list[dict]] = {}
    outgoing_by_port: dict[tuple[str, str], list[dict]] = {}
    for e in edges:
        incoming_by_port.setdefault((e["to"], e["to_port"]), []).append(e)
        outgoing_by_port.setdefault((e["from"], e["from_port"]), []).append(e)

    io_inputs = inputs or (netlist.get("circuit", {}) or {}).get("inputs")
    io_outputs = outputs or (netlist.get("circuit", {}) or {}).get("outputs")
    external_inputs = _resolve_external_inputs(node_by_id, incoming_by_port, io_inputs)
    external_outputs = _resolve_external_outputs(node_by_id, outgoing_by_port, io_outputs)

    a_ext = np.zeros((n,), dtype=np.complex128)
    for ref, amp in external_inputs.items():
        key = (ref.node, ref.port)
        if key not in idx_of:
            raise ValueError(f"external input refers to missing port: {ref.node}.{ref.port}")
        a_ext[idx_of[key]] += complex(float(amp))

    # Solve: (I - S C) b = S a_ext
    A = np.eye(n, dtype=np.complex128) - (S @ C)
    rhs = S @ a_ext
    try:
        b = np.linalg.solve(A, rhs)
    except np.linalg.LinAlgError as exc:
        return {"applicable": False, "reason": f"scattering solve failed: {exc}"}

    # Report requested outputs using outgoing wave b at those ports.
    out_rows = []
    for ref in external_outputs:
        key = (ref.node, ref.port)
        if key not in idx_of:
            continue
        amp = complex(b[idx_of[key]])
        power = float(abs(amp) ** 2)
        out_rows.append(
            {
                "node": ref.node,
                "port": ref.port,
                "amplitude": {"re": float(amp.real), "im": float(amp.imag)},
                "power": power,
                "loss_db": _loss_db_from_eta(power),
            }
        )
    out_rows.sort(key=lambda r: (str(r["node"]).lower(), str(r["port"]).lower()))

    # Diagnostics
    cond = float(np.linalg.cond(A))

    return {
        "applicable": True,
        "ports": [{"node": nid, "port": p} for (nid, p) in port_list],
        "external_inputs": [
            {"node": ref.node, "port": ref.port, "amplitude": float(amp)}
            for ref, amp in sorted(external_inputs.items(), key=lambda kv: (kv[0].node.lower(), kv[0].port.lower()))
        ],
        "external_outputs": out_rows,
        "diagnostics": {"condition_number": cond},
    }


def simulate_chain(netlist: dict, *, wavelength_nm: float | None) -> dict:
    nodes = netlist.get("nodes", [])
    edges = netlist.get("edges", [])

    ok, reason, chain_order = _is_simple_chain(netlist)
    if not ok:
        return {"applicable": False, "reason": reason}

    edge_by_from = {e["from"]: e for e in edges}

    eta_total = 1.0
    per_component = []
    for idx, node_id in enumerate(chain_order):
        node = _node_by_id(nodes, node_id)
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}
        try:
            eta = float(_power_transmission_2port(kind, params, wavelength_nm=wavelength_nm))
        except Exception as exc:
            return {"applicable": False, "reason": f"unsupported component in chain: {node_id} ({kind}): {exc}"}
        eta_total *= clamp(eta, 0.0, 1.0)
        per_component.append(
            {
                "node_id": node_id,
                "kind": kind,
                "eta": eta,
                "loss_db": _loss_db_from_eta(eta),
            }
        )

        # Apply optional edge loss for the segment leaving this node.
        if idx < len(chain_order) - 1:
            e = edge_by_from.get(node_id)
            if e is not None:
                try:
                    g = _edge_transfer(e.get("params") or {}, wavelength_nm=wavelength_nm)
                    eta_edge = float(abs(complex(g)) ** 2)
                except Exception as exc:
                    return {"applicable": False, "reason": f"unsupported edge model in chain from {node_id}: {exc}"}
                eta_total *= clamp(eta_edge, 0.0, 1.0)

    loss_db_total = _loss_db_from_eta(eta_total)
    return {
        "applicable": True,
        "node_order": chain_order,
        "eta_total": eta_total,
        "total_loss_db": loss_db_total,
        "per_component": per_component,
    }


def simulate_dag(
    netlist: dict,
    *,
    wavelength_nm: float | None,
    inputs: list[dict] | None,
    outputs: list[dict] | None,
) -> dict:
    nodes = netlist.get("nodes", [])
    edges = netlist.get("edges", [])
    order = (netlist.get("topology", {}) or {}).get("topological_order")
    if not order:
        order = _topological_order(nodes, edges)
    order = list(order)

    node_by_id = {str(n.get("id")): n for n in nodes}
    edge_norm = [_normalize_edge(e) for e in edges]

    incoming_by_port: dict[tuple[str, str], list[dict]] = {}
    outgoing_by_port: dict[tuple[str, str], list[dict]] = {}
    for e in edge_norm:
        incoming_by_port.setdefault((e["to"], e["to_port"]), []).append(e)
        outgoing_by_port.setdefault((e["from"], e["from_port"]), []).append(e)

    warnings = []
    for key, es in incoming_by_port.items():
        if len(es) > 1:
            warnings.append(f"Multiple incoming edges to {key[0]}.{key[1]}: summing amplitudes (v1 behavior).")
    for key, es in outgoing_by_port.items():
        if len(es) > 1:
            warnings.append(f"Multiple outgoing edges from {key[0]}.{key[1]}: duplicating amplitude (v1 behavior).")

    # External IO detection
    io_inputs = inputs or (netlist.get("circuit", {}) or {}).get("inputs")
    io_outputs = outputs or (netlist.get("circuit", {}) or {}).get("outputs")
    external_inputs = _resolve_external_inputs(node_by_id, incoming_by_port, io_inputs)
    external_outputs = _resolve_external_outputs(node_by_id, outgoing_by_port, io_outputs)

    # Solve forward
    port_amp: dict[tuple[str, str], complex] = {}
    for ref, amp in external_inputs.items():
        port_amp[(ref.node, ref.port)] = complex(amp)

    node_outputs: dict[tuple[str, str], complex] = {}

    for node_id in order:
        node = node_by_id.get(node_id)
        if not node:
            continue
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}

        ports = component_ports(kind, params=params)
        in_ports = list(ports.in_ports)
        out_ports = list(ports.out_ports)
        mat = component_forward_matrix(kind, params, wavelength_nm=wavelength_nm)
        if mat.shape != (len(out_ports), len(in_ports)):
            raise ValueError(f"{node_id} ({kind}) forward matrix has wrong shape: {mat.shape}")

        a = np.zeros((len(in_ports),), dtype=np.complex128)
        for idx, port in enumerate(in_ports):
            inc_edges = incoming_by_port.get((node_id, port), [])
            if inc_edges:
                total = 0.0 + 0.0j
                for e in inc_edges:
                    g = _edge_transfer(e.get("params") or {}, wavelength_nm=wavelength_nm)
                    total += complex(g) * node_outputs.get((e["from"], e["from_port"]), 0.0 + 0.0j)
                a[idx] = total
            else:
                a[idx] = port_amp.get((node_id, port), 0.0 + 0.0j)

        b = mat @ a
        for idx, port in enumerate(out_ports):
            node_outputs[(node_id, port)] = complex(b[idx])

    out_rows = []
    for ref in external_outputs:
        amp = node_outputs.get((ref.node, ref.port), 0.0 + 0.0j)
        power = float(abs(amp) ** 2)
        out_rows.append(
            {
                "node": ref.node,
                "port": ref.port,
                "amplitude": {"re": float(amp.real), "im": float(amp.imag)},
                "power": power,
                "loss_db": _loss_db_from_eta(power),
            }
        )

    out_rows.sort(key=lambda r: (str(r["node"]).lower(), str(r["port"]).lower()))
    return {
        "external_inputs": [
            {"node": ref.node, "port": ref.port, "amplitude": float(amp)}
            for ref, amp in sorted(external_inputs.items(), key=lambda kv: (kv[0].node.lower(), kv[0].port.lower()))
        ],
        "external_outputs": out_rows,
        "warnings": warnings,
    }


def _power_transmission_2port(kind: str, params: dict, *, wavelength_nm: float | None) -> float:
    mat = component_forward_matrix(kind, params, wavelength_nm=wavelength_nm)
    if mat.shape != (1, 1):
        raise ValueError("not a 2-port component")
    t = complex(mat[0, 0])
    return float(abs(t) ** 2)


def _loss_db_from_eta(eta: float) -> float:
    eta = float(eta)
    if not math.isfinite(eta) or eta <= 0.0:
        return float("inf")
    return float(-10.0 * math.log10(eta))


def _node_by_id(nodes: list[dict], node_id: str) -> dict:
    for node in nodes:
        if str(node.get("id")) == node_id:
            return node
    raise KeyError(f"node not found: {node_id}")


def _normalize_edge(edge: dict) -> dict:
    src = str(edge.get("from", "")).strip()
    dst = str(edge.get("to", "")).strip()
    from_port = str(edge.get("from_port", "out")).strip() or "out"
    to_port = str(edge.get("to_port", "in")).strip() or "in"
    params = edge.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("edge.params must be an object when present")
    return {
        "id": edge.get("id"),
        "from": src,
        "to": dst,
        "from_port": from_port,
        "to_port": to_port,
        "kind": edge.get("kind", "optical"),
        "label": edge.get("label"),
        "params": params,
    }


def _edge_transfer(edge_params: dict, *, wavelength_nm: float | None) -> complex:
    """Return complex amplitude transfer for an edge.

    Edges are modeled as reciprocal propagation elements between two ports.
    This transfer is applied in both directions in the scattering solver.
    """

    if not edge_params:
        return 1.0 + 0.0j

    # Loss (power) in dB.
    loss_db = 0.0
    il_db = edge_params.get("insertion_loss_db")
    if il_db is None:
        il_db = edge_params.get("loss_db")
    if il_db is not None:
        loss_db += max(0.0, float(il_db))

    length_um = edge_params.get("length_um")
    loss_db_per_cm = edge_params.get("loss_db_per_cm")
    if loss_db_per_cm is not None and length_um is not None:
        loss_db += max(0.0, float(loss_db_per_cm)) * (max(0.0, float(length_um)) / 1e4)

    eta = 10 ** (-loss_db / 10.0)
    amp = math.sqrt(max(0.0, float(eta)))

    # Phase (rad).
    if edge_params.get("phase_rad") is not None:
        phi = float(edge_params.get("phase_rad") or 0.0)
    else:
        phi = 0.0
        if edge_params.get("delay_ps") is not None:
            if wavelength_nm is None:
                raise ValueError("edge delay_ps requires wavelength_nm")
            delay_ps = float(edge_params.get("delay_ps") or 0.0)
            delay_s = delay_ps * 1e-12
            lam_m = float(wavelength_nm) * 1e-9
            if lam_m <= 0.0:
                raise ValueError("wavelength_nm must be > 0 for edge delay")
            c_m_s = 299_792_458.0
            freq_hz = c_m_s / lam_m
            phi = float(2.0 * math.pi * freq_hz * delay_s)
        elif edge_params.get("n_eff") is not None and length_um is not None:
            if wavelength_nm is None:
                raise ValueError("edge n_eff/length_um requires wavelength_nm")
            n_eff = float(edge_params.get("n_eff") or 0.0)
            if not math.isfinite(n_eff) or n_eff <= 0.0:
                raise ValueError("edge n_eff must be finite and > 0")
            length_m = max(0.0, float(length_um)) * 1e-6
            lam_m = float(wavelength_nm) * 1e-9
            if lam_m <= 0.0:
                raise ValueError("wavelength_nm must be > 0 for edge phase")
            phi = float(2.0 * math.pi * n_eff * length_m / lam_m)

    return amp * complex(math.cos(phi), math.sin(phi))


def _is_simple_chain(netlist: dict) -> tuple[bool, str, list[str]]:
    nodes = netlist.get("nodes", [])
    edges = [_normalize_edge(e) for e in (netlist.get("edges", []) or [])]
    if not nodes:
        return False, "no nodes", []
    if len(edges) != max(0, len(nodes) - 1):
        return False, "edge count not consistent with chain", []

    node_ids = [str(n.get("id")) for n in nodes]
    indeg = {nid: 0 for nid in node_ids}
    outdeg = {nid: 0 for nid in node_ids}

    for e in edges:
        indeg[e["to"]] = indeg.get(e["to"], 0) + 1
        outdeg[e["from"]] = outdeg.get(e["from"], 0) + 1

    starts = [nid for nid in node_ids if indeg.get(nid, 0) == 0]
    ends = [nid for nid in node_ids if outdeg.get(nid, 0) == 0]
    if len(starts) != 1 or len(ends) != 1:
        return False, "chain requires exactly one start and one end", []

    # Ensure all intermediate nodes have in=1 out=1
    for nid in node_ids:
        if nid in starts:
            if outdeg.get(nid, 0) != 1:
                return False, f"start node {nid} must have outdegree 1", []
        elif nid in ends:
            if indeg.get(nid, 0) != 1:
                return False, f"end node {nid} must have indegree 1", []
        else:
            if indeg.get(nid, 0) != 1 or outdeg.get(nid, 0) != 1:
                return False, f"node {nid} is not chain-like (indeg/outdeg)", []

    # Ensure all edges use default 2-port port mapping (out->in).
    for e in edges:
        if e["from_port"] != "out" or e["to_port"] != "in":
            return False, "chain solver requires out->in 2-port edges", []

    # Walk the chain
    next_by_node = {e["from"]: e["to"] for e in edges}
    order = []
    cur = starts[0]
    seen = set()
    while True:
        if cur in seen:
            return False, "cycle detected during chain walk", []
        seen.add(cur)
        order.append(cur)
        if cur == ends[0]:
            break
        cur = next_by_node.get(cur)
        if not cur:
            return False, "broken chain", []

    if len(order) != len(node_ids):
        return False, "chain walk did not visit all nodes", []
    return True, "ok", order


def _topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    node_ids = [str(n.get("id")) for n in nodes]
    adjacency = {nid: set() for nid in node_ids}
    indegree = {nid: 0 for nid in node_ids}

    for e in edges:
        src = str(e.get("from"))
        dst = str(e.get("to"))
        if src in adjacency and dst in indegree and dst not in adjacency[src]:
            adjacency[src].add(dst)
            indegree[dst] += 1

    ready = sorted([nid for nid in node_ids if indegree[nid] == 0], key=lambda x: x.lower())
    out = []
    while ready:
        nid = ready.pop(0)
        out.append(nid)
        for nxt in sorted(adjacency[nid], key=lambda x: x.lower()):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort(key=lambda x: x.lower())
    if len(out) != len(node_ids):
        raise ValueError("PIC netlist contains a cycle (DAG solver requires acyclic graph).")
    return out


def _resolve_external_inputs(
    node_by_id: dict[str, dict],
    incoming_by_port: dict[tuple[str, str], list[dict]],
    inputs: list[dict] | None,
) -> dict[PICPortRef, float]:
    if inputs:
        out = {}
        for item in inputs:
            node = str(item.get("node"))
            port = str(item.get("port", "in"))
            amp = float(item.get("amplitude", 1.0))
            out[PICPortRef(node=node, port=port)] = amp
        return out

    # Auto-detect: all input ports with no incoming edges.
    candidates: list[PICPortRef] = []
    for node_id, node in node_by_id.items():
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}
        ports = component_ports(kind, params=params)
        for port in ports.in_ports:
            if (node_id, port) not in incoming_by_port:
                candidates.append(PICPortRef(node=node_id, port=port))

    if len(candidates) == 1:
        return {candidates[0]: 1.0}
    if not candidates:
        raise ValueError("No external inputs detected. Provide circuit.inputs or explicit inputs.")
    raise ValueError(f"Multiple external input candidates detected: {candidates}. Provide circuit.inputs or explicit inputs.")


def _resolve_external_outputs(
    node_by_id: dict[str, dict],
    outgoing_by_port: dict[tuple[str, str], list[dict]],
    outputs: list[dict] | None,
) -> list[PICPortRef]:
    if outputs:
        out = []
        for item in outputs:
            node = str(item.get("node"))
            port = str(item.get("port", "out"))
            out.append(PICPortRef(node=node, port=port))
        return out

    candidates: list[PICPortRef] = []
    for node_id, node in node_by_id.items():
        kind = str(node.get("kind", "")).strip().lower()
        params = node.get("params", {}) or {}
        ports = component_ports(kind, params=params)
        for port in ports.out_ports:
            if (node_id, port) not in outgoing_by_port:
                candidates.append(PICPortRef(node=node_id, port=port))

    if not candidates:
        raise ValueError("No external outputs detected. Provide circuit.outputs or explicit outputs.")
    return sorted(candidates, key=lambda r: (r.node.lower(), r.port.lower()))
