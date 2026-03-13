"""Run multi-scenario GA replay checks and emit summary artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REPLAY_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "demo1_quick_smoke",
        "configs/quickstart/qkd_quick_smoke.yml",
        "results/ga_release/replay_matrix/demo1_quick_smoke",
    ),
    (
        "demo1_matrix_full",
        "configs/demo1_matrix_full.yml",
        "results/ga_release/replay_matrix/demo1_matrix_full",
    ),
)


def run_replay_case(
    *,
    repo_root: Path,
    case_id: str,
    config_path: Path,
    output_path: Path,
    timeout_seconds: float,
) -> dict:
    started = time.perf_counter()
    cmd = [
        sys.executable,
        "-m",
        "photonstrust.cli",
        "run",
        str(config_path),
        "--output",
        str(output_path),
    ]

    completed = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    elapsed = time.perf_counter() - started
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    run_registry = output_path / "run_registry.json"
    run_registry_exists = run_registry.exists()
    run_registry_rows = 0
    if run_registry_exists:
        try:
            payload = json.loads(run_registry.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                run_registry_rows = len(payload)
        except Exception:
            run_registry_rows = 0

    return {
        "case_id": case_id,
        "config_path": str(config_path).replace("\\", "/"),
        "output_path": str(output_path).replace("\\", "/"),
        "returncode": int(completed.returncode),
        "elapsed_seconds": float(elapsed),
        "run_registry_exists": bool(run_registry_exists),
        "run_registry_rows": int(run_registry_rows),
        "ok": bool(completed.returncode == 0 and run_registry_exists),
        "stdout": stdout,
        "stderr": stderr,
    }


def run_ga_replay_matrix(
    repo_root: Path,
    *,
    timeout_seconds: float,
    cases: tuple[tuple[str, str, str], ...] = DEFAULT_REPLAY_CASES,
) -> dict:
    results: list[dict] = []
    for case_id, cfg, out in cases:
        config_path = Path(cfg) if Path(cfg).is_absolute() else (repo_root / cfg)
        output_path = Path(out) if Path(out).is_absolute() else (repo_root / out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results.append(
            run_replay_case(
                repo_root=repo_root,
                case_id=case_id,
                config_path=config_path,
                output_path=output_path,
                timeout_seconds=timeout_seconds,
            )
        )

    ok = all(bool(row.get("ok", False)) for row in results)
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.ga_replay_matrix",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "ok": bool(ok),
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GA replay matrix checks.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Per-case timeout in seconds (default: 180).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/specs/milestones/ga_replay_matrix_2026-02-16.json"),
        help="Path to write replay matrix summary JSON.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    summary = run_ga_replay_matrix(repo_root, timeout_seconds=float(args.timeout))
    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if bool(summary.get("ok", False)):
        print("GA replay matrix: PASS")
        print(str(output_path))
        return 0

    print("GA replay matrix: FAIL")
    for row in summary.get("cases") or []:
        if bool(row.get("ok", False)):
            continue
        print(f" - case failed: {row.get('case_id')}")
    print(str(output_path))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
