"""LVS-lite mismatch summaries for PIC layouts (v0.1).

This is not full foundry LVS. The intent is to provide a trustworthy and
deterministic "expected connectivity vs observed connectivity" report that
can be used in:
- CI gates,
- evidence packs,
- and review diffs.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Any

from photonstrust.components.pic.library import component_ports
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.schema import validate_graph
from photonstrust.layout.pic.extract_connectivity import extract_connectivity_from_routes
from photonstrust.pic.layout.verification import verify_layout_signoff_bundle
from photonstrust.utils import hash_dict


def run_pic_lvs_lite(
    request: dict[str, Any],
    *,
    require_schema: bool = False,
) -> dict[str, Any]:
    """Run LVS-lite for a PIC graph vs layout sidecars.

    Request (v0.1):
      - graph: PhotonTrust graph dict (profile=pic_circuit)
      - ports: ports.json dict (from build_pic_layout_artifacts)
      - routes: routes.json dict (from build_pic_layout_artifacts)
      - settings: {coord_tol_um?: number}
    """

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    graph = request.get("graph")
    if not isinstance(graph, dict):
        raise TypeError("request.graph must be an object")
    validate_graph(graph, require_jsonschema=require_schema)
    if str(graph.get("profile", "")).strip().lower() != "pic_circuit":
        raise ValueError("run_pic_lvs_lite requires graph.profile=pic_circuit")

    ports = request.get("ports")
    routes = request.get("routes")
    if not isinstance(ports, dict):
        raise TypeError("request.ports must be an object (ports.json contents)")
    if not isinstance(routes, dict):
        raise TypeError("request.routes must be an object (routes.json contents)")

    settings_raw = request["settings"] if "settings" in request else None
    settings: dict[str, Any] = settings_raw if isinstance(settings_raw, dict) else {}
    tol_um = float(settings.get("coord_tol_um", 1e-6) or 1e-6)
    if tol_um <= 0.0:
        raise ValueError("settings.coord_tol_um must be > 0")

    signoff_bundle_request = request.get("signoff_bundle")
    if signoff_bundle_request is not None and not isinstance(signoff_bundle_request, dict):
        raise TypeError("request.signoff_bundle must be an object")

    compiled = compile_graph(graph, require_schema=require_schema)
    netlist = compiled.compiled
    graph_hash = hash_dict(graph)

    # Expected directed edges from netlist.
    expected_edges = []
    for e in (netlist.get("edges") or []):
        if not isinstance(e, dict):
            continue
        expected_edges.append(
            {
                "from": str(e.get("from", "")).strip(),
                "from_port": str(e.get("from_port", "out")),
                "to": str(e.get("to", "")).strip(),
                "to_port": str(e.get("to_port", "in")),
            }
        )

    # Observed undirected edges from sidecars.
    obs = extract_connectivity_from_routes(routes, ports, tol_um=tol_um)
    observed_edges = obs.edges

    node_kind: dict[str, str] = {}
    node_params: dict[str, dict[str, Any]] = {}
    for n in (netlist.get("nodes") or []):
        if not isinstance(n, dict):
            continue
        node_id = str(n.get("id", "")).strip()
        kind = str(n.get("kind", "")).strip().lower()
        if node_id:
            node_kind[node_id] = kind
            params = n.get("params", {})
            if params is None:
                params = {}
            if not isinstance(params, dict):
                params = {}
            node_params[node_id] = params

    def role(node: str, port: str) -> str | None:
        k = node_kind.get(node)
        if not k:
            return None
        p = component_ports(k, params=node_params.get(node) or {})
        if port in p.in_ports:
            return "in"
        if port in p.out_ports:
            return "out"
        return None

    def undirected_key(a_node: str, a_port: str, b_node: str, b_port: str) -> tuple[tuple[str, str], tuple[str, str]]:
        a = (a_node, a_port)
        b = (b_node, b_port)
        return (a, b) if (a[0].lower(), a[1].lower()) <= (b[0].lower(), b[1].lower()) else (b, a)

    exp_undirected = {
        undirected_key(e["from"], e["from_port"], e["to"], e["to_port"]): e for e in expected_edges if e["from"] and e["to"]
    }
    obs_undirected = {
        undirected_key(str(e["a"]["node"]), str(e["a"]["port"]), str(e["b"]["node"]), str(e["b"]["port"])): e
        for e in observed_edges
        if isinstance(e, dict)
    }

    missing = []
    for k, e in exp_undirected.items():
        if k not in obs_undirected:
            missing.append({"from": e["from"], "from_port": e["from_port"], "to": e["to"], "to_port": e["to_port"]})

    extra = []
    for k, e in obs_undirected.items():
        if k not in exp_undirected:
            a = e.get("a") or {}
            b = e.get("b") or {}
            extra.append({"a": a, "b": b, "route_id": e.get("route_id")})

    # Port role mismatches (where endpoints match but cannot be oriented to match expected direction).
    role_mismatches = []
    for k, exp in exp_undirected.items():
        obs_e = obs_undirected.get(k)
        if not obs_e:
            continue
        a = obs_e.get("a") or {}
        b = obs_e.get("b") or {}
        an = str(a.get("node", ""))
        ap = str(a.get("port", ""))
        bn = str(b.get("node", ""))
        bp = str(b.get("port", ""))
        r_an_ap = role(an, ap)
        r_bn_bp = role(bn, bp)
        if r_an_ap is None or r_bn_bp is None:
            # Unknown ports are treated as mismatches.
            role_mismatches.append(
                {
                    "expected": exp,
                    "observed": {"a": a, "b": b, "route_id": obs_e.get("route_id")},
                    "reason": "unknown_port",
                }
            )
            continue

        oriented = None
        if r_an_ap == "out" and r_bn_bp == "in":
            oriented = {"from": an, "from_port": ap, "to": bn, "to_port": bp}
        elif r_an_ap == "in" and r_bn_bp == "out":
            oriented = {"from": bn, "from_port": bp, "to": an, "to_port": ap}

        if oriented is None:
            role_mismatches.append(
                {
                    "expected": exp,
                    "observed": {"a": a, "b": b, "route_id": obs_e.get("route_id")},
                    "reason": "ambiguous_or_invalid_port_roles",
                }
            )
            continue

        if (
            oriented["from"] != exp["from"]
            or oriented["from_port"] != exp["from_port"]
            or oriented["to"] != exp["to"]
            or oriented["to_port"] != exp["to_port"]
        ):
            role_mismatches.append(
                {
                    "expected": exp,
                    "observed": {"a": a, "b": b, "route_id": obs_e.get("route_id")},
                    "reason": "direction_mismatch",
                    "oriented": oriented,
                }
            )

    # Unconnected ports (endpoints in expected edges not seen in observed edges).
    exp_ports = set()
    for e in expected_edges:
        exp_ports.add((e["from"], e["from_port"]))
        exp_ports.add((e["to"], e["to_port"]))
    obs_ports = set()
    for e in observed_edges:
        a = e.get("a") or {}
        b = e.get("b") or {}
        obs_ports.add((str(a.get("node", "")), str(a.get("port", ""))))
        obs_ports.add((str(b.get("node", "")), str(b.get("port", ""))))

    unconnected = [{"node": n, "port": p} for (n, p) in sorted(exp_ports - obs_ports, key=lambda t: (t[0].lower(), t[1].lower()))]

    violations_annotated: list[dict[str, Any]] = []
    for m in missing:
        if not isinstance(m, dict):
            continue
        entity = (
            f"{str(m.get('from', ''))}:{str(m.get('from_port', ''))}->"
            f"{str(m.get('to', ''))}:{str(m.get('to_port', ''))}"
        )
        msg = f"Missing expected connectivity edge: {entity}"
        violations_annotated.append(
            {
                "id": f"lvs.missing_edge:{entity}",
                "source": "pic.lvs_lite",
                "code": "lvs.missing_edge",
                "severity": "error",
                "applicability": "blocking",
                "entity_ref": entity,
                "message": msg,
                "location": None,
            }
        )

    for e in extra:
        if not isinstance(e, dict):
            continue
        a = e.get("a") if isinstance(e.get("a"), dict) else {}
        b = e.get("b") if isinstance(e.get("b"), dict) else {}
        entity = (
            f"{str(a.get('node', ''))}:{str(a.get('port', ''))}<->"
            f"{str(b.get('node', ''))}:{str(b.get('port', ''))}"
        )
        rid = str(e.get("route_id", "")).strip()
        msg = f"Extra observed connectivity edge: {entity}"
        violations_annotated.append(
            {
                "id": f"lvs.extra_edge:{entity}:{rid}",
                "source": "pic.lvs_lite",
                "code": "lvs.extra_edge",
                "severity": "error",
                "applicability": "blocking",
                "entity_ref": entity,
                "message": msg,
                "location": {"route_id": rid} if rid else None,
            }
        )

    for i, rm in enumerate(role_mismatches):
        if not isinstance(rm, dict):
            continue
        exp = rm.get("expected") if isinstance(rm.get("expected"), dict) else {}
        observed = rm.get("observed") if isinstance(rm.get("observed"), dict) else {}
        obs_a = observed.get("a") if isinstance(observed.get("a"), dict) else {}
        obs_b = observed.get("b") if isinstance(observed.get("b"), dict) else {}
        expected_entity = (
            f"{str(exp.get('from', ''))}:{str(exp.get('from_port', ''))}->"
            f"{str(exp.get('to', ''))}:{str(exp.get('to_port', ''))}"
        )
        observed_entity = (
            f"{str(obs_a.get('node', ''))}:{str(obs_a.get('port', ''))}<->"
            f"{str(obs_b.get('node', ''))}:{str(obs_b.get('port', ''))}"
        )
        reason = str(rm.get("reason", "mismatch")).strip() or "mismatch"
        msg = f"Port role mismatch ({reason}): expected {expected_entity}, observed {observed_entity}"
        violations_annotated.append(
            {
                "id": f"lvs.port_role_mismatch:{i}:{expected_entity}",
                "source": "pic.lvs_lite",
                "code": "lvs.port_role_mismatch",
                "severity": "error",
                "applicability": "blocking",
                "entity_ref": expected_entity,
                "message": msg,
                "location": {"route_id": observed.get("route_id")} if isinstance(observed, dict) else None,
            }
        )

    for p in unconnected:
        if not isinstance(p, dict):
            continue
        entity = f"{str(p.get('node', ''))}:{str(p.get('port', ''))}"
        msg = f"Expected port is unconnected in observed layout: {entity}"
        violations_annotated.append(
            {
                "id": f"lvs.unconnected_port:{entity}",
                "source": "pic.lvs_lite",
                "code": "lvs.unconnected_port",
                "severity": "error",
                "applicability": "blocking",
                "entity_ref": entity,
                "message": msg,
                "location": None,
            }
        )

    for d in obs.dangling_routes:
        if not isinstance(d, dict):
            continue
        rid = str(d.get("route_id", "")).strip() or "route"
        msg = f"Observed route has dangling endpoint(s): {rid}"
        violations_annotated.append(
            {
                "id": f"lvs.dangling_route:{rid}",
                "source": "pic.lvs_lite",
                "code": "lvs.dangling_route",
                "severity": "warning",
                "applicability": "advisory",
                "entity_ref": f"route:{rid}",
                "message": msg,
                "location": {
                    "a_um": d.get("a_um"),
                    "b_um": d.get("b_um"),
                },
            }
        )

    base_pass = len(missing) == 0 and len(extra) == 0 and len(role_mismatches) == 0 and len(unconnected) == 0

    report = {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": graph.get("graph_id"),
        "provenance": {
            "graph_hash": graph_hash,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "settings": {"coord_tol_um": tol_um},
        "expected": {
            "edges": expected_edges,
            "edges_count": int(len(expected_edges)),
        },
        "observed": {
            "edges": observed_edges,
            "edges_count": int(len(observed_edges)),
            "dangling_routes": obs.dangling_routes,
            "warnings": obs.warnings,
        },
        "mismatches": {
            "missing_edges": missing,
            "extra_edges": extra,
            "port_role_mismatches": role_mismatches,
            "unconnected_ports": unconnected,
        },
        "violations_annotated": violations_annotated,
        "summary": {
            "pass": base_pass,
            "missing_edges": int(len(missing)),
            "extra_edges": int(len(extra)),
            "port_role_mismatches": int(len(role_mismatches)),
            "unconnected_ports": int(len(unconnected)),
            "violations": int(len(violations_annotated)),
            "blocking_violations": int(
                len([v for v in violations_annotated if str(v.get("applicability", "")).strip().lower() == "blocking"])
            ),
        },
    }

    if signoff_bundle_request is not None:
        signoff_bundle_result = verify_layout_signoff_bundle(**signoff_bundle_request)
        signoff_summary_raw = signoff_bundle_result.get("summary")
        signoff_summary: dict[str, Any] = signoff_summary_raw if isinstance(signoff_summary_raw, dict) else {}
        report["signoff_bundle"] = signoff_bundle_result
        report["summary"]["signoff_pass"] = bool(signoff_bundle_result.get("pass"))
        report["summary"]["signoff_total_checks"] = int(signoff_summary.get("total_checks", 0) or 0)
        report["summary"]["signoff_failed_checks"] = int(signoff_summary.get("failed_checks", 0) or 0)
        if not bool(signoff_bundle_result.get("pass")):
            report["summary"]["pass"] = False
            for i, raw in enumerate(signoff_bundle_result.get("violations", []) or []):
                msg = str(raw)
                label = "signoff"
                if ":" in msg:
                    label = str(msg.split(":", 1)[0]).strip() or "signoff"
                report["violations_annotated"].append(
                    {
                        "id": f"lvs.signoff:{label}:{i}",
                        "source": "pic.lvs_lite.signoff",
                        "code": f"lvs.signoff.{label}",
                        "severity": "error",
                        "applicability": "blocking",
                        "entity_ref": f"signoff_check:{label}",
                        "message": msg,
                        "location": None,
                    }
                )
            report["summary"]["violations"] = int(len(report.get("violations_annotated", []) or []))
            report["summary"]["blocking_violations"] = int(
                len(
                    [
                        v
                        for v in (report.get("violations_annotated", []) or [])
                        if str(v.get("applicability", "")).strip().lower() == "blocking"
                    ]
                )
            )

    return report
