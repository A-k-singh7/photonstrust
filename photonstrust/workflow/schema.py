"""Schema helpers for workflow and evidence bundle artifacts."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # .../photonstrust/workflow/schema.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def workflow_invdesign_chain_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_workflow_invdesign_chain_report.v0.schema.json").resolve()


def workflow_chip_chain_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_workflow_chip_chain_report.v0.schema.json").resolve()


def pic_chip_assembly_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_chip_assembly.v0.schema.json").resolve()


def pic_signoff_ladder_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_signoff_ladder.v0.schema.json").resolve()


def evidence_bundle_manifest_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.evidence_bundle_manifest.v0.schema.json").resolve()


def evidence_bundle_signature_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.evidence_bundle_signature.v0.schema.json").resolve()


def evidence_bundle_publish_manifest_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.evidence_bundle_publish_manifest.v0.schema.json").resolve()


def multifidelity_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.multifidelity_report.v0.schema.json").resolve()


def pic_foundry_drc_sealed_summary_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_foundry_drc_sealed_summary.v0.schema.json").resolve()


def pic_foundry_lvs_sealed_summary_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_foundry_lvs_sealed_summary.v0.schema.json").resolve()


def pic_foundry_pex_sealed_summary_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_foundry_pex_sealed_summary.v0.schema.json").resolve()


def pic_foundry_approval_sealed_summary_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_foundry_approval_sealed_summary.v0.schema.json").resolve()


def event_trace_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.event_trace.v0.schema.json").resolve()


def protocol_steps_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.protocol_steps.v0.schema.json").resolve()


def external_sim_result_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.external_sim_result.v0.schema.json").resolve()


def day10_tapeout_rehearsal_packet_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.day10_tapeout_rehearsal_packet.v0.schema.json").resolve()


def pic_tapeout_gate_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_tapeout_gate.v0.schema.json").resolve()


def pic_qkd_certificate_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_qkd_certificate.v0.schema.json").resolve()


def etsi_qkd_compliance_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.etsi_qkd_compliance_report.v0.schema.json").resolve()


def m3_checkpoint_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.m3_checkpoint_report.v0.schema.json").resolve()
