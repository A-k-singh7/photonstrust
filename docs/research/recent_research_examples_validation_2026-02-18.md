# Recent Research Examples Validation (2026-02-18)

This document defines the research anchors used to validate core PhotonTrust
QKD model behavior and maps each anchor to executable checks.

## Primary Sources

1. Ma, Zeng, Zhou (2018), *Phase-Matching Quantum Key Distribution*,
   Phys. Rev. X 8, 031043.
   - DOI: https://doi.org/10.1103/PhysRevX.8.031043
   - arXiv: https://arxiv.org/abs/1805.05538
   - Used anchors: Eq. (1), Appendix B.2 (Eqs. (B14), (B22), (B23)),
     PLOB reference Eq. (B35), and the `O(sqrt(eta))` scaling claim.

2. Xu, Curty, Qi, Qian, Lo (2013), *Practical aspects of
   measurement-device-independent quantum key distribution*.
   - arXiv: https://arxiv.org/abs/1305.6965
   - Used anchors: asymptotic key-rate Eq. (1) and decoy-state/Appendix
     system modeling references used by the implemented MDI surface.

3. Pirandola et al. (2017), *Fundamental limits of repeaterless quantum
   communications*.
   - DOI: https://doi.org/10.1038/ncomms15043
   - Used anchor: repeaterless secret-key capacity (PLOB bound).

4. Wang et al. (2020/2021), *Gigahertz MDI-QKD at metropolitan distances*.
   - arXiv: https://arxiv.org/abs/2010.14236
   - Used as recent experimental context for scale (non-gating reference).

## Executable Validation Suite

Command:

```bash
python scripts/validation/validate_recent_research_examples.py
```

Output artifact:

- `results/research_validation/recent_research_validation_report.json`

Suite implementation:

- `photonstrust/benchmarks/research_validation.py`

Checks:

1. `spdc_thermal_geometric_statistics`
   - Validates SPDC source emission and multipair probabilities against
     thermal/geometric pair statistics (`P(n) = mu^n/(1+mu)^(n+1)`).

2. `pm_qkd_geometric_mean_asymmetry_scaling`
   - Validates PM-QKD asymmetry handling against `sqrt(eta_a*eta_b)` scaling
     by checking split invariance in a loss-only setting.

3. `direct_link_plob_bound`
   - Validates direct-link BBM92 outputs remain below PLOB repeaterless bound.

4. `mdi_eq1_ec_efficiency_sensitivity`
   - Validates MDI Eq. (1)-consistent behavior: increasing EC overhead
     (`f_ec`) does not increase key rate.

## Notes

- The suite is intended for model-consistency validation against literature
  anchors, not an exact reproduction of hardware-specific finite-size
  experiments.
- Local copies of key reference PDFs used during implementation:
  - `tmp_pmqkd_1805.05538.pdf`
  - `tmp_mdi_1305.6965.pdf`
