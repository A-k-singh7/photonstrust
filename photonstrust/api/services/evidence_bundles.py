"""Evidence bundle helpers for exported and published run artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata as importlib_metadata
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException

from photonstrust.api import runs as run_store
from photonstrust.api.runtime import api_version, generated_at_utc
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.evidence.bundle import verify_bundle_zip
from photonstrust.workflow.schema import evidence_bundle_publish_manifest_schema_path


_BUNDLE_FIXED_DT = (1980, 1, 1, 0, 0, 0)
_BUNDLE_CHUNK_BYTES = 1024 * 1024
_BUNDLE_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


def iter_manifest_artifact_relpaths(manifest: dict[str, Any]) -> list[str]:
    out: list[str] = []
    arts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    for value in arts.values():
        if isinstance(value, str) and value.strip():
            out.append(str(value).strip())

    cards = arts.get("cards")
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue
            card_artifacts = card.get("artifacts") if isinstance(card.get("artifacts"), dict) else {}
            for value in card_artifacts.values():
                if isinstance(value, str) and value.strip():
                    out.append(str(value).strip())

    seen: set[str] = set()
    uniq: list[str] = []
    for rel in out:
        key = str(rel).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(str(rel).strip())
    return uniq


def is_workflow_manifest(manifest: dict[str, Any]) -> bool:
    if str(manifest.get("run_type", "")).strip() == "pic_workflow_invdesign_chain":
        return True
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    return isinstance(outputs.get("pic_workflow"), dict)


def workflow_child_run_ids(manifest: dict[str, Any]) -> list[str]:
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    workflow = outputs.get("pic_workflow") if isinstance(outputs.get("pic_workflow"), dict) else {}
    raw = [
        workflow.get("invdesign_run_id"),
        workflow.get("layout_run_id"),
        workflow.get("lvs_lite_run_id"),
        workflow.get("klayout_pack_run_id"),
        workflow.get("spice_export_run_id"),
    ]
    out: list[str] = []
    seen: set[str] = set()
    for run_id in raw:
        if not isinstance(run_id, str) or not run_id.strip():
            continue
        try:
            canon = run_store.validate_run_id(run_id)
        except Exception:
            continue
        if canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
    return out


def resolve_include_children(manifest: dict[str, Any], include_children: bool | None) -> bool:
    default_children = is_workflow_manifest(manifest)
    return bool(default_children) if include_children is None else bool(include_children)


def bundle_relpath(include_children: bool) -> str:
    return "evidence_bundle_with_children.zip" if include_children else "evidence_bundle_root_only.zip"


def published_bundles_root() -> Path:
    root = run_store.runs_root() / "_published_bundles" / "sha256"
    root.mkdir(parents=True, exist_ok=True)
    return root


def published_bundle_path(digest: str) -> Path:
    return published_bundles_root() / f"{digest}.zip"


def published_bundle_manifest_path(digest: str) -> Path:
    return published_bundles_root() / f"{digest}.manifest.json"


def validate_bundle_digest(digest: str) -> str:
    value = str(digest or "").strip().lower()
    if not _BUNDLE_DIGEST_RE.match(value):
        raise HTTPException(status_code=400, detail="digest must be a 64-char lowercase hex sha256")
    return value


def _zip_write_bytes(zf: zipfile.ZipFile, arcname: str, data: bytes) -> tuple[str, int]:
    arc = str(arcname).replace("\\", "/")
    info = zipfile.ZipInfo(arc)
    info.date_time = _BUNDLE_FIXED_DT
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)
    return hashlib.sha256(data).hexdigest(), int(len(data))


def _zip_write_file(zf: zipfile.ZipFile, arcname: str, src_path: Path) -> tuple[str, int]:
    arc = str(arcname).replace("\\", "/")
    info = zipfile.ZipInfo(arc)
    info.date_time = _BUNDLE_FIXED_DT
    info.compress_type = zipfile.ZIP_DEFLATED

    sha = hashlib.sha256()
    size = 0
    with Path(src_path).open("rb") as src, zf.open(info, "w") as dest:
        while True:
            chunk = src.read(_BUNDLE_CHUNK_BYTES)
            if not chunk:
                break
            dest.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), int(size)


def sha256_file(path: Path) -> tuple[str, int]:
    sha = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(_BUNDLE_CHUNK_BYTES)
            if not chunk:
                break
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), int(size)


def _build_cyclonedx_sbom(*, timestamp: str | None = None) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    for dist in sorted(importlib_metadata.distributions(), key=lambda d: str((d.metadata or {}).get("Name", "")).lower()):
        name = str((dist.metadata or {}).get("Name") or "").strip()
        if not name:
            continue
        components.append(
            {
                "type": "library",
                "name": name,
                "version": str(dist.version or ""),
            }
        )

    version = api_version()
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": str(timestamp or generated_at_utc()),
            "tools": [
                {
                    "vendor": "PhotonTrust",
                    "name": "photonstrust.api.bundle",
                    "version": version,
                }
            ],
            "component": {
                "type": "application",
                "name": "photonstrust",
                "version": version,
            },
        },
        "components": components,
    }


def _verify_payload(verify: Any) -> dict[str, Any]:
    return {
        "ok": bool(verify.ok),
        "bundle_root": str(verify.bundle_root),
        "manifest_sha256": str(verify.manifest_sha256),
        "verified_files": int(verify.verified_files),
        "missing_files": int(verify.missing_files),
        "mismatched_files": int(verify.mismatched_files),
        "signature_verified": bool(verify.signature_verified),
        "errors": list(verify.errors),
    }


def export_bundle_for_run(
    *,
    run_id: str,
    root_dir: Path,
    root_manifest: dict[str, Any],
    include_children: bool,
    rebuild: bool,
    fetch_manifest: Callable[[str], dict[str, Any]],
) -> Path:
    bundle_path = root_dir / bundle_relpath(include_children)
    tmp_path = root_dir / f"{bundle_path.name}.tmp"
    if bundle_path.exists() and bundle_path.is_file() and not rebuild:
        return bundle_path

    child_ids = workflow_child_run_ids(root_manifest) if include_children else []
    included_run_ids = [run_store.validate_run_id(run_id)] + child_ids

    files: list[tuple[str, Path]] = []
    generated_files: list[tuple[str, bytes]] = []
    missing: list[dict[str, Any]] = []

    for included_run_id in included_run_ids:
        try:
            run_dir = run_store.run_dir_for_id(included_run_id)
        except Exception:
            continue
        if not run_dir.exists():
            missing.append({"run_id": included_run_id, "path": None, "error": "run directory missing"})
            continue

        manifest_file = run_dir / run_store.RUN_MANIFEST_BASENAME
        if manifest_file.exists() and manifest_file.is_file():
            files.append((f"runs/run_{included_run_id}/{run_store.RUN_MANIFEST_BASENAME}", manifest_file))
            manifest = run_store.read_run_manifest(run_dir) or {}
        else:
            manifest = fetch_manifest(included_run_id)
            try:
                generated_files.append(
                    (
                        f"runs/run_{included_run_id}/{run_store.RUN_MANIFEST_BASENAME}",
                        json.dumps(manifest, indent=2).encode("utf-8"),
                    )
                )
            except Exception:
                missing.append(
                    {
                        "run_id": included_run_id,
                        "path": run_store.RUN_MANIFEST_BASENAME,
                        "error": "failed to serialize synthesized manifest",
                    }
                )

        if isinstance(manifest, dict):
            for rel in iter_manifest_artifact_relpaths(manifest):
                try:
                    artifact_path = run_store.resolve_artifact_path(run_dir, rel)
                except FileNotFoundError as exc:
                    missing.append({"run_id": included_run_id, "path": rel, "error": str(exc)})
                    continue
                except Exception as exc:
                    missing.append({"run_id": included_run_id, "path": rel, "error": str(exc)})
                    continue
                files.append((f"runs/run_{included_run_id}/{str(rel).replace('\\', '/')}", artifact_path))
        else:
            missing.append({"run_id": included_run_id, "path": None, "error": "manifest not readable"})

    seen_arc: set[str] = set()
    uniq_files: list[tuple[str, Path]] = []
    for arc, file_path in files:
        key = str(arc).lower()
        if key in seen_arc:
            continue
        seen_arc.add(key)
        uniq_files.append((arc, file_path))
    uniq_files.sort(key=lambda item: str(item[0]).lower())

    root_input = root_manifest.get("input") if isinstance(root_manifest.get("input"), dict) else {}
    root_execution_mode = str(root_input.get("execution_mode", "preview") or "preview").strip().lower() or "preview"
    if root_execution_mode == "certification":
        missing_invdesign = []
        for row in missing:
            rel = str((row or {}).get("path", "") or "").strip().lower()
            if rel.endswith("invdesign_report.json") or rel.endswith("optimized_graph.json"):
                missing_invdesign.append(row)
        if missing_invdesign:
            raise HTTPException(
                status_code=400,
                detail="certification evidence bundle missing required inverse-design artifacts",
            )

    validated_run_id = run_store.validate_run_id(run_id)
    bundle_root = f"photonstrust_evidence_bundle_{validated_run_id}"
    generated_at = str(root_manifest.get("generated_at") or generated_at_utc())
    readme = "\n".join(
        [
            "# PhotonTrust Evidence Bundle",
            "",
            f"- generated_at: {generated_at}",
            f"- root_run_id: {validated_run_id}",
            f"- include_children: {str(include_children).lower()}",
            "",
            "This bundle contains run manifests + declared artifacts for offline review.",
            "Integrity metadata is recorded in bundle_manifest.json (sha256 per file).",
            "",
        ]
    ).encode("utf-8")

    sbom_rel = "sbom/cyclonedx.json"
    sbom_bytes = json.dumps(_build_cyclonedx_sbom(timestamp=generated_at), indent=2).encode("utf-8")
    generated_files.append((sbom_rel, sbom_bytes))

    bundle_manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "generated_at": generated_at,
        "kind": "photonstrust.evidence_bundle",
        "root_run_id": validated_run_id,
        "include_children": bool(include_children),
        "included_run_ids": list(included_run_ids),
        "files": [],
        "missing": missing,
        "sbom": {
            "path": sbom_rel,
            "format": "cyclonedx+json",
            "sha256": None,
            "bytes": None,
        },
    }

    try:
        with zipfile.ZipFile(tmp_path, mode="w") as zf:
            sha, size = _zip_write_bytes(zf, f"{bundle_root}/README.md", readme)
            bundle_manifest["files"].append({"path": "README.md", "sha256": sha, "bytes": size})

            generated_files.sort(key=lambda item: str(item[0]).lower())
            for arc, data in generated_files:
                sha, size = _zip_write_bytes(zf, f"{bundle_root}/{arc}", data)
                bundle_manifest["files"].append({"path": str(arc).replace("\\", "/"), "sha256": sha, "bytes": size})
                if str(arc).replace("\\", "/") == sbom_rel:
                    sbom_obj = bundle_manifest.get("sbom") if isinstance(bundle_manifest.get("sbom"), dict) else None
                    if isinstance(sbom_obj, dict):
                        sbom_obj["sha256"] = sha
                        sbom_obj["bytes"] = int(size)

            for arc, file_path in uniq_files:
                sha, size = _zip_write_file(zf, f"{bundle_root}/{arc}", file_path)
                bundle_manifest["files"].append(
                    {
                        "path": str(arc).replace("\\", "/"),
                        "sha256": sha,
                        "bytes": size,
                    }
                )

            manifest_bytes = json.dumps(bundle_manifest, indent=2).encode("utf-8")
            sha, size = _zip_write_bytes(zf, f"{bundle_root}/bundle_manifest.json", manifest_bytes)
            bundle_manifest["bundle_manifest_sha256"] = sha
            bundle_manifest["bundle_manifest_bytes"] = size
    except Exception as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        tmp_path.replace(bundle_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle_path


def publish_bundle_for_run(
    *,
    run_id: str,
    root_dir: Path,
    root_manifest: dict[str, Any],
    include_children: bool,
    rebuild: bool,
    fetch_manifest: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    bundle_path = export_bundle_for_run(
        run_id=run_id,
        root_dir=root_dir,
        root_manifest=root_manifest,
        include_children=include_children,
        rebuild=rebuild,
        fetch_manifest=fetch_manifest,
    )
    if not bundle_path.exists() or not bundle_path.is_file():
        raise HTTPException(status_code=400, detail="bundle file was not created")

    bundle_sha, bundle_bytes = sha256_file(bundle_path)
    publish_root = published_bundles_root()
    zip_dest = publish_root / f"{bundle_sha}.zip"
    if not zip_dest.exists():
        shutil.copy2(bundle_path, zip_dest)

    verify = verify_bundle_zip(zip_dest, require_signature=False)
    publish_manifest = {
        "schema_version": "0.1",
        "kind": "photonstrust.evidence_bundle_publish_manifest",
        "generated_at": generated_at_utc(),
        "bundle_sha256": bundle_sha,
        "bundle_bytes": int(bundle_bytes),
        "bundle_path": str(zip_dest),
        "source_run_id": run_store.validate_run_id(run_id),
        "include_children": bool(include_children),
        "verify": _verify_payload(verify),
    }
    validate_instance(publish_manifest, evidence_bundle_publish_manifest_schema_path(), require_jsonschema=False)
    publish_manifest_path = publish_root / f"{bundle_sha}.manifest.json"
    publish_manifest_path.write_text(json.dumps(publish_manifest, indent=2), encoding="utf-8")

    return {
        "generated_at": generated_at_utc(),
        "bundle_sha256": bundle_sha,
        "bundle_bytes": int(bundle_bytes),
        "bundle_path": str(zip_dest),
        "publish_manifest_path": str(publish_manifest_path),
        "verify": publish_manifest["verify"],
    }


def verify_published_bundle(digest: str) -> dict[str, Any]:
    value = validate_bundle_digest(digest)
    zip_path = published_bundle_path(value)
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="published bundle not found")

    verify = verify_bundle_zip(zip_path, require_signature=False)
    publish_manifest_path = published_bundle_manifest_path(value)
    return {
        "generated_at": generated_at_utc(),
        "bundle_sha256": value,
        "bundle_path": str(zip_path),
        "publish_manifest_path": str(publish_manifest_path) if publish_manifest_path.exists() else None,
        "verify": _verify_payload(verify),
    }
