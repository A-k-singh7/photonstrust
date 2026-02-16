# Phase 43: MDI-QKD + TF/PM-QKD Protocol Surfaces (Research Brief)

Date: 2026-02-14

## Goal

Extend PhotonTrust's QKD layer beyond direct-link entanglement-based BBM92-style
rate modeling by adding explicit protocol-family surfaces for:

- MDI-QKD (measurement-device-independent; untrusted relay with Bell-state measurement)
- TF-QKD / PM-QKD (twin-field / phase-matching; single-photon interference at an untrusted relay)

Implement protocol-family key-rate computation for relay-based QKD in a way that
is faithful to the published analytical models (no placeholder scaling laws).

The intent is not to over-claim beyond what is implemented. The intent is to:

1) make protocol selection explicit in config and in artifacts,
2) implement the actual security-model key-rate equations (MDI-QKD and PM-QKD)
   anchored to primary sources,
3) prevent incorrect sanity gates (e.g., naive PLOB comparisons) from flagging
   protocols whose network structure changes the applicable bounds.

## Primary anchors (protocol papers)

MDI-QKD:

- H.-K. Lo, M. Curty, B. Qi, "Measurement-Device-Independent Quantum Key Distribution",
  Physical Review Letters 108, 130503 (2012).
  DOI: 10.1103/PhysRevLett.108.130503

- Feihu Xu, Marcos Curty, Bing Qi, Li Qian, Hoi-Kwong Lo,
  "Practical aspects of measurement-device-independent quantum key distribution",
  New J. Phys. 15 113007 (2013).
  arXiv:1305.6965

TF-QKD:

- M. Lucamarini, Z. L. Yuan, J. F. Dynes, A. J. Shields,
  "Overcoming the rate-distance barrier of quantum key distribution without using quantum repeaters",
  Nature 557, 400-403 (2018).
  arXiv:1811.06826, DOI: 10.1038/s41586-018-0066-6

PM-QKD:

- X. Ma, P. Zeng, H. Zhou,
  "Phase-Matching Quantum Key Distribution",
  Physical Review X 8, 031043 (2018).
  arXiv:1805.05538, DOI: 10.1103/PhysRevX.8.031043

Security analysis refinement for TF-family (test/code mode idea; helps explain what is being assumed):

- K. Tamaki, H.-K. Lo, W. Wang, M. Lucamarini,
  "Information theoretic security of quantum key distribution overcoming the repeaterless secret key capacity bound",
  arXiv:1805.05511

Sanity bound reference already used in-repo:

- PLOB bound for pure-loss repeaterless secret-key capacity:
  S. Pirandola et al. (2017), DOI: 10.1038/ncomms15043

## What changes physically vs. BBM92-style direct link

### MDI-QKD

Core idea:

- Alice and Bob send states to an untrusted middle relay that performs a
  (possibly imperfect) Bell-state measurement.
- Security does not rely on trusting detectors at the measurement node.

Engineering implications:

- Key rate typically scales with the product of the two segment transmissivities
  (symmetric case behaves like ~ eta_segment^2), so it is often rate-limited vs.
  direct-link decoy BB84 at moderate distances, but it improves security posture.
- Requires two independent transmitters and precise timing/indistinguishability
  constraints at the relay.

Key-rate model anchors (what we will implement):

- Asymptotic secure key-rate expression (Xu et al., arXiv:1305.6965, Eq. (1)):

  R >= P_Z^{1,1} * Y_Z^{1,1} * [1 - H2(e_X^{1,1})] - Q_Z * f_EC * H2(E_Z)

  where Q_Z and E_Z are the signal-state gain and QBER in the Z basis, and
  Y_Z^{1,1} and e_X^{1,1} are the single-photon yield (Z) and phase error (X).

- Two-decoy analytical bounds (Xu et al., arXiv:1305.6965, Sec. 4 / Table 2 / Eqs. (6)-(7)):
  lower bound for Y_Z^{1,1} based on measured gains Q_{qa,qb}^Z.

- System model for coherent-state gains (Xu et al., arXiv:1305.6965, Appendix B.2, Eqs. (B.4)-(B.12)):
  closed-form expressions for Q_Z and E_Z using modified Bessel I0.

Applicability constraints that must be surfaced in artifacts:

- "MDI" is a security posture statement (detector side-channel closure), but a
  concrete key-rate model still requires assumptions about sources, decoy-state
  estimation, and relay detection model.

### TF-QKD / PM-QKD

Core idea:

- Alice and Bob send phase-randomized coherent states to an untrusted relay.
- The relay performs single-photon interference / phase matching; key is encoded
  in a global phase relation.

Why this interacts with PLOB:

- PLOB bounds a *point-to-point pure-loss channel* between Alice and Bob.
- TF/PM introduce an untrusted relay and effectively operate over two segments.
  It is therefore expected that a direct PLOB comparison against the full
  end-to-end loss can become a false-positive sanity check.

Key-rate model anchors (what we will implement):

- PM-QKD sifted-bit key rate (Ma et al., arXiv:1805.05538, Eq. (1)):

  r_PM >= 1 - H(EZ_mu) - H(EX_mu)

- Practical key rate with phase slicing (Ma et al., arXiv:1805.05538, Eq. (4) and Appendix B.2 Eq. (B23)):

  R_PM >= (2/M) * Q_mu * [1 - f_EC * H(EZ_mu) - H(EX_mu)]

- Phase error bound in terms of photon-number components (Ma et al., arXiv:1805.05538, Eq. (2)-(3) and Appendix B.2 Eq. (B24)):
  EX_mu expressed via {q_k}, {Y_k}, and {e_k^Z}.

Applicability constraints that must be surfaced:

- TF/PM are extremely sensitive to phase noise / frequency offsets / fiber
  length drift and require stabilization or post-compensation.
- Security proofs can rely on specific mode assumptions and decoy-state
  estimation workflows; a "preview" model must label itself as such.

## Modeling policy for PhotonTrust

PhotonTrust already has a strict anti-overclaim posture (Phase 41 added explicit
notes and applicability warnings; Phase 42 standardized evidence + envelope fields).

For Phase 43:

- Protocol selection becomes explicit in config and artifacts.
- Implementations are anchored to the analytical models in the primary papers above
  (no placeholder scaling law implementations).
- Any remaining assumptions (e.g., symmetric link split, identical detectors at relay,
  omitted hardware stabilization dynamics) are explicitly surfaced in Reliability Card notes.

## Implications for existing sanity gates

`tests/test_qkd_plob_bound.py` currently assumes the modeled protocol is
"repeaterless point-to-point" and checks key_rate <= PLOB(eta_total).

Phase 43 must:

- scope the PLOB gate to direct-link protocol families only (e.g., BBM92-style
  point-to-point models), and
- replace it for relay-based protocols with protocol-appropriate sanity checks
  (non-negative key rate, monotonic vs. distance/loss under symmetric settings,
  and boundedness vs. trivial per-pulse limits).

## Deliverable definition ("protocol surface")

Minimum deliverable for each new protocol family:

- Config:
  - `protocol.name` enumerates the protocol family.
  - Additional required parameters are validated and recorded in artifacts.
- Engine:
  - a deterministic computation path exists for `compute_point`.
- Artifacts:
  - reliability cards explicitly record protocol family and relay assumptions.
  - card notes include a non-overclaim statement aligned to the implemented model scope.
