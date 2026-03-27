# PhotonsTrust Phase B Expansion: Deep Scientific Research Report

## Executive Summary

This report provides the physics models, key equations, parameter requirements, and integration
points for eight Phase B expansion areas of the PhotonsTrust QKD simulation framework. All
equations are presented in implementation-ready form for Python/NumPy. Each section includes
references to real papers, exact formulas, required parameters, and how the new module connects
to existing Phase A components.

---

## 1. Advanced QKD Protocols

### 1.1 Measurement-Device-Independent QKD (MDI-QKD) Enhancements

**Existing Phase A state:** `photonstrust/qkd_protocols/mdi_qkd.py` already implements the
asymptotic key rate from Xu et al. (arXiv:1305.6965) with two-decoy bounds.

**Phase B enhancements: Finite-key composable MDI-QKD**

**Key Rate Formula (asymptotic, Lo-Curty-Qi 2012):**

```
R = Q_11^Z * [1 - H(e_11^X)] - Q_mu_nu^Z * f * H(E_mu_nu^Z)
```

where:
- `Q_11^Z`: gain of single-photon pairs in the Z basis
- `e_11^X`: phase error rate of single-photon pairs in the X basis
- `Q_mu_nu^Z`: overall gain when Alice sends intensity mu, Bob sends intensity nu
- `E_mu_nu^Z`: overall QBER
- `f`: error correction inefficiency (typically f ~ 1.16)
- `H(x) = -x*log2(x) - (1-x)*log2(1-x)`: binary entropy

**Three-intensity decoy bounds for Y_11 (single-photon yield):**

```
Y_11^L = (mu * Q_nu_nu^Z * e^(nu) - nu * Q_mu_mu^Z * e^(mu)) / (mu * nu * (mu - nu))
```

**Finite-key MDI-QKD key length (composable, Curty et al. 2014):**

```
l = s_0^Z + s_1^Z * [1 - H(phi_1^Z)] - lambda_EC
    - 6*log2(21/eps_sec) - log2(2/eps_cor)
```

where:
- `s_0^Z, s_1^Z`: vacuum and single-photon counts in the Z basis
- `phi_1^Z`: phase error rate upper bound for single-photon events
- `lambda_EC`: error correction leakage
- `eps_sec, eps_cor`: security and correctness parameters

**Parameters needed:**
- `mu_a, mu_b`: signal intensities for Alice/Bob
- `nu_a, nu_b`: decoy intensities
- `omega_a, omega_b`: vacuum intensities (for 3-intensity)
- `p_mu, p_nu, p_omega`: intensity selection probabilities
- `N`: total number of signals sent
- `epsilon_sec, epsilon_cor`: composable security parameters

**References:**
- Lo, Curty, Qi, PRL 108, 130503 (2012)
- Xu, Curty, Qi, Qian, Lo, "Practical aspects of MDI-QKD", arXiv:1305.6965
- Curty et al., "Finite-key analysis for MDI-QKD", Nature Comms 5, 3732 (2014)

**Integration with Phase A:** Extends `mdi_qkd.py` by adding the finite-key layer from
`finite_key_composable.py` (EpsilonBudget class). Reuses `compute_channel_diagnostics`
for segment attenuation and `build_detector_profile` for detection modeling.

---

### 1.2 Twin-Field QKD (TF-QKD) / Phase-Matching QKD

**Existing Phase A state:** `photonstrust/qkd_protocols/pm_qkd.py` implements PM-QKD
from Ma, Zeng, Zhou (Phys. Rev. X 8, 031043, 2018).

**Phase B enhancement: Sending-or-Not-Sending (SNS) variant with improved bounds**

**PLOB Bound (repeaterless bound):**

```
C_PLOB = -log2(1 - eta)   [bits per channel use]
```

For eta << 1: `C_PLOB ~ 1.44 * eta`

TF-QKD/PM-QKD achieves `R ~ O(sqrt(eta))`, beating this bound.

**SNS-TF-QKD Key Rate (Wang et al. 2018):**

```
R = (2/N) * {s_1^L * [1 - H(e_1^ph,U)] - f * n_t * H(E_mu)}
```

where:
- `s_1^L`: lower bound on single-photon detection events
- `e_1^ph,U`: upper bound on single-photon phase error rate
- `n_t`: total detection events in signal windows
- `N`: total number of pulses sent
- Factor of 2 accounts for the relay being in the middle

**Single-photon yield in TF-QKD (sending-or-not-sending):**

For Alice/Bob with link transmittances `eta_a, eta_b`:

```
Y_1 ~ eta_eff * eta_d + p_dark

where eta_eff = sqrt(eta_a * eta_b)  [for symmetric case]
```

The key scaling advantage:

```
R_TF ~ O(sqrt(eta_a * eta_b))   vs.   R_BB84 ~ O(eta_a * eta_b)
```

**Phase-matching gain and error (Ma et al. 2018, Eq. B14, B22):**

```
Q_mu = sum_{k=0}^{inf} [p_k(mu_a) * p_l(mu_b) * Y_{k,l}]

E_mu^Z = sum_{k} [p_k * Y_k * e_k^Z] / Q_mu
```

where `p_k(mu) = e^{-mu} * mu^k / k!` is the Poisson distribution.

**Parameters needed:**
- `mu_s`: signal intensity (optimized, typically ~ 0.1-0.5)
- `mu_1, mu_2`: decoy intensities
- `p_s`: probability of choosing "sending" (vs "not sending")
- `delta_phase`: phase slice width (typically pi/M for M slices)
- `M`: number of phase slices (typically 16)
- All channel and detector parameters from existing PM-QKD model

**References:**
- Lucamarini, Yuan, Dynes, Shields, Nature 557, 400 (2018)
- Ma, Zeng, Zhou, Phys. Rev. X 8, 031043 (2018)
- Wang, Yu, Hu, PRX Quantum 3, 040307 (2022) - SNS with tight finite-key
- Pirandola, Laurenza, Ottaviani, Banchi, Nature Comms 8, 15043 (2017) - PLOB bound

**Integration with Phase A:** Direct extension of `pm_qkd.py` with the `tf_variant=True`
flag. SNS protocol adds a new code path. Reuses relay segment channel diagnostics and
`relay_split_distances_km` from `common.py`.

---

### 1.3 Continuous-Variable QKD (CV-QKD)

**This is a new protocol family not present in Phase A.**

**GG02 Protocol Key Rate (Gaussian-modulated coherent states, asymptotic):**

**Homodyne detection (reverse reconciliation):**

```
K = beta * I(A;B) - chi(B;E)
```

**Mutual information I(A;B):**

```
I_AB_hom = 0.5 * log2(1 + SNR)

SNR = eta * T * V_A / (1 + eta * T * xi + (1-eta*T) * N_0 + v_el)
```

where:
- `V_A`: modulation variance (in shot-noise units, SNU)
- `T`: channel transmittance
- `eta`: detector quantum efficiency
- `xi`: excess noise (in SNU, referred to channel input)
- `N_0 = 1`: vacuum noise (shot noise unit)
- `v_el`: electronic noise variance (SNU)
- `beta`: reconciliation efficiency (typically 0.95-0.98)

**Heterodyne detection:**

```
I_AB_het = log2(1 + SNR_het)

SNR_het = eta * T * V_A / (2 + eta * T * xi + 2*v_el)
```

(Note: heterodyne measures both quadratures simultaneously, factor of 2 in denominator.)

**Holevo bound chi(B;E) for collective attacks:**

For a thermal-loss channel with excess noise:

```
chi(B;E) = g((lambda_1 - 1)/2) + g((lambda_2 - 1)/2)
           - g((lambda_3 - 1)/2) - g((lambda_4 - 1)/2)
```

where `g(x) = (x+1)*log2(x+1) - x*log2(x)` is the bosonic entropic function, and
`lambda_{1,2,3,4}` are the symplectic eigenvalues of the covariance matrix:

```
gamma_AB = [[V*I,  sqrt(T)*Z],
            [sqrt(T)*Z,  T*(V + xi)*I]]

where V = V_A + 1, Z = sqrt(V^2 - 1) * sigma_z, I = identity(2)
```

Symplectic eigenvalues:
```
lambda_{1,2}^2 = 0.5 * [A +/- sqrt(A^2 - 4*B)]

A = V^2 + T^2*(V + xi)^2 - 2*T*(V^2 - 1)
B = [T*(V*xi + V + xi) - V^2 + 1]^2   [simplified for homodyne]
```

**Finite-size CV-QKD key rate:**

```
K_finite = (n / N) * [beta * I(A;B) - chi(B;E) - Delta(n)]

Delta(n) = (2*d + 1) * sqrt(log2(2/eps_s) / n)
         + log2(2/eps_h) / n
         + 2 * log2(2/(eps_pa * eps_s)) / n
```

where `n` is the number of signals used for key generation, `N` the total, `d` the
dimension of the parameter estimation problem.

**Parameters needed:**
- `V_A`: modulation variance (SNU), typically 1-40
- `T` or equivalently `eta_channel`: channel transmittance
- `xi`: excess noise (SNU), typically 0.001-0.05
- `eta_det`: detector quantum efficiency (homodyne/heterodyne)
- `v_el`: electronic noise variance
- `beta`: reconciliation efficiency
- `detection_type`: "homodyne" or "heterodyne"
- `f_rep`: repetition rate
- `N`: total signals, `n`: key generation signals
- `epsilon_s, epsilon_h, epsilon_pa`: composable security parameters

**References:**
- Grosshans, Grangier, PRL 88, 057902 (2002) - GG02 protocol
- Weedbrook et al., PRL 93, 170504 (2004) - no-switching (heterodyne)
- Leverrier, PRL 114, 070501 (2015) - composable security against coherent attacks
- Laudenbach et al., Adv. Quantum Tech. 1, 1800011 (2018) - comprehensive review
- Pirandola, Nature Comms 8, 15043 (2017) - PLOB bound

**Integration with Phase A:**
- New protocol engine in `qkd_protocols/cv_qkd.py`
- Reuses `channels/fiber.py` for `T = 10^(-alpha*L/10)` and `channels/free_space.py`
- Requires new detector model class for homodyne/heterodyne in `physics/detector.py`
  (efficiency, electronic noise, local oscillator power, common-mode rejection ratio)
- Connects to `finite_key_composable.py` via the epsilon-chain framework

---

### 1.4 Device-Independent QKD (DI-QKD)

**Devetak-Winter asymptotic key rate:**

```
R >= H(A|E) - H(A|B)
```

**Bound on H(A|E) from CHSH violation:**

For a measured CHSH value S (2 < S <= 2*sqrt(2)):

```
H(A|E) >= 1 - h((1 + sqrt((S/2)^2 - 1)) / 2)
```

where `h(x)` is the binary entropy function. This is the Pironio et al. (2009) bound.

**CHSH parameter:**

```
S = |<A_0 B_0> + <A_0 B_1> + <A_1 B_0> - <A_1 B_1>|
```

Classical bound: S <= 2. Quantum maximum (Tsirelson bound): S = 2*sqrt(2) ~ 2.828.

**H(A|B) from observed QBER Q:**

```
H(A|B) = h(Q)
```

**Complete DI-QKD key rate (asymptotic, collective attacks):**

```
r = 1 - h((1 + sqrt((S/2)^2 - 1)) / 2) - h(Q)
```

**Finite-key DI-QKD (entropy accumulation, Arnon-Friedman et al. 2018):**

```
l >= H_min^eps(A^n | E) - lambda_EC - log2(2/eps_cor)

H_min^eps(A^n | E) >= n * r_opt(S_obs) - sqrt(n) * v * sqrt(1 - 2*log(eps_s * eps_EA))
```

where `r_opt(S_obs)` is the single-round rate evaluated at the observed CHSH value,
`v` is related to the range of the min-tradeoff function, and `eps_EA` is the
entropy accumulation smoothing parameter.

**Parameters needed:**
- `S_obs`: observed CHSH value
- `Q`: observed QBER
- `n`: number of rounds
- `eps_sec, eps_cor, eps_EA`: security parameters
- `detection_efficiency`: critical -- requires eta > ~83% for loophole-free
- `visibility`: interference visibility of entangled pairs
- `heralding_efficiency`: for heralded entanglement sources

**References:**
- Pironio et al., New J. Phys. 11, 045021 (2009)
- Vazirani, Vidick, PRL 113, 140501 (2014)
- Arnon-Friedman et al., Nature Comms 9, 459 (2018) - entropy accumulation
- Acin, Brunner, Gisin, Massar, Pironio, PRL 98, 230501 (2007)
- Nadlinger et al., Nature 607, 682 (2022) - experimental DI-QKD

**Integration with Phase A:**
- New module `qkd_protocols/di_qkd.py`
- Connects to `qkd_protocols/bbm92.py` for entanglement source modeling
- Requires Bell inequality evaluation engine (new module)
- Detection efficiency model from `physics/detector.py` is critical
- Finite-key layer from `finite_key_composable.py`

---

## 2. Quantum Network Layer

### 2.1 Quantum Repeaters (1G/2G/3G)

**Existing Phase A state:** `photonstrust/repeater.py` has basic repeater spacing optimization
using `_chain_metrics`, `physics/memory.py` provides T1/T2 memory model.

**First-Generation Repeater (Briegel et al., 1998):**

Heralded entanglement generation + entanglement purification + swapping.

**Elementary link generation rate:**

```
R_link = f_rep * p_link / 2

p_link = 1 - (1 - eta_source * eta_channel * eta_det)^M
```

where:
- `f_rep`: repetition rate
- `p_link`: probability of heralded success per attempt across M multiplexed modes
- `eta_source`: source heralding efficiency
- `eta_channel = 10^(-alpha * L_seg / (2 * 10))`: channel transmittance per half-segment
- `M`: number of multiplexed modes (spatial/temporal/spectral)
- Factor `/2` accounts for two-way classical communication

**Waiting time for n-segment repeater chain (Briegel et al.):**

```
T_wait(n) = (3 * L_seg / (2 * c)) * sum_{k=1}^{n} (1/p_link_k)
```

For identical segments: `T_wait ~ (3L_0 / (2c)) * n / p_link`

More precise (Collins et al. 2007):

```
<T_n> = (L_0/c) * H_n / p_link

H_n = sum_{k=1}^{n} 1/k   (harmonic number)
```

**Entanglement swapping fidelity degradation:**

After m levels of swapping (with Bell-state measurement success probability p_BSM):

```
F_swap = 0.5 + 0.5 * (2*F_link - 1)^(2^m)

p_BSM = 0.5  (linear optics, without photon-number resolution)
p_BSM = 1.0  (ideal, with PNR detectors or deterministic gates)
```

**Second-Generation Repeater (quantum error correction):**

Key rate with QEC:

```
R_2G = f_rep * p_enc * R_code / (n_code * T_cycle)
```

where `n_code` is the number of physical qubits per logical qubit, `R_code` is
the code rate, and `T_cycle` is the cycle time per encoded Bell pair distribution.

**Third-Generation Repeater (all-photonic, Azuma et al. 2015):**

```
R_3G ~ f_rep * (eta_link)^(1/n_seg)
```

Uses photonic cluster states; no quantum memory needed. Rate scales with
n-th root of total transmittance for n segments.

**Parameters needed:**
- `n_segments`: number of repeater segments
- `L_total, L_seg`: total and segment distances
- `p_link`: link success probability
- `M`: multiplexing factor
- `F_link`: elementary link fidelity
- `p_BSM`: Bell-state measurement success probability
- Memory parameters: `T1, T2, eta_store, eta_retrieve` (from Phase A memory model)
- `n_code`: QEC code size (2G)
- `n_purification_rounds`: for 1G

**References:**
- Briegel, Dur, Cirac, Zoller, PRL 81, 5932 (1998)
- Duan, Lukin, Cirac, Zoller, Nature 414, 413 (2001) - DLCZ
- Azuma, Economou, Elkouss, Stace, Rudolph, PRL 115, 010502 (2015) - all-photonic
- Muralidharan et al., Sci. Rep. 6, 20463 (2016) - generation comparison
- Collins, Jenkins, Kuzmich, PRL 98, 060502 (2007) - multiplexed repeaters

**Integration with Phase A:**
- Extends `repeater.py` with full 1G/2G/3G models
- Reuses `physics/memory.py` (T1/T2 analytic and QuTiP models) for 1G/2G
- Extends `network/routing.py` for repeater-aware path selection
- Connects to `channels/fiber.py` for per-segment channel loss

---

### 2.2 Entanglement Swapping and Purification

**Entanglement Swapping (Bell-state measurement):**

Input: two Bell pairs |Phi+>_{A,R1} and |Phi+>_{R2,B}
After BSM on qubits R1, R2:

```
F_swapped = F_1 * F_2 + (1 - F_1) * (1 - F_2) / 3
```

(for Werner states with input fidelities F_1 and F_2)

**BBPSSW Purification Protocol (Bennett et al. 1996):**

Input: two identical Werner states with fidelity F.
Output fidelity (on success):

```
F' = (F^2 + (1-F)^2/9) / (F^2 + 2*F*(1-F)/3 + 5*(1-F)^2/9)

p_success = F^2 + 2*F*(1-F)/3 + 5*(1-F)^2/9
```

Purification succeeds when F > 0.5, converges to F -> 1.

**DEJMPS Purification Protocol (Deutsch et al. 1996):**

More general -- works on Bell-diagonal states without twirl.
For Bell-diagonal state with coefficients (A, B, C, D) where A+B+C+D = 1:

```
A' = (A^2 + B^2) / N
B' = 2*C*D / N
C' = (C^2 + D^2) / N
D' = 2*A*B / N

N = (A + B)^2 + (C + D)^2   (normalization / success probability)
```

Fidelity to |Phi+> is coefficient A.

**Recurrence purification with n rounds:**

Apply iteratively: F_0 -> F_1 -> ... -> F_n.

```python
def dejmps_round(A, B, C, D):
    N = (A + B)**2 + (C + D)**2
    return (A**2 + B**2)/N, 2*C*D/N, (C**2 + D**2)/N, 2*A*B/N, N
```

**Parameters needed:**
- Input fidelity `F` or Bell-diagonal coefficients `(A, B, C, D)`
- Number of purification rounds
- `p_BSM`: Bell-state measurement success probability
- Gate error rates (for imperfect local operations)
- `p_gate`: two-qubit gate fidelity

**References:**
- Bennett et al., PRL 76, 722 (1996) - BBPSSW
- Deutsch et al., PRL 77, 2818 (1996) - DEJMPS
- Dur, Briegel, Rep. Prog. Phys. 70, 1381 (2007)

**Integration with Phase A:**
- New module `network/purification.py`
- Connects to repeater chain model in `repeater.py`
- Memory decoherence during purification rounds handled by `physics/memory.py`

---

### 2.3 Quantum Memory Models

**Existing Phase A state:** `physics/memory.py` implements T1/T2 decay (analytic + QuTiP).

**Phase B enhancements: Platform-specific models**

**Nitrogen-Vacancy (NV) centers in diamond:**

```
T2* ~ 1 / (n_bath * A_hf)        [free induction decay]
T2  ~ 10 ms - 1 s (with DD)      [dynamical decoupling extended]
T1  ~ 6 ms at 300K, hours at 4K

Fidelity(t) = 0.5 + 0.5 * exp(-(t/T2)^n_se)

where n_se ~ 1-3 (stretched exponential parameter)
```

**Trapped ion memories (e.g., 171-Yb+):**

```
T2  ~ 10 min (hyperfine qubit)
T1  ~ hours
eta_store ~ 0.5-0.9
eta_retrieve ~ 0.5-0.9
F_gate ~ 0.99-0.999
```

**Rare-earth doped crystals (e.g., Eu:YSO, Pr:YSO):**

```
T2       ~ 6 hours (at 2K, Eu:YSO with ZEFOZ)
T_store  ~ 1 hour (record)
eta      ~ 0.5-0.9 (AFC protocol)
Bandwidth ~ 10 MHz - 10 GHz (AFC)
Multimode capacity: N_modes ~ T_store * BW
```

**AFC (Atomic Frequency Comb) storage efficiency:**

```
eta_AFC = (d_eff)^2 * exp(-d_eff) * exp(-7/F^2) * eta_reemission

d_eff = d / F    (effective optical depth)
F = Delta / gamma  (finesse: comb spacing / tooth width)
```

**General decoherence model (extension of existing):**

```
rho(t) = E(t) * rho(0) * E(t)^dagger

E_depol(t) = sqrt(1 - p(t)) * I + sqrt(p(t)/3) * (X, Y, Z)

p(t) = 1 - (1/4) * (1 + 3*exp(-t/T1)) * (1 + exp(-t/T_phi))
      where 1/T2 = 1/(2*T1) + 1/T_phi
```

**Parameters needed (per platform):**
- `T1, T2`: longitudinal/transverse relaxation times
- `T_phi`: pure dephasing time (1/T_phi = 1/T2 - 1/(2*T1))
- `eta_store, eta_retrieve`: write/read efficiencies
- `n_modes`: multimode capacity
- `bandwidth_mhz`: storage bandwidth
- `gate_fidelity`: local gate fidelity
- `platform`: "nv_diamond", "trapped_ion", "rare_earth", "quantum_dot"
- `n_se`: stretched exponential parameter for NV

**References:**
- Heshami et al., J. Mod. Opt. 63, 2005 (2016) - review of quantum memories
- Zhong et al., Nature 517, 177 (2015) - 6-hour coherence in Eu:YSO
- Bradley et al., PRX 9, 031045 (2019) - NV diamond memory
- Afzelius et al., PRA 79, 052329 (2009) - AFC protocol

**Integration with Phase A:**
- Extends `physics/memory.py` with platform-specific subclasses
- Existing `MemoryStats` dataclass works but needs `multimode_capacity` and `bandwidth`
- Connects to repeater models via `_chain_metrics` in `repeater.py`

---

### 2.4 Network Routing for QKD

**Existing Phase A state:** `network/routing.py` has Dijkstra shortest path and
max-key-rate-path; `network/trusted_node.py` has bottleneck key rate model.

**Phase B enhancements:**

**Entanglement-aware routing cost metric:**

```
w(e) = -log2(p_link(e))    [additive, like a distance]

Path cost: W(P) = sum_{e in P} w(e) = -log2(prod p_link(e))
```

Shortest path in this metric maximizes end-to-end success probability.

**Expected end-to-end entanglement rate (multi-hop):**

```
R_e2e = f_rep / <T_total>

<T_total> = max_i {L_i / (c * p_i)} * [1 + sum of purification overhead]
```

For swap-ASAP (swap as soon as possible):
```
<T_swap_asap> = max_{i in segments} (L_i / (c * p_link_i))
```

**Max-flow entanglement routing (multi-pair, multi-path):**

Model as a flow network where edge capacities = expected entanglement generation rate:

```
capacity(u,v) = f_rep * M_uv * p_link(u,v)
```

Standard max-flow algorithms (Ford-Fulkerson, push-relabel) apply with quantum
constraints (no cloning => each entangled pair consumed once).

**Routing with fidelity constraints:**

```
F_path = F_link^n_swaps * F_purified(n_rounds)

Constraint: F_path >= F_min (application-dependent)
```

**Parameters needed:**
- Network graph `G = (V, E)` with link properties
- Per-link: `distance_km, fiber_loss, eta_det, p_link, capacity`
- `F_min`: minimum fidelity threshold
- `M_uv`: multiplexing factor per link
- `algorithm`: "dijkstra", "max_flow", "k_shortest", "fidelity_constrained"

**References:**
- Van Meter et al., IEEE/ACM Trans. Networking 22, 1648 (2014)
- Pant et al., npj Quantum Info 5, 25 (2019) - routing in quantum networks
- Caleffi, IEEE JSAC 35, 2393 (2017) - optimal routing

**Integration with Phase A:**
- Extends `network/routing.py` with new algorithms
- Extends `network/types.py` (NetworkTopology, NetworkPath) with quantum attributes
- Connects to repeater models for per-link rate computation

---

### 2.5 Trusted Node vs. MDI Relay Architectures

**Existing Phase A:** `network/trusted_node.py` has basic bottleneck model.

**Trusted node end-to-end key rate:**

```
R_trusted = min_{i in links} R_link_i
```

All intermediate nodes must be trusted. Key is XORed hop-by-hop:

```
K_final = K_1 XOR K_2 XOR ... XOR K_n
```

**MDI relay architecture:**

Each relay performs Bell-state measurement without learning the key:

```
R_MDI_relay = Q_11 * [1 - H(e_11)] per relay segment
```

End-to-end rate for chain of MDI relays:

```
R_e2e_MDI = min_{i} R_MDI_relay_i
```

No trust assumption needed at relay nodes, but lower rate than trusted nodes.

**Hybrid architecture decision metric:**

```
Security_gain(MDI) = 1 - p_compromise(node)
Rate_penalty(MDI) = R_trusted / R_MDI

Use MDI relay when: Security_gain / Rate_penalty > threshold
```

**Integration with Phase A:** Extends `network/trusted_node.py` and
`qkd_protocols/mdi_qkd.py` to support relay chains.

---

## 3. Advanced Security Proofs

### 3.1 Composable Security Framework

**Existing Phase A state:** `qkd_protocols/finite_key_composable.py` has `EpsilonBudget`
and `split_epsilon` with balanced/pa_heavy/custom strategies.

**Phase B: Full composable key rate implementation**

**Composable security definition:**

A QKD protocol is `eps_QKD`-secure if:

```
eps_QKD <= eps_cor + eps_sec

eps_sec = eps_PA + eps_PE + eps_EC + eps_smooth

where:
  eps_cor  : correctness error (probability keys differ)
  eps_PA   : privacy amplification failure probability
  eps_PE   : parameter estimation failure probability
  eps_EC   : error correction failure probability
  eps_smooth: smoothing parameter for min-entropy
```

**Composable finite-key rate (BB84, Tomamichel et al. 2012):**

```
l = floor[ H_min^eps_s(X|E) - lambda_EC - log2(2/eps_cor)
           - 2*log2(1/(2*eps_PA)) ]

H_min^eps_s(X|E) >= n * [1 - h(e_ph + delta_PE)] - sqrt(n) * Delta_AEP
```

where:

```
delta_PE = sqrt( (n+k)/(n*k) * (2*log(1/eps_PE) + (d+1)*log(n+k+1)) / 2 )

Delta_AEP = 4 * log2(2^(1-h(e_ph)) + 2) * sqrt(log2(2/eps_s^2))
```

**Parameters:**
- `n`: key generation signals, `k`: parameter estimation signals
- `e_ph`: phase error rate estimate
- `d`: dimension of parameter estimation (d=1 for BB84)
- All epsilon components from `EpsilonBudget`
- `lambda_EC = n * f * h(e_bit)`: error correction leakage

**References:**
- Tomamichel, Lim, Gisin, Renner, Nature Comms 3, 634 (2012)
- Renner, Int. J. Quantum Info 6, 1 (2008) - composable framework
- Scarani et al., Rev. Mod. Phys. 81, 1301 (2009) - security proofs review

**Integration with Phase A:** Direct enhancement of `finite_key_composable.py`.
Connects to all protocol engines via `apply_finite_key_dispatch` in `finite_key.py`.

---

### 3.2 Improved Decoy-State Bounds

**Phase A:** `bb84_decoy.py` uses vacuum+weak decoy bounds (2-intensity).

**3-Intensity Protocol (vacuum + weak + signal):**

```
Y_1^L = (mu_1 * e^{mu_1} * Q_{mu_2} - mu_2 * e^{mu_2} * Q_{mu_1}
         - (mu_1^2 - mu_2^2)/(mu_s^2) * (e^{mu_s} * Q_{mu_s} - Y_0))
        / (mu_1 * mu_2 * (mu_2 - mu_1))

Y_0^L = max(0, (mu_2 * Q_{mu_1} * e^{mu_1} - mu_1 * Q_{mu_2} * e^{mu_2})
              / (mu_2 - mu_1))
```

**4-Intensity Protocol (adds a second weak decoy):**

```
Y_1^L and e_1^U are obtained by solving the linear program:

minimize / maximize: Y_1, e_1

subject to:
  Q_{mu_i} * e^{mu_i} = sum_{n=0}^{N_cut} (mu_i^n / n!) * Y_n   for i = 1,...,4
  Q_{mu_i} * E_{mu_i} * e^{mu_i} = sum_{n=0}^{N_cut} (mu_i^n / n!) * Y_n * e_n
  0 <= Y_n <= 1,  0 <= e_n <= 0.5
```

**Key rate with tight decoy bounds:**

```
R_decoy = Q_1^L * [1 - H(e_1^U)] - f * Q_mu * H(E_mu)

Q_1^L = mu * e^{-mu} * Y_1^L   (lower bound on single-photon gain)
```

**Parameters needed:**
- `mu_s`: signal intensity
- `mu_1, mu_2, mu_3`: decoy intensities (for 4-intensity)
- `p_s, p_1, p_2, p_3`: selection probabilities
- `Q_{mu_i}`: observed gains at each intensity
- `E_{mu_i}`: observed error rates at each intensity

**References:**
- Ma, Qi, Zhao, Lo, PRA 72, 012326 (2005) - practical decoy
- Lim et al., PRA 89, 022307 (2014) - tight finite-key decoy
- Rusca et al., Appl. Phys. Lett. 112, 171104 (2018) - 4-intensity

**Integration:** Replaces decoy bound computation in `bb84_decoy.py` and `mdi_qkd.py`.

---

### 3.3 Security Against Coherent Attacks

**De Finetti theorem approach:**

For an n-round QKD protocol symmetric under permutations, any state
rho_{A^n B^n E^n} is close to a convex combination of i.i.d. states:

```
||rho_{A^n B^n E^n} - integral sigma^{tensor n} d_mu(sigma)|| <= delta(n, d)

delta(n, d) ~ (n+1)^{d^2} * 2^{-cn}   [exponentially small correction]
```

**Postselection technique (Christandl, Koenig, Renner 2009):**

Security against coherent attacks holds if:

```
eps_coherent <= (n+1)^{d^2 - 1} * eps_collective
```

where `d` is the dimension of each subsystem, `n` is the number of signals.

For BB84 (d=2): `eps_coherent <= (n+1)^3 * eps_collective`

**Entropy Accumulation Theorem (Dupuis, Fawzi, Renner 2020):**

```
H_min^eps(A^n | E) >= n * inf_omega [H(A|E)_omega] - sqrt(n) * O(log(1/eps))
```

The infimum is over all states compatible with the observed statistics.

**Integration:** Enhancement to `finite_key_composable.py` proof method selection.

---

### 3.4 Source Imperfection Models

**Loss-tolerant protocol (Tamaki et al. 2014):**

Bounds Eve's information even with state-preparation flaws:

```
R_LT = Q_1^L * [1 - H(e_1^{ph,U})] - f * Q_mu * H(E_mu)

e_1^{ph,U} = (e_1^{bit,U} + delta_source) / (1 - 2*delta_source)
```

where `delta_source` quantifies the deviation of prepared states from ideal:

```
delta_source = max_{i in {0,1,+,-}} |<psi_i^{ideal}|psi_i^{actual}> - 1|
```

**Intensity fluctuation model:**

If the actual intensity mu is drawn from distribution p(mu) around mean mu_0:

```
Q_mu = integral p(mu') * Q(mu') d_mu'
     ~ Q(mu_0) + 0.5 * sigma_mu^2 * d^2Q/dmu^2 |_{mu_0}

sigma_mu^2 = Var[mu]   (intensity fluctuation variance)
```

**Key rate penalty from intensity fluctuations:**

```
Delta_R ~ -sigma_mu^2 * |d^2 R / d mu^2|   [second-order correction]
```

**Parameters:**
- `delta_source`: state preparation flaw parameter
- `sigma_mu / mu_0`: relative intensity fluctuation
- Per-state fidelity: `F_H, F_V, F_D, F_A` for the four BB84 states

**References:**
- Tamaki, Curty, Kato, Lo, PRA 90, 052314 (2014)
- Pereira et al., npj Quantum Info 5, 62 (2019) - flawed and leaky sources
- Zapatero, Curty, Sci. Rep. 11, 11181 (2021)

**Integration:** New parameter inputs to `bb84_decoy.py` and `mdi_qkd.py`. Connects to
`security/assessment.py` for source vulnerability scoring.

---

## 4. Advanced Channel Physics

### 4.1 Wavelength-Dependent Atmospheric Transmission

**Existing Phase A:** `channels/free_space.py` uses scalar `extinction_db_per_km`.
`satellite/extinction.py` provides basic extinction models.

**Beer-Lambert Law (spectral):**

```
T(lambda, z) = exp(-integral_0^z alpha(lambda, z') dz')

alpha(lambda, z) = alpha_mol_abs(lambda, z) + alpha_mol_scat(lambda, z)
                 + alpha_aer_abs(lambda, z) + alpha_aer_scat(lambda, z)
```

**Rayleigh scattering (molecular):**

```
alpha_Rayleigh(lambda) = (8*pi^3 * (n^2 - 1)^2) / (3 * N_s * lambda^4)
                       * (6 + 3*rho) / (6 - 7*rho)
```

where `n` is the refractive index, `N_s` is molecular number density,
`rho ~ 0.0279` is the depolarization factor.

For standard atmosphere at sea level:

```
alpha_Rayleigh(lambda) ~ 0.00864 * lambda_um^{-4.09 + 0.00472*lambda_um + 0.000389/lambda_um}
[lambda_um in micrometers, result in km^{-1}]
```

**Mie scattering (aerosol):**

```
alpha_Mie(lambda) = alpha_Mie(lambda_0) * (lambda_0 / lambda)^q

q ~ 0.5 - 2.0 (Angstrom exponent, depends on aerosol type)
```

**Simplified MODTRAN-compatible transmission:**

```
T_atm(lambda) = T_Rayleigh(lambda) * T_Mie(lambda) * T_H2O(lambda) * T_O3(lambda) * ...

T_Rayleigh = exp(-tau_R / cos(theta_z))
T_Mie = exp(-tau_M / cos(theta_z))
```

where `theta_z` is the zenith angle.

**Molecular absorption (simplified HITRAN line model):**

```
alpha_abs(nu) = S_j * f(nu - nu_j, gamma_L, gamma_D)

S_j(T) = S_j(T_ref) * (Q(T_ref)/Q(T)) * exp(-c2*E_j*(1/T - 1/T_ref))
         * (1 - exp(-c2*nu_j/T)) / (1 - exp(-c2*nu_j/T_ref))
```

where `f` is the Voigt profile, `S_j` is line strength, `gamma_L, gamma_D` are
Lorentzian and Doppler widths.

**Parameters needed:**
- `lambda_nm`: wavelength
- `visibility_km`: meteorological visibility
- `aerosol_type`: "rural", "urban", "maritime", "tropospheric"
- `water_vapor_column_cm`: precipitable water vapor
- `altitude_m`: ground station altitude
- `zenith_angle_deg`: observation angle
- `season`: for atmospheric profiles

**References:**
- Berk et al., SPIE 2005 - MODTRAN5
- Kneizys et al., AFGL-TR-88-0177 (1988) - LOWTRAN7
- Bodhaine et al., J. Atmos. Ocean. Tech. 16, 1854 (1999) - Rayleigh scattering

**Integration with Phase A:**
- Extends `satellite/extinction.py` with spectral models
- Replaces scalar `atmospheric_extinction_db_per_km` in `channels/free_space.py`
  with wavelength-dependent function
- Feeds into `satellite/pass_budget.py` for spectral link budget

---

### 4.2 Adaptive Optics for Turbulence Correction

**Existing Phase A:** `satellite/turbulence.py` has Hufnagel-Valley Cn2 and Rytov variance.

**Atmospheric coherence diameter (Fried parameter):**

```
r0 = [0.423 * k^2 * sec(theta) * integral Cn2(z) dz]^{-3/5}

k = 2*pi / lambda
```

**Strehl ratio without AO:**

```
SR_0 = exp(-(D/r0)^{5/3})     [Marechal approximation, valid for D >> r0]
```

**Strehl ratio with AO correction (J Zernike modes corrected):**

```
SR_AO = exp(-sigma_res^2)

sigma_res^2 = sigma_total^2 - sum_{j=1}^{J} a_j * (D/r0)^{5/3}
```

Noll's residual variance after correcting J Zernike modes:

```
sigma_J^2 ~ 0.2944 * J^{-sqrt(3)/2} * (D/r0)^{5/3}
```

For specific low-order corrections (Noll 1976):

```
J = 1 (piston only):          sigma^2 = 1.0299 * (D/r0)^{5/3}
J = 3 (tip-tilt removed):     sigma^2 = 0.134  * (D/r0)^{5/3}
J = 10:                       sigma^2 = 0.0648 * (D/r0)^{5/3}
J = 21:                       sigma^2 = 0.0347 * (D/r0)^{5/3}
```

**Coupling efficiency into single-mode fiber (with AO):**

```
eta_SMF = (pi/4)^2 * SR_AO * (D/r0)^2 / (1 + (D/r0)^2)
```

For QKD, effective channel transmittance with AO:

```
eta_AO = eta_channel_geometric * eta_SMF * eta_atm
```

**Temporal bandwidth requirement:**

```
f_G = 0.43 * v_wind / r0    [Greenwood frequency]
f_AO >= (2-3) * f_G         [AO bandwidth requirement]
```

**Parameters needed:**
- `J`: number of corrected Zernike modes
- `D`: receiver aperture diameter
- `r0`: Fried parameter (from existing turbulence model)
- `v_wind`: wind speed at turbulence layer
- `f_AO`: AO system bandwidth
- `lambda_beacon`: AO beacon wavelength

**References:**
- Noll, JOSA 66, 207 (1976) - Zernike polynomials and turbulence
- Hardy, "Adaptive Optics for Astronomical Telescopes" (1998)
- Gruneisen et al., Opt. Express 23, 23924 (2015) - AO for QKD
- Pugh et al., Quantum Sci. Tech. 2, 024009 (2017) - satellite QKD with AO

**Integration with Phase A:**
- New module connecting `satellite/turbulence.py` output (Cn2, Rytov) to AO correction
- Modifies effective transmittance in `channels/free_space.py`
- Feeds corrected Strehl into `satellite/pass_budget.py`

---

### 4.3 Underwater QKD Channel Model

**Beer-Lambert attenuation:**

```
T_water(d) = exp(-c(lambda) * d)

c(lambda) = a(lambda) + b(lambda)
```

where:
- `a(lambda)`: absorption coefficient (m^{-1})
- `b(lambda)`: scattering coefficient (m^{-1})
- `c(lambda)`: total extinction coefficient (m^{-1})
- `d`: link distance (m)

**Jerlov water type classification:**

| Water Type | c(lambda_min) [m^{-1}] | lambda_min [nm] |
|-----------|------------------------|-----------------|
| Type I (clearest) | 0.022 | 475 |
| Type IA | 0.029 | 470 |
| Type IB | 0.042 | 465 |
| Type II | 0.083 | 465 |
| Type III | 0.167 | 460 |
| Coastal-1 | 0.179 | 520 |
| Coastal-9 | 0.400 | 545 |

**Absorption in pure water (Pope and Fry 1997):**

Blue-green window: minimum absorption at ~418 nm, a ~ 0.0044 m^{-1}

```
a_water(lambda) [m^{-1}] ~ {
    0.0044  at 418 nm
    0.0196  at 475 nm
    0.0593  at 550 nm
    0.288   at 650 nm
    2.56    at 750 nm
}
```

**Scattering (Haltrin 2006):**

```
b(lambda) = b_m(lambda) + b_p(lambda)

b_m(lambda) = 0.0030 * (550/lambda)^{4.3}  [molecular/Rayleigh]
b_p(lambda) = b_p(550) * (550/lambda)^n    [particulate, n ~ 0.3-1.7]
```

**Underwater QKD key rate:**

```
R_underwater = f_rep * eta_source * T_water(d) * eta_det * Y_protocol - noise_terms
```

QBER from scattering-induced depolarization:

```
e_scatter ~ (1 - exp(-b(lambda)*d * (1 - g))) / 2

where g = <cos(theta)> is the asymmetry factor (~0.9 for ocean water)
```

**Parameters needed:**
- `water_type`: Jerlov type (I, IA, IB, II, III, C1-C9)
- `depth_m`: operating depth
- `lambda_nm`: operating wavelength (optimal: 420-520 nm)
- `chlorophyll_concentration_mg_m3`: for CASE-2 waters
- `d`: link distance in meters
- `salinity_ppt`: salinity (affects absorption)

**References:**
- Shi et al., JOSA A 32, 349 (2015) - underwater QKD channel
- Lanzagorta, "Underwater Communications" (2012)
- Gariano, Lanzagorta, Proc. SPIE 10660 (2018)
- Ji et al., Opt. Express 25, 19795 (2017) - underwater BB84

**Integration with Phase A:**
- New channel model `channels/underwater.py` alongside `fiber.py` and `free_space.py`
- Reuses `compute_channel_diagnostics` framework from `channels/engine.py`
- Connects to protocol engines via `channel.model = "underwater"` in scenario config

---

### 4.4 Urban Canyon and Indoor QKD

**Urban free-space path loss (extended from Phase A free-space):**

```
L_urban(d) = L_geometric(d) + L_atm(d) + L_building_scatter + L_background_noise

L_building_scatter = alpha_scatter * n_reflections * R_loss_per_reflection_dB

R_loss_per_reflection_dB ~ 3-10 dB (depends on surface material)
```

**Indoor optical channel (LED/diffuse):**

```
H_LOS(0) = (m+1) * A_det / (2*pi*d^2) * cos^m(phi) * cos(theta) * T_filter * g(theta)

m = -ln(2) / ln(cos(Phi_1/2))  [Lambertian mode number]
```

where `A_det` is detector area, `phi` is emission angle, `theta` is incidence angle,
`Phi_1/2` is LED half-power angle.

**Background noise in urban environment:**

```
n_background = L_radiance * A_det * Omega_FOV * Delta_lambda * eta_det

Day:     L_radiance ~ 10^4 W/(m^2 sr nm) [urban, sunlit buildings]
Night:   L_radiance ~ 10^{-2} to 10^0 W/(m^2 sr nm) [street lighting]
```

**Parameters:** `n_reflections`, `surface_type`, `indoor/outdoor`,
`background_radiance`, `filter_bandwidth_nm`

**Integration:** Extends `channels/free_space.py` with urban propagation modes.
Connects to `satellite/background.py` for noise models.

---

### 4.5 Multi-Hop Fiber Networks

**Cascaded fiber link budget:**

```
eta_total = prod_{i=1}^{N_links} eta_fiber_i * eta_connector_i * eta_splice_i

eta_fiber_i = 10^(-alpha * L_i / 10)
eta_connector_i = 10^(-L_conn_i / 10)
```

**Noise accumulation through amplified links:**

```
n_noise_total = sum_{i=1}^{N_links} n_noise_i * prod_{j=i+1}^{N_links} eta_j
```

For Raman noise with classical WDM co-propagation:

```
P_Raman_total = sum_{i=1}^{N_spans} P_Raman_per_span_i * eta_remaining_i
```

**Integration:** Extends `channels/fiber.py` and `channels/coexistence.py` (Raman)
for multi-span link modeling.

---

## 5. Realistic Detector Models

### 5.1 SNSPD (Superconducting Nanowire Single-Photon Detectors)

**Existing Phase A:** `physics/detector.py` has generic detector model with PDE, jitter,
dark counts, dead time, and afterpulsing.

**SNSPD-specific detection efficiency model:**

```
eta_SNSPD(I_bias) = eta_abs * eta_internal(I_bias)

eta_abs = 1 - R_opt - T_opt   [optical absorption, cavity-enhanced]

eta_internal(I_bias) = [1 + exp(-k*(I_bias/I_sw - a))]^{-1}
```

where `I_sw` is the switching current, `k, a` are device-specific parameters.

**Count rate saturation (kinetic inductance model):**

```
CR_measured = CR_input * eta / (1 + CR_input * eta * tau_reset)

tau_reset = L_k / (R_load + R_hotspot)

L_k = mu_0 * lambda_L^2 * l / (w * t)
```

where:
- `L_k`: kinetic inductance
- `lambda_L`: London penetration depth
- `l, w, t`: nanowire length, width, thickness
- `R_load`: readout impedance (typically 50 Ohm)
- `R_hotspot`: hotspot resistance (~few kOhm)

**Recovery time and effective detection efficiency:**

```
eta_eff(t) = eta_max * (1 - exp(-t / tau_reset))

tau_reset ~ L_k / R_load ~ 5-50 ns (typical)
```

**Timing jitter model:**

```
sigma_jitter = sqrt(sigma_intrinsic^2 + sigma_geometric^2 + sigma_electronic^2)

sigma_intrinsic ~ 1-5 ps (NbN at 1550 nm)
sigma_geometric ~ l_wire / (2 * v_signal)  [length-dependent]
```

**Dark count rate:**

```
DCR = A * exp(-E_a / (k_B * T)) + DCR_background

where E_a ~ Delta_SC (superconducting gap energy)
```

Typical values at 0.8 K:
- NbN: DCR ~ 0.1-10 Hz, eta ~ 90-98% at 1550 nm
- WSi: DCR ~ 0.01-1 Hz, eta ~ 93% at 1550 nm

**Parameters:**
- `material`: "NbN", "NbTiN", "WSi", "MoSi"
- `I_bias / I_sw`: bias current ratio
- `L_k_nH`: kinetic inductance
- `wire_length_um, wire_width_nm, wire_thickness_nm`
- `operating_temp_K`: typically 0.8-2.5 K
- `R_load_ohm`: readout impedance
- `cavity_type`: "none", "single_mirror", "optical_stack"

**References:**
- Natarajan, Tanner, Hadfield, Supercond. Sci. Tech. 25, 063001 (2012)
- Marsili et al., Nature Photon. 7, 210 (2013) - 93% system efficiency
- Esmaeil Zadeh et al., Nano Lett. 21, 2 (2021) - SNSPDs for quantum info
- Reddy et al., Optica 7, 1649 (2020) - 98% efficiency

**Integration with Phase A:** Extends `physics/detector.py` with SNSPD-specific
subclass. Connects to `build_detector_profile` and all protocol engines.

---

### 5.2 InGaAs/InP Avalanche Photodiodes

**Gated-mode detection probability:**

```
p_click = 1 - exp(-eta_APD * n_photons) + p_dark + p_afterpulse

eta_APD = eta_coupling * eta_abs * P_avalanche(V_excess)
```

**Afterpulsing model (trapped carrier release):**

```
p_afterpulse(t_holdoff) = sum_i N_trap_i * exp(-t_holdoff / tau_i)

For dominant trap: p_AP ~ P_AP0 * exp(-t_holdoff / tau_trap)
```

Typical values:
- `tau_trap ~ 0.3-5 us` (trap lifetime)
- `P_AP0 ~ 0.05-0.20` (afterpulse coefficient)
- `t_holdoff ~ 1-20 us` (hold-off / dead time)

**Gate timing model:**

```
p_detection_per_gate = 1 - (1 - p_dark_per_gate) * (1 - p_signal_per_gate)

p_dark_per_gate = DCR * t_gate

p_signal_per_gate = eta_APD * (1 - exp(-mu * T_channel))
```

**Effective count rate with dead time and afterpulsing:**

```
R_eff = R_true / (1 + R_true * t_dead + R_true * p_AP * tau_trap)
```

**Temperature dependence:**

```
DCR(T) = DCR_0 * exp(-E_a / (k_B * T))

E_a ~ 0.08-0.15 eV (activation energy for InGaAs)

eta(T) = eta_0 * (1 - alpha_T * (T - T_0))
```

**Parameters:**
- `V_excess`: excess bias voltage above breakdown
- `t_gate_ns`: gate width
- `f_gate_mhz`: gate frequency
- `t_holdoff_us`: hold-off time
- `tau_trap_us`: trap lifetime(s)
- `P_AP0`: afterpulse coefficient
- `temperature_K`: operating temperature (typically 220-250K)
- `E_a_eV`: activation energy

**References:**
- Cova et al., J. Mod. Opt. 51, 1267 (2004)
- Yuan et al., Appl. Phys. Lett. 91, 041114 (2007) - 1.25 GHz gated InGaAs
- Namekata et al., Opt. Express 14, 10043 (2006)

**Integration:** New detector class in `physics/detector.py` alongside generic model.
Connects via `build_detector_profile` to all protocol compute functions.

---

### 5.3 Detector Blinding and Countermeasures

**Existing Phase A:** `security/attacks/blinding.py` has basic exploitability scoring.

**Phase B: Physics-based blinding model**

**CW blinding threshold:**

```
P_blind = I_latch * R_load / eta_coupling

For InGaAs APD: P_blind ~ 0.05-1 mW
For SNSPD:      P_blind ~ 1-10 mW (harder to blind)
```

**Faked-state attack success probability:**

```
p_control = p_trigger(P_attack) * p_correct_basis

p_trigger(P) = {
  1   if P >= P_threshold
  0   if P < P_threshold
}   [ideal threshold detector model]
```

QBER introduced by blinding: `e_blind ~ 0` (Eve controls detector clicks perfectly)

**Countermeasure effectiveness:**

```
# Watchdog detector
p_detect_attack = 1 - exp(-P_attack * eta_watchdog * t_monitor / E_photon)

# Random detector efficiency variation
p_undetected = prod_i (1 - |eta_i - eta_nominal| / eta_nominal)
```

**Parameters:** `P_attack_mw`, `countermeasure_type`, `watchdog_sensitivity`

**References:**
- Lydersen et al., Nature Photon. 4, 686 (2010) - detector blinding
- Yuan, Dynes, Shields, Nature Photon. 4, 800 (2010) - countermeasures
- Chaiwongkhot et al., EPJ Quantum Tech. 9, 23 (2022) - TES blinding

**Integration:** Extends `security/attacks/blinding.py` with physics-based models.
Connects to detector models in `physics/detector.py`.

---

### 5.4 Photon-Number-Resolving (PNR) Detectors

**Multiplexed PNR from non-PNR detectors:**

```
p(n_detected | n_incident) = C(N_det, n_detected)
    * sum_{k=0}^{n_detected} (-1)^k * C(n_detected, k)
    * ((n_detected - k) / N_det)^n_incident * eta^n_incident
```

where `N_det` is the number of detectors in the multiplexed array.

**TES energy resolution:**

```
Delta_E = sqrt(4 * k_B * T_c^2 * C / alpha)

n_photon = round(E_pulse / E_photon)

sigma_n = Delta_E / E_photon
```

where:
- `T_c`: critical temperature
- `C`: heat capacity
- `alpha = T/R * dR/dT`: TES sensitivity parameter

**PNR-enabled MDI-QKD gain:**

With PNR detectors, Bell-state measurement can distinguish all 4 Bell states:

```
p_BSM = 1.0  (vs. 0.5 for linear optics without PNR)
```

This doubles the MDI-QKD key rate.

**Parameters:** `N_pixels` (array size), `energy_resolution_eV`, `T_c_mK`, `max_photon_number`

**References:**
- Lita, Miller, Nam, Opt. Express 16, 3032 (2008) - TES at 95% efficiency
- Divochiy et al., Nature Photon. 2, 302 (2008) - PNR with parallel SNSPDs

**Integration:** New detector type in `physics/detector.py`. Enhances `mdi_qkd.py`
Bell-state measurement model.

---

## 6. Quantum Random Number Generation (QRNG)

### 6.1 Vacuum Fluctuation QRNG

**Existing Phase A:** `qrng/sources.py` has `vacuum_fluctuation_source()`,
`qrng/entropy.py` has min-entropy estimation, `qrng/conditioning.py` has Toeplitz extraction.

**Phase B: Refined physics model**

**Homodyne measurement of vacuum state:**

The measured quadrature x has distribution:

```
p(x) = (1 / sqrt(2*pi*sigma_total^2)) * exp(-x^2 / (2*sigma_total^2))

sigma_total^2 = sigma_quantum^2 + sigma_classical^2

sigma_quantum^2 = N_0 * eta_homodyne  (quantum noise = shot noise)
sigma_classical^2 = v_el + v_RIN + v_CMRR  (classical noise sources)
```

**Conditional min-entropy (quantum contribution only):**

```
H_min(X|E) = -log2(max_x p(x|E_side_info))

For Gaussian: H_min = 0.5 * log2(2*pi*e*sigma_quantum^2) - H_side
```

**Extractable randomness per sample:**

```
k = floor(H_min(X|E)) - 2*log2(1/epsilon) - 1

bits per sample = k / n_ADC_bits
```

**ADC quantization:**

```
p_i = erf((x_{i+1}) / (sqrt(2)*sigma)) - erf((x_i) / (sqrt(2)*sigma))

H_min^{quant} = -log2(max_i p_i)
```

**Parameters:**
- `homodyne_efficiency`: typically 0.5-0.99
- `electronic_noise_power_dBm`: electronic noise floor
- `LO_power_mW`: local oscillator power
- `CMRR_dB`: common-mode rejection ratio (balanced detector)
- `adc_bits`: ADC resolution (8-16 bits typical)
- `sampling_rate_gsps`: ADC sampling rate
- `epsilon`: security parameter for extraction

**References:**
- Gabriel et al., Nature Photon. 4, 711 (2010) - vacuum fluctuation QRNG
- Zheng et al., PRX Quantum 4, 020329 (2023) - source-DI QRNG
- Drahi et al., PRX Quantum 1, 010305 (2020) - certified randomness

**Integration with Phase A:** Extends `qrng/sources.py` vacuum source with refined
noise model. Enhances `qrng/entropy.py` with conditional min-entropy.

---

### 6.2 Device-Independent QRNG

**Min-entropy from CHSH violation:**

```
H_min(A|E) >= -log2( (1 + sqrt(2 - (S/2)^2)) / 2 )
```

For maximum violation S = 2*sqrt(2): `H_min = 1` (one perfect random bit).

**Randomness generation rate:**

```
R_QRNG = f_rep * [H_min(A|E) - delta_finite(n, eps)]

delta_finite ~ O(1/sqrt(n)) * log(1/eps)
```

**Spot-checking protocol:**

```
n_test = gamma * N    (fraction used for Bell test)
n_gen = (1-gamma) * N (fraction used for randomness)

k_extracted = n_gen * H_min - O(sqrt(N) * log(1/eps))
```

**Parameters:** `S_observed`, `n_rounds`, `gamma` (test fraction), `epsilon`

**References:**
- Pironio et al., Nature 464, 1021 (2010) - certified randomness
- Bierhorst et al., Nature 556, 223 (2018) - experimentally certified

**Integration:** New source type in `qrng/sources.py`, `source_type="device_independent"`.

---

### 6.3 Semi-Device-Independent QRNG

**Prepare-and-measure scenario with bounded dimension:**

```
p_guess(b|x,B) <= (1 + sqrt(1 - 1/d^2)) / 2   [dimension witness bound]

H_min >= -log2(p_guess)
```

where `d` is the certified Hilbert space dimension.

**Source-independent QRNG (SI-QRNG):**

```
H_min(X|E) >= 1 - h(e_prepared)

e_prepared = fraction of anti-correlated outcomes in verification basis
```

**Parameters:** `dimension_bound`, `preparation_error`, `protocol_type`

**References:**
- Lunghi et al., PRL 114, 150501 (2015) - SDI-QRNG
- Cao et al., PRX Quantum 3, 010305 (2022) - source-independent QRNG

**Integration:** New source type in `qrng/sources.py`.

---

### 6.4 Min-Entropy Estimation and Randomness Extraction

**Existing Phase A:** `qrng/entropy.py` has `estimate_min_entropy` using most-common-value.

**NIST SP 800-90B compliant estimators:**

1. Most Common Value (MCV):
```
H_min = -log2(p_max)
p_max = max_x (count(x) / n)
```

2. Collision estimator:
```
H_min^{collision} = -log2(sum_x p_x^2)
```

3. Compression estimator:
```
H_min^{compression} ~ n_compressed / n_original  (ratio-based)
```

4. Markov estimator:
```
H_min^{Markov} = -log2(max_x p(x_t | x_{t-1}))
```

**Quantum leftover hash lemma (QLHL):**

```
l_extracted <= H_min^eps(X|E) - 2*log2(1/eps_ext) + 2

For Toeplitz matrix extraction:
  l = k - 2*log2(1/eps) - 1

  where k = H_min^eps(X^n | E^n)
```

**Toeplitz matrix construction:**

An (l x n) Toeplitz matrix T is defined by its first row r and first column c:

```
T[i,j] = r[j-i]  for j >= i
T[i,j] = c[i-j]  for i > j

Total random bits needed: n + l - 1 (for the seed)
```

**Fast Toeplitz multiplication via FFT:**

```
output = IFFT(FFT(seed_extended) * FFT(input_padded))[0:l]

Complexity: O(n * log(n))   vs.  O(n * l) for naive
```

**Parameters:**
- `n_input_bits`: raw sample length
- `l_output_bits`: extracted key length
- `epsilon_ext`: extraction security parameter
- `H_min`: estimated min-entropy
- `estimator`: "mcv", "collision", "compression", "markov"

**References:**
- Tomamichel et al., IEEE Trans. IT 57, 5524 (2011) - QLHL
- Ma et al., npj Quantum Info 2, 16021 (2016) - quantum random number generation
- NIST SP 800-90B (2018) - entropy estimation

**Integration:** Extends `qrng/entropy.py` with multiple NIST estimators.
Enhances `qrng/conditioning.py` with FFT-accelerated Toeplitz extraction.

---

## 7. Error Correction and Privacy Amplification

### 7.1 LDPC Codes for QKD Reconciliation

**Binary LDPC code for information reconciliation:**

Reconciliation efficiency:

```
f_EC = n_syndrome / (n * H(e))

where:
  n: block length
  n_syndrome: number of syndrome bits disclosed
  H(e): binary entropy of the error rate e
  Ideal: f_EC = 1.0, practical: f_EC ~ 1.05-1.22
```

**Belief propagation (sum-product) decoding:**

Message from variable node v to check node c:

```
L_{v->c} = L_ch(v) + sum_{c' in N(v)\c} L_{c'->v}
```

Message from check node c to variable node v:

```
L_{c->v} = 2 * atanh(prod_{v' in N(c)\v} tanh(L_{v'->c} / 2))
```

Channel LLR (log-likelihood ratio) for BSC:

```
L_ch = (-1)^{s_i} * log((1-e)/e)

where s_i = syndrome bit (Alice XOR Bob for position i)
```

**Rate-adaptive LDPC (for QKD):**

```
R_code = 1 - n_checks / n

Adaptive: puncture or shorten to match observed QBER:
  R_effective = max(0, 1 - f_EC * H(e_observed))
```

**Key rate penalty from reconciliation:**

```
lambda_EC = n * f_EC * H(e)   [bits leaked in error correction]
```

**Parameters:**
- `code_rate`: LDPC code rate
- `block_length`: typically 2^16 to 2^20
- `max_iterations`: BP decoder iterations (50-200)
- `e_target`: target error rate range
- `code_family`: "MacKay", "multi-edge", "rate-adaptive"

**References:**
- Elkouss et al., Proc. IEEE ISIT, 1879 (2009) - rate-adaptive LDPC for QKD
- Mink, Nakassis, "LDPC for QKD Reconciliation", arXiv:1205.4977
- Martinez-Mateo et al., Sci. Rep. 3, 1576 (2013) - high-performance reconciliation

**Integration with Phase A:**
- New module `protocols/reconciliation.py` or `pipeline/error_correction.py`
- Connects to key rate formulas in all protocol engines via `lambda_EC`
- Parameterizes `f_EC` that currently appears as constant in `bb84_decoy.py`

---

### 7.2 Cascade Protocol

**Pass structure:**

```
Pass 1: block_size = ceil(0.73 / e)
Pass i (i >= 2): block_size = 2 * block_size_{i-1}

Number of passes: typically 4-16
```

**BINARY subroutine:**

For a block with odd parity (contains odd number of errors):
```
1. Split block in half
2. Exchange parity of first half
3. Recurse into the half with odd parity
4. After log2(block_size) steps, the error position is found
```

**Information leakage per pass:**

```
I_leaked_pass_i = ceil(n / block_size_i) * 1 bit  (parity bits)
                + correction_bits_from_BINARY

Total: I_leaked = sum_i I_leaked_pass_i
```

**Reconciliation efficiency:**

```
f_Cascade = I_leaked / (n * H(e))

Optimized Cascade achieves: f ~ 1.02-1.10
```

**Parameters:**
- `initial_block_size`: first-pass block size (or auto from QBER)
- `n_passes`: number of passes (4-16)
- `e_estimated`: estimated QBER
- `n_bits`: sifted key length

**References:**
- Brassard, Salvail, CRYPTO 1993 - original Cascade
- Martinez-Mateo et al., arXiv:1407.3257 - demystifying Cascade
- Pedersen, Toyran, arXiv:1307.7829 - high performance Cascade

**Integration:** New module `pipeline/cascade.py`. Alternative to LDPC reconciliation.

---

### 7.3 Polar Codes for Quantum Channels

**Polar code construction for QKD:**

Channel polarization: for a BSC(e), define recursive channels:

```
W_N^{(i)}: reliability of i-th sub-channel after N = 2^n transforms

Bhattacharyya parameter:
Z(W^{(2i-1)}) = 2*Z(W^{(i)}) - Z(W^{(i)})^2   [bad channel]
Z(W^{(2i)})   = Z(W^{(i)})^2                    [good channel]

Z(BSC(e)) = 2*sqrt(e*(1-e))
```

**Rate selection:**

```
Frozen set F: indices i where Z(W_N^{(i)}) > 1 - delta
Information set I: indices i where Z(W_N^{(i)}) < delta

Code rate: R = |I| / N
```

**Successive cancellation (SC) decoder:**

```
L_N^{(i)}(y, u_1^{i-1}) = {
  L_{N/2}^{(2i-1)} boxplus L_{N/2}^{(2i)}  if i odd
  L_{N/2}^{(2i-1)} * (-1)^{u_i} * L_{N/2}^{(2i)}  if i even
}

where boxplus: f(a,b) = 2*atanh(tanh(a/2)*tanh(b/2))
```

**Advantages for QKD:**
- Near-capacity performance at large block lengths
- Systematic encoding (no rate loss)
- Low-complexity O(N log N) decoding

**Parameters:** `N`: code length (power of 2), `e_design`: design QBER, `list_size` (for SCL)

**References:**
- Jouguet, Kunz-Jacques, PRA 90, 042329 (2014) - polar codes for CV-QKD
- Lee, Kim, Journal of KPS 75, 1045 (2019)

**Integration:** Alternative code in `pipeline/error_correction.py`.

---

### 7.4 Privacy Amplification with Universal Hashing

**Existing Phase A:** `qrng/conditioning.py` has `apply_toeplitz_conditioning`.

**Toeplitz hashing for privacy amplification:**

```
K_final = T * K_corrected   (mod 2, binary matrix-vector product)

T: (l x n) Toeplitz matrix
n: length of corrected key
l: length of final secure key

l = H_min^eps(X^n | E) - 2*log2(1/(2*eps_PA))
```

**Security guarantee (quantum leftover hash lemma):**

```
0.5 * ||rho_{K,E} - tau_l tensor rho_E||_1 <= eps_PA

when l <= H_min^eps(X^n | E) - 2*log2(1/(2*eps_PA))
```

where `tau_l = I/2^l` is the maximally mixed state on l qubits.

**FFT-based Toeplitz multiplication:**

```python
def toeplitz_multiply_fft(seed, input_bits, l):
    # seed: (n + l - 1) random bits defining the Toeplitz matrix
    # input_bits: n-bit corrected key
    n = len(input_bits)
    N_fft = next_power_of_2(n + l - 1)

    # Zero-pad
    seed_padded = np.zeros(N_fft)
    seed_padded[:n+l-1] = seed

    input_padded = np.zeros(N_fft)
    input_padded[:n] = input_bits

    # Multiply in frequency domain
    result = np.real(np.fft.ifft(np.fft.fft(seed_padded) * np.fft.fft(input_padded)))

    # Extract and threshold
    output = (result[:l] % 2).astype(int)
    return output
```

**Seed requirements:**

- Toeplitz matrix seed: `n + l - 1` random bits
- Can be pre-shared or generated from QRNG module

**Alternative: polynomial hashing**

```
h(x) = (sum_{i=0}^{n-1} x_i * a^i) mod p   (in GF(2^m))

Computational cost: O(n * log(n)) using NTT
```

**Parameters:**
- `n`: corrected key length
- `l`: output key length (from composable security proof)
- `eps_PA`: privacy amplification error
- `method`: "toeplitz_fft", "polynomial", "treehash"

**References:**
- Renner, Wolf, ISIT 2005 - QLHL for QKD
- Tang et al., Sci. Rep. 9, 17733 (2019) - high-speed PA implementation
- Hayashi, Tsurumaru, NJP 14, 093014 (2012) - PA with less randomness

**Integration with Phase A:**
- Extends `qrng/conditioning.py` Toeplitz implementation
- New module `pipeline/privacy_amplification.py` for QKD post-processing
- Connects to composable key length `l` from `finite_key_composable.py`

---

## 8. System Integration

### 8.1 Classical Post-Processing Pipeline

**Complete QKD post-processing chain:**

```
Raw key (Alice) ──> Sifting ──> Parameter Estimation ──> Error Correction
                                                              |
Final key <── Privacy Amplification <── Error Verification <──'
```

**Sifting (BB84):**

```
n_sifted = N_raw * p_basis_match

BB84: p_basis_match = 0.5 (random basis)
Efficient BB84: p_basis_match ~ 1 - h(e) (biased basis choice)
```

**Parameter estimation (random sampling):**

```
n_PE = ceil(2 * log(1/eps_PE) / (2 * delta_PE^2))

delta_PE: confidence interval half-width
eps_PE: failure probability
```

**Error verification (hash check):**

```
p_undetected_error = 2^{-l_hash}

l_hash = ceil(log2(1/eps_cor))  bits

Typical: l_hash = 40 bits for eps_cor = 10^{-12}
```

**Pipeline throughput:**

```
R_final = R_raw * p_sift * (1 - r_PE) * (1 - f*H(e)) * (1 - r_PA_overhead)
```

**Parameters:**
- `N_block`: block size for processing
- `pipeline_mode`: "streaming" or "batch"
- Timing parameters for each stage

**Integration:** New module `pipeline/post_processing.py` orchestrating the full chain.
Connects sifting to existing protocol engines, EC to new reconciliation modules,
PA to `privacy_amplification.py`.

---

### 8.2 Key Management and Key Lifecycle

**Existing Phase A:** `kms/key_pool.py` has `SimulatedKeyPool` with ETSI QKD 014 interface.

**Key lifecycle states:**

```
GENERATED -> STORED -> REQUESTED -> DELIVERED -> CONSUMED -> EXPIRED/DESTROYED

State transitions with timestamps:
  t_generated: when QKD protocol produces the key
  t_stored: when key enters the pool
  t_delivered: when application receives the key
  t_consumed: when key is used for encryption
  t_expired: t_generated + TTL (time-to-live)
```

**Key consumption rate model:**

```
R_consumption = R_encryption * key_size / message_rate

# For OTP (one-time pad):
R_consumption_OTP = data_rate_bps   (1:1 ratio)

# For AES-256 key refresh:
R_consumption_AES = 256 / T_refresh  (bits/s, where T_refresh is key rotation interval)
```

**Key pool dynamics:**

```
dN_pool/dt = R_generation - R_consumption - R_expiration

N_pool(t) = N_pool(0) + integral_0^t [R_gen(t') - R_cons(t') - R_exp(t')] dt'
```

**Key relay through trusted nodes:**

```
K_AB = K_A1 XOR K_12 XOR ... XOR K_nB

Latency: T_relay = sum_i (L_i/c + T_process_i)
```

**Parameters:**
- `key_size_bits`: typically 256 (AES) or variable (OTP)
- `ttl_seconds`: key time-to-live
- `max_pool_size`: maximum stored keys
- `R_generation_kbps`: QKD key generation rate
- `encryption_mode`: "AES-256-GCM", "OTP", "hybrid"

**References:**
- ETSI GS QKD 014 v1.1.1 (2019) - REST-based key delivery API
- ETSI GS QKD 004 v2.1.1 (2020) - Application interface
- ETSI GS QKD 018 (2022) - Orchestration interface

**Integration with Phase A:** Extends `kms/key_pool.py` with lifecycle management,
TTL-based expiration, and consumption rate modeling.

---

### 8.3 Integration with Classical Encryption

**AES-256 with QKD key supply:**

```
Encryption: C = AES-256-GCM(K_QKD, nonce, plaintext)

Key refresh policy:
  T_refresh = min(T_crypto_period, N_max_blocks / R_data)

  T_crypto_period ~ 1 hour to 1 day (policy-dependent)
  N_max_blocks = 2^32 for GCM (NIST recommendation)
```

**One-Time Pad (information-theoretic security):**

```
C = M XOR K_QKD

Requirement: |K| >= |M| (key length >= message length)
Key consumption: R_key = R_data  (1:1)
```

**Hybrid classical-quantum key establishment:**

```
K_hybrid = KDF(K_QKD || K_PQC)

where:
  K_QKD: quantum-distributed key
  K_PQC: post-quantum key exchange (e.g., Kyber/ML-KEM)
  KDF: key derivation function (e.g., HKDF-SHA256)
```

This provides defense-in-depth: secure if either QKD or PQC is unbroken.

**Parameters:**
- `cipher`: "AES-256-GCM", "ChaCha20-Poly1305", "OTP"
- `key_refresh_policy`: "time_based", "volume_based", "hybrid"
- `pqc_algorithm`: "ML-KEM-768", "ML-KEM-1024", "none"

**Integration:** New module `integrations/classical_crypto.py`. Connects to `kms/key_pool.py`
for key consumption.

---

### 8.4 QKD Network Management (ETSI Standards)

**ETSI QKD 014 API (REST-based key delivery):**

```
GET /api/v1/keys/{slave_SAE_ID}/status
  Response: {key_size, stored_key_count, max_key_count, max_key_per_request, ...}

POST /api/v1/keys/{slave_SAE_ID}/enc_keys
  Request:  {number: N, size: key_size}
  Response: {keys: [{key_ID, key: base64}, ...]}

POST /api/v1/keys/{master_SAE_ID}/dec_keys
  Request:  {key_IDs: [{key_ID}, ...]}
  Response: {keys: [{key_ID, key: base64}, ...]}
```

**ETSI QKD 004 API (Application Interface):**

```
QKD_OPEN(source, destination, QoS, key_stream_ID) -> status
QKD_GET_KEY(key_stream_ID, index) -> key_buffer, status
QKD_CLOSE(key_stream_ID) -> status

QoS parameters:
  - requested_key_rate (bps)
  - max_QBER
  - priority_level
  - timeout_ms
```

**ETSI QKD 015 (Control Interface):**

```
Link monitoring:
  - QBER_current, key_rate_current, link_status
  - Alarm thresholds: QBER_max, key_rate_min

Network management:
  - Route establishment / teardown
  - Key relay path configuration
  - Load balancing across parallel links
```

**Performance metrics (ETSI QKD 018):**

```
SKR: Secure Key Rate (bits/s)
QBER: Quantum Bit Error Rate
Availability: uptime / (uptime + downtime)
Latency: time from key generation to delivery
Key_freshness: time since key was generated
```

**Parameters:**
- All ETSI API endpoint configurations
- `sae_id_alice, sae_id_bob`: security application entity IDs
- `qos_profile`: QoS requirements
- `monitoring_interval_s`: telemetry polling interval

**References:**
- ETSI GS QKD 014 v1.1.1 (2019)
- ETSI GS QKD 004 v2.1.1 (2020)
- ETSI GS QKD 015 v1.1.1 (2022)
- ETSI GS QKD 018 v1.1.1 (2022)

**Integration with Phase A:** Extends `kms/` module and `api_server.py` with
full ETSI QKD 014/004 compliance. Connects to `network/` for multi-node management.

---

### 8.5 Benchmarking Standards

**Standard metrics for QKD system comparison:**

```
SKR_vs_distance: R(L) curve [primary metric]
SKR_at_reference: R(L=50km), R(L=100km), R(L=200km)
Maximum_distance: L_max where R > 0
QBER_vs_distance: e(L) curve
Efficiency: SKR / (f_rep * eta_channel)
```

**Figure of merit (Takeoka et al.):**

```
FoM = SKR / C_PLOB = R / [-log2(1-eta)]
```

Values: FoM < 1 (cannot exceed PLOB without repeaters),
FoM > 1 indicates repeater-assisted or TF-QKD advantage.

**Parameters:** Standard test conditions (fiber type, wavelength, detector specs)

**Integration:** New module `benchmarks/qkd_benchmarks.py` connecting to all protocol
engines for standardized comparison runs.

---

## Summary of New Modules for Phase B

| Module Path | Topic | Priority |
|-------------|-------|----------|
| `qkd_protocols/cv_qkd.py` | CV-QKD (GG02, heterodyne) | High |
| `qkd_protocols/di_qkd.py` | Device-independent QKD | Medium |
| `qkd_protocols/sns_tf_qkd.py` | SNS-TF-QKD variant | High |
| `network/purification.py` | Entanglement purification (BBPSSW/DEJMPS) | High |
| `network/repeater_chain.py` | 1G/2G/3G repeater models | High |
| `channels/underwater.py` | Underwater channel model | Medium |
| `channels/urban.py` | Urban/indoor propagation | Low |
| `channels/spectral_atmosphere.py` | Wavelength-dependent extinction | Medium |
| `satellite/adaptive_optics.py` | AO correction model | Medium |
| `physics/detector_snspd.py` | SNSPD physics model | High |
| `physics/detector_ingaas.py` | InGaAs APD physics model | High |
| `physics/detector_pnr.py` | PNR/TES detector model | Medium |
| `physics/memory_platforms.py` | Platform-specific memories | High |
| `pipeline/error_correction.py` | LDPC/Cascade/Polar codes | High |
| `pipeline/privacy_amplification.py` | Toeplitz PA (FFT) | High |
| `pipeline/post_processing.py` | Full post-processing chain | High |
| `qrng/sources_advanced.py` | DI-QRNG, SDI-QRNG | Medium |
| `qrng/entropy_nist.py` | NIST SP 800-90B estimators | Medium |
| `integrations/classical_crypto.py` | AES/OTP/hybrid integration | Medium |
| `kms/lifecycle.py` | Key lifecycle management | Medium |
| `benchmarks/qkd_benchmarks.py` | Standardized benchmarking | Low |

---

## Key References (Consolidated)

### Protocols
1. Lo, Curty, Qi, PRL 108, 130503 (2012) - MDI-QKD
2. Lucamarini, Yuan, Dynes, Shields, Nature 557, 400 (2018) - TF-QKD
3. Ma, Zeng, Zhou, PRX 8, 031043 (2018) - PM-QKD
4. Wang et al., PRX Quantum 3, 040307 (2022) - SNS-TF-QKD
5. Grosshans, Grangier, PRL 88, 057902 (2002) - GG02 (CV-QKD)
6. Leverrier, PRL 114, 070501 (2015) - composable CV-QKD security
7. Pironio et al., NJP 11, 045021 (2009) - DI-QKD
8. Pirandola et al., Nature Comms 8, 15043 (2017) - PLOB bound

### Networks and Repeaters
9. Briegel, Dur, Cirac, Zoller, PRL 81, 5932 (1998)
10. Bennett et al., PRL 76, 722 (1996) - BBPSSW purification
11. Deutsch et al., PRL 77, 2818 (1996) - DEJMPS purification
12. Azuma et al., PRL 115, 010502 (2015) - all-photonic repeater

### Security
13. Renner, Int. J. Quantum Info 6, 1 (2008) - composable security
14. Tomamichel et al., Nature Comms 3, 634 (2012) - finite-key analysis
15. Tamaki et al., PRA 90, 052314 (2014) - loss-tolerant protocol
16. Arnon-Friedman et al., Nature Comms 9, 459 (2018) - entropy accumulation

### Detectors and Hardware
17. Natarajan et al., Supercond. Sci. Tech. 25, 063001 (2012) - SNSPD review
18. Marsili et al., Nature Photon. 7, 210 (2013) - 93% SNSPD
19. Noll, JOSA 66, 207 (1976) - Zernike/turbulence
20. Heshami et al., J. Mod. Opt. 63, 2005 (2016) - quantum memories

### Post-Processing
21. Martinez-Mateo et al., Sci. Rep. 3, 1576 (2013) - LDPC for QKD
22. Brassard, Salvail, CRYPTO 1993 - Cascade protocol
23. Tang et al., Sci. Rep. 9, 17733 (2019) - high-speed PA

### Standards
24. ETSI GS QKD 014 v1.1.1 (2019)
25. ETSI GS QKD 004 v2.1.1 (2020)
26. NIST SP 800-90B (2018) - entropy estimation
