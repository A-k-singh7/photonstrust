from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402


_RUN_ID_KEY_RE = re.compile(r".*(?:^|_)(?:run_id|source_run_id|layout_run_id|root_run_id)$")


def _fixture_graph() -> dict[str, Any]:
    fixture_path = Path(__file__).parent / "fixtures" / "phase57_w32_canonical_pic_chain_graph.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text_lines(path: Path, *, drop_prefixes: tuple[str, ...] = ()) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not any(line.startswith(prefix) for prefix in drop_prefixes)]
    payload = ("\n".join(kept) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_abs_path(value: str) -> bool:
    text = str(value)
    if text.startswith("/") or text.startswith("\\"):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", text))


def _normalize(obj: Any, key: str | None = None) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in {"generated_at", "output_dir", "manifest_path"}:
                out[k] = "<VOLATILE>"
                continue
            if k in {"run_id", "pack_id", "replayed_from_run_id"}:
                out[k] = "<RUN_ID>"
                continue
            if _RUN_ID_KEY_RE.match(k):
                out[k] = "<RUN_ID>" if v is not None else None
                continue
            if k == "included_run_ids" and isinstance(v, list):
                out[k] = ["<RUN_ID>"] * len(v)
                continue
            out[k] = _normalize(v, key=k)
        return out
    if isinstance(obj, list):
        return [_normalize(v, key=key) for v in obj]
    if isinstance(obj, str):
        if key and key.endswith("_path") and _is_abs_path(obj):
            return f"<ABS_PATH>/{Path(obj).name}"
        if _is_abs_path(obj):
            return "<ABS_PATH>"
        return re.sub(r"run_[a-f0-9]{8,64}", "run_<RUN_ID>", obj)
    return obj


def _stable_hash_json(obj: Any) -> str:
    normalized = _normalize(obj)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stable_bundle_view(bundle_manifest: dict[str, Any]) -> dict[str, Any]:
    files_raw = bundle_manifest.get("files") if isinstance(bundle_manifest.get("files"), list) else []
    normalized_paths = []
    for row in files_raw:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        if not isinstance(path, str):
            continue
        normalized_paths.append(_normalize(path))
    normalized_paths.sort()

    return {
        "schema_version": bundle_manifest.get("schema_version"),
        "kind": bundle_manifest.get("kind"),
        "include_children": bool(bundle_manifest.get("include_children")),
        "files": normalized_paths,
        "missing_count": len(bundle_manifest.get("missing") or []),
        "included_run_count": len(bundle_manifest.get("included_run_ids") or []),
    }


def _run_chain_and_capture(client: TestClient, graph: dict[str, Any], runs_root: Path) -> dict[str, Any]:
    compile_res = client.post("/v0/graph/compile", json={"graph": graph, "require_schema": True})
    assert compile_res.status_code == 200
    compile_payload = compile_res.json()

    layout_res = client.post(
        "/v0/pic/layout/build",
        json={
            "graph": graph,
            "pdk": {"name": "generic_silicon_photonics"},
            "settings": {"ui_scale_um_per_unit": 1.0},
            "require_schema": False,
        },
    )
    assert layout_res.status_code == 200
    layout_payload = layout_res.json()

    layout_run_id = str(layout_payload["run_id"])
    layout_dir = runs_root / f"run_{layout_run_id}"
    assert (layout_dir / "ports.json").exists()
    assert (layout_dir / "routes.json").exists()
    assert (layout_dir / "layout_provenance.json").exists()

    # Keep klayout hermetic and deterministic: use a local synthetic GDS artifact.
    gds_rel = "phase57_fixture_layout.gds"
    (layout_dir / gds_rel).write_bytes(b"PHOTONTRUST_PHASE57_W32_SYNTHETIC_GDS")

    klayout_res = client.post(
        "/v0/pic/layout/klayout/run",
        json={"source_run_id": layout_run_id, "gds_artifact_path": gds_rel, "settings": {}},
    )
    assert klayout_res.status_code == 200
    klayout_payload = klayout_res.json()
    klayout_pack = klayout_payload.get("pack") or {}
    assert klayout_pack.get("status") in {"skipped", "pass", "fail", "error"}

    lvs_res = client.post(
        "/v0/pic/layout/lvs_lite",
        json={"graph": graph, "layout_run_id": layout_run_id, "settings": {"coord_tol_um": 1.0e-6}},
    )
    assert lvs_res.status_code == 200
    lvs_payload = lvs_res.json()
    assert lvs_payload.get("report", {}).get("summary", {}).get("pass") is True

    spice_res = client.post(
        "/v0/pic/spice/export",
        json={
            "graph": graph,
            "settings": {"top_name": "PT_TOP", "subckt_prefix": "PT", "include_stub_subckts": True},
        },
    )
    assert spice_res.status_code == 200
    spice_payload = spice_res.json()

    spice_run_id = str(spice_payload["run_id"])
    spice_dir = runs_root / f"run_{spice_run_id}"
    for rel in ("netlist.sp", "spice_map.json", "spice_provenance.json"):
        assert (spice_dir / rel).exists(), rel

    bundle_res = client.get(f"/v0/runs/{spice_run_id}/bundle", params={"include_children": "false", "rebuild": "true"})
    assert bundle_res.status_code == 200
    assert "application/zip" in str(bundle_res.headers.get("content-type", "")).lower()

    bundle_zip = zipfile.ZipFile(io.BytesIO(bundle_res.content))
    bundle_names = set(bundle_zip.namelist())
    bundle_manifest_name = next(name for name in bundle_names if name.endswith("/bundle_manifest.json"))
    bundle_manifest = json.loads(bundle_zip.read(bundle_manifest_name).decode("utf-8"))

    manifests = {
        "layout": json.loads(Path(layout_payload["manifest_path"]).read_text(encoding="utf-8")),
        "klayout": json.loads(Path(klayout_payload["manifest_path"]).read_text(encoding="utf-8")),
        "lvs": json.loads(Path(lvs_payload["manifest_path"]).read_text(encoding="utf-8")),
        "spice": json.loads(Path(spice_payload["manifest_path"]).read_text(encoding="utf-8")),
    }

    reports = {
        "layout": layout_payload["report"],
        "klayout": klayout_pack,
        "lvs": lvs_payload["report"],
        "spice": spice_payload["report"],
    }

    stable_artifact_hashes = {
        "layout_ports_sha256": _sha256_file(layout_dir / "ports.json"),
        "layout_routes_sha256": _sha256_file(layout_dir / "routes.json"),
        "spice_netlist_sha256": _sha256_text_lines(spice_dir / "netlist.sp", drop_prefixes=("* generated_at=",)),
        "spice_map_sha256": _sha256_file(spice_dir / "spice_map.json"),
    }

    return {
        "compile_hash": _stable_hash_json(compile_payload),
        "manifest_hashes": {k: _stable_hash_json(v) for k, v in manifests.items()},
        "report_hashes": {k: _stable_hash_json(v) for k, v in reports.items()},
        "bundle_manifest_hash": _stable_hash_json(_stable_bundle_view(bundle_manifest)),
        "stable_artifact_hashes": stable_artifact_hashes,
        "lvs_summary": _normalize((lvs_payload.get("report") or {}).get("summary") or {}),
        "spice_summary": _normalize((spice_payload.get("report") or {}).get("summary") or {}),
    }


def test_canonical_chain_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    graph = _fixture_graph()
    client = TestClient(app)

    run_a = _run_chain_and_capture(client, graph, tmp_path)
    run_b = _run_chain_and_capture(client, graph, tmp_path)

    assert run_a["compile_hash"] == run_b["compile_hash"]
    assert run_a["manifest_hashes"] == run_b["manifest_hashes"]
    assert run_a["report_hashes"] == run_b["report_hashes"]
    assert run_a["bundle_manifest_hash"] == run_b["bundle_manifest_hash"]
    assert run_a["stable_artifact_hashes"] == run_b["stable_artifact_hashes"]
    assert run_a["lvs_summary"] == run_b["lvs_summary"]
    assert run_a["spice_summary"] == run_b["spice_summary"]
