# PIC Upgrade Wave 2 ("much better") — 2026-02-16

## What was added now

The PIC verification core was expanded from 4 checks to a broader signoff-oriented set:

1. **Design-rule envelope check**
   - `verify_design_rule_envelope(...)`
   - Enforces PDK minimums for waveguide width, coupler gap, and bend radius.

2. **Thermal-crosstalk matrix check**
   - `verify_thermal_crosstalk_matrix(...)`
   - Models heater-to-victim thermal coupling and verifies victim temperature/phase limits.

3. **Resonance alignment check**
   - `verify_resonance_alignment(...)`
   - Verifies wavelength detune (pm) and optional linewidth bounds for ring/filter channels.

4. **Phase-shifter range/power check**
   - `verify_phase_shifter_range(...)`
   - Verifies required phase span is reachable under per-shifter and optional total-power budgets.

5. **Signoff bundle aggregation expanded**
   - `verify_layout_signoff_bundle(...)` now supports all checks above in one pass/fail bundle with score and consolidated violations.

Exports updated in:
- `photonstrust/pic/layout/verification/__init__.py`

Tests expanded in:
- `tests/test_pic_layout_verification_core.py`

## Validation status

- Targeted PIC verification tests: **9 passed**
- Full suite: **182 passed, 7 skipped**
- Release gate: **PASS**

## Next ideas (Wave 3 candidates)

1. **Statistical yield for PIC signoff**
   - Add yield-estimation mode (e.g., Gaussian/Monte Carlo) on top of process variation + resonance checks.

2. **Frequency-domain spectral checks**
   - Add pass/fail checks for extinction ratio, insertion loss ripple, and channel spacing over wavelength sweep.

3. **Control-loop robustness checks**
   - Verify heater DAC quantization + drift margins (can the control loop retune back inside spec?).

4. **PDK-specific signoff profiles**
   - Named profiles (`generic`, `foundry_A`, `foundry_B`) with fixed limits and report templates.

5. **Evidence-grade signoff artifacts**
   - Emit signed signoff JSON + compact HTML/PDF for customer-facing PIC verification evidence.
