"""Check completeness of pilot readiness packet files."""

from __future__ import annotations

from pathlib import Path


REQUIRED_PACKET_FILES = (
    "README.md",
    "01_pilot_intake_checklist.md",
    "02_pilot_success_criteria_template.md",
    "03_claim_boundaries_summary.md",
    "04_day0_operator_runbook.md",
    "05_external_pilot_cycle_outcome_template.md",
    "06_external_pilot_gate_log_template.md",
    "07_pilot_to_paid_conversion_memo_template.md",
    "08_support_runbook_handoff_checklist.md",
    "pilot_cycle_01_outcome_example.md",
    "pilot_cycle_02_outcome_example.md",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    packet_dir = repo_root / "docs" / "operations" / "pilot_readiness_packet"

    missing = [name for name in REQUIRED_PACKET_FILES if not (packet_dir / name).exists()]
    if missing:
        print("Pilot readiness packet check: FAIL")
        for name in missing:
            print(f" - missing: {packet_dir / name}")
        return 1

    print("Pilot readiness packet check: PASS")
    print(f"Checked {len(REQUIRED_PACKET_FILES)} required files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
