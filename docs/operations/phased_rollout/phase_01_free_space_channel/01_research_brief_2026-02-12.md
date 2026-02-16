# Research Brief

## Metadata
- Work item ID: PT-PHASE-01
- Title: Free-space/satellite channel foundation
- Authors: PhotonTrust core team
- Date: 2026-02-12
- Related modules: `photonstrust/channels/*`, `photonstrust/qkd.py`, `photonstrust/config.py`

## 1. Problem and motivation
PhotonTrust was fiber-first and lacked a physically explicit free-space channel
path. This blocked satellite-oriented verification and weakened model coverage
for academic benchmarks spanning terrestrial and orbital links.

## 2. Research questions and hypotheses
- RQ1: Can a minimal decomposition model capture key free-space loss channels
  while staying compatible with existing QKD flow?
- RQ2: Can background counts be propagated into QBER and key-rate penalties
  without breaking existing interfaces?
- H1: Effective channel efficiency should monotonically decrease with distance
  under fixed atmospheric and pointing assumptions.
- H2: Increasing background counts should increase QBER and reduce key rate.

## 3. Related work and baseline methods
Free-space QKD literature and satellite demonstrations motivate decomposed link
loss accounting (geometric, atmospheric, pointing, turbulence).
Current baseline in PhotonTrust was `fiber_loss_db_per_km` only, which is
insufficient for orbital or free-space scenarios.

## 4. Mathematical formulation
The model uses multiplicative channel efficiency:
`eta_total = eta_geom * eta_atm * eta_point * eta_turb * eta_connector`.
Atmospheric path uses airmass-proxied extinction. Pointing loss uses a Gaussian
jitter proxy relative to beam divergence.

## 5. Method design
Implemented deterministic helper functions for each component and a single
aggregation function returning both total efficiency and diagnostics metadata.
QKD path was extended by channel-model switch (`fiber`, `free_space`) to avoid
breaking old configs.

## 6. Experimental design
Controls:
- distance sweep under fixed channel parameters,
- pointing-jitter sweep at fixed distance,
- background count sweep through QKD flow.
Metrics:
- `eta_channel`, `loss_db`, `qber_total`, and `key_rate_bps`.

## 7. Risk and failure analysis
Risk: model is simplified versus full atmospheric optics.
Mitigation: explicit assumption fields and diagnostics payload; future phases
can replace individual components without changing external contracts.

## 8. Reproducibility package
- Deterministic seeds where stochastic components are used.
- Scenario config: `configs/demo5_satellite_downlink.yml`.
- Unit/integration tests under `tests/`.

## 9. Acceptance criteria
- New free-space channel module implemented.
- Existing fiber scenarios remain valid.
- New tests pass.
- End-to-end demo run produces reliability artifacts.

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-12).

## Sources
- All-day free-space QKD protocol (npj QI, 2025):
  https://www.nature.com/articles/s41534-025-01085-y
- Free-space TF-QKD (arXiv, 2025):
  https://arxiv.org/abs/2503.17744
- ESA EAGLE-1 program context:
  https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Eagle-1
