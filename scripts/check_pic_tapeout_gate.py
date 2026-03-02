#!/usr/bin/env python3
"""Run fail-closed checks for a PIC tapeout package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Callable

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.verification.waivers import load_and_validate_pic_waivers
from photonstrust.workflow.schema import (
    pic_foundry_drc_sealed_summary_schema_path,
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
)


DEFAULT_REQUIRED_ARTIFACTS = [
    "inputs/graph.json",
    "inputs/ports.json",
    "inputs/routes.json",
    "inputs/layout.gds",
]

DEFAULT_FOUNDRY_SUMMARY_REL = {
    "drc": "foundry_drc_sealed_summary.json",
    "lvs": "foundry_lvs_sealed_summary.json",
    "pex": "foundry_pex_sealed_summary.json",
}

FOUNDRY_SCHEMA_PATHS = {
    "drc": pic_foundry_drc_sealed_summary_schema_path,
    "lvs": pic_foundry_lvs_sealed_summary_schema_path,
    "pex": pic_foundry_pex_sealed_summary_schema_path,
}

_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PhotonTrust PIC tapeout package gate")
    parser.add_argument("--run-dir", type=Path, required=True, help="Tapeout run directory to validate")
    parser.add_argument(
        "--required-artifact",
        action="append",
        default=None,
        help=(
            "Artifact path relative to --run-dir; can be repeated. "
            "Defaults to inputs/graph.json, inputs/ports.json, inputs/routes.json, inputs/layout.gds"
        ),
    )
    parser.add_argument(
        "--run-pic-gate",
        action="store_true",
        help="Optionally invoke scripts/check_pic_gate.py and require it to pass",
    )
    parser.add_argument(
        "--pic-gate-args",
        default="--dry-run",
        help="Arguments forwarded to scripts/check_pic_gate.py (default: '--dry-run')",
    )
    parser.add_argument("--waiver-file", type=Path, default=None, help="Optional waiver JSON file path")
    parser.add_argument(
        "--require-foundry-signoff",
        action="store_true",
        help="Require sealed foundry DRC/LVS/PEX summary artifacts and signoff status",
    )
    parser.add_argument(
        "--drc-summary-rel",
        default=DEFAULT_FOUNDRY_SUMMARY_REL["drc"],
        help="Relative path under --run-dir for DRC sealed summary JSON",
    )
    parser.add_argument(
        "--lvs-summary-rel",
        default=DEFAULT_FOUNDRY_SUMMARY_REL["lvs"],
        help="Relative path under --run-dir for LVS sealed summary JSON",
    )
    parser.add_argument(
        "--pex-summary-rel",
        default=DEFAULT_FOUNDRY_SUMMARY_REL["pex"],
        help="Relative path under --run-dir for PEX sealed summary JSON",
    )
    parser.add_argument(
        "--allow-waived-failures",
        action="store_true",
        help="Allow fail statuses only when all failed_check_ids are covered by active waivers",
    )
    parser.add_argument(
        "--require-non-mock-backend",
        action="store_true",
        help="Require execution_backend != mock for foundry sealed summaries",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("results/pic_tapeout_gate/pic_tapeout_gate_report.json"),
        help="Path for machine-readable tapeout gate report JSON",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    args = parser.parse_args()

    if bool(args.require_non_mock_backend) and not bool(args.require_foundry_signoff):
        parser.error("--require-non-mock-backend requires --require-foundry-signoff")
    if bool(args.allow_waived_failures) and not bool(args.require_foundry_signoff):
        parser.error("--allow-waived-failures requires --require-foundry-signoff")
    if bool(args.allow_waived_failures) and args.waiver_file is None:
        parser.error("--allow-waived-failures requires --waiver-file")

    return args


def _run_check(name: str, fn: Callable[[], dict[str, Any]], checks: list[dict[str, Any]]) -> None:
    started = time.perf_counter()
    try:
        details = fn()
        checks.append(
            {
                "name": name,
                "passed": True,
                "duration_s": time.perf_counter() - started,
                "details": details,
            }
        )
    except Exception as exc:
        checks.append(
            {
                "name": name,
                "passed": False,
                "duration_s": time.perf_counter() - started,
                "details": {"error": str(exc)},
            }
        )


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _validate_foundry_summary(
    *,
    kind: str,
    summary_path: Path,
    require_non_mock_backend: bool,
) -> dict[str, Any]:
    if kind not in FOUNDRY_SCHEMA_PATHS:
        raise ValueError(f"unsupported foundry summary kind: {kind}")
    if not summary_path.exists() or not summary_path.is_file():
        raise FileNotFoundError(str(summary_path))

    payload = _load_json_object(summary_path)
    validate_instance(payload, FOUNDRY_SCHEMA_PATHS[kind]())

    status = str(payload.get("status", "")).strip().lower()
    if status not in {"pass", "fail", "error"}:
        raise ValueError(f"invalid foundry {kind} status: {status!r}")

    backend = str(payload.get("execution_backend", "")).strip().lower()
    if require_non_mock_backend and backend == "mock":
        raise ValueError(f"foundry {kind} execution_backend is mock but non-mock is required")

    failed_ids_raw = payload.get("failed_check_ids")
    failed_ids = [str(v).strip() for v in failed_ids_raw if str(v).strip()] if isinstance(failed_ids_raw, list) else []
    if len(failed_ids) != len(set(failed_ids)):
        raise ValueError(f"foundry {kind} failed_check_ids has duplicates")
    if status == "fail" and not failed_ids:
        raise ValueError(f"foundry {kind} status is fail but failed_check_ids is empty")
    if kind == "drc":
        raw_rule_results = payload.get("rule_results")
        if not isinstance(raw_rule_results, dict):
            raise ValueError("foundry drc rule_results must be an object")

        missing_rule_ids = [rule_id for rule_id in _MANDATORY_DRC_RULE_IDS if rule_id not in raw_rule_results]
        if missing_rule_ids:
            raise ValueError(f"foundry drc missing mandatory rule_results: {missing_rule_ids}")

        failed_rule_result_ids: list[str] = []
        for rule_id in _MANDATORY_DRC_RULE_IDS:
            raw_result = raw_rule_results.get(rule_id)
            if not isinstance(raw_result, dict):
                raise ValueError(f"foundry drc rule_results[{rule_id!r}] must be an object")
            rule_status = str(raw_result.get("status", "")).strip().lower()
            if rule_status not in {"pass", "fail", "error"}:
                raise ValueError(f"foundry drc rule_results[{rule_id!r}].status is invalid: {rule_status!r}")
            if rule_status == "fail":
                failed_rule_result_ids.append(rule_id)

        failed_ids_set = sorted(set(failed_ids), key=lambda t: (t.lower(), t))
        failed_rule_result_ids = sorted(failed_rule_result_ids, key=lambda t: (t.lower(), t))
        if failed_ids_set != failed_rule_result_ids:
            raise ValueError(
                "foundry drc failed_check_ids must match failed rule_results "
                f"(failed_check_ids={failed_ids_set}, failed_rule_results={failed_rule_result_ids})"
            )
        if status == "pass" and failed_rule_result_ids:
            raise ValueError("foundry drc status is pass but rule_results contain failed rules")
        if status == "fail" and not failed_rule_result_ids:
            raise ValueError("foundry drc status is fail but rule_results has no failed rules")

    return {
        "kind": kind,
        "path": str(summary_path),
        "status": status,
        "execution_backend": backend,
        "failed_check_ids": failed_ids,
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    report_path = args.report_path if args.report_path.is_absolute() else (repo_root / args.report_path)
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    run_dir = args.run_dir if args.run_dir.is_absolute() else (repo_root / args.run_dir)
    run_dir = run_dir.resolve()
    required_artifacts = list(args.required_artifact or DEFAULT_REQUIRED_ARTIFACTS)

    waiver_file = None
    if args.waiver_file is not None:
        waiver_file = args.waiver_file if args.waiver_file.is_absolute() else (repo_root / args.waiver_file)
        waiver_file = waiver_file.resolve()

    foundry_summary_rel = {
        "drc": str(args.drc_summary_rel),
        "lvs": str(args.lvs_summary_rel),
        "pex": str(args.pex_summary_rel),
    }

    if args.dry_run:
        print("[dry-run] PIC tapeout gate plan")
        print(f"- run_dir: {run_dir}")
        print(f"- required_artifacts: {len(required_artifacts)}")
        for rel in required_artifacts:
            print(f"  - {rel}")
        print(f"- run_pic_gate: {bool(args.run_pic_gate)}")
        print(f"- pic_gate_args: {str(args.pic_gate_args)}")
        print(f"- require_foundry_signoff: {bool(args.require_foundry_signoff)}")
        if bool(args.require_foundry_signoff):
            print("- foundry_summary_rel:")
            print(f"  - drc: {foundry_summary_rel['drc']}")
            print(f"  - lvs: {foundry_summary_rel['lvs']}")
            print(f"  - pex: {foundry_summary_rel['pex']}")
            print(f"- allow_waived_failures: {bool(args.allow_waived_failures)}")
            print(f"- require_non_mock_backend: {bool(args.require_non_mock_backend)}")
        print(f"- waiver_file: {waiver_file}")
        print(f"- report_path: {report_path}")
        return 0

    checks: list[dict[str, Any]] = []
    waiver_result: dict[str, Any] | None = None

    def _check_required_artifacts() -> dict[str, Any]:
        if not run_dir.exists() or not run_dir.is_dir():
            raise RuntimeError(f"run_dir does not exist or is not a directory: {run_dir}")
        missing: list[str] = []
        present: list[str] = []
        for rel in required_artifacts:
            path = (run_dir / rel).resolve()
            if path.exists():
                present.append(rel)
            else:
                missing.append(rel)
        if missing:
            raise RuntimeError(f"required artifacts missing ({len(missing)}): {missing}")
        return {
            "run_dir": str(run_dir),
            "required_count": len(required_artifacts),
            "present": present,
        }

    _run_check("required_artifacts", _check_required_artifacts, checks)

    if bool(args.run_pic_gate):

        def _check_pic_gate() -> dict[str, Any]:
            script_path = (repo_root / "scripts" / "check_pic_gate.py").resolve()
            if not script_path.exists():
                raise RuntimeError(f"PIC gate script not found: {script_path}")

            cmd = [sys.executable, str(script_path), *shlex.split(str(args.pic_gate_args))]
            completed = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                stdout_tail = (completed.stdout or "")[-1200:]
                stderr_tail = (completed.stderr or "")[-1200:]
                raise RuntimeError(
                    f"check_pic_gate.py failed ({completed.returncode}). "
                    f"stdout={stdout_tail} stderr={stderr_tail}"
                )
            return {
                "command": cmd,
                "returncode": int(completed.returncode),
            }

        _run_check("pic_gate", _check_pic_gate, checks)

    if waiver_file is not None:

        def _check_waivers() -> dict[str, Any]:
            nonlocal waiver_result
            result = load_and_validate_pic_waivers(waiver_file)
            waiver_result = result
            if not bool(result.get("ok", False)):
                summary_raw = result.get("summary")
                summary: dict[str, Any] = summary_raw if isinstance(summary_raw, dict) else {}
                issues_raw = result.get("issues")
                issues: list[Any] = issues_raw if isinstance(issues_raw, list) else []
                raise RuntimeError(
                    "waiver validation failed "
                    f"(active={summary.get('active', 0)}, expired={summary.get('expired', 0)}, "
                    f"invalid={summary.get('invalid', 0)}): {issues[:5]}"
                )
            return {
                "path": str(waiver_file),
                "summary": result.get("summary"),
                "active_rule_ids": result.get("active_rule_ids"),
            }

        _run_check("waivers", _check_waivers, checks)

    if bool(args.require_foundry_signoff):

        def _check_foundry_signoff() -> dict[str, Any]:
            nonlocal waiver_result

            rows: list[dict[str, Any]] = []
            failing_by_kind: dict[str, list[str]] = {}
            for kind in ("drc", "lvs", "pex"):
                rel = foundry_summary_rel[kind]
                path = (run_dir / rel).resolve()
                row = _validate_foundry_summary(
                    kind=kind,
                    summary_path=path,
                    require_non_mock_backend=bool(args.require_non_mock_backend),
                )
                rows.append(row)
                if row["status"] == "error":
                    raise RuntimeError(f"foundry {kind} status is error")
                if row["status"] == "fail":
                    failing_by_kind[kind] = list(row.get("failed_check_ids") or [])

            waived: dict[str, list[str]] = {}
            unresolved: dict[str, list[str]] = {}
            if failing_by_kind:
                if not bool(args.allow_waived_failures):
                    raise RuntimeError(f"foundry signoff has fail statuses: {failing_by_kind}")
                if waiver_file is None:
                    raise RuntimeError("--allow-waived-failures requires --waiver-file")

                if waiver_result is None:
                    waiver_result = load_and_validate_pic_waivers(waiver_file)
                if not bool(waiver_result.get("ok", False)):
                    raise RuntimeError("waiver validation failed; cannot apply waivers")
                active_rule_ids = set(str(v) for v in (waiver_result.get("active_rule_ids") or []))

                for kind, failed_ids in failing_by_kind.items():
                    waived_ids: list[str] = []
                    unresolved_ids: list[str] = []
                    for rid in failed_ids:
                        if str(rid) in active_rule_ids:
                            waived_ids.append(str(rid))
                        else:
                            unresolved_ids.append(str(rid))
                    if waived_ids:
                        waived[kind] = waived_ids
                    if unresolved_ids:
                        unresolved[kind] = unresolved_ids

                if unresolved:
                    raise RuntimeError(f"unwaived foundry failures remain: {unresolved}")

            return {
                "summaries": rows,
                "failing_checks": failing_by_kind,
                "waived_checks": waived,
            }

        _run_check("foundry_signoff", _check_foundry_signoff, checks)

    all_passed = all(bool(item.get("passed")) for item in checks)
    report = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_tapeout_gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "required_artifacts": required_artifacts,
        "checks": checks,
        "all_passed": bool(all_passed),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"PIC tapeout gate report: {report_path}")
    print(f"PIC tapeout gate: {'PASS' if all_passed else 'FAIL'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
