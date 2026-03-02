"""PIC signoff ladder core helpers."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.utils import hash_dict

_HEX_CHARS = set("0123456789abcdef")
_MULTI_STAGE_ORDER: tuple[str, ...] = (
    "chip_assembly",
    "drc",
    "lvs",
    "pex",
    "foundry_approval",
)
_UNACCEPTABLE_EXECUTION_BACKENDS: set[str] = {"mock", "stub"}


def build_pic_signoff_ladder(
    request: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic PIC signoff ladder report from chip assembly outputs."""

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    assembly_report = request.get("assembly_report")
    if not isinstance(assembly_report, dict):
        raise TypeError("request.assembly_report must be an object")
    if str(assembly_report.get("kind", "")).strip() != "pic.chip_assembly":
        raise ValueError("request.assembly_report.kind must be pic.chip_assembly")

    policy = request.get("policy")
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise TypeError("request.policy must be an object when provided")

    summaries = _collect_stage_summaries(request)
    # Phase-2 hardening: enforce the research-grade 5-stage ladder for every signoff build.
    multi_stage_enabled = True

    chip_assembly_hash = hash_dict(assembly_report)
    chip_assembly_run_id = _resolve_chip_assembly_run_id(
        assembly_report=assembly_report,
        chip_assembly_hash=chip_assembly_hash,
    )
    policy_hash = hash_dict(policy)

    allow_waived_failures = bool(policy.get("allow_waived_failures") is True)
    global_waiver_ids = _normalized_waiver_rule_ids(policy.get("active_waiver_rule_ids"))
    stage_waiver_ids = _normalized_stage_waivers(policy.get("stage_waiver_rule_ids"))

    chip_assembly_stage = _build_chip_assembly_stage(
        assembly_report=assembly_report,
        allow_waived_failures=allow_waived_failures,
        applicable_waiver_ids=_waiver_ids_for_stage(
            stage="chip_assembly",
            global_waiver_ids=global_waiver_ids,
            stage_waiver_ids=stage_waiver_ids,
        ),
        chip_assembly_hash=chip_assembly_hash,
        chip_assembly_run_id=chip_assembly_run_id,
    )

    ladder: list[dict[str, Any]] = []
    previous_stage_hash = chip_assembly_hash
    for stage in _iter_stage_specs(
        chip_assembly_stage=chip_assembly_stage,
        summaries=summaries,
        allow_waived_failures=allow_waived_failures,
        global_waiver_ids=global_waiver_ids,
        stage_waiver_ids=stage_waiver_ids,
        previous_status=str(chip_assembly_stage.get("status", "")).strip().lower() or "pass",
    ):
        stage_with_chain, previous_stage_hash = _attach_hash_chain(stage=stage, prev_stage_hash=previous_stage_hash)
        ladder.append(stage_with_chain)

    _validate_deterministic_ladder_structure(ladder)
    _validate_stage_semantics(ladder)

    final_decision = _derive_final_decision(ladder)

    report = {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "pic.signoff_ladder",
        "run_id": _resolve_signoff_run_id(
            run_id=run_id,
            chip_assembly_run_id=chip_assembly_run_id,
            chip_assembly_hash=chip_assembly_hash,
            policy_hash=policy_hash,
        ),
        "inputs": {
            "chip_assembly_run_id": chip_assembly_run_id,
            "chip_assembly_hash": chip_assembly_hash,
            "policy_hash": policy_hash,
            "multi_stage_enabled": bool(multi_stage_enabled),
        },
        "ladder": ladder,
        "final_decision": final_decision,
        "evidence_chain_root": previous_stage_hash,
        "provenance": {
            "photonstrust_version": _photonstrust_version() or "unknown",
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    verify_pic_signoff_hash_chain(report)

    return {
        "report": report,
        "decision": final_decision["decision"],
    }


def _build_chip_assembly_stage(
    *,
    assembly_report: dict[str, Any],
    allow_waived_failures: bool,
    applicable_waiver_ids: set[str],
    chip_assembly_hash: str,
    chip_assembly_run_id: str,
) -> dict[str, Any]:
    outputs = assembly_report.get("outputs") if isinstance(assembly_report.get("outputs"), dict) else {}
    output_summary = outputs.get("summary") if isinstance(outputs.get("summary"), dict) else {}
    stitch = assembly_report.get("stitch") if isinstance(assembly_report.get("stitch"), dict) else {}
    stitch_summary = stitch.get("summary") if isinstance(stitch.get("summary"), dict) else {}

    assembly_status = str(output_summary.get("status", "")).strip().lower()
    failed_links = _int_or_none(stitch_summary.get("failed_links"))
    failure_rule_ids: list[str] = []
    if assembly_status != "pass":
        failure_rule_ids.append("chip_assembly.status_not_pass")
    if failed_links != 0:
        failure_rule_ids.append("chip_assembly.failed_links")

    stage_pass = not failure_rule_ids

    reasons: list[str] = []
    if assembly_status != "pass":
        reasons.append(f"outputs.summary.status={assembly_status or 'missing'}")
    if failed_links != 0:
        reasons.append(f"stitch.summary.failed_links={_display_value(stitch_summary.get('failed_links'))}")
    if not reasons:
        reasons.append("outputs.summary.status=pass and stitch.summary.failed_links=0")

    stage_status = "pass" if stage_pass else "fail"
    stage_reason = "; ".join(reasons)
    waived_rule_ids: list[str] = []

    if failure_rule_ids and allow_waived_failures:
        failures_fully_covered = all(rule_id in applicable_waiver_ids for rule_id in failure_rule_ids)
        if failures_fully_covered:
            stage_status = "waived"
            waived_rule_ids = sorted(set(failure_rule_ids), key=lambda v: v.lower())
            covered_ids = ", ".join(failure_rule_ids)
            stage_reason = (
                f"waived failures covered by active waiver IDs: {covered_ids}; "
                f"underlying failures: {'; '.join(reasons)}"
            )

    evidence_hashes: list[str] = [chip_assembly_hash]
    output_hash = str(output_summary.get("output_hash", "")).strip().lower()
    if _is_lower_hex(output_hash, min_len=64, max_len=64) and output_hash not in evidence_hashes:
        evidence_hashes.append(output_hash)

    return {
        "level": 1,
        "stage": "chip_assembly",
        "status": stage_status,
        "run_id": chip_assembly_run_id,
        "reason": stage_reason,
        "evidence_hashes": evidence_hashes,
        "failure_rule_ids": sorted(set(failure_rule_ids), key=lambda v: v.lower()),
        "waived_rule_ids": waived_rule_ids,
    }


def _collect_stage_summaries(request: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    out: dict[str, dict[str, Any] | None] = {}
    for stage in ("drc", "lvs", "pex", "foundry_approval"):
        if stage == "foundry_approval":
            raw = request.get("foundry_approval")
        else:
            raw = request.get(f"{stage}_summary")
        out[stage] = dict(raw) if isinstance(raw, dict) else None
    return out


def _normalized_stage_waivers(value: Any) -> dict[str, set[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, set[str]] = {}
    for raw_stage, raw_ids in value.items():
        stage = str(raw_stage or "").strip().lower()
        if not stage:
            continue
        out[stage] = _normalized_waiver_rule_ids(raw_ids)
    return out


def _waiver_ids_for_stage(
    *,
    stage: str,
    global_waiver_ids: set[str],
    stage_waiver_ids: dict[str, set[str]],
) -> set[str]:
    per_stage = stage_waiver_ids.get(stage, set())
    return set(global_waiver_ids).union(per_stage)


def _iter_stage_specs(
    *,
    chip_assembly_stage: dict[str, Any],
    summaries: dict[str, dict[str, Any] | None],
    allow_waived_failures: bool,
    global_waiver_ids: set[str],
    stage_waiver_ids: dict[str, set[str]],
    previous_status: str,
) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = [chip_assembly_stage]

    prior_stage = "chip_assembly"
    prior_status = previous_status
    for level, stage in enumerate(_MULTI_STAGE_ORDER[1:], start=2):
        if prior_status in {"fail", "error", "hold", "skipped"}:
            stages.append(
                {
                    "level": level,
                    "stage": stage,
                    "status": "skipped",
                    "run_id": _resolve_stage_run_id(stage=stage, summary=None),
                    "reason": f"skipped because prior stage {prior_stage} status={prior_status}",
                    "evidence_hashes": [],
                    "failure_rule_ids": [],
                    "waived_rule_ids": [],
                }
            )
            prior_stage = stage
            prior_status = "skipped"
            continue

        summary = summaries.get(stage)
        applicable_waivers = _waiver_ids_for_stage(
            stage=stage,
            global_waiver_ids=global_waiver_ids,
            stage_waiver_ids=stage_waiver_ids,
        )
        if stage == "foundry_approval":
            stage_row = _build_foundry_approval_stage(
                level=level,
                summary=summary,
                allow_waived_failures=allow_waived_failures,
                applicable_waiver_ids=applicable_waivers,
            )
        else:
            stage_row = _build_foundry_summary_stage(
                level=level,
                stage=stage,
                summary=summary,
                allow_waived_failures=allow_waived_failures,
                applicable_waiver_ids=applicable_waivers,
            )
        stages.append(stage_row)
        prior_stage = stage
        prior_status = str(stage_row.get("status", "")).strip().lower()

    return stages


def _build_foundry_summary_stage(
    *,
    level: int,
    stage: str,
    summary: dict[str, Any] | None,
    allow_waived_failures: bool,
    applicable_waiver_ids: set[str],
) -> dict[str, Any]:
    evidence_hashes: list[str] = []
    failure_rule_ids: list[str] = []
    waived_rule_ids: list[str] = []
    run_id = _resolve_stage_run_id(stage=stage, summary=summary)

    if not isinstance(summary, dict):
        return {
            "level": level,
            "stage": stage,
            "status": "fail",
            "run_id": run_id,
            "reason": f"{stage} summary missing",
            "evidence_hashes": evidence_hashes,
            "failure_rule_ids": [f"{stage}.summary_missing"],
            "waived_rule_ids": [],
        }

    evidence_hashes.append(hash_dict(summary))
    status = str(summary.get("status", "")).strip().lower()
    backend = str(summary.get("execution_backend", "")).strip().lower()
    failed_ids_raw = summary.get("failed_check_ids")
    failed_ids = (
        sorted({str(v).strip() for v in failed_ids_raw if str(v).strip()}, key=lambda v: v.lower())
        if isinstance(failed_ids_raw, list)
        else []
    )
    check_counts = summary.get("check_counts") if isinstance(summary.get("check_counts"), dict) else {}
    total_count = _int_or_none(check_counts.get("total"))
    failed_count = _int_or_none(check_counts.get("failed"))
    errored_count = _int_or_none(check_counts.get("errored"))
    has_failed_count = failed_count is not None and failed_count > 0
    has_errored_count = errored_count is not None and errored_count > 0
    status_pass_contradiction = status == "pass" and (bool(failed_ids) or has_failed_count or has_errored_count)

    if status_pass_contradiction:
        stage_status = "error"
        failure_rule_ids = [f"{stage}.status_pass_contradiction"]
        contradiction_signals: list[str] = []
        if failed_ids:
            contradiction_signals.append(f"failed_check_ids={len(failed_ids)}")
        if has_failed_count:
            contradiction_signals.append(f"check_counts.failed={failed_count}")
        if has_errored_count:
            contradiction_signals.append(f"check_counts.errored={errored_count}")
        reason = f"{stage} status=pass contradicts reported failures ({', '.join(contradiction_signals)})"
    elif status == "pass":
        backend_acceptable = bool(backend) and backend not in _UNACCEPTABLE_EXECUTION_BACKENDS
        empty_check_set = total_count is not None and total_count == 0
        if not backend_acceptable:
            stage_status = "error"
            failure_rule_ids = [f"{stage}.backend_not_acceptable"]
            reason = f"{stage} status=pass requires execution_backend; got {backend or 'missing'}"
        elif empty_check_set:
            stage_status = "error"
            failure_rule_ids = [f"{stage}.empty_check_set"]
            reason = f"{stage} status=pass with check_counts.total=0"
        else:
            stage_status = "pass"
            reason = f"{stage} status=pass"
    elif status == "fail":
        stage_status = "fail"
        failure_rule_ids = failed_ids or [f"{stage}.failed"]
        reason = f"{stage} status=fail"
    elif status == "error":
        stage_status = "error"
        failure_rule_ids = failed_ids or [f"{stage}.error"]
        reason = f"{stage} status=error"
    else:
        stage_status = "error"
        failure_rule_ids = [f"{stage}.status_invalid"]
        reason = f"{stage} status invalid: {status or 'missing'}"

    if stage_status in {"fail", "error"} and allow_waived_failures and failure_rule_ids:
        if all(rule_id.strip().lower() in applicable_waiver_ids for rule_id in failure_rule_ids):
            stage_status = "waived"
            waived_rule_ids = sorted(set(failure_rule_ids), key=lambda v: v.lower())
            reason = f"{stage} failures waived: {', '.join(waived_rule_ids)}"

    if backend:
        reason = f"{reason}; backend={backend}"

    return {
        "level": level,
        "stage": stage,
        "status": stage_status,
        "run_id": run_id,
        "reason": reason,
        "evidence_hashes": evidence_hashes,
        "failure_rule_ids": sorted(set(failure_rule_ids), key=lambda v: v.lower()),
        "waived_rule_ids": waived_rule_ids,
    }


def _build_foundry_approval_stage(
    *,
    level: int,
    summary: dict[str, Any] | None,
    allow_waived_failures: bool,
    applicable_waiver_ids: set[str],
) -> dict[str, Any]:
    stage = "foundry_approval"
    evidence_hashes: list[str] = []
    failure_rule_ids: list[str] = []
    waived_rule_ids: list[str] = []
    run_id = _resolve_stage_run_id(stage=stage, summary=summary)

    if not isinstance(summary, dict):
        return {
            "level": level,
            "stage": stage,
            "status": "fail",
            "run_id": run_id,
            "reason": "foundry_approval summary missing",
            "evidence_hashes": evidence_hashes,
            "failure_rule_ids": ["foundry_approval.summary_missing"],
            "waived_rule_ids": [],
        }

    evidence_hashes.append(hash_dict(summary))
    decision_text = str(summary.get("decision", "")).strip().lower()
    status_text = str(summary.get("status", "")).strip().lower()

    decision_signal = _normalize_foundry_approval_signal(decision_text)
    status_signal = _normalize_foundry_approval_signal(status_text)
    decision_status_mismatch = (
        bool(decision_text)
        and bool(status_text)
        and decision_signal in {"pass", "hold", "error"}
        and status_signal in {"pass", "hold", "error"}
        and decision_signal != status_signal
    )

    if decision_status_mismatch:
        stage_status = "hold"
        reason = f"foundry_approval decision/status mismatch: decision={decision_text}, status={status_text}"
        failure_rule_ids = ["foundry_approval.decision_status_mismatch"]
    else:
        merged = decision_text or status_text
        merged_signal = decision_signal if decision_text else status_signal
        if merged_signal == "pass":
            stage_status = "pass"
            reason = f"foundry_approval status={merged}"
        elif merged_signal in {"hold", "error"}:
            stage_status = "fail" if merged_signal != "error" else "error"
            reason = f"foundry_approval status={merged}"
            failed_ids_raw = summary.get("failed_check_ids")
            if isinstance(failed_ids_raw, list):
                failure_rule_ids = sorted({str(v).strip() for v in failed_ids_raw if str(v).strip()}, key=lambda v: v.lower())
            if not failure_rule_ids:
                failure_rule_ids = [f"foundry_approval.{merged}"]
        else:
            stage_status = "error"
            reason = f"foundry_approval status invalid: {merged or 'missing'}"
            failure_rule_ids = ["foundry_approval.status_invalid"]

    if stage_status in {"fail", "error"} and allow_waived_failures and failure_rule_ids:
        if all(rule_id.strip().lower() in applicable_waiver_ids for rule_id in failure_rule_ids):
            stage_status = "waived"
            waived_rule_ids = sorted(set(failure_rule_ids), key=lambda v: v.lower())
            reason = f"foundry_approval failures waived: {', '.join(waived_rule_ids)}"

    return {
        "level": level,
        "stage": stage,
        "status": stage_status,
        "run_id": run_id,
        "reason": reason,
        "evidence_hashes": evidence_hashes,
        "failure_rule_ids": sorted(set(failure_rule_ids), key=lambda v: v.lower()),
        "waived_rule_ids": waived_rule_ids,
    }


def _normalize_foundry_approval_signal(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"go", "pass", "approved"}:
        return "pass"
    if normalized in {"hold", "fail", "rejected"}:
        return "hold"
    if normalized == "error":
        return "error"
    if normalized:
        return "invalid"
    return ""


def _resolve_stage_run_id(*, stage: str, summary: dict[str, Any] | None) -> str:
    if isinstance(summary, dict):
        raw_run_id = str(summary.get("run_id", "")).strip().lower()
        if _is_lower_hex(raw_run_id, min_len=8, max_len=64):
            return raw_run_id
        return hash_dict({"kind": f"pic_{stage}_run_id", "summary_hash": hash_dict(summary)})[:12]
    return hash_dict({"kind": f"pic_{stage}_run_id", "missing": True})[:12]


def verify_pic_signoff_hash_chain(report: dict[str, Any]) -> bool:
    """Validate deterministic ladder structure and stage hash-chain integrity."""

    if not isinstance(report, dict):
        raise TypeError("report must be an object")
    if str(report.get("kind", "")).strip() != "pic.signoff_ladder":
        raise ValueError("report.kind must be pic.signoff_ladder")

    inputs = report.get("inputs")
    if not isinstance(inputs, dict):
        raise TypeError("report.inputs must be an object")
    chip_assembly_hash = str(inputs.get("chip_assembly_hash", "")).strip().lower()
    if not _is_lower_hex(chip_assembly_hash, min_len=64, max_len=64):
        raise ValueError("report.inputs.chip_assembly_hash must be a 64-char lowercase hex hash")
    policy_hash = str(inputs.get("policy_hash", "")).strip().lower()
    if not _is_lower_hex(policy_hash, min_len=64, max_len=64):
        raise ValueError("report.inputs.policy_hash must be a 64-char lowercase hex hash")

    ladder = _validate_deterministic_ladder_structure(report.get("ladder"))
    _validate_stage_semantics(ladder)
    expected_prev_hash = chip_assembly_hash

    for i, stage in enumerate(ladder):
        row_path = f"report.ladder[{i}]"
        prev_stage_hash = str(stage.get("prev_stage_hash", "")).strip().lower()
        stage_hash = str(stage.get("stage_hash", "")).strip().lower()

        if not _is_lower_hex(prev_stage_hash, min_len=64, max_len=64):
            raise ValueError(f"{row_path}.prev_stage_hash must be a 64-char lowercase hex hash")
        if not _is_lower_hex(stage_hash, min_len=64, max_len=64):
            raise ValueError(f"{row_path}.stage_hash must be a 64-char lowercase hex hash")
        if prev_stage_hash != expected_prev_hash:
            raise ValueError(f"{row_path}.prev_stage_hash does not match prior stage chain hash")

        expected_stage_hash = hash_dict(_stage_hash_payload(stage=stage, prev_stage_hash=prev_stage_hash))
        if stage_hash != expected_stage_hash:
            raise ValueError(f"{row_path}.stage_hash mismatch (evidence chain tamper detected)")

        expected_prev_hash = stage_hash

    evidence_chain_root = str(report.get("evidence_chain_root", "")).strip().lower()
    if not _is_lower_hex(evidence_chain_root, min_len=64, max_len=64):
        raise ValueError("report.evidence_chain_root must be a 64-char lowercase hex hash")
    if evidence_chain_root != expected_prev_hash:
        raise ValueError("report.evidence_chain_root does not match final stage hash")

    final_decision = report.get("final_decision")
    if not isinstance(final_decision, dict):
        raise TypeError("report.final_decision must be an object")
    decision = str(final_decision.get("decision", "")).strip().upper()
    if decision not in {"GO", "HOLD"}:
        raise ValueError("report.final_decision.decision must be GO or HOLD")
    expected_decision = _derive_final_decision(ladder)["decision"]
    if decision != expected_decision:
        raise ValueError("report.final_decision.decision does not match ladder state")

    return True


def _validate_deterministic_ladder_structure(ladder: Any) -> list[dict[str, Any]]:
    if not isinstance(ladder, list):
        raise TypeError("report.ladder must be an array")
    if len(ladder) != len(_MULTI_STAGE_ORDER):
        raise ValueError(f"report.ladder must contain exactly {len(_MULTI_STAGE_ORDER)} ordered stages")

    rows: list[dict[str, Any]] = []
    for i, expected_stage in enumerate(_MULTI_STAGE_ORDER):
        row_path = f"report.ladder[{i}]"
        raw = ladder[i]
        if not isinstance(raw, dict):
            raise TypeError(f"{row_path} must be an object")

        level = _int_or_none(raw.get("level"))
        if level != i + 1:
            raise ValueError(f"{row_path}.level must be {i + 1}")

        stage = str(raw.get("stage", "")).strip().lower()
        if stage != expected_stage:
            raise ValueError(f"{row_path}.stage must be {expected_stage}")

        rows.append(raw)

    return rows


def _validate_stage_semantics(ladder: list[dict[str, Any]]) -> None:
    blocking_seen = False
    blocking_stage = ""
    for i, row in enumerate(ladder):
        row_path = f"report.ladder[{i}]"
        stage = str(row.get("stage", "")).strip().lower()
        status = str(row.get("status", "")).strip().lower()
        if status not in {"pass", "fail", "hold", "waived", "skipped", "error"}:
            raise ValueError(f"{row_path}.status is invalid: {status or 'missing'}")

        evidence_hashes = _validated_evidence_hashes(row.get("evidence_hashes"), row_path=row_path)
        failure_rule_ids = _validated_rule_ids(row.get("failure_rule_ids"), row_path=row_path, field="failure_rule_ids")
        waived_rule_ids = _validated_rule_ids(row.get("waived_rule_ids"), row_path=row_path, field="waived_rule_ids")

        if i == 0 and status == "skipped":
            raise ValueError(f"{row_path}.status cannot be skipped")
        if i == 0 and not evidence_hashes:
            raise ValueError(f"{row_path}.evidence_hashes must include chip assembly evidence")

        if blocking_seen and status != "skipped":
            raise ValueError(f"{row_path}.status must be skipped because prior stage {blocking_stage} is blocking")

        if status == "pass":
            if failure_rule_ids or waived_rule_ids:
                raise ValueError(f"{row_path} pass stage cannot include failure or waived rule IDs")
        elif status == "waived":
            if not failure_rule_ids or not waived_rule_ids:
                raise ValueError(f"{row_path} waived stage must include failure and waived rule IDs")
            failure_norm = {item.strip().lower() for item in failure_rule_ids}
            waived_norm = {item.strip().lower() for item in waived_rule_ids}
            if failure_norm != waived_norm:
                raise ValueError(f"{row_path} waived_rule_ids must match failure_rule_ids for waived stage")
        elif status in {"fail", "error", "hold"}:
            if not failure_rule_ids:
                raise ValueError(f"{row_path} {status} stage must include failure_rule_ids")
            if waived_rule_ids:
                raise ValueError(f"{row_path} {status} stage must not include waived_rule_ids")
        elif status == "skipped":
            if evidence_hashes or failure_rule_ids or waived_rule_ids:
                raise ValueError(f"{row_path} skipped stage must not include evidence or rule IDs")

        if status in {"fail", "error", "hold", "skipped"}:
            blocking_seen = True
            blocking_stage = stage or f"index {i}"


def _validated_evidence_hashes(value: Any, *, row_path: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{row_path}.evidence_hashes must be an array")
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{row_path}.evidence_hashes[{idx}] must be a string")
        item_norm = item.strip().lower()
        if not _is_lower_hex(item_norm, min_len=64, max_len=64):
            raise ValueError(f"{row_path}.evidence_hashes[{idx}] must be a 64-char lowercase hex hash")
        out.append(item_norm)
    return out


def _validated_rule_ids(value: Any, *, row_path: str, field: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{row_path}.{field} must be an array")
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{row_path}.{field}[{idx}] must be a non-empty string")
        out.append(item.strip())
    return out


def _stage_hash_payload(*, stage: dict[str, Any], prev_stage_hash: str) -> dict[str, Any]:
    return {
        "level": int(stage.get("level", 0)),
        "stage": str(stage.get("stage", "")),
        "status": str(stage.get("status", "")),
        "run_id": str(stage.get("run_id", "")),
        "reason": str(stage.get("reason", "")),
        "evidence_hashes": list(stage.get("evidence_hashes") or []),
        "failure_rule_ids": list(stage.get("failure_rule_ids") or []),
        "waived_rule_ids": list(stage.get("waived_rule_ids") or []),
        "prev_stage_hash": prev_stage_hash,
    }


def _attach_hash_chain(stage: dict[str, Any], *, prev_stage_hash: str) -> tuple[dict[str, Any], str]:
    payload = _stage_hash_payload(stage=stage, prev_stage_hash=prev_stage_hash)
    stage_hash = hash_dict(payload)
    out = dict(stage)
    out["prev_stage_hash"] = prev_stage_hash
    out["stage_hash"] = stage_hash
    return out, stage_hash


def _derive_final_decision(ladder: list[dict[str, Any]]) -> dict[str, Any]:
    failing = [row for row in ladder if str(row.get("status", "")).strip().lower() in {"fail", "error", "hold"}]
    if failing:
        reasons = []
        for row in failing:
            reasons.append(_final_reason_from_stage(row))
        return {"decision": "HOLD", "reasons": reasons or ["one or more stages failed"]}

    skipped = [row for row in ladder if str(row.get("status", "")).strip().lower() == "skipped"]
    if skipped:
        reasons = [_final_reason_from_stage(row) for row in skipped]
        return {"decision": "HOLD", "reasons": reasons or ["one or more stages skipped"]}

    waived = [row for row in ladder if str(row.get("status", "")).strip().lower() == "waived"]
    if waived:
        reasons = [_final_reason_from_stage(row) for row in waived]
        return {"decision": "GO", "reasons": reasons}

    last = ladder[-1] if ladder else {}
    return {"decision": "GO", "reasons": [_final_reason_from_stage(last)]}


def _resolve_chip_assembly_run_id(*, assembly_report: dict[str, Any], chip_assembly_hash: str) -> str:
    raw_run_id = str(assembly_report.get("assembly_run_id", "")).strip().lower()
    if _is_lower_hex(raw_run_id, min_len=8, max_len=64):
        return raw_run_id
    return hash_dict({"kind": "pic_chip_assembly_run_id", "chip_assembly_hash": chip_assembly_hash})[:12]


def _resolve_signoff_run_id(
    *,
    run_id: str | None,
    chip_assembly_run_id: str,
    chip_assembly_hash: str,
    policy_hash: str,
) -> str:
    candidate = str(run_id or "").strip()
    if _is_lower_hex(candidate, min_len=8, max_len=64):
        return candidate
    return hash_dict(
        {
            "kind": "pic_signoff_ladder",
            "chip_assembly_run_id": chip_assembly_run_id,
            "chip_assembly_hash": chip_assembly_hash,
            "policy_hash": policy_hash,
        }
    )[:12]


def _final_reason_from_stage(stage: dict[str, Any]) -> str:
    reason = str(stage.get("reason", "")).strip()
    if stage.get("status") == "pass":
        return reason or "chip_assembly stage passed"
    if stage.get("status") == "waived":
        return reason or "chip_assembly stage waived"
    return reason or "chip_assembly stage failed"


def _normalized_waiver_rule_ids(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    normalized: set[str] = set()
    for item in value:
        if isinstance(item, str):
            item_str = item.strip().lower()
            if item_str:
                normalized.add(item_str)
    return normalized


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def _display_value(value: Any) -> str:
    raw = str(value or "").strip()
    return raw or "missing"


def _is_lower_hex(value: str, *, min_len: int, max_len: int) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) < min_len or len(value) > max_len:
        return False
    return all(ch in _HEX_CHARS for ch in value)


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        # Source checkout fallback.
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
