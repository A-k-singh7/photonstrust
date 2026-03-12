#!/usr/bin/env python3
"""Apply branch protection required checks for PhotonTrust."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


REQUIRED_CHECK_PROFILES: dict[str, tuple[str, ...]] = {
    "startup-fast": (
        "ci-smoke / core-smoke",
        "ci-smoke / api-contract-smoke",
        "security-baseline / pip-audit-runtime",
    ),
    "strict": (
        "ci-smoke / core-smoke",
        "ci-smoke / api-contract-smoke",
        "Web Playwright Tests / playwright-ui",
        "cv-quick-verify / verify",
        "cv-quick-verify / Tapeout Gate Final",
        "security-baseline / pip-audit-runtime",
        "security-baseline / web-determinism-and-audit",
    ),
}
DEFAULT_PROFILE = "startup-fast"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply GitHub branch protection required checks")
    parser.add_argument("--repo", required=True, help="Repository slug in owner/repo format")
    parser.add_argument("--branch", default="main", help="Protected branch name")
    parser.add_argument(
        "--profile",
        choices=sorted(REQUIRED_CHECK_PROFILES),
        default=DEFAULT_PROFILE,
        help="Required check profile (default: startup-fast)",
    )
    parser.add_argument(
        "--required-check",
        dest="required_checks",
        action="append",
        default=None,
        help="Required status check context. Repeat for multiple checks.",
    )
    parser.add_argument(
        "--required-approvals",
        type=int,
        default=1,
        help="Minimum approving reviews required before merge",
    )
    parser.add_argument(
        "--enforce-admins",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply branch protection to admins",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply protection (default is dry-run with payload output)",
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Verify required checks after apply",
    )
    parser.add_argument("--output-payload", type=Path, default=None, help="Optional payload JSON output path")
    return parser.parse_args()


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _resolve_required_checks(profile: str, cli_checks: list[str] | None) -> list[str]:
    if cli_checks:
        return _unique_ordered(list(cli_checks))
    return _unique_ordered(list(REQUIRED_CHECK_PROFILES[str(profile)]))


def _build_payload(*, required_checks: list[str], approvals: int, enforce_admins: bool) -> dict[str, Any]:
    contexts = [{"context": item} for item in required_checks]
    return {
        "required_status_checks": {
            "strict": True,
            "checks": contexts,
        },
        "enforce_admins": bool(enforce_admins),
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": max(1, int(approvals)),
            "require_last_push_approval": False,
        },
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,
        "lock_branch": False,
        "allow_fork_syncing": True,
    }


def _gh_api_json(command: list[str], *, stdin_json: dict[str, Any] | None = None) -> dict[str, Any]:
    input_text = json.dumps(stdin_json) if stdin_json is not None else None
    proc = subprocess.run(command, input=input_text, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"gh api failed ({proc.returncode}): {stderr}")

    stdout = (proc.stdout or "").strip()
    if not stdout:
        return {}
    payload = json.loads(stdout)
    if isinstance(payload, dict):
        return payload
    return {}


def _put_branch_protection(*, repo: str, branch: str, payload: dict[str, Any]) -> dict[str, Any]:
    command = [
        "gh",
        "api",
        "--method",
        "PUT",
        f"repos/{repo}/branches/{branch}/protection",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        "--input",
        "-",
    ]
    return _gh_api_json(command, stdin_json=payload)


def _get_branch_protection(*, repo: str, branch: str) -> dict[str, Any]:
    command = [
        "gh",
        "api",
        f"repos/{repo}/branches/{branch}/protection",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    return _gh_api_json(command)


def _current_contexts(payload: dict[str, Any]) -> set[str]:
    required_obj = payload.get("required_status_checks")
    required = required_obj if isinstance(required_obj, dict) else {}

    checks_obj = required.get("checks")
    checks = checks_obj if isinstance(checks_obj, list) else []
    contexts: set[str] = set()
    for row in checks:
        if not isinstance(row, dict):
            continue
        context = row.get("context")
        if isinstance(context, str) and context.strip():
            contexts.add(context.strip())

    if contexts:
        return contexts

    legacy_obj = required.get("contexts")
    legacy_contexts = legacy_obj if isinstance(legacy_obj, list) else []
    for item in legacy_contexts:
        if isinstance(item, str) and item.strip():
            contexts.add(item.strip())
    return contexts


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else (Path.cwd() / path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    required_checks = _resolve_required_checks(str(args.profile), args.required_checks)
    payload = _build_payload(
        required_checks=required_checks,
        approvals=int(args.required_approvals),
        enforce_admins=bool(args.enforce_admins),
    )

    if args.output_payload is not None:
        _write_payload(args.output_payload, payload)

    if not bool(args.apply):
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "repo": args.repo,
                    "branch": args.branch,
                    "profile": args.profile,
                    "required_checks": required_checks,
                    "payload": payload,
                },
                separators=(",", ":"),
            )
        )
        return 0

    _put_branch_protection(repo=str(args.repo), branch=str(args.branch), payload=payload)

    missing_checks: list[str] = []
    observed_checks: list[str] = []
    if bool(args.verify):
        current = _get_branch_protection(repo=str(args.repo), branch=str(args.branch))
        observed = _current_contexts(current)
        observed_checks = sorted(observed)
        missing_checks = [item for item in required_checks if item not in observed]

    print(
        json.dumps(
            {
                "dry_run": False,
                "repo": args.repo,
                "branch": args.branch,
                "profile": args.profile,
                "required_checks": required_checks,
                "observed_checks": observed_checks,
                "missing_checks": missing_checks,
                "verified": bool(args.verify),
                "ok": len(missing_checks) == 0,
            },
            separators=(",", ":"),
        )
    )
    return 0 if not missing_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
