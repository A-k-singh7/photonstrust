#!/usr/bin/env python3
"""Build a deterministic PIC tapeout package directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from photonstrust.pic.tapeout_package import build_tapeout_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic PIC tapeout package")
    parser.add_argument("--run-dir", type=Path, required=True, help="Source run package directory")
    parser.add_argument("--run-id", type=str, default=None, help="Optional package run identifier")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/tapeout_packages"),
        help="Package output root directory",
    )
    parser.add_argument(
        "--signoff-ladder-path",
        type=Path,
        default=None,
        help="Optional signoff ladder JSON path (defaults to <run-dir>/signoff_ladder.json)",
    )
    parser.add_argument(
        "--waivers-path",
        type=Path,
        default=None,
        help="Optional waivers JSON path (defaults to <run-dir>/waivers.json)",
    )
    parser.add_argument(
        "--allow-missing-signoff",
        action="store_true",
        help="Generate placeholder signoff ladder when signoff JSON is missing",
    )
    parser.add_argument(
        "--allow-stub-pex",
        action="store_true",
        help="Generate stub foundry_pex_sealed_summary.json when missing",
    )
    parser.add_argument(
        "--require-foundry-approval",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require foundry_approval_sealed_summary.json verification artifact (default: true)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("results/tapeout_packages/tapeout_package_report.json"),
        help="Machine-readable report output path",
    )
    return parser.parse_args()


def _resolve_cli_path(path: Path, *, cwd: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    invocation_cwd = Path.cwd()

    run_dir = _resolve_cli_path(args.run_dir, cwd=invocation_cwd)
    output_root = _resolve_cli_path(args.output_root, cwd=invocation_cwd)

    request = {
        "run_dir": str(run_dir),
        "run_id": str(args.run_id).strip() if args.run_id else None,
        "output_root": str(output_root),
        "allow_missing_signoff": bool(args.allow_missing_signoff),
        "allow_stub_pex": bool(args.allow_stub_pex),
        "require_foundry_approval": bool(args.require_foundry_approval),
    }
    if args.signoff_ladder_path is not None:
        request["signoff_ladder_path"] = str(_resolve_cli_path(args.signoff_ladder_path, cwd=invocation_cwd))
    if args.waivers_path is not None:
        request["waivers_path"] = str(_resolve_cli_path(args.waivers_path, cwd=invocation_cwd))

    try:
        report = build_tapeout_package(request, repo_root=repo_root)
    except Exception as exc:
        print(f"tapeout package build: FAIL ({exc})")
        return 1

    report_path = _resolve_cli_path(args.report_path, cwd=invocation_cwd)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("tapeout package build: PASS")
    print(f"package_dir: {report['package_dir']}")
    print(f"manifest_path: {report['manifest_path']}")
    print(f"report_path: {str(report_path.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
