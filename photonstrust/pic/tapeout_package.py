"""Tapeout package builder for foundry handoff artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any

from photonstrust.utils import hash_dict

_DEFAULT_OUTPUT_ROOT = Path("results/tapeout_packages")
_DEFAULT_MANIFEST_NAME = "MANIFEST.sha256"
_DEFAULT_README_NAME = "README.md"
_DEFAULT_PACKAGE_MANIFEST_NAME = "tapeout_package_manifest.json"

_INPUT_SOURCES = {
    "graph.json": Path("inputs/graph.json"),
    "ports.json": Path("inputs/ports.json"),
    "routes.json": Path("inputs/routes.json"),
    "layout.gds": Path("inputs/layout.gds"),
}

_VERIFICATION_DEFAULTS = {
    "foundry_drc_sealed_summary.json": Path("foundry_drc_sealed_summary.json"),
    "foundry_lvs_sealed_summary.json": Path("foundry_lvs_sealed_summary.json"),
    "foundry_pex_sealed_summary.json": Path("foundry_pex_sealed_summary.json"),
}


def build_tapeout_package(
    request: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic tapeout package from a run directory.

    Required request fields:
      - run_dir: str path to source run package directory

    Optional request fields:
      - run_id: str package run identifier (default deterministic hash from run_dir)
      - output_root: str output root (default results/tapeout_packages)
      - signoff_ladder_path: str explicit path to signoff ladder JSON
      - waivers_path: str explicit path to waivers JSON
      - allow_missing_signoff: bool (default False)
      - allow_stub_pex: bool (default False)
    """

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    resolved_repo_root = _resolve_repo_root(repo_root)
    run_dir = _resolve_required_path(request, "run_dir", repo_root=resolved_repo_root)
    if not run_dir.exists() or not run_dir.is_dir():
        raise ValueError(f"run_dir does not exist or is not a directory: {run_dir}")

    output_root = _resolve_optional_path(request.get("output_root"), repo_root=resolved_repo_root, fallback=_DEFAULT_OUTPUT_ROOT)
    output_root.mkdir(parents=True, exist_ok=True)

    run_id = _resolve_run_id(request.get("run_id"), run_dir=run_dir)
    package_dir = output_root / f"tapeout_{run_id}"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=False)

    inputs_dir = package_dir / "inputs"
    verification_dir = package_dir / "verification"
    signoff_dir = package_dir / "signoff"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    verification_dir.mkdir(parents=True, exist_ok=True)
    signoff_dir.mkdir(parents=True, exist_ok=True)

    copied_inputs = _copy_inputs(run_dir=run_dir, inputs_dir=inputs_dir)
    copied_verification = _copy_verification(
        run_dir=run_dir,
        verification_dir=verification_dir,
        allow_stub_pex=bool(request.get("allow_stub_pex", False)),
    )
    signoff_rel = _copy_signoff(
        request=request,
        run_dir=run_dir,
        signoff_dir=signoff_dir,
        allow_missing_signoff=bool(request.get("allow_missing_signoff", False)),
    )

    readme_path = package_dir / _DEFAULT_README_NAME
    readme_path.write_text(
        _build_readme(
            run_id=run_id,
            source_run_dir=run_dir,
            copied_inputs=copied_inputs,
            copied_verification=copied_verification,
            signoff_rel=signoff_rel,
        ),
        encoding="utf-8",
    )

    package_manifest_path = package_dir / _DEFAULT_PACKAGE_MANIFEST_NAME
    package_manifest = _build_package_manifest_payload(package_dir=package_dir, run_id=run_id, source_run_dir=run_dir)
    package_manifest_path.write_text(json.dumps(package_manifest, indent=2), encoding="utf-8")

    manifest_path = package_dir / _DEFAULT_MANIFEST_NAME
    lines = _build_sha_manifest_lines(package_dir=package_dir)
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "schema_version": "0.1",
        "kind": "photonstrust.tapeout_package",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "package_manifest_path": str(package_manifest_path.resolve()),
        "file_count": int(len(lines)),
        "package_hash": hash_dict({"run_id": run_id, "lines": lines}),
    }


def _resolve_repo_root(repo_root: Path | None) -> Path:
    if repo_root is None:
        return Path(__file__).resolve().parents[2]
    if not isinstance(repo_root, Path):
        raise TypeError("repo_root must be a pathlib.Path when provided")
    return repo_root.resolve()


def _resolve_optional_path(value: Any, *, repo_root: Path, fallback: Path) -> Path:
    if value is None:
        candidate = fallback
    else:
        if not isinstance(value, str):
            raise TypeError("path values must be strings when provided")
        text = value.strip()
        if not text:
            raise ValueError("path values must be non-empty when provided")
        candidate = Path(text)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _resolve_required_path(request: dict[str, Any], key: str, *, repo_root: Path) -> Path:
    if key not in request:
        raise ValueError(f"request.{key} is required")
    value = request[key]
    if not isinstance(value, str):
        raise TypeError(f"request.{key} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"request.{key} must be a non-empty string")
    path = Path(text)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_run_id(raw: Any, *, run_dir: Path) -> str:
    text = str(raw or "").strip().lower()
    if text:
        return text
    return hash_dict({"run_dir": str(run_dir.resolve())})[:12]


def _copy_inputs(*, run_dir: Path, inputs_dir: Path) -> dict[str, str]:
    copied: dict[str, str] = {}
    for name, rel in _INPUT_SOURCES.items():
        src = (run_dir / rel).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"required input artifact missing: {src}")
        dst = inputs_dir / name
        shutil.copy2(src, dst)
        copied[name] = str(dst.relative_to(inputs_dir.parent)).replace("\\", "/")
    return copied


def _copy_verification(
    *,
    run_dir: Path,
    verification_dir: Path,
    allow_stub_pex: bool,
) -> dict[str, str]:
    copied: dict[str, str] = {}
    for name, rel in _VERIFICATION_DEFAULTS.items():
        src = (run_dir / rel).resolve()
        dst = verification_dir / name
        if src.exists() and src.is_file():
            shutil.copy2(src, dst)
        elif name == "foundry_pex_sealed_summary.json" and allow_stub_pex:
            stub = {
                "schema_version": "0.1",
                "kind": "pic.foundry_pex_sealed_summary",
                "run_id": "stub_pex",
                "status": "error",
                "execution_backend": "stub",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "check_counts": {"total": 0, "passed": 0, "failed": 0, "errored": 0},
                "failed_check_ids": [],
                "failed_check_names": [],
                "deck_fingerprint": None,
                "error_code": "missing_source_artifact",
            }
            dst.write_text(json.dumps(stub, indent=2), encoding="utf-8")
        else:
            raise FileNotFoundError(f"required verification artifact missing: {src}")
        copied[name] = str(dst.relative_to(verification_dir.parent)).replace("\\", "/")
    return copied


def _copy_signoff(
    *,
    request: dict[str, Any],
    run_dir: Path,
    signoff_dir: Path,
    allow_missing_signoff: bool,
) -> dict[str, str]:
    copied: dict[str, str] = {}

    signoff_src = _resolve_user_or_default_path(
        request.get("signoff_ladder_path"),
        run_dir=run_dir,
        default_rel=Path("signoff_ladder.json"),
    )
    signoff_dst = signoff_dir / "signoff_ladder.json"
    if signoff_src.exists() and signoff_src.is_file():
        shutil.copy2(signoff_src, signoff_dst)
    elif allow_missing_signoff:
        placeholder = {
            "schema_version": "0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kind": "pic.signoff_ladder",
            "run_id": hash_dict({"kind": "placeholder_signoff", "source_run": str(run_dir)})[:12],
            "inputs": {
                "chip_assembly_run_id": hash_dict({"missing": True})[:12],
                "chip_assembly_hash": hash_dict({"missing": "chip_assembly"}),
                "policy_hash": hash_dict({"missing": "policy"}),
            },
            "ladder": [
                {
                    "level": 1,
                    "stage": "chip_assembly",
                    "status": "hold",
                    "reason": "placeholder signoff generated by tapeout package builder",
                }
            ],
            "final_decision": {"decision": "HOLD", "reasons": ["placeholder signoff generated"]},
            "provenance": {
                "photonstrust_version": "unknown",
                "python": "unknown",
                "platform": "unknown",
            },
        }
        signoff_dst.write_text(json.dumps(placeholder, indent=2), encoding="utf-8")
    else:
        raise FileNotFoundError(f"required signoff ladder artifact missing: {signoff_src}")
    copied["signoff_ladder.json"] = str(signoff_dst.relative_to(signoff_dir.parent)).replace("\\", "/")

    waivers_src = _resolve_user_or_default_path(
        request.get("waivers_path"),
        run_dir=run_dir,
        default_rel=Path("waivers.json"),
    )
    waivers_dst = signoff_dir / "waivers.json"
    if waivers_src.exists() and waivers_src.is_file():
        shutil.copy2(waivers_src, waivers_dst)
    else:
        waivers_dst.write_text(json.dumps({"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []}, indent=2), encoding="utf-8")
    copied["waivers.json"] = str(waivers_dst.relative_to(signoff_dir.parent)).replace("\\", "/")

    return copied


def _resolve_user_or_default_path(raw: Any, *, run_dir: Path, default_rel: Path) -> Path:
    if raw is None:
        return (run_dir / default_rel).resolve()
    if not isinstance(raw, str):
        raise TypeError("path overrides must be strings")
    text = raw.strip()
    if not text:
        raise ValueError("path overrides must be non-empty")
    path = Path(text)
    if not path.is_absolute():
        path = run_dir / path
    return path.resolve()


def _build_readme(
    *,
    run_id: str,
    source_run_dir: Path,
    copied_inputs: dict[str, str],
    copied_verification: dict[str, str],
    signoff_rel: dict[str, str],
) -> str:
    lines = [
        "# PhotonTrust Tapeout Package",
        "",
        f"- `run_id`: `{run_id}`",
        f"- `generated_at`: `{datetime.now(timezone.utc).isoformat()}`",
        f"- `source_run_dir`: `{str(source_run_dir.resolve())}`",
        "",
        "## Included Artifacts",
        "",
        "### inputs/",
    ]
    for key in sorted(copied_inputs.keys(), key=lambda v: v.lower()):
        lines.append(f"- `{copied_inputs[key]}`")
    lines.append("")
    lines.append("### verification/")
    for key in sorted(copied_verification.keys(), key=lambda v: v.lower()):
        lines.append(f"- `{copied_verification[key]}`")
    lines.append("")
    lines.append("### signoff/")
    for key in sorted(signoff_rel.keys(), key=lambda v: v.lower()):
        lines.append(f"- `{signoff_rel[key]}`")
    lines.extend(
        [
            "",
            "## Integrity Verification",
            "",
            "Use `MANIFEST.sha256` to verify package integrity with your preferred SHA256 checker.",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_package_manifest_payload(*, package_dir: Path, run_id: str, source_run_dir: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(package_dir.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        rel = str(path.relative_to(package_dir)).replace("\\", "/")
        if rel == _DEFAULT_MANIFEST_NAME:
            continue
        rows.append(
            {
                "path": rel,
                "sha256": _sha256_file(path),
                "bytes": int(path.stat().st_size),
            }
        )
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.tapeout_package_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_run_dir": str(source_run_dir.resolve()),
        "files": rows,
        "file_count": len(rows),
        "bundle_sha256": hash_dict([{"path": row["path"], "sha256": row["sha256"]} for row in rows]),
    }


def _build_sha_manifest_lines(*, package_dir: Path) -> list[str]:
    lines: list[str] = []
    for path in sorted(package_dir.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        rel = str(path.relative_to(package_dir)).replace("\\", "/")
        if rel == _DEFAULT_MANIFEST_NAME:
            continue
        lines.append(f"{_sha256_file(path)}  {rel}")
    return lines


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

