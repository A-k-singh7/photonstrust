"""Tapeout package builder for foundry handoff artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Callable

from photonstrust.measurements.schema import validate_instance
from photonstrust.pic.signoff import build_pic_signoff_ladder
from photonstrust.utils import hash_dict
from photonstrust.verification.waivers import load_and_validate_pic_waivers
from photonstrust.workflow.schema import (
    pic_foundry_approval_sealed_summary_schema_path,
    pic_foundry_drc_sealed_summary_schema_path,
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
    pic_signoff_ladder_schema_path,
)

_DEFAULT_OUTPUT_ROOT = Path("results/tapeout_packages")
_DEFAULT_MANIFEST_NAME = "MANIFEST.sha256"
_DEFAULT_README_NAME = "README.md"
_DEFAULT_PACKAGE_MANIFEST_NAME = "tapeout_package_manifest.json"
_RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

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
_OPTIONAL_VERIFICATION_DEFAULTS = {
    "foundry_approval_sealed_summary.json": Path("foundry_approval_sealed_summary.json"),
}

_VERIFICATION_SCHEMAS: dict[str, tuple[str, Callable[[], Path]]] = {
    "foundry_drc_sealed_summary.json": ("pic.foundry_drc_sealed_summary", pic_foundry_drc_sealed_summary_schema_path),
    "foundry_lvs_sealed_summary.json": ("pic.foundry_lvs_sealed_summary", pic_foundry_lvs_sealed_summary_schema_path),
    "foundry_pex_sealed_summary.json": ("pic.foundry_pex_sealed_summary", pic_foundry_pex_sealed_summary_schema_path),
    "foundry_approval_sealed_summary.json": (
        "pic.foundry_approval_sealed_summary",
        pic_foundry_approval_sealed_summary_schema_path,
    ),
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
      - require_foundry_approval: bool (default True)
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
    package_dir = _resolve_package_dir(output_root=output_root, run_id=run_id)
    if package_dir.exists():
        shutil.rmtree(package_dir)
    _ensure_path_under_root(path=package_dir, root=output_root, label="package_dir")
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
        require_foundry_approval=bool(request.get("require_foundry_approval", True)),
    )
    signoff_rel = _copy_signoff(
        request=request,
        run_dir=run_dir,
        repo_root=resolved_repo_root,
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
    if raw is None:
        return hash_dict({"run_dir": str(run_dir.resolve())})[:12]
    if not isinstance(raw, str):
        raise TypeError("request.run_id must be a string when provided")
    text = raw.strip()
    if not text:
        raise ValueError("request.run_id must be non-empty when provided")
    if "/" in text or "\\" in text:
        raise ValueError("request.run_id must not contain path separators")
    if text == "." or text == ".." or ".." in text:
        raise ValueError("request.run_id must not contain traversal segments")
    if not _RUN_ID_PATTERN.fullmatch(text):
        raise ValueError("request.run_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    return text


def _resolve_package_dir(*, output_root: Path, run_id: str) -> Path:
    resolved_output_root = output_root.resolve()
    package_dir = (resolved_output_root / f"tapeout_{run_id}").resolve()
    _ensure_path_under_root(path=package_dir, root=resolved_output_root, label="package_dir")
    return package_dir


def _ensure_path_under_root(*, path: Path, root: Path, label: str) -> None:
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes output_root: {path}") from exc


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
    require_foundry_approval: bool,
) -> dict[str, str]:
    copied: dict[str, str] = {}
    for name, rel in _VERIFICATION_DEFAULTS.items():
        src = (run_dir / rel).resolve()
        dst = verification_dir / name
        if src.exists() and src.is_file():
            shutil.copy2(src, dst)
        elif name == "foundry_pex_sealed_summary.json" and allow_stub_pex:
            now_iso = datetime.now(timezone.utc).isoformat()
            stub = {
                "schema_version": "0.1",
                "kind": "pic.foundry_pex_sealed_summary",
                "run_id": "stub_pex_0001",
                "status": "error",
                "execution_backend": "mock",
                "started_at": now_iso,
                "finished_at": now_iso,
                "check_counts": {"total": 0, "passed": 0, "failed": 0, "errored": 0},
                "failed_check_ids": [],
                "failed_check_names": [],
                "deck_fingerprint": None,
                "error_code": "missing_source_artifact",
            }
            dst.write_text(json.dumps(stub, indent=2), encoding="utf-8")
        else:
            raise FileNotFoundError(f"required verification artifact missing: {src}")
        _validate_verification_artifact(path=dst, artifact_name=name)
        copied[name] = str(dst.relative_to(verification_dir.parent)).replace("\\", "/")

    for name, rel in _OPTIONAL_VERIFICATION_DEFAULTS.items():
        src = (run_dir / rel).resolve()
        dst = verification_dir / name
        if src.exists() and src.is_file():
            shutil.copy2(src, dst)
        elif src.exists():
            raise FileNotFoundError(f"verification artifact path is not a file: {src}")
        elif require_foundry_approval:
            raise FileNotFoundError(f"required verification artifact missing: {src}")
        else:
            continue
        _validate_verification_artifact(path=dst, artifact_name=name)
        copied[name] = str(dst.relative_to(verification_dir.parent)).replace("\\", "/")
    return copied


def _build_placeholder_signoff_ladder(*, run_dir: Path) -> dict[str, Any]:
    placeholder_seed = hash_dict({"kind": "placeholder_signoff", "source_run": str(run_dir.resolve())})
    assembly_report = {
        "kind": "pic.chip_assembly",
        "assembly_run_id": placeholder_seed[:12],
        "outputs": {
            "summary": {
                "status": "fail",
                "output_hash": placeholder_seed,
            }
        },
        "stitch": {
            "summary": {
                "failed_links": 1,
            }
        },
    }
    payload = build_pic_signoff_ladder(
        {
            "assembly_report": assembly_report,
            "policy": {"multi_stage": True},
        }
    )
    report = payload.get("report")
    if not isinstance(report, dict):
        raise ValueError("placeholder signoff builder returned unexpected payload")
    return report


def _copy_signoff(
    *,
    request: dict[str, Any],
    run_dir: Path,
    repo_root: Path,
    signoff_dir: Path,
    allow_missing_signoff: bool,
) -> dict[str, str]:
    copied: dict[str, str] = {}

    signoff_src, has_signoff_override = _resolve_user_or_default_path(
        request.get("signoff_ladder_path"),
        run_dir=run_dir,
        repo_root=repo_root,
        default_rel=Path("signoff_ladder.json"),
    )
    signoff_dst = signoff_dir / "signoff_ladder.json"
    if signoff_src.exists() and signoff_src.is_file():
        shutil.copy2(signoff_src, signoff_dst)
    elif signoff_src.exists():
        raise FileNotFoundError(f"signoff ladder path is not a file: {signoff_src}")
    elif allow_missing_signoff:
        if has_signoff_override:
            raise FileNotFoundError(f"explicit signoff_ladder_path does not exist: {signoff_src}")
        placeholder = _build_placeholder_signoff_ladder(run_dir=run_dir)
        signoff_dst.write_text(json.dumps(placeholder, indent=2), encoding="utf-8")
    else:
        raise FileNotFoundError(f"required signoff ladder artifact missing: {signoff_src}")
    _validate_signoff_ladder_artifact(path=signoff_dst)
    copied["signoff_ladder.json"] = str(signoff_dst.relative_to(signoff_dir.parent)).replace("\\", "/")

    waivers_src, has_waivers_override = _resolve_user_or_default_path(
        request.get("waivers_path"),
        run_dir=run_dir,
        repo_root=repo_root,
        default_rel=Path("waivers.json"),
    )
    waivers_dst = signoff_dir / "waivers.json"
    if waivers_src.exists() and waivers_src.is_file():
        shutil.copy2(waivers_src, waivers_dst)
    elif waivers_src.exists():
        raise FileNotFoundError(f"waivers path is not a file: {waivers_src}")
    elif has_waivers_override:
        raise FileNotFoundError(f"explicit waivers_path does not exist: {waivers_src}")
    else:
        waivers_dst.write_text(json.dumps({"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []}, indent=2), encoding="utf-8")
    _validate_waivers_artifact(path=waivers_dst)
    copied["waivers.json"] = str(waivers_dst.relative_to(signoff_dir.parent)).replace("\\", "/")

    return copied


def _resolve_user_or_default_path(
    raw: Any,
    *,
    run_dir: Path,
    repo_root: Path,
    default_rel: Path,
) -> tuple[Path, bool]:
    if raw is None:
        return (run_dir / default_rel).resolve(), False
    if not isinstance(raw, str):
        raise TypeError("path overrides must be strings")
    text = raw.strip()
    if not text:
        raise ValueError("path overrides must be non-empty")
    path = Path(text)
    if not path.is_absolute():
        run_candidate = (run_dir / path).resolve()
        repo_candidate = (repo_root / path).resolve()
        run_exists = run_candidate.exists()
        repo_exists = repo_candidate.exists()
        if run_exists and repo_exists and run_candidate != repo_candidate:
            raise ValueError(
                f"path override is ambiguous and resolves to multiple files: "
                f"{run_candidate} and {repo_candidate}"
            )
        if run_exists:
            return run_candidate, True
        if repo_exists:
            return repo_candidate, True
        return run_candidate, True
    return path.resolve(), True


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _validate_schema_payload(*, payload: dict[str, Any], schema_path: Path, label: str) -> None:
    try:
        validate_instance(payload, schema_path)
    except Exception as exc:
        raise ValueError(f"{label} failed schema validation: {exc}") from exc


def _validate_verification_artifact(*, path: Path, artifact_name: str) -> None:
    if artifact_name not in _VERIFICATION_SCHEMAS:
        raise ValueError(f"unsupported verification artifact: {artifact_name}")
    expected_kind, schema_path_fn = _VERIFICATION_SCHEMAS[artifact_name]
    payload = _load_json_object(path, label=f"verification artifact {artifact_name}")
    _validate_schema_payload(
        payload=payload,
        schema_path=schema_path_fn(),
        label=f"verification artifact {artifact_name}",
    )
    _validate_verification_content(
        payload=payload,
        expected_kind=expected_kind,
        label=f"verification artifact {artifact_name}",
    )


def _validate_verification_content(*, payload: dict[str, Any], expected_kind: str, label: str) -> None:
    if expected_kind == "pic.foundry_approval_sealed_summary":
        _validate_foundry_approval_content(payload=payload, label=label)
        return

    kind = str(payload.get("kind", "")).strip()
    if kind != expected_kind:
        raise ValueError(f"{label} has kind={kind!r}, expected {expected_kind!r}")

    status = str(payload.get("status", "")).strip().lower()
    check_counts = payload.get("check_counts")
    if not isinstance(check_counts, dict):
        raise ValueError(f"{label} missing check_counts object")

    total = _require_int(check_counts, "total", label=label)
    passed = _require_int(check_counts, "passed", label=label)
    failed = _require_int(check_counts, "failed", label=label)
    errored = _require_int(check_counts, "errored", label=label)
    if total != (passed + failed + errored):
        raise ValueError(
            f"{label} has inconsistent check_counts: total={total} "
            f"but passed+failed+errored={passed + failed + errored}"
        )

    failed_ids = payload.get("failed_check_ids")
    failed_names = payload.get("failed_check_names")
    if not isinstance(failed_ids, list):
        raise ValueError(f"{label} failed_check_ids must be an array")
    if not isinstance(failed_names, list):
        raise ValueError(f"{label} failed_check_names must be an array")
    if len(failed_ids) != len(failed_names):
        raise ValueError(
            f"{label} has mismatched failed_check_ids/failed_check_names lengths: "
            f"{len(failed_ids)} vs {len(failed_names)}"
        )
    if any((not isinstance(item, str) or not item.strip()) for item in failed_ids):
        raise ValueError(f"{label} failed_check_ids entries must be non-empty strings")
    if any((not isinstance(item, str) or not item.strip()) for item in failed_names):
        raise ValueError(f"{label} failed_check_names entries must be non-empty strings")

    if status == "pass":
        if failed != 0 or errored != 0 or failed_ids:
            raise ValueError(f"{label} status=pass cannot include failed/errored checks")
    elif status == "fail":
        if failed <= 0 or not failed_ids:
            raise ValueError(f"{label} status=fail requires failed_check_ids and failed count > 0")
    elif status == "error":
        raw_error_code = payload.get("error_code")
        error_code = raw_error_code.strip() if isinstance(raw_error_code, str) else ""
        if errored <= 0 and not failed_ids and not error_code:
            raise ValueError(f"{label} status=error requires errored checks, failed checks, or error_code")
    else:
        raise ValueError(f"{label} has unsupported status={status!r}")


def _validate_foundry_approval_content(*, payload: dict[str, Any], label: str) -> None:
    kind = str(payload.get("kind", "")).strip()
    expected_kind = "pic.foundry_approval_sealed_summary"
    if kind != expected_kind:
        raise ValueError(f"{label} has kind={kind!r}, expected {expected_kind!r}")

    decision = str(payload.get("decision", "")).strip().upper()
    status = str(payload.get("status", "")).strip().lower()
    failed_ids = payload.get("failed_check_ids")
    failed_names = payload.get("failed_check_names")

    if not isinstance(failed_ids, list):
        raise ValueError(f"{label} failed_check_ids must be an array")
    if not isinstance(failed_names, list):
        raise ValueError(f"{label} failed_check_names must be an array")
    if len(failed_ids) != len(failed_names):
        raise ValueError(
            f"{label} has mismatched failed_check_ids/failed_check_names lengths: "
            f"{len(failed_ids)} vs {len(failed_names)}"
        )
    if any((not isinstance(item, str) or not item.strip()) for item in failed_ids):
        raise ValueError(f"{label} failed_check_ids entries must be non-empty strings")
    if any((not isinstance(item, str) or not item.strip()) for item in failed_names):
        raise ValueError(f"{label} failed_check_names entries must be non-empty strings")

    if decision == "GO" and status != "pass":
        raise ValueError(f"{label} has decision=GO but status={status!r}")
    if decision == "HOLD" and status == "pass":
        raise ValueError(f"{label} has decision=HOLD but status=pass")

    raw_error_code = payload.get("error_code")
    error_code = raw_error_code.strip() if isinstance(raw_error_code, str) else ""
    if status == "pass":
        if failed_ids:
            raise ValueError(f"{label} status=pass cannot include failed checks")
        if error_code:
            raise ValueError(f"{label} status=pass cannot include error_code")
    elif status in {"fail", "error"}:
        if not failed_ids and not error_code:
            raise ValueError(f"{label} status={status} requires failed checks or error_code")
    else:
        raise ValueError(f"{label} has unsupported status={status!r}")


def _require_int(container: dict[str, Any], key: str, *, label: str) -> int:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} check_counts.{key} must be an integer")
    return int(value)


def _validate_signoff_ladder_artifact(*, path: Path) -> None:
    payload = _load_json_object(path, label="signoff ladder artifact")
    _validate_schema_payload(
        payload=payload,
        schema_path=pic_signoff_ladder_schema_path(),
        label="signoff ladder artifact",
    )

    ladder = payload.get("ladder")
    if not isinstance(ladder, list) or not ladder:
        raise ValueError("signoff ladder artifact requires at least one ladder row")
    if any(not isinstance(row, dict) for row in ladder):
        raise ValueError("signoff ladder artifact ladder rows must be objects")

    final_decision = payload.get("final_decision")
    if not isinstance(final_decision, dict):
        raise ValueError("signoff ladder artifact final_decision must be an object")
    decision = str(final_decision.get("decision", "")).strip().upper()
    if decision not in {"GO", "HOLD"}:
        raise ValueError(f"signoff ladder artifact has unsupported final_decision.decision={decision!r}")

    statuses = [str(row.get("status", "")).strip().lower() for row in ladder]
    blocking_statuses = {"fail", "error", "hold", "skipped"}
    has_blocking = any(status in blocking_statuses for status in statuses)
    if decision == "GO" and has_blocking:
        raise ValueError("signoff ladder artifact final_decision=GO conflicts with ladder blocking status")
    if decision == "HOLD" and not has_blocking:
        raise ValueError("signoff ladder artifact final_decision=HOLD requires at least one blocking ladder status")


def _validate_waivers_artifact(*, path: Path) -> None:
    try:
        validated = load_and_validate_pic_waivers(path)
    except Exception as exc:
        raise ValueError(f"waivers artifact failed validation: {exc}") from exc

    if bool(validated.get("ok", False)):
        return

    issues = validated.get("issues")
    if isinstance(issues, list) and issues:
        issue_text = "; ".join(str(item) for item in issues[:3])
    else:
        issue_text = "waiver validation returned ok=false"
    raise ValueError(f"waivers artifact failed validation: {issue_text}")


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
