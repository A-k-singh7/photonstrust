#!/usr/bin/env python3
"""Run local foundry DRC/LVS/PEX smoke checks through sealed generic CLI lanes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.layout.pic.foundry_lvs_sealed import run_foundry_lvs_sealed
from photonstrust.layout.pic.foundry_pex_sealed import run_foundry_pex_sealed


STAGES = ("drc", "lvs", "pex")

STAGE_RUNNERS = {
    "drc": run_foundry_drc_sealed,
    "lvs": run_foundry_lvs_sealed,
    "pex": run_foundry_pex_sealed,
}

STAGE_LOCAL_BACKENDS = {
    "drc": "local_rules",
    "lvs": "local_lvs",
    "pex": "local_pex",
}

STAGE_DEFAULT_CHECKS = {
    "drc": ("DRC.SMOKE.DEFAULT", "drc_smoke_default"),
    "lvs": ("LVS.SMOKE.DEFAULT", "lvs_smoke_default"),
    "pex": ("PEX.SMOKE.DEFAULT", "pex_smoke_default"),
}

STAGE_DRC_STUB_RULE_CHECKS = (
    ("DRC.WG.MIN_WIDTH", "wg_min_width"),
    ("DRC.WG.MIN_SPACING", "wg_min_spacing"),
    ("DRC.WG.MIN_BEND_RADIUS", "wg_min_bend_radius"),
    ("DRC.WG.MIN_ENCLOSURE", "wg_min_enclosure"),
)

RUN_DIR_CONTEXT_PATHS = {
    "graph": (Path("inputs/graph.json"), Path("graph.json")),
    "routes": (Path("inputs/routes.json"), Path("routes.json")),
    "ports": (Path("inputs/ports.json"), Path("ports.json")),
    "pdk": (Path("pdk_manifest.json"), Path("inputs/pdk_manifest.json"), Path("pdk.json")),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PhotonTrust local foundry smoke harness")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/foundry_smoke/foundry_smoke_report.json"),
        help="Path for machine-readable foundry smoke report JSON",
    )
    parser.add_argument(
        "--deck-fingerprint",
        default="sha256:foundry-smoke-open-core",
        help="Synthetic or real deck fingerprint label (never deck content)",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=20.0,
        help="Per-stage generic CLI timeout in seconds",
    )
    parser.add_argument(
        "--runner-config",
        type=Path,
        default=None,
        help="Optional local JSON file with stage generic_cli contracts",
    )
    parser.add_argument(
        "--use-local-backend",
        action="store_true",
        help=(
            "Use local sealed backends from layout run directory context "
            "(drc=local_rules, lvs=local_lvs, pex=local_pex)"
        ),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Layout run directory for --use-local-backend (defaults to current working directory)",
    )
    parser.add_argument(
        "--fail-stage",
        choices=["none", *STAGES],
        default="none",
        help="In stub mode, force one stage into fail status",
    )
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit non-zero when overall status is fail/error (default: true)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    parser.add_argument(
        "--allow-ci",
        action="store_true",
        help="Allow execution when CI environment variable is truthy",
    )
    return parser.parse_args()


def _is_truthy_env(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_json_value(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = _load_json_value(path)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _load_runner_config(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"runner-config file not found: {path}")

    payload = _load_json_object(path)
    raw_stages = payload.get("stages") if isinstance(payload.get("stages"), dict) else payload
    if not isinstance(raw_stages, dict):
        raise ValueError("runner-config must be an object or contain object key 'stages'")

    out: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        stage_raw = raw_stages.get(stage)
        if not isinstance(stage_raw, dict):
            raise ValueError(f"runner-config missing object for stage '{stage}'")

        nested = stage_raw.get("generic_cli")
        if isinstance(nested, dict):
            cli_payload: dict[str, Any] = dict(nested)
        else:
            cli_payload = dict(stage_raw)

        if "command" not in cli_payload and isinstance(stage_raw.get("generic_cli_command"), list):
            cli_payload["command"] = stage_raw.get("generic_cli_command")
        if "timeout_s" not in cli_payload and stage_raw.get("generic_cli_timeout_sec") is not None:
            cli_payload["timeout_s"] = stage_raw.get("generic_cli_timeout_sec")
        if "cwd" not in cli_payload and isinstance(stage_raw.get("generic_cli_cwd"), str):
            cli_payload["cwd"] = stage_raw.get("generic_cli_cwd")
        if "env" not in cli_payload and isinstance(stage_raw.get("generic_cli_env"), dict):
            cli_payload["env"] = stage_raw.get("generic_cli_env")

        command = cli_payload.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
            raise ValueError(f"runner-config stage '{stage}' has invalid generic_cli command")

        out[stage] = cli_payload

    return out


def _resolve_run_dir(path: Path | None) -> Path:
    if path is None:
        return Path.cwd().resolve()
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def _load_optional_run_context_json(run_dir: Path, rel_paths: tuple[Path, ...]) -> Any | None:
    for rel_path in rel_paths:
        candidate = (run_dir / rel_path).resolve()
        if candidate.exists() and candidate.is_file():
            return _load_json_value(candidate)
    return None


def _context_locations(name: str) -> str:
    rel_paths = RUN_DIR_CONTEXT_PATHS[name]
    return ", ".join(str(path).replace("\\", "/") for path in rel_paths)


def _as_named_object(payload: Any, *, key: str) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return dict(payload)
    if isinstance(payload, list):
        return {key: payload}
    return None


def _required_named_rows(payload: Any, *, key: str, label: str) -> list[Any]:
    rows: list[Any] | None = None
    if isinstance(payload, list):
        rows = list(payload)
    elif isinstance(payload, dict) and isinstance(payload.get(key), list):
        rows = list(payload.get(key) or [])

    if rows is None:
        raise ValueError(
            f"local run-dir context invalid: {label} must be a JSON list or object.{key} list at one of: "
            f"{_context_locations(label)}"
        )
    if len(rows) == 0:
        raise ValueError(
            f"local run-dir context invalid: {label} must be non-empty at one of: {_context_locations(label)}"
        )
    return rows


def _extract_pdk_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    nested = payload.get("pdk")
    if isinstance(nested, dict):
        return dict(nested)
    return dict(payload)


def _build_local_stage_requests(run_dir: Path) -> dict[str, dict[str, Any]]:
    graph_raw = _load_optional_run_context_json(run_dir, RUN_DIR_CONTEXT_PATHS["graph"])
    routes_raw = _load_optional_run_context_json(run_dir, RUN_DIR_CONTEXT_PATHS["routes"])
    ports_raw = _load_optional_run_context_json(run_dir, RUN_DIR_CONTEXT_PATHS["ports"])
    pdk_raw = _load_optional_run_context_json(run_dir, RUN_DIR_CONTEXT_PATHS["pdk"])

    if not isinstance(graph_raw, dict):
        raise ValueError(
            f"local run-dir context invalid: graph must be a JSON object at one of: {_context_locations('graph')}"
        )
    graph = dict(graph_raw)
    routes_rows = _required_named_rows(routes_raw, key="routes", label="routes")
    ports_rows = _required_named_rows(ports_raw, key="ports", label="ports")
    if not isinstance(pdk_raw, dict):
        raise ValueError(
            "local run-dir context invalid: pdk manifest must be a JSON object at one of: "
            f"{_context_locations('pdk')}"
        )

    routes_for_drc_pex: dict[str, Any] | list[Any]
    routes_for_lvs: dict[str, Any]
    if isinstance(routes_raw, dict):
        routes_for_drc_pex = dict(routes_raw)
        routes_for_lvs = dict(routes_raw)
    else:
        routes_for_drc_pex = list(routes_rows)
        routes_for_lvs = {"routes": list(routes_rows)}

    ports: dict[str, Any]
    if isinstance(ports_raw, dict):
        ports = dict(ports_raw)
    else:
        ports = {"ports": list(ports_rows)}

    pdk = _extract_pdk_payload(pdk_raw)
    if pdk is None:
        raise ValueError(
            "local run-dir context invalid: pdk manifest must be a JSON object at one of: "
            f"{_context_locations('pdk')}"
        )

    drc_request: dict[str, Any] = {
        "backend": STAGE_LOCAL_BACKENDS["drc"],
        "routes": routes_for_drc_pex,
        "pdk": pdk,
    }
    lvs_request: dict[str, Any] = {
        "backend": STAGE_LOCAL_BACKENDS["lvs"],
        "graph": graph,
        "routes": routes_for_lvs,
        "ports": ports,
    }
    pex_request: dict[str, Any] = {
        "backend": STAGE_LOCAL_BACKENDS["pex"],
        "graph": graph,
        "routes": routes_for_drc_pex,
        "pdk": pdk,
    }

    return {
        "drc": drc_request,
        "lvs": lvs_request,
        "pex": pex_request,
    }


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    counts_raw = summary.get("check_counts")
    counts = counts_raw if isinstance(counts_raw, dict) else {}
    failed_ids_raw = summary.get("failed_check_ids")
    failed_names_raw = summary.get("failed_check_names")
    return {
        "run_id": str(summary.get("run_id", "")),
        "status": str(summary.get("status", "")).strip().lower(),
        "execution_backend": str(summary.get("execution_backend", "")).strip().lower(),
        "check_counts": {
            "total": int(counts.get("total", 0)),
            "passed": int(counts.get("passed", 0)),
            "failed": int(counts.get("failed", 0)),
            "errored": int(counts.get("errored", 0)),
        },
        "failed_check_ids": [str(v).strip() for v in failed_ids_raw if str(v).strip()] if isinstance(failed_ids_raw, list) else [],
        "failed_check_names": [str(v).strip() for v in failed_names_raw if str(v).strip()] if isinstance(failed_names_raw, list) else [],
        "error_code": str(summary.get("error_code")) if summary.get("error_code") is not None else None,
        "deck_fingerprint": str(summary.get("deck_fingerprint")) if summary.get("deck_fingerprint") is not None else None,
    }


def _derive_overall_status(stages: dict[str, dict[str, Any]]) -> str:
    statuses = [str((stages.get(stage) or {}).get("status", "")).strip().lower() for stage in STAGES]
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "fail" for status in statuses):
        return "fail"
    return "pass"


def _build_stub_generic_cli(stage: str, *, summary_path: Path, fail_stage: str, timeout_sec: float) -> dict[str, Any]:
    check_id, check_name = STAGE_DEFAULT_CHECKS[stage]
    checks: list[dict[str, str]]
    if stage == "drc":
        checks = [
            {"id": rule_id, "name": rule_name, "status": "clean"}
            for rule_id, rule_name in STAGE_DRC_STUB_RULE_CHECKS
        ]
        if stage == fail_stage:
            checks[0]["status"] = "violation"
    else:
        check_status = "violation" if stage == fail_stage else "clean"
        checks = [{"id": check_id, "name": check_name, "status": check_status}]
    script = (
        "import json, pathlib, sys; "
        "out = pathlib.Path(sys.argv[1]); "
        f"payload = {{'checks':{checks!r}}}; "
        "out.write_text(json.dumps(payload), encoding='utf-8')"
    )
    return {
        "command": [sys.executable, "-c", script, "{summary_json_path}"],
        "timeout_s": float(timeout_sec),
        "summary_json_path": "{stage_summary}",
        "output_paths": {"stage_summary": str(summary_path)},
        "check_status_map": {"clean": "pass", "violation": "fail"},
    }


def _print_plan(
    *,
    output_json: Path,
    mode: str,
    strict: bool,
    fail_stage: str,
    deck_fingerprint: str,
    timeout_sec: float,
    runner_config: Path | None,
    run_dir: Path | None,
    use_local_backend: bool,
) -> None:
    print("[dry-run] foundry smoke plan")
    print(f"- mode: {mode}")
    print(f"- output_json: {output_json}")
    print(f"- strict: {strict}")
    print(f"- fail_stage: {fail_stage}")
    print(f"- deck_fingerprint: {deck_fingerprint}")
    print(f"- timeout_sec: {timeout_sec}")
    print(f"- runner_config: {runner_config}")
    print(f"- use_local_backend: {use_local_backend}")
    print(f"- run_dir: {run_dir}")
    print(f"- stages: {', '.join(STAGES)}")


def _run_stage(stage: str, *, deck_fingerprint: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    if stage not in STAGE_RUNNERS:
        raise RuntimeError(f"unsupported stage: {stage}")
    runner = STAGE_RUNNERS[stage]
    request = dict(request_payload)
    if "deck_fingerprint" not in request:
        request["deck_fingerprint"] = deck_fingerprint
    summary = runner(
        request
    )
    if not isinstance(summary, dict):
        raise RuntimeError(f"runner returned non-object summary for stage: {stage}")
    return summary


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if _is_truthy_env(os.environ.get("CI")) and not bool(args.allow_ci):
        print("foundry_smoke: local-only script refused in CI (use --allow-ci to override)")
        return 2

    output_json = args.output_json if args.output_json.is_absolute() else (repo_root / args.output_json)
    output_json = output_json.resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)

    timeout_sec = float(args.timeout_sec)
    if timeout_sec <= 0:
        timeout_sec = 20.0

    runner_config_path: Path | None = None
    run_dir_path: Path | None = None
    mode = "stub"
    stage_payloads: dict[str, dict[str, Any]] = {}
    stage_requests: dict[str, dict[str, Any]]

    try:
        if bool(args.use_local_backend) and args.runner_config is not None:
            raise ValueError("--use-local-backend cannot be combined with --runner-config")

        if bool(args.use_local_backend):
            run_dir_path = _resolve_run_dir(args.run_dir)
            if not run_dir_path.exists() or not run_dir_path.is_dir():
                raise FileNotFoundError(f"run-dir does not exist or is not a directory: {run_dir_path}")
            stage_requests = _build_local_stage_requests(run_dir_path)
            mode = "local"
        elif args.runner_config is not None:
            runner_config_path = args.runner_config if args.runner_config.is_absolute() else (repo_root / args.runner_config)
            runner_config_path = runner_config_path.resolve()
            stage_payloads = _load_runner_config(runner_config_path)
            mode = "config"
            stage_requests = {}
        else:
            stage_requests = {}
    except Exception as exc:
        print(f"foundry_smoke error: {exc}")
        return 1

    if args.dry_run:
        _print_plan(
            output_json=output_json,
            mode=mode,
            strict=bool(args.strict),
            fail_stage=str(args.fail_stage),
            deck_fingerprint=str(args.deck_fingerprint),
            timeout_sec=timeout_sec,
            runner_config=runner_config_path,
            run_dir=run_dir_path,
            use_local_backend=bool(args.use_local_backend),
        )
        return 0

    if mode == "stub":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        scratch_dir = (output_json.parent / f"_foundry_smoke_{stamp}").resolve()
        scratch_dir.mkdir(parents=True, exist_ok=True)
        fail_stage = str(args.fail_stage)
        for stage in STAGES:
            stage_summary_path = scratch_dir / f"{stage}_summary.json"
            stage_payloads[stage] = _build_stub_generic_cli(
                stage,
                summary_path=stage_summary_path,
                fail_stage=fail_stage,
                timeout_sec=timeout_sec,
            )
    if mode in {"stub", "config"}:
        stage_requests = {}
        for stage in STAGES:
            cli_payload = dict(stage_payloads.get(stage, {}))
            if "timeout_s" not in cli_payload:
                cli_payload["timeout_s"] = timeout_sec
            stage_requests[stage] = {
                "backend": "generic_cli",
                "generic_cli": cli_payload,
            }

    stage_summaries: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        stage_request = dict(stage_requests.get(stage, {}))
        requested_backend = str(stage_request.get("backend") or "").strip().lower() or "generic_cli"
        if requested_backend == "generic_cli":
            raw_cli_payload = stage_request.get("generic_cli")
            cli_payload = dict(raw_cli_payload) if isinstance(raw_cli_payload, dict) else {}
            if "timeout_s" not in cli_payload:
                cli_payload["timeout_s"] = timeout_sec
            stage_request["generic_cli"] = cli_payload
            stage_request["backend"] = "generic_cli"

        try:
            summary = _run_stage(stage, deck_fingerprint=str(args.deck_fingerprint), request_payload=stage_request)
        except Exception as exc:
            print(f"foundry_smoke error: stage={stage} {exc}")
            summary = {
                "run_id": "",
                "status": "error",
                "execution_backend": requested_backend,
                "check_counts": {"total": 0, "passed": 0, "failed": 0, "errored": 0},
                "failed_check_ids": [],
                "failed_check_names": [],
                "error_code": "smoke_stage_exception",
                "deck_fingerprint": str(args.deck_fingerprint),
            }
        stage_summaries[stage] = _normalize_summary(summary)

    overall_status = _derive_overall_status(stage_summaries)
    report = {
        "schema_version": "0.1",
        "kind": "photonstrust.foundry_real_backend_smoke",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "strict": bool(args.strict),
        "overall_status": overall_status,
        "deck_fingerprint": str(args.deck_fingerprint),
        "stages": stage_summaries,
    }
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        "foundry_smoke "
        f"drc={stage_summaries['drc'].get('status')} "
        f"lvs={stage_summaries['lvs'].get('status')} "
        f"pex={stage_summaries['pex'].get('status')} "
        f"overall={overall_status}"
    )
    print(f"report_path: {output_json}")

    if overall_status == "pass":
        return 0
    if bool(args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
