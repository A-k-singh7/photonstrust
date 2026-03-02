from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.pic.signoff import build_pic_signoff_ladder, verify_pic_signoff_hash_chain
from photonstrust.utils import hash_dict


def _schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pic_signoff_ladder.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _assembly_report(
    *,
    assembly_run_id: str = "abcdef12",
    status: str = "pass",
    failed_links: int = 0,
    output_hash: str = "c" * 64,
) -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-02-26T00:00:00Z",
        "kind": "pic.chip_assembly",
        "assembly_run_id": assembly_run_id,
        "inputs": {
            "graph_hash": "a" * 64,
            "block_refs": [],
        },
        "outputs": {
            "summary": {
                "status": status,
                "assembled_blocks": 0,
                "output_hash": output_hash,
            }
        },
        "stitch": {
            "summary": {
                "status": status,
                "stitched_links": 0,
                "failed_links": failed_links,
            }
        },
        "provenance": {
            "photonstrust_version": "test",
            "python": "3.12",
            "platform": "test",
        },
    }


def _passing_stage_summaries() -> dict:
    return {
        "drc_summary": {
            "run_id": "d" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "failed_check_ids": [],
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
        },
        "lvs_summary": {
            "run_id": "e" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "failed_check_ids": [],
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
        },
        "pex_summary": {
            "run_id": "f" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "failed_check_ids": [],
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
        },
        "foundry_approval": {
            "run_id": "1" * 12,
            "decision": "GO",
            "status": "approved",
        },
    }


def test_build_pic_signoff_ladder_pass_path() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"mode": "default"},
        **_passing_stage_summaries(),
    }

    first = build_pic_signoff_ladder(request)
    second = build_pic_signoff_ladder(request)

    report = first["report"]
    row = report["ladder"][0]

    assert first["decision"] == "GO"
    assert report["kind"] == "pic.signoff_ladder"
    assert report["run_id"] == second["report"]["run_id"]
    assert re.fullmatch(r"[a-f0-9]{12}", report["run_id"])

    assert report["inputs"]["chip_assembly_run_id"] == "abcdef12"
    assert report["inputs"]["chip_assembly_hash"] == hash_dict(assembly_report)
    assert report["inputs"]["policy_hash"] == hash_dict({"mode": "default"})
    assert report["inputs"]["multi_stage_enabled"] is True

    assert [stage["stage"] for stage in report["ladder"]] == [
        "chip_assembly",
        "drc",
        "lvs",
        "pex",
        "foundry_approval",
    ]
    assert row["level"] == 1
    assert row["stage"] == "chip_assembly"
    assert row["status"] == "pass"
    assert row["run_id"] == "abcdef12"
    assert row["evidence_hashes"] == [hash_dict(assembly_report), "c" * 64]
    assert str(row["reason"]).strip()

    assert report["final_decision"]["decision"] == "GO"
    assert len(report["final_decision"]["reasons"]) >= 1
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_fail_path_and_run_id_rules() -> None:
    assembly_report = _assembly_report(
        assembly_run_id="NOT_HEX",
        status="partial",
        failed_links=3,
        output_hash="not-a-valid-hash",
    )
    request = {"assembly_report": assembly_report, "policy": {"strict": True}}

    first = build_pic_signoff_ladder(request, run_id="BAD-RUN-ID")
    second = build_pic_signoff_ladder(request, run_id="BAD-RUN-ID")
    explicit = build_pic_signoff_ladder(request, run_id="deadbeef")

    report = first["report"]
    row = report["ladder"][0]

    assert first["decision"] == "HOLD"
    assert report["run_id"] == second["report"]["run_id"]
    assert re.fullmatch(r"[a-f0-9]{12}", report["run_id"])
    assert explicit["report"]["run_id"] == "deadbeef"

    assert re.fullmatch(r"[a-f0-9]{12}", report["inputs"]["chip_assembly_run_id"])
    assert report["inputs"]["multi_stage_enabled"] is True
    assert row["run_id"] == report["inputs"]["chip_assembly_run_id"]
    assert row["status"] == "fail"
    assert row["evidence_hashes"] == [hash_dict(assembly_report)]
    assert "failed_links" in row["reason"]
    assert [stage["status"] for stage in report["ladder"]] == ["fail", "skipped", "skipped", "skipped", "skipped"]

    assert report["final_decision"]["decision"] == "HOLD"
    assert len(report["final_decision"]["reasons"]) >= 1
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_waived_path_with_full_rule_coverage() -> None:
    assembly_report = _assembly_report(
        status="partial",
        failed_links=3,
        output_hash="not-a-valid-hash",
    )
    request = {
        "assembly_report": assembly_report,
        "policy": {
            "allow_waived_failures": True,
            "active_waiver_rule_ids": [
                "chip_assembly.status_not_pass",
                "chip_assembly.failed_links",
            ],
        },
        **_passing_stage_summaries(),
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    row = report["ladder"][0]

    assert result["decision"] == "GO"
    assert row["status"] == "waived"
    assert "waived failures" in row["reason"]
    assert "chip_assembly.status_not_pass" in row["reason"]
    assert "chip_assembly.failed_links" in row["reason"]
    assert report["final_decision"]["decision"] == "GO"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_partial_waiver_coverage_stays_hold() -> None:
    assembly_report = _assembly_report(
        status="partial",
        failed_links=3,
        output_hash="not-a-valid-hash",
    )
    request = {
        "assembly_report": assembly_report,
        "policy": {
            "allow_waived_failures": True,
            "active_waiver_rule_ids": ["chip_assembly.status_not_pass"],
        },
        **_passing_stage_summaries(),
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    row = report["ladder"][0]

    assert result["decision"] == "HOLD"
    assert row["status"] == "fail"
    assert "failed_links" in row["reason"]
    assert [stage["status"] for stage in report["ladder"]] == ["fail", "skipped", "skipped", "skipped", "skipped"]
    assert report["final_decision"]["decision"] == "HOLD"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_input_validation() -> None:
    with pytest.raises(TypeError, match="request must be an object"):
        build_pic_signoff_ladder("bad")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="request.assembly_report must be an object"):
        build_pic_signoff_ladder({})

    with pytest.raises(ValueError, match="request.assembly_report.kind must be pic.chip_assembly"):
        build_pic_signoff_ladder({"assembly_report": {"kind": "wrong"}})

    with pytest.raises(TypeError, match="request.policy must be an object when provided"):
        build_pic_signoff_ladder({"assembly_report": _assembly_report(), "policy": "bad"})  # type: ignore[arg-type]


def test_build_pic_signoff_ladder_enforces_five_stage_default_with_missing_summaries() -> None:
    result = build_pic_signoff_ladder({"assembly_report": _assembly_report(), "policy": {"mode": "default"}})
    report = result["report"]

    assert [stage["stage"] for stage in report["ladder"]] == [
        "chip_assembly",
        "drc",
        "lvs",
        "pex",
        "foundry_approval",
    ]
    assert [stage["status"] for stage in report["ladder"]] == ["pass", "fail", "skipped", "skipped", "skipped"]
    assert report["inputs"]["multi_stage_enabled"] is True
    assert report["final_decision"]["decision"] == "HOLD"
    assert result["decision"] == "HOLD"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_stage_scoped_waiver_allows_target_stage_only() -> None:
    request = {
        "assembly_report": _assembly_report(),
        "policy": {
            "allow_waived_failures": True,
            "stage_waiver_rule_ids": {
                "drc": ["DRC.WG.MIN_WIDTH"],
            },
        },
        **_passing_stage_summaries(),
    }
    request["drc_summary"] = {
        "run_id": "2" * 12,
        "status": "fail",
        "execution_backend": "generic_cli",
        "failed_check_ids": ["DRC.WG.MIN_WIDTH"],
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]

    assert result["decision"] == "GO"
    assert report["ladder"][1]["stage"] == "drc"
    assert report["ladder"][1]["status"] == "waived"
    assert "DRC.WG.MIN_WIDTH" in report["ladder"][1]["waived_rule_ids"]
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_stage_scoped_waiver_does_not_leak_between_stages() -> None:
    request = {
        "assembly_report": _assembly_report(),
        "policy": {
            "allow_waived_failures": True,
            "stage_waiver_rule_ids": {
                "drc": ["DRC.WG.MIN_WIDTH"],
            },
        },
        **_passing_stage_summaries(),
    }
    request["drc_summary"] = {
        "run_id": "3" * 12,
        "status": "fail",
        "execution_backend": "generic_cli",
        "failed_check_ids": ["DRC.WG.MIN_WIDTH"],
    }
    request["lvs_summary"] = {
        "run_id": "4" * 12,
        "status": "fail",
        "execution_backend": "generic_cli",
        "failed_check_ids": ["DRC.WG.MIN_WIDTH"],
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]

    assert result["decision"] == "HOLD"
    assert report["ladder"][1]["status"] == "waived"
    assert report["ladder"][2]["status"] == "fail"
    assert report["ladder"][3]["status"] == "skipped"
    assert report["ladder"][4]["status"] == "skipped"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_multi_stage_pass_path() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        **_passing_stage_summaries(),
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]

    assert result["decision"] == "GO"
    assert report["final_decision"]["decision"] == "GO"
    assert report["inputs"]["multi_stage_enabled"] is True
    assert len(report["ladder"]) == 5
    assert [row["stage"] for row in report["ladder"]] == [
        "chip_assembly",
        "drc",
        "lvs",
        "pex",
        "foundry_approval",
    ]
    assert all(str(row["status"]).lower() in {"pass", "waived"} for row in report["ladder"])
    assert re.fullmatch(r"[a-f0-9]{64}", str(report.get("evidence_chain_root", "")))
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_multi_stage_waives_foundry_failures() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {
            "multi_stage": True,
            "allow_waived_failures": True,
            "active_waiver_rule_ids": ["DRC.WG.MIN_WIDTH"],
        },
        "drc_summary": {
            "run_id": "2" * 12,
            "status": "fail",
            "execution_backend": "generic_cli",
            "failed_check_ids": ["DRC.WG.MIN_WIDTH"],
        },
        "lvs_summary": {"run_id": "3" * 12, "status": "pass", "execution_backend": "generic_cli", "failed_check_ids": []},
        "pex_summary": {"run_id": "4" * 12, "status": "pass", "execution_backend": "generic_cli", "failed_check_ids": []},
        "foundry_approval": {"run_id": "5" * 12, "decision": "GO"},
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    drc_row = report["ladder"][1]

    assert result["decision"] == "GO"
    assert drc_row["stage"] == "drc"
    assert drc_row["status"] == "waived"
    assert "DRC.WG.MIN_WIDTH" in drc_row["waived_rule_ids"]
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_multi_stage_fail_fast_on_drc() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        "drc_summary": {
            "run_id": "6" * 12,
            "status": "fail",
            "execution_backend": "generic_cli",
            "failed_check_ids": ["DRC.WG.MIN_SPACING"],
        },
        "lvs_summary": {"run_id": "7" * 12, "status": "pass", "execution_backend": "generic_cli", "failed_check_ids": []},
        "pex_summary": {"run_id": "8" * 12, "status": "pass", "execution_backend": "generic_cli", "failed_check_ids": []},
        "foundry_approval": {"run_id": "9" * 12, "decision": "GO"},
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]

    assert result["decision"] == "HOLD"
    assert report["final_decision"]["decision"] == "HOLD"
    assert report["ladder"][1]["stage"] == "drc"
    assert report["ladder"][1]["status"] == "fail"
    assert report["ladder"][2]["status"] == "skipped"
    assert report["ladder"][3]["status"] == "skipped"
    assert report["ladder"][4]["status"] == "skipped"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


@pytest.mark.parametrize(
    ("stage", "backend"),
    [
        ("drc", ""),
        ("lvs", "mock"),
        ("pex", "stub"),
    ],
)
def test_build_pic_signoff_ladder_rejects_pass_stage_with_unacceptable_backend(stage: str, backend: str) -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        **_passing_stage_summaries(),
    }
    summary_key = f"{stage}_summary"
    request[summary_key]["execution_backend"] = backend

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    stage_index = {"drc": 1, "lvs": 2, "pex": 3}[stage]
    stage_row = report["ladder"][stage_index]

    assert result["decision"] == "HOLD"
    assert stage_row["status"] == "error"
    assert stage_row["failure_rule_ids"] == [f"{stage}.backend_not_acceptable"]
    assert "requires execution_backend" in stage_row["reason"]
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


@pytest.mark.parametrize("stage", ["drc", "lvs", "pex"])
def test_build_pic_signoff_ladder_rejects_pass_stage_with_empty_check_set(stage: str) -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        **_passing_stage_summaries(),
    }
    summary_key = f"{stage}_summary"
    request[summary_key]["check_counts"]["total"] = 0
    request[summary_key]["check_counts"]["passed"] = 0

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    stage_index = {"drc": 1, "lvs": 2, "pex": 3}[stage]
    stage_row = report["ladder"][stage_index]

    assert result["decision"] == "HOLD"
    assert stage_row["status"] == "error"
    assert stage_row["failure_rule_ids"] == [f"{stage}.empty_check_set"]
    assert "check_counts.total=0" in stage_row["reason"]
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_detects_pass_status_contradiction_in_foundry_summary() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        **_passing_stage_summaries(),
    }
    request["drc_summary"] = {
        "run_id": "a" * 12,
        "status": "pass",
        "execution_backend": "generic_cli",
        "failed_check_ids": ["DRC.WG.MIN_WIDTH"],
        "check_counts": {"total": 1, "passed": 0, "failed": 0, "errored": 1},
    }

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    drc_row = report["ladder"][1]

    assert result["decision"] == "HOLD"
    assert drc_row["stage"] == "drc"
    assert drc_row["status"] == "error"
    assert drc_row["failure_rule_ids"] == ["drc.status_pass_contradiction"]
    assert "failed_check_ids=1" in drc_row["reason"]
    assert "check_counts.errored=1" in drc_row["reason"]
    assert report["ladder"][2]["status"] == "skipped"
    assert report["ladder"][3]["status"] == "skipped"
    assert report["ladder"][4]["status"] == "skipped"
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_build_pic_signoff_ladder_detects_foundry_approval_decision_status_mismatch() -> None:
    assembly_report = _assembly_report()
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        **_passing_stage_summaries(),
    }
    request["foundry_approval"] = {"run_id": "2" * 12, "decision": "GO", "status": "rejected"}

    result = build_pic_signoff_ladder(request)
    report = result["report"]
    approval_row = report["ladder"][4]

    assert result["decision"] == "HOLD"
    assert approval_row["stage"] == "foundry_approval"
    assert approval_row["status"] == "hold"
    assert approval_row["failure_rule_ids"] == ["foundry_approval.decision_status_mismatch"]
    assert "decision=go" in approval_row["reason"]
    assert "status=rejected" in approval_row["reason"]
    assert verify_pic_signoff_hash_chain(report) is True
    validate(instance=report, schema=_schema())


def test_verify_pic_signoff_hash_chain_detects_missing_stage_hash() -> None:
    request = {
        "assembly_report": _assembly_report(),
        "policy": {"mode": "default"},
        **_passing_stage_summaries(),
    }
    report = build_pic_signoff_ladder(request)["report"]
    report["ladder"][2].pop("stage_hash")

    with pytest.raises(ValueError, match="stage_hash"):
        verify_pic_signoff_hash_chain(report)


def test_verify_pic_signoff_hash_chain_detects_tamper() -> None:
    request = {
        "assembly_report": _assembly_report(),
        "policy": {"mode": "default"},
        **_passing_stage_summaries(),
    }
    report = build_pic_signoff_ladder(request)["report"]
    report["ladder"][3]["reason"] = "tampered"

    with pytest.raises(ValueError, match="tamper detected"):
        verify_pic_signoff_hash_chain(report)


def test_verify_pic_signoff_hash_chain_detects_stage_reordering() -> None:
    request = {
        "assembly_report": _assembly_report(),
        "policy": {"mode": "default"},
        **_passing_stage_summaries(),
    }
    report = build_pic_signoff_ladder(request)["report"]
    report["ladder"][1], report["ladder"][2] = report["ladder"][2], report["ladder"][1]

    with pytest.raises(ValueError, match=r"report\.ladder\[1\]\.level must be 2"):
        verify_pic_signoff_hash_chain(report)
