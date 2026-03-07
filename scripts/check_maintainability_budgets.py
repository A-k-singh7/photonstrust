#!/usr/bin/env python3
"""Check Phase 0 maintainability line budgets against the local repo tree."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_config_path() -> Path:
    return _repo_root() / "configs" / "maintainability" / "phase0_refactor_budgets.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check maintainability line budgets")
    parser.add_argument(
        "--config",
        type=Path,
        default=_default_config_path(),
        help="Path to a maintainability budget policy JSON file",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root(),
        help="Repository root used for glob resolution",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write the computed report JSON",
    )
    return parser.parse_args()


def _read_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("maintainability budget policy must be a JSON object")
    budgets = payload.get("budgets")
    if not isinstance(budgets, list) or not budgets:
        raise ValueError("maintainability budget policy requires a non-empty 'budgets' list")
    return payload


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def _normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _resolve_matches(repo_root: Path, include_glob: str, exclude_globs: list[str]) -> list[Path]:
    include_matches = {
        path.resolve(): path
        for path in repo_root.glob(include_glob)
        if path.is_file()
    }
    excluded = {
        path.resolve()
        for pattern in exclude_globs
        for path in repo_root.glob(pattern)
        if path.is_file()
    }
    kept = [path for resolved, path in include_matches.items() if resolved not in excluded]
    kept.sort(key=lambda item: item.as_posix())
    return kept


def _relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _evaluate_budget(repo_root: Path, raw_budget: dict[str, Any], *, index: int) -> dict[str, Any]:
    if not isinstance(raw_budget, dict):
        raise ValueError(f"budget entry {index} must be an object")

    label = str(raw_budget.get("label") or f"budget_{index}").strip()
    include_glob = str(raw_budget.get("include_glob") or "").strip()
    if not include_glob:
        raise ValueError(f"budget '{label}' is missing include_glob")

    max_lines = int(raw_budget.get("max_lines") or 0)
    if max_lines < 1:
        raise ValueError(f"budget '{label}' must set max_lines >= 1")

    allow_zero_matches = bool(raw_budget.get("allow_zero_matches", False))
    exclude_globs = _normalize_str_list(raw_budget.get("exclude_globs"))
    matches = _resolve_matches(repo_root, include_glob, exclude_globs)

    rows = []
    offending_rows = []
    for path in matches:
        lines = _count_lines(path)
        row = {
            "path": _relative_path(repo_root, path),
            "lines": lines,
            "ok": lines <= max_lines,
        }
        rows.append(row)
        if not row["ok"]:
            offending_rows.append(row)

    missing_match = not matches and not allow_zero_matches
    ok = not missing_match and not offending_rows
    observed_max_lines = max((row["lines"] for row in rows), default=0)

    return {
        "label": label,
        "description": str(raw_budget.get("description") or "").strip(),
        "include_glob": include_glob,
        "exclude_globs": exclude_globs,
        "max_lines": max_lines,
        "allow_zero_matches": allow_zero_matches,
        "matched_file_count": len(rows),
        "observed_max_lines": observed_max_lines,
        "ok": ok,
        "missing_match": missing_match,
        "files": rows,
        "offending_files": offending_rows,
    }


def _build_report(policy: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    budgets = [
        _evaluate_budget(repo_root, budget, index=index)
        for index, budget in enumerate(policy.get("budgets") or [], start=1)
    ]
    overall_ok = all(item.get("ok", False) for item in budgets)
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.maintainability_budget_report",
        "policy_kind": str(policy.get("kind") or ""),
        "phase": str(policy.get("phase") or ""),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root.resolve()),
        "status": {
            "overall": "pass" if overall_ok else "fail",
            "budget_count": len(budgets),
            "failed_budget_count": sum(1 for item in budgets if not item.get("ok", False)),
        },
        "budgets": budgets,
        "characterization_commands": _normalize_str_list(policy.get("characterization_commands")),
    }


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    policy_path = Path(args.config).resolve()
    policy = _read_policy(policy_path)
    report = _build_report(policy, repo_root)
    rendered = json.dumps(report, indent=2)

    if args.output_json is not None:
        output_path = Path(args.output_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    return 0 if report["status"]["overall"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
