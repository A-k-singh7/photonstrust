"""KLayout run artifact pack (v0.1).

This module provides a deterministic wrapper for running a trusted KLayout macro
template in batch mode and capturing all relevant provenance:
- command line
- runtime variables (-rd)
- stdout/stderr logs
- input/output file hashes

KLayout is treated as an optional external tool (tool seam).
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.layout.pic.klayout_runner import ExternalToolNotFoundError, run_klayout_macro


def _repo_root() -> Path:
    # .../photonstrust/layout/pic/klayout_artifact_pack.py -> parents[3] is repo root.
    return Path(__file__).resolve().parents[3]


def default_klayout_macro_template_path() -> Path:
    return (_repo_root() / "tools" / "klayout" / "macros" / "pt_pic_extract_and_drc_lite.py").resolve()


def klayout_run_artifact_pack_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_klayout_run_artifact_pack.v0.schema.json").resolve()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


@dataclass(frozen=True)
class KLayoutArtifactPackPaths:
    pack_json: Path
    stdout_txt: Path
    stderr_txt: Path
    ports_extracted_json: Path
    routes_extracted_json: Path
    drc_lite_json: Path
    macro_provenance_json: Path


def default_pack_paths(output_dir: Path) -> KLayoutArtifactPackPaths:
    out = Path(output_dir)
    return KLayoutArtifactPackPaths(
        pack_json=out / "klayout_run_artifact_pack.json",
        stdout_txt=out / "klayout_stdout.txt",
        stderr_txt=out / "klayout_stderr.txt",
        ports_extracted_json=out / "ports_extracted.json",
        routes_extracted_json=out / "routes_extracted.json",
        drc_lite_json=out / "drc_lite.json",
        macro_provenance_json=out / "macro_provenance.json",
    )


def build_klayout_run_artifact_pack(
    *,
    input_gds_path: str | Path,
    output_dir: str | Path,
    macro_path: str | Path | None = None,
    klayout_exe: str | None = None,
    settings: dict[str, Any] | None = None,
    timeout_s: float | None = 300.0,
    allow_missing_tool: bool = True,
) -> dict[str, Any]:
    """Run the PhotonTrust KLayout macro template and write an artifact pack manifest.

    This function always attempts to write `klayout_run_artifact_pack.json`.

    If KLayout is missing and `allow_missing_tool=True`, it will emit a schema-valid
    pack with `status="skipped"` and a clear `execution.error` message.
    """

    input_gds = Path(input_gds_path)
    if not input_gds.exists() or not input_gds.is_file():
        raise FileNotFoundError(str(input_gds))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    s = dict(settings or {})
    # Default layer spec and label parsing must match layout builder defaults.
    wg = s.get("waveguide_layer") if isinstance(s.get("waveguide_layer"), dict) else {}
    lb = s.get("label_layer") if isinstance(s.get("label_layer"), dict) else {}

    wg_layer = int(wg.get("layer", 1) or 1)
    wg_datatype = int(wg.get("datatype", 0) or 0)
    label_layer = int(lb.get("layer", 10) or 10)
    label_datatype = int(lb.get("datatype", 0) or 0)
    label_prefix = str(s.get("label_prefix", "PTPORT") or "PTPORT").strip() or "PTPORT"

    min_waveguide_width_um = float(s.get("min_waveguide_width_um", 0.5) or 0.5)
    endpoint_snap_tol_um = float(s.get("endpoint_snap_tol_um", 2.0) or 2.0)
    top_cell = str(s.get("top_cell", "") or "").strip() or None

    macro = Path(macro_path) if macro_path is not None else default_klayout_macro_template_path()
    if not macro.exists() or not macro.is_file():
        raise FileNotFoundError(str(macro))

    paths = default_pack_paths(out_dir)

    pack_id = uuid.uuid4().hex[:12]
    generated_at = datetime.now(timezone.utc).isoformat()

    # Variables passed to KLayout (-rd).
    variables: dict[str, Any] = {
        "input_gds": str(input_gds.resolve()),
        "output_dir": str(out_dir.resolve()),
        "wg_layer": int(wg_layer),
        "wg_datatype": int(wg_datatype),
        "label_layer": int(label_layer),
        "label_datatype": int(label_datatype),
        "label_prefix": str(label_prefix),
        "min_waveguide_width_um": float(min_waveguide_width_um),
        "endpoint_snap_tol_um": float(endpoint_snap_tol_um),
        "ports_json": str(paths.ports_extracted_json.resolve()),
        "routes_json": str(paths.routes_extracted_json.resolve()),
        "drc_json": str(paths.drc_lite_json.resolve()),
        "provenance_json": str(paths.macro_provenance_json.resolve()),
    }
    if top_cell:
        variables["top_cell"] = str(top_cell)

    status = "error"
    execution: dict[str, Any] = {
        "backend": "klayout_cli",
        "ok": False,
        "returncode": None,
        "command": None,
        "stdout_path": str(paths.stdout_txt.name),
        "stderr_path": str(paths.stderr_txt.name),
        "error": None,
    }

    # Always write log files (even for skipped/error paths) so the run folder is self-explanatory.
    paths.stdout_txt.write_text("", encoding="utf-8")
    paths.stderr_txt.write_text("", encoding="utf-8")

    try:
        res = run_klayout_macro(
            macro,
            klayout_exe=klayout_exe,
            variables=variables,
            timeout_s=timeout_s,
        )
        execution.update(
            {
                "ok": bool(res.ok),
                "returncode": int(res.returncode),
                "command": list(res.command),
            }
        )
        paths.stdout_txt.write_text(res.stdout or "", encoding="utf-8")
        paths.stderr_txt.write_text(res.stderr or "", encoding="utf-8")
    except ExternalToolNotFoundError as exc:
        if not allow_missing_tool:
            raise
        execution["error"] = str(exc)
        status = "skipped"
    except Exception as exc:
        execution["error"] = str(exc)
        status = "error"

    drc = _safe_read_json(paths.drc_lite_json) if paths.drc_lite_json.exists() else None
    drc_status = ((drc.get("summary") or {}).get("status") if isinstance(drc, dict) else None) if drc else None
    if status != "skipped":
        if str(drc_status) == "pass":
            status = "pass"
        elif str(drc_status) == "fail":
            status = "fail"
        elif str(drc_status) == "error":
            status = "error"
        else:
            # If KLayout ran but did not produce DRC output, treat as error.
            if execution.get("returncode") == 0:
                status = "error"

    outputs: dict[str, Any] = {
        "ports_extracted_json": str(paths.ports_extracted_json.name) if paths.ports_extracted_json.exists() else None,
        "routes_extracted_json": str(paths.routes_extracted_json.name) if paths.routes_extracted_json.exists() else None,
        "drc_lite_json": str(paths.drc_lite_json.name) if paths.drc_lite_json.exists() else None,
        "macro_provenance_json": str(paths.macro_provenance_json.name) if paths.macro_provenance_json.exists() else None,
    }

    output_hashes: dict[str, str] = {}
    for k, rel in outputs.items():
        if not rel:
            continue
        p = out_dir / rel
        if p.exists() and p.is_file():
            output_hashes[k.replace("_json", "_sha256")] = _sha256_file(p)

    pack = {
        "schema_version": "0.1",
        "generated_at": generated_at,
        "pack_id": pack_id,
        "status": status,
        "inputs": {
            "input_gds_path": str(input_gds.resolve()),
            "input_gds_sha256": _sha256_file(input_gds),
            "macro_path": str(macro.resolve()),
            "macro_sha256": _sha256_file(macro),
            "variables": {k: variables[k] for k in sorted(variables.keys(), key=lambda s: str(s).lower())},
        },
        "execution": execution,
        "outputs": outputs,
        "output_hashes": output_hashes,
        "summary": {
            "ports_extracted": ((drc.get("metrics") or {}).get("ports_extracted") if isinstance(drc, dict) else None),
            "routes_extracted": ((drc.get("metrics") or {}).get("routes_extracted") if isinstance(drc, dict) else None),
            "drc_status": str(drc_status) if drc_status is not None else None,
            "issue_count": ((drc.get("summary") or {}).get("issue_count") if isinstance(drc, dict) else None),
            "error_count": ((drc.get("summary") or {}).get("error_count") if isinstance(drc, dict) else None),
        },
        "provenance": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    _write_json(paths.pack_json, pack)
    return pack

