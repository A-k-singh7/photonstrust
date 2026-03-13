from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_runtime_environment import (
    check_isolated_environment,
    check_locked_versions,
    parse_lock_file,
)
from scripts.production_readiness_check import build_command_plan


def test_parse_lock_file_accepts_pinned_requirements(tmp_path: Path) -> None:
    lock_path = tmp_path / "runtime.lock.txt"
    lock_path.write_text(
        "\n".join(
            [
                "# comment",
                "numpy==2.3.2",
                "PyYAML==6.0.2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    parsed = parse_lock_file(lock_path)
    assert parsed == {"numpy": "2.3.2", "pyyaml": "6.0.2"}


def test_parse_lock_file_rejects_unpinned_requirement(tmp_path: Path) -> None:
    lock_path = tmp_path / "runtime.lock.txt"
    lock_path.write_text("numpy>=1.0\n", encoding="utf-8")

    with pytest.raises(ValueError):
        _ = parse_lock_file(lock_path)


def test_check_locked_versions_detects_missing_and_mismatch() -> None:
    failures = check_locked_versions(
        {"numpy": "2.3.2", "pyyaml": "6.0.2"},
        installed_versions={"numpy": "2.0.0"},
    )
    assert any("numpy" in line and "installed=2.0.0" in line for line in failures)
    assert any("missing locked dependency: pyyaml==6.0.2" in line for line in failures)


def test_check_isolated_environment_requires_repo_local_venv(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    outside_failures = check_isolated_environment(
        repo_root,
        require_local_venv=True,
        active_venv=tmp_path / "external-venv",
    )
    assert any("outside repository root" in line for line in outside_failures)

    inside_failures = check_isolated_environment(
        repo_root,
        require_local_venv=True,
        active_venv=repo_root / ".venv.production",
    )
    assert inside_failures == []


def test_build_command_plan_toggles_release_packet_refresh() -> None:
    common_kwargs = {
        "python_exe": Path("python"),
        "lock_file": Path("requirements/runtime.lock.txt"),
        "smoke_config": Path("configs/quickstart/qkd_quick_smoke.yml"),
        "smoke_output": Path("results/production_readiness/runtime_smoke"),
        "include_qiskit": True,
    }
    refresh_plan = build_command_plan(refresh_release_packet=True, **common_kwargs)
    verify_plan = build_command_plan(refresh_release_packet=False, **common_kwargs)

    refresh_names = [name for name, _cmd in refresh_plan]
    verify_names = [name for name, _cmd in verify_plan]
    assert "release_packet_refresh" in refresh_names
    assert "release_packet_verify" not in refresh_names
    assert "release_packet_verify" in verify_names
    assert "release_packet_signature_verify" in verify_names


def test_build_command_plan_can_disable_qiskit_lane() -> None:
    plan_with_qiskit = build_command_plan(
        python_exe=Path("python"),
        lock_file=Path("requirements/runtime.lock.txt"),
        smoke_config=Path("configs/quickstart/qkd_quick_smoke.yml"),
        smoke_output=Path("results/production_readiness/runtime_smoke"),
        refresh_release_packet=True,
        include_qiskit=True,
    )
    plan_without_qiskit = build_command_plan(
        python_exe=Path("python"),
        lock_file=Path("requirements/runtime.lock.txt"),
        smoke_config=Path("configs/quickstart/qkd_quick_smoke.yml"),
        smoke_output=Path("results/production_readiness/runtime_smoke"),
        refresh_release_packet=True,
        include_qiskit=False,
    )

    with_names = [name for name, _cmd in plan_with_qiskit]
    without_names = [name for name, _cmd in plan_without_qiskit]
    assert "qiskit_lane" in with_names
    assert "qiskit_lane" not in without_names
