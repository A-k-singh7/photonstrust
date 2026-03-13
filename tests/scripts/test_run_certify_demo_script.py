from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from photonstrust.graph.compiler import compile_graph
from photonstrust.pipeline.certify import run_certify


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_GRAPH_PATH = REPO_ROOT / "graphs" / "demo_qkd_transmitter.json"


def test_run_certify_demo_script_dry_run_writes_certificate_path(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "run_certify_demo.py"
    output_dir = tmp_path / "certify_demo_output"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
            "--output",
            str(output_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["dry_run"] is True
    assert isinstance(payload.get("output_path"), str)
    certificate_path = Path(payload["output_path"])
    assert certificate_path.exists()
    assert certificate_path.name == "certificate.json"


def test_demo_graph_compiles_and_run_certify_dry_run_returns_decision(tmp_path: Path) -> None:
    graph = json.loads(DEMO_GRAPH_PATH.read_text(encoding="utf-8"))
    compiled = compile_graph(graph, require_schema=False)

    assert compiled.profile == "pic_circuit"
    assert isinstance(compiled.compiled, dict)
    assert isinstance((compiled.compiled or {}).get("edges"), list)
    assert len((compiled.compiled or {}).get("edges") or []) >= 1

    result = run_certify(graph, output_dir=tmp_path / "certify_direct", dry_run=True)
    assert isinstance(result, dict)
    assert isinstance(result.get("certificate"), dict)
    assert str(result.get("decision") or "").strip().upper() in {"GO", "HOLD"}
