from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "apply_branch_protection.py"
    spec = importlib.util.spec_from_file_location("apply_branch_protection_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_payload_contains_required_checks() -> None:
    module = _load_script_module()
    payload = module._build_payload(  # noqa: SLF001
        required_checks=["ci-smoke / core-smoke", "ci-smoke / api-contract-smoke"],
        approvals=2,
        enforce_admins=True,
    )

    checks = payload["required_status_checks"]["checks"]
    contexts = [row["context"] for row in checks]
    assert contexts == ["ci-smoke / core-smoke", "ci-smoke / api-contract-smoke"]
    assert payload["required_pull_request_reviews"]["required_approving_review_count"] == 2
    assert payload["enforce_admins"] is True


def test_main_dry_run_writes_payload(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    payload_path = tmp_path / "branch_protection_payload.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_branch_protection.py",
            "--repo",
            "photonstrust/photonstrust",
            "--output-payload",
            str(payload_path),
        ],
    )

    assert module.main() == 0

    output = json.loads(capsys.readouterr().out.strip())
    assert output["dry_run"] is True
    assert output["profile"] == "startup-fast"
    assert output["required_checks"] == [
        "ci-smoke / core-smoke",
        "ci-smoke / api-contract-smoke",
        "security-baseline / pip-audit-runtime",
    ]
    assert payload_path.exists()
    assert payload_path.read_text(encoding="utf-8").endswith("\n")


def test_main_dry_run_strict_profile(
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_branch_protection.py",
            "--repo",
            "photonstrust/photonstrust",
            "--profile",
            "strict",
        ],
    )

    assert module.main() == 0
    output = json.loads(capsys.readouterr().out.strip())
    assert output["profile"] == "strict"
    assert output["required_checks"] == [
        "ci-smoke / core-smoke",
        "ci-smoke / api-contract-smoke",
        "Web Playwright Tests / playwright-ui",
        "cv-quick-verify / verify",
        "cv-quick-verify / Tapeout Gate Final",
        "security-baseline / pip-audit-runtime",
        "security-baseline / web-determinism-and-audit",
    ]


def test_main_dry_run_main_future_safe_profile(
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_branch_protection.py",
            "--repo",
            "photonstrust/photonstrust",
            "--profile",
            "main-future-safe",
        ],
    )

    assert module.main() == 0
    output = json.loads(capsys.readouterr().out.strip())
    assert output["profile"] == "main-future-safe"
    assert output["required_checks"] == [
        "CodeQL",
        "ci-smoke / core-smoke",
        "ci-smoke / api-contract-smoke",
        "Web Playwright Tests / playwright-ui",
        "cv-quick-verify / verify",
        "cv-quick-verify / Tapeout Gate Final",
        "security-baseline / pip-audit-runtime",
        "security-baseline / web-determinism-and-audit",
        "tapeout-gate / PIC Tapeout Gate",
    ]


def test_main_explicit_checks_override_profile(
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_branch_protection.py",
            "--repo",
            "photonstrust/photonstrust",
            "--profile",
            "strict",
            "--required-check",
            "custom / alpha",
            "--required-check",
            "custom / beta",
        ],
    )

    assert module.main() == 0
    output = json.loads(capsys.readouterr().out.strip())
    assert output["profile"] == "strict"
    assert output["required_checks"] == ["custom / alpha", "custom / beta"]


def test_main_apply_returns_nonzero_if_required_check_missing(
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    def _fake_put(*, repo: str, branch: str, payload: dict) -> dict:  # noqa: ANN001
        _ = repo, branch, payload
        return {}

    def _fake_get(*, repo: str, branch: str) -> dict:  # noqa: ANN001
        _ = repo, branch
        return {
            "required_status_checks": {
                "checks": [
                    {"context": "ci-smoke / core-smoke"},
                ]
            }
        }

    monkeypatch.setattr(module, "_put_branch_protection", _fake_put)
    monkeypatch.setattr(module, "_get_branch_protection", _fake_get)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_branch_protection.py",
            "--repo",
            "photonstrust/photonstrust",
            "--apply",
            "--required-check",
            "ci-smoke / core-smoke",
            "--required-check",
            "ci-smoke / api-contract-smoke",
        ],
    )

    assert module.main() == 1

    output = json.loads(capsys.readouterr().out.strip())
    assert output["dry_run"] is False
    assert output["ok"] is False
    assert output["missing_checks"] == ["ci-smoke / api-contract-smoke"]
