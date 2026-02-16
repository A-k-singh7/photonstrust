from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from photonstrust.spice.export import export_pic_graph_to_spice_artifacts


def _demo_pic_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "demo_spice_graph",
        "profile": "pic_circuit",
        "metadata": {"title": "demo", "created_at": "2026-02-14"},
        "circuit": {"id": "c1", "wavelength_nm": 1550.0},
        "nodes": [
            {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 100.0}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
        ],
        "edges": [
            {"id": "e1", "from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in", "kind": "optical"},
        ],
    }


def test_pic_spice_export_schema_and_determinism(tmp_path: Path):
    graph = _demo_pic_graph()
    r1 = export_pic_graph_to_spice_artifacts({"graph": graph}, tmp_path / "r1")
    r2 = export_pic_graph_to_spice_artifacts({"graph": graph}, tmp_path / "r2")

    schema_path = Path("schemas") / "photonstrust.pic_spice_export.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=r1, schema=schema)
    validate(instance=r2, schema=schema)

    net1 = (tmp_path / "r1" / r1["artifacts"]["netlist_path"]).read_text(encoding="utf-8")
    net2 = (tmp_path / "r2" / r2["artifacts"]["netlist_path"]).read_text(encoding="utf-8")
    # Ignore timestamps by comparing structural lines.
    keep = lambda s: "\n".join([ln for ln in s.splitlines() if not ln.startswith("* generated_at=")])
    assert keep(net1) == keep(net2)

