from __future__ import annotations

from photonstrust.graph.diagnostics import validate_graph_semantics


def test_pic_port_validation_catches_unknown_ports() -> None:
    graph = {
        "schema_version": "0.1",
        "graph_id": "diag_pic_ports",
        "profile": "pic_circuit",
        "metadata": {"title": "diag", "description": "", "created_at": "2026-02-13"},
        "circuit": {
            "id": "diag_pic_ports",
            "wavelength_nm": 1550,
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
        ],
        "edges": [
            # Invalid port name "out9" should be caught.
            {"id": "e1", "from": "cpl_in", "from_port": "out9", "to": "ps1", "to_port": "in", "kind": "optical"},
        ],
    }

    diags = validate_graph_semantics(graph)
    codes = {d["code"] for d in diags["errors"]}
    assert "edge.from_port" in codes


def test_qkd_param_type_and_range_validation() -> None:
    graph = {
        "schema_version": "0.1",
        "graph_id": "diag_qkd_params",
        "profile": "qkd_link",
        "metadata": {"title": "diag", "description": "", "created_at": "2026-02-13"},
        "scenario": {"id": "diag_qkd_params", "distance_km": 1, "band": "c_1550", "wavelength_nm": 1550},
        "uncertainty": {},
        "nodes": [
            {
                "id": "source_1",
                "kind": "qkd.source",
                "params": {
                    "type": "emitter_cavity",
                    "rep_rate_mhz": "fast",  # type error
                    "coupling_efficiency": 1.5,  # range error (max 1)
                    "unknown_knob": 123,  # unknown param warning
                },
            },
            {"id": "channel_1", "kind": "qkd.channel", "params": {"model": "fiber"}},
            {"id": "detector_1", "kind": "qkd.detector", "params": {"class": "snspd"}},
            {"id": "timing_1", "kind": "qkd.timing", "params": {"sync_drift_ps_rms": 10}},
            {"id": "protocol_1", "kind": "qkd.protocol", "params": {"name": "BBM92"}},
        ],
        "edges": [],
    }

    diags = validate_graph_semantics(graph)
    error_codes = {d["code"] for d in diags["errors"]}
    warn_codes = {d["code"] for d in diags["warnings"]}

    assert "param.type" in error_codes
    assert "param.range" in error_codes
    assert "param.unknown" in warn_codes


def test_pic_kind_support_validation_catches_unsupported_kinds() -> None:
    graph = {
        "schema_version": "0.1",
        "graph_id": "diag_pic_kind",
        "profile": "pic_circuit",
        "metadata": {"title": "diag", "description": "", "created_at": "2026-02-13"},
        "circuit": {"id": "diag_pic_kind", "wavelength_nm": 1550},
        "nodes": [{"id": "x1", "kind": "pic.this_does_not_exist", "params": {}}],
        "edges": [],
    }
    diags = validate_graph_semantics(graph)
    error_codes = {d["code"] for d in diags["errors"]}
    assert "kind.unsupported" in error_codes


def test_pic_edge_kind_domain_validation_blocks_mismatch() -> None:
    graph = {
        "schema_version": "0.1",
        "graph_id": "diag_pic_domain",
        "profile": "pic_circuit",
        "metadata": {"title": "diag", "description": "", "created_at": "2026-02-13"},
        "circuit": {"id": "diag_pic_domain", "wavelength_nm": 1550},
        "nodes": [
            {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 100}},
            {"id": "wg2", "kind": "pic.waveguide", "params": {"length_um": 100}},
        ],
        "edges": [
            {"id": "e1", "from": "wg1", "from_port": "out", "to": "wg2", "to_port": "in", "kind": "electrical"}
        ],
    }

    diags = validate_graph_semantics(graph)
    error_codes = {d["code"] for d in diags["errors"]}
    assert "edge.kind_domain" in error_codes
