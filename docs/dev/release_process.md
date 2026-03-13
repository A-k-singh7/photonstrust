# Release Process

PhotonTrust uses explicit release-gate and evidence workflows.

## Core Release Commands

```bash
python scripts/release/release_gate_check.py --output results/release_gate/release_gate_report.json
python scripts/release/build_release_gate_packet.py
python scripts/release/sign_release_gate_packet.py
python scripts/release/verify_release_gate_packet.py
python scripts/release/verify_release_gate_packet_signature.py
```

## Typical Flow

1. Run CI and targeted validation checks.
2. Run the release gate.
3. Build the release gate packet.
4. Sign and verify the packet.
5. Review tracked evidence under `reports/` and intentional `results/` subtrees.

## Supporting Docs

- `../../CHANGELOG.md`
- `../operations/program_completion_report_2026-02-12.md`
- `../operations/product/phase1_ci_strengthening_2026-03-04.md`
