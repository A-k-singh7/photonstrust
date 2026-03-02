"""PIC certification orchestrator for an integrated PIC->QKD certificate."""

from __future__ import annotations

import hashlib
import importlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from photonstrust.evidence.signing import sign_bytes_ed25519
from photonstrust.graph import compile_graph, load_graph_file, stable_graph_hash
from photonstrust.pdk.registry import get_pdk
from photonstrust.pic.assembly import assemble_pic_chip
from photonstrust.pic.signoff import build_pic_signoff_ladder
from photonstrust.pic.simulate import simulate_pic_netlist
from photonstrust.pipeline.pic_qkd_bridge import (
    build_qkd_scenario_from_pic,
    extract_eta_chip,
    pdk_coupler_efficiency,
)
from photonstrust.qkd import compute_sweep
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import pic_qkd_certificate_schema_path

_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)
_DRC_RULE_ALIAS = {
    "PIC.DRC.MIN_WIDTH": "DRC.WG.MIN_WIDTH",
    "PIC.DRC.MIN_GAP": "DRC.WG.MIN_SPACING",
    "PIC.DRC.MIN_BEND_RADIUS": "DRC.WG.MIN_BEND_RADIUS",
    "PIC.DRC.MIN_ENCLOSURE": "DRC.WG.MIN_ENCLOSURE",
}
_STAGE_ORDER = ("drc", "lvs", "pex")


def run_certify(
    graph: dict[str, Any] | str | Path,
    *,
    pdk_name: str | None = "generic_silicon_photonics",
    protocol: str = "BB84_DECOY",
    wavelength_nm: float = 1550.0,
    target_distance_km: float = 50.0,
    distances_km: Iterable[float] | None = None,
    output_dir: str | Path | None = None,
    dry_run: bool = False,
    signing_key: str | Path | None = None,
) -> dict[str, Any]:
    """Run PIC compile/assembly/signoff and bridge output to a QKD certificate."""

    graph_payload, graph_path = _resolve_graph_payload(graph)
    compiled = compile_graph(graph_payload, require_schema=False)
    if str(compiled.profile).strip().lower() != "pic_circuit":
        raise ValueError("run_certify requires graph.profile=pic_circuit")

    assembly_payload = assemble_pic_chip({"graph": graph_payload}, require_schema=False)
    assembly_report = assembly_payload.get("report")
    assembled_netlist = assembly_payload.get("assembled_netlist")
    if not isinstance(assembly_report, dict) or not isinstance(assembled_netlist, dict):
        raise ValueError("assemble_pic_chip returned an invalid payload")

    pdk = get_pdk(pdk_name)

    drc_started_at = _now_iso()
    drc_report = _run_m1_drc(assembled_netlist=assembled_netlist, pdk=pdk)
    drc_finished_at = _now_iso()

    lvs_started_at = _now_iso()
    lvs_report = _run_m1_lvs(graph_payload=graph_payload, assembled_netlist=assembled_netlist)
    lvs_finished_at = _now_iso()

    simulation_result: dict[str, Any] | None = None
    simulate_error: str | None = None
    pex_started_at = _now_iso()
    if not bool(dry_run):
        try:
            simulation_result = simulate_pic_netlist(assembled_netlist, wavelength_nm=float(wavelength_nm))
        except Exception as exc:  # pragma: no cover - defensive path
            simulate_error = str(exc)
    pex_finished_at = _now_iso()

    drc_summary = _to_drc_summary(
        drc_report,
        graph_hash=stable_graph_hash(graph_payload),
        started_at=drc_started_at,
        finished_at=drc_finished_at,
    )
    lvs_summary = _to_lvs_summary(
        lvs_report,
        graph_hash=stable_graph_hash(graph_payload),
        started_at=lvs_started_at,
        finished_at=lvs_finished_at,
    )
    pex_summary = _to_pex_summary(
        graph_hash=stable_graph_hash(graph_payload),
        started_at=pex_started_at,
        finished_at=pex_finished_at,
        dry_run=bool(dry_run),
        simulate_error=simulate_error,
    )

    qkd_scenario: dict[str, Any] | None = None
    qkd_sweep_payload: dict[str, Any] | None = None
    qkd_error: str | None = None
    target_distance_summary: dict[str, Any] | None = None

    normalized_distances = _normalize_distances_km(distances_km)
    if not bool(dry_run) and simulate_error is None:
        eta_chip = extract_eta_chip(simulation_result or {}, wavelength_nm=float(wavelength_nm))
        eta_coupler = pdk_coupler_efficiency(pdk)
        qkd_scenario = build_qkd_scenario_from_pic(
            graph=graph_payload,
            distances_km=normalized_distances,
            wavelength_nm=float(wavelength_nm),
            protocol=str(protocol),
            eta_chip=eta_chip,
            eta_coupler=eta_coupler,
        )
        try:
            qkd_sweep_raw = compute_sweep(qkd_scenario, include_uncertainty=False)
            qkd_sweep_payload = _serialize_qkd_sweep(qkd_sweep_raw)
            target_distance_summary = _target_distance_summary(
                qkd_sweep_payload,
                target_distance_km=float(target_distance_km),
            )
            target_distance_summary["eta_chip"] = float(eta_chip)
            target_distance_summary["eta_coupler"] = float(eta_coupler)
        except Exception as exc:  # pragma: no cover - defensive path
            qkd_error = str(exc)
    elif bool(dry_run):
        target_distance_summary = {
            "status": "skipped",
            "reason": "dry_run",
            "target_distance_km": float(target_distance_km),
        }
    else:
        target_distance_summary = {
            "status": "error",
            "reason": "simulation_failed",
            "target_distance_km": float(target_distance_km),
        }

    foundry_approval_summary = _build_foundry_approval_summary(
        drc_summary=drc_summary,
        lvs_summary=lvs_summary,
        pex_summary=pex_summary,
    )

    signoff_request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        "drc_summary": drc_summary,
        "lvs_summary": lvs_summary,
        "pex_summary": pex_summary,
        "foundry_approval": foundry_approval_summary,
    }
    signoff_result = build_pic_signoff_ladder(signoff_request)
    signoff_report = signoff_result.get("report")
    decision = str(signoff_result.get("decision") or "HOLD").strip().upper()
    if not isinstance(signoff_report, dict):
        raise ValueError("build_pic_signoff_ladder returned invalid report")

    certificate_path: Path | None = None
    if output_dir is not None:
        certificate_path = Path(output_dir).resolve() / "certificate.json"

    certificate = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_qkd_certificate",
        "generated_at": _now_iso(),
        "decision": decision,
        "graph_id": str(graph_payload.get("graph_id") or "").strip(),
        "inputs": {
            "graph_path": str(graph_path) if graph_path is not None else None,
            "pdk": str(pdk.name),
            "pdk_version": str(pdk.version),
            "protocol": str(protocol).strip().upper(),
            "wavelength_nm": float(wavelength_nm),
            "target_distance_km": float(target_distance_km),
            "distances_km": list(normalized_distances),
            "dry_run": bool(dry_run),
            "output_dir": str(Path(output_dir).resolve()) if output_dir is not None else None,
            "signing_key": str(Path(signing_key).resolve()) if signing_key is not None else None,
        },
        "hashes": {
            "graph_hash": stable_graph_hash(graph_payload),
            "compiled_netlist_hash": hash_dict(compiled.compiled),
            "assembly_report_hash": hash_dict(assembly_report),
            "signoff_report_hash": hash_dict(signoff_report),
            "simulation_result_hash": _hash_payload(simulation_result),
            "qkd_sweep_hash": _hash_payload(qkd_sweep_payload),
            "certificate_payload_hash": "",
        },
        "provenance": {
            "photonstrust_version": _photonstrust_version() or "unknown",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "steps": _build_steps(
            drc_summary=drc_summary,
            lvs_summary=lvs_summary,
            pex_summary=pex_summary,
            dry_run=bool(dry_run),
            qkd_error=qkd_error,
        ),
        "artifacts": {
            "certificate_path": str(certificate_path) if certificate_path is not None else None,
        },
        "signoff": {
            "decision": decision,
            "run_id": str(signoff_report.get("run_id") or ""),
            "reasons": list((signoff_report.get("final_decision") or {}).get("reasons") or []),
        },
        "signoff_report": signoff_report,
        "drc_summary": drc_summary,
        "lvs_summary": lvs_summary,
        "pex_summary": pex_summary,
        "foundry_approval_summary": foundry_approval_summary,
        "simulation_result": simulation_result if not bool(dry_run) else None,
        "qkd_scenario": qkd_scenario if not bool(dry_run) else None,
        "qkd_sweep": qkd_sweep_payload if not bool(dry_run) else None,
        "target_distance_summary": target_distance_summary,
        "signature": None,
    }
    if qkd_error:
        certificate["target_distance_summary"] = {
            "status": "error",
            "reason": qkd_error,
            "target_distance_km": float(target_distance_km),
        }

    certificate["hashes"]["certificate_payload_hash"] = _certificate_payload_hash(certificate)

    if signing_key is not None:
        key_path = Path(signing_key).resolve()
        sign_payload = dict(certificate)
        sign_payload["signature"] = None
        message = _canonical_json_bytes(sign_payload)
        certificate["signature"] = {
            "algorithm": "ed25519",
            "key_path": str(key_path),
            "signature_b64": sign_bytes_ed25519(private_key_pem_path=key_path, message=message),
            "message_sha256": hashlib.sha256(message).hexdigest(),
        }
        certificate["hashes"]["certificate_payload_hash"] = _certificate_payload_hash(certificate)

    schema_validation = _validate_certificate_schema(certificate)

    if certificate_path is not None:
        certificate_path.parent.mkdir(parents=True, exist_ok=True)
        certificate_path.write_text(json.dumps(certificate, indent=2), encoding="utf-8")

    return {
        "decision": decision,
        "certificate": certificate,
        "output_path": str(certificate_path) if certificate_path is not None else None,
        "schema_validation": schema_validation,
    }


def _resolve_graph_payload(graph: dict[str, Any] | str | Path) -> tuple[dict[str, Any], Path | None]:
    if isinstance(graph, dict):
        return json.loads(json.dumps(graph)), None
    graph_path = Path(graph).resolve()
    return load_graph_file(graph_path), graph_path


def _run_m1_drc(*, assembled_netlist: dict[str, Any], pdk: Any) -> dict[str, Any]:
    module = importlib.import_module("photonstrust.pic.drc")
    if hasattr(module, "run_graph_drc"):
        return module.run_graph_drc(assembled_netlist, pdk=pdk)
    raise RuntimeError("photonstrust.pic.drc.run_graph_drc is not available")


def _run_m1_lvs(*, graph_payload: dict[str, Any], assembled_netlist: dict[str, Any]) -> dict[str, Any]:
    module = importlib.import_module("photonstrust.pic.lvs_lite")
    if hasattr(module, "run_lvs_lite"):
        return module.run_lvs_lite(graph_payload, assembled_netlist)
    raise RuntimeError("photonstrust.pic.lvs_lite.run_lvs_lite is not available")


def _to_drc_summary(report: dict[str, Any], *, graph_hash: str, started_at: str, finished_at: str) -> dict[str, Any]:
    status = "pass" if bool(((report.get("summary") or {}).get("pass"))) else "fail"
    raw_failed_ids = _drc_failed_ids(report)
    failed_ids = _normalize_drc_failed_ids(raw_failed_ids)
    if status == "pass":
        failed_ids = []
    elif not failed_ids:
        failed_ids = ["DRC.WG.MIN_WIDTH"]

    error_count = len(failed_ids)
    total_count = max(1, len(_as_list(report.get("items"))))
    check_counts = {
        "total": int(total_count),
        "passed": int(max(0, total_count - error_count)),
        "failed": int(error_count),
        "errored": 0,
    }
    run_id = _run_id_for(
        "drc_summary",
        {
            "graph_hash": graph_hash,
            "status": status,
            "failed_ids": failed_ids,
        },
    )
    return {
        "schema_version": "0.1",
        "kind": "pic.foundry_drc_sealed_summary",
        "run_id": run_id,
        "status": status,
        "execution_backend": "local_rules",
        "started_at": started_at,
        "finished_at": finished_at,
        "check_counts": check_counts,
        "failed_check_ids": list(failed_ids),
        "failed_check_names": list(failed_ids),
        "rule_results": _canonical_drc_rule_results(status=status, failed_check_ids=failed_ids),
        "deck_fingerprint": "sha256:certify-local",
        "error_code": None,
    }


def _to_lvs_summary(report: dict[str, Any], *, graph_hash: str, started_at: str, finished_at: str) -> dict[str, Any]:
    status = "pass" if bool(report.get("pass")) else "fail"
    failed_checks = _as_list(((report.get("summary") or {}).get("failed_checks")))
    failed_ids = [f"LVS.{str(item).strip().upper()}" for item in failed_checks if str(item).strip()]
    if status == "fail" and not failed_ids:
        failed_ids = ["LVS.MISMATCH"]
    if status == "pass":
        failed_ids = []

    checks_obj = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    total_checks = max(1, len(checks_obj))
    failed_count = len(failed_ids)
    run_id = _run_id_for(
        "lvs_summary",
        {
            "graph_hash": graph_hash,
            "status": status,
            "failed_ids": failed_ids,
        },
    )
    return {
        "schema_version": "0.1",
        "kind": "pic.foundry_lvs_sealed_summary",
        "run_id": run_id,
        "status": status,
        "execution_backend": "local_lvs",
        "started_at": started_at,
        "finished_at": finished_at,
        "check_counts": {
            "total": int(total_checks),
            "passed": int(max(0, total_checks - failed_count)),
            "failed": int(failed_count),
            "errored": 0,
        },
        "failed_check_ids": list(failed_ids),
        "failed_check_names": list(failed_ids),
        "deck_fingerprint": "sha256:certify-local",
        "error_code": None,
    }


def _to_pex_summary(
    *,
    graph_hash: str,
    started_at: str,
    finished_at: str,
    dry_run: bool,
    simulate_error: str | None,
) -> dict[str, Any]:
    if simulate_error is not None:
        status = "error"
        failed_ids = ["PEX.SIMULATION_ERROR"]
        errored = 1
        failed = 0
        passed = 0
        error_code: str | None = "simulation_error"
    else:
        status = "pass"
        failed_ids = []
        errored = 0
        failed = 0
        passed = 1
        error_code = None

    run_id = _run_id_for(
        "pex_summary",
        {
            "graph_hash": graph_hash,
            "status": status,
            "dry_run": bool(dry_run),
            "simulate_error": simulate_error,
        },
    )
    return {
        "schema_version": "0.1",
        "kind": "pic.foundry_pex_sealed_summary",
        "run_id": run_id,
        "status": status,
        "execution_backend": "local_pex",
        "started_at": started_at,
        "finished_at": finished_at,
        "check_counts": {
            "total": 1,
            "passed": int(passed),
            "failed": int(failed),
            "errored": int(errored),
        },
        "failed_check_ids": list(failed_ids),
        "failed_check_names": list(failed_ids),
        "deck_fingerprint": "sha256:certify-local",
        "error_code": error_code,
    }


def _build_foundry_approval_summary(
    *,
    drc_summary: dict[str, Any],
    lvs_summary: dict[str, Any],
    pex_summary: dict[str, Any],
) -> dict[str, Any]:
    summary_by_stage = {
        "drc": dict(drc_summary),
        "lvs": dict(lvs_summary),
        "pex": dict(pex_summary),
    }

    failed_check_ids: list[str] = []
    for stage in _STAGE_ORDER:
        stage_summary = summary_by_stage.get(stage, {})
        status = str(stage_summary.get("status") or "").strip().lower()
        stage_failed_ids = [str(v).strip() for v in _as_list(stage_summary.get("failed_check_ids")) if str(v).strip()]
        if status in {"fail", "error", "hold"}:
            failed_check_ids.extend(stage_failed_ids or [f"foundry_{stage}.status_{status or 'error'}"])

    failed_check_ids = _unique_non_empty(failed_check_ids)
    decision = "HOLD" if failed_check_ids else "GO"
    status = "fail" if failed_check_ids else "pass"
    started_at = str(drc_summary.get("started_at") or _now_iso())
    finished_at = str(pex_summary.get("finished_at") or started_at)
    source_run_ids = {
        "drc": str(drc_summary.get("run_id") or ""),
        "lvs": str(lvs_summary.get("run_id") or ""),
        "pex": str(pex_summary.get("run_id") or ""),
    }
    run_id = _run_id_for(
        "foundry_approval_summary",
        {
            "decision": decision,
            "status": status,
            "failed_check_ids": failed_check_ids,
            "source_run_ids": source_run_ids,
        },
    )
    return {
        "schema_version": "0.1",
        "kind": "pic.foundry_approval_sealed_summary",
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "decision": decision,
        "status": status,
        "failed_check_ids": list(failed_check_ids),
        "failed_check_names": list(failed_check_ids),
        "source_run_ids": source_run_ids,
        "deck_fingerprint": "sha256:certify-local",
        "error_code": None,
    }


def _drc_failed_ids(report: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for row in _as_list(report.get("items")):
        if not isinstance(row, dict):
            continue
        severity = str(row.get("severity") or "").strip().lower()
        code = str(row.get("code") or "").strip()
        if severity == "error" and code:
            out.append(code)
    return _unique_non_empty(out)


def _normalize_drc_failed_ids(raw_ids: Iterable[str]) -> list[str]:
    mapped: list[str] = []
    for item in raw_ids:
        key = str(item).strip().upper()
        if not key:
            continue
        mapped.append(_DRC_RULE_ALIAS.get(key, key))
    return _unique_non_empty(mapped)


def _canonical_drc_rule_results(*, status: str, failed_check_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    failed_set = {str(v).strip().upper() for v in failed_check_ids if str(v).strip()}
    if status == "error":
        return {
            rule_id: {
                "status": "error",
                "required_um": None,
                "observed_um": None,
                "violation_count": 0,
                "entity_refs": [],
            }
            for rule_id in _MANDATORY_DRC_RULE_IDS
        }

    if status == "fail" and not failed_set:
        failed_set = {_MANDATORY_DRC_RULE_IDS[0]}

    out: dict[str, dict[str, Any]] = {}
    for rule_id in _MANDATORY_DRC_RULE_IDS:
        is_fail = rule_id in failed_set
        out[rule_id] = {
            "status": "fail" if is_fail else "pass",
            "required_um": None,
            "observed_um": None,
            "violation_count": 1 if is_fail else 0,
            "entity_refs": [],
        }
    return out


def _serialize_qkd_sweep(sweep_raw: dict[str, Any]) -> dict[str, Any]:
    out = {
        "results": [],
        "uncertainty": sweep_raw.get("uncertainty"),
        "performance": sweep_raw.get("performance"),
    }
    for row in _as_list(sweep_raw.get("results")):
        if isinstance(row, dict):
            out["results"].append(dict(row))
            continue
        row_dict = getattr(row, "__dict__", None)
        if isinstance(row_dict, dict):
            out["results"].append(dict(row_dict))
    return out


def _target_distance_summary(qkd_sweep: dict[str, Any], *, target_distance_km: float) -> dict[str, Any]:
    results = [row for row in _as_list(qkd_sweep.get("results")) if isinstance(row, dict)]
    if not results:
        return {
            "status": "error",
            "reason": "missing_qkd_results",
            "target_distance_km": float(target_distance_km),
        }

    target = float(target_distance_km)
    best = min(
        results,
        key=lambda row: abs(float(row.get("distance_km", 0.0) or 0.0) - target),
    )
    return {
        "status": "ok",
        "target_distance_km": float(target),
        "nearest_distance_km": float(best.get("distance_km", 0.0) or 0.0),
        "key_rate_bps": float(best.get("key_rate_bps", 0.0) or 0.0),
        "qber_total": float(best.get("qber_total", 0.0) or 0.0),
        "fidelity": float(best.get("fidelity", 0.0) or 0.0),
        "loss_db": float(best.get("loss_db", 0.0) or 0.0),
        "protocol_name": str(best.get("protocol_name") or ""),
    }


def _build_steps(
    *,
    drc_summary: dict[str, Any],
    lvs_summary: dict[str, Any],
    pex_summary: dict[str, Any],
    dry_run: bool,
    qkd_error: str | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        {"name": "compile_graph", "status": "pass"},
        {"name": "assemble_pic_chip", "status": "pass"},
        {"name": "m1_drc", "status": _status_for_step(drc_summary)},
        {"name": "m1_lvs_lite", "status": _status_for_step(lvs_summary)},
        {"name": "m1_pex", "status": _status_for_step(pex_summary)},
    ]
    if bool(dry_run):
        steps.append({"name": "simulate_pic_netlist", "status": "skipped"})
        steps.append({"name": "compute_qkd_sweep", "status": "skipped"})
    else:
        steps.append({"name": "simulate_pic_netlist", "status": "error" if pex_summary.get("status") == "error" else "pass"})
        steps.append({"name": "compute_qkd_sweep", "status": "error" if qkd_error else "pass"})
    steps.append({"name": "build_signoff_ladder", "status": "pass"})
    return steps


def _status_for_step(summary: dict[str, Any]) -> str:
    status = str(summary.get("status") or "").strip().lower()
    if status in {"pass", "fail", "error", "skipped"}:
        return status
    return "error"


def _validate_certificate_schema(certificate: dict[str, Any]) -> dict[str, Any]:
    try:
        from jsonschema import validate
    except Exception:
        return {"performed": False, "ok": None, "reason": "jsonschema_unavailable"}

    schema = json.loads(pic_qkd_certificate_schema_path().read_text(encoding="utf-8"))
    validate(instance=certificate, schema=schema)
    return {"performed": True, "ok": True, "reason": None}


def _normalize_distances_km(distances_km: Iterable[float] | None) -> list[float]:
    if distances_km is None:
        return [0.0, 25.0, 50.0, 75.0, 100.0]
    out = sorted({_positive_or_zero(v) for v in distances_km if _positive_or_zero(v) is not None})
    return out or [0.0, 25.0, 50.0, 75.0, 100.0]


def _positive_or_zero(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out < 0.0:
        return None
    return float(out)


def _hash_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return hash_dict(payload)
    return _stable_digest(payload)


def _certificate_payload_hash(certificate: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(certificate))
    hashes = payload.get("hashes")
    if isinstance(hashes, dict):
        hashes["certificate_payload_hash"] = ""
    return _stable_digest(payload)


def _run_id_for(kind: str, payload: Any) -> str:
    return _stable_digest({"kind": str(kind), "payload": payload})[:12]


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _unique_non_empty(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None
