# PhotonsTrust Phase C: Deep Scientific Research Report

## QKD Network Optimization, Satellite Scheduling, Experimental Calibration, and Protocol Comparison

---

## Table of Contents

1. [Multi-Hop QKD Network Optimization](#1-multi-hop-qkd-network-optimization)
2. [Satellite Constellation Scheduling](#2-satellite-constellation-scheduling)
3. [Noise Model Calibration Pipeline](#3-noise-model-calibration-pipeline)
4. [Reliability Card and Protocol Comparison Framework](#4-reliability-card-and-protocol-comparison-framework)
5. [Network-Layer QKD Architecture](#5-network-layer-qkd-architecture)

---

## 1. Multi-Hop QKD Network Optimization

### 1.1 Network Topology Models

#### 1.1.1 Trusted-Node Networks

In a trusted-node QKD network, intermediate relay nodes are assumed to be physically secured. Each link performs independent QKD, and keys are relayed through XOR-based one-time-pad encryption at each node. The end-to-end key rate is limited by the bottleneck (slowest) link.

**Beijing-Shanghai Backbone** (Chen et al., PRL 2021): A 2,000 km backbone with 32 trusted relay nodes, achieving end-to-end key distribution at a rate limited by the weakest segment. Typical link lengths are 50-100 km with fiber-based BB84 decoy-state QKD at each hop.

**SECOQC Network** (Peev et al., New J. Phys. 2009): A six-node network in Vienna with heterogeneous link technologies (BB84, entanglement-based, CV-QKD), demonstrating multi-protocol interoperability across a metropolitan-scale topology.

**Tokyo QKD Network** (Sasaki et al., Opt. Express 2011): A mesh network integrating multiple QKD devices from different manufacturers, with a key management layer providing application-transparent key supply.

**Published topology parameters:**

| Network | Nodes | Links | Max Link (km) | Total Distance (km) |
|---------|-------|-------|---------------|---------------------|
| Beijing-Shanghai | 32 | 31 | 96 | ~2,000 |
| SECOQC Vienna | 6 | 8 | 85 | ~200 |
| Tokyo QKD | 6 | 9 | 45 | ~90 |
| Cambridge QKD | 3 | 3 | 10 | ~20 |

#### 1.1.2 Untrusted-Node Networks with Quantum Repeaters

In untrusted-node architectures, no intermediate node needs to be trusted. Instead, quantum repeaters distribute entanglement across multiple segments using:

- **Entanglement swapping**: Bell-state measurements at repeater nodes connect adjacent entangled pairs.
- **Entanglement purification**: Multiple noisy pairs are consumed to produce fewer higher-fidelity pairs (BBPSSW/DEJMPS protocols).

The end-to-end entanglement rate for a 1G repeater chain with n segments is:

```
R_e2e = R_link / H_n * p_swap^m

where:
  R_link = f_rep * p_link         -- elementary link generation rate
  p_link = eta_half^2 * eta_d^2 * eta_mem^2  -- link generation probability
  eta_half = 10^(-alpha * L_seg / (2 * 10))  -- half-segment transmittance
  H_n = sum_{k=1}^{n} 1/k         -- n-th harmonic number (multiplexing penalty)
  m = ceil(log2(n))                -- number of swap levels
  p_swap                           -- Bell-state measurement success probability
```

**Fidelity through nested swapping:**

```
F_chain = 0.5 + 0.5 * (2*F_link - 1)^(2^m)
```

With memory decoherence during waiting time t_wait:

```
F_chain(t) = 0.5 + (F_chain - 0.5) * exp(-t_wait / T_2)
```

These equations are already implemented in `photonstrust/network/repeater_chain.py` as `first_gen_repeater_chain()`.

#### 1.1.3 Hybrid Trusted/Untrusted Architectures

A practical deployment may combine both paradigms:

- **Core backbone**: Trusted nodes at major cities (lower cost, mature technology).
- **Last-mile/metro**: Quantum repeaters for high-security segments.
- **Satellite links**: For inter-city connectivity where fiber is unavailable.

The hybrid routing problem requires a heterogeneous graph model where each edge has:
- `link_type`: fiber_trusted, fiber_repeater, free_space_satellite
- `key_rate_bps(d)`: link-type-dependent key rate function
- `security_level`: {information_theoretic, device_independent, trusted_relay}
- `reliability`: link availability (probability of being operational)

### 1.2 Routing Algorithms for QKD Networks

#### 1.2.1 Shortest Path with Fidelity/Rate Constraints

The existing `photonstrust/network/routing.py` implements Dijkstra's algorithm with physical distance as the metric. For QKD-specific routing, we need constrained shortest path formulations.

**Rate-Constrained Shortest Path:**

```
minimize  sum_{(i,j) in path} d_{ij}
subject to  min_{(i,j) in path} R_{ij} >= R_min
```

**Fidelity-Constrained Shortest Path (for repeater networks):**

```
minimize  sum_{(i,j) in path} d_{ij}
subject to  product_{(i,j) in path} F_{ij} >= F_min
```

Since fidelity is multiplicative, we can take logarithms and use a standard additive Dijkstra formulation:

```
minimize  sum_{(i,j)} d_{ij}
subject to  sum_{(i,j)} (-log(F_{ij})) <= -log(F_min)
```

**Algorithm: Constrained Dijkstra (pseudocode)**

```
function CONSTRAINED_DIJKSTRA(G, s, t, R_min):
    dist[s] = 0, bottleneck[s] = infinity
    PQ = {(0, infinity, s)}  // (distance, bottleneck_rate, node)

    while PQ not empty:
        (d, bn, u) = PQ.extract_min()
        if u == t:
            return reconstruct_path(prev, t)

        for v in neighbors(u):
            link = get_link(u, v)
            new_dist = d + link.distance_km
            new_bn = min(bn, link.key_rate_bps)

            if new_bn >= R_min and new_dist < dist[v]:
                dist[v] = new_dist
                bottleneck[v] = new_bn
                prev[v] = u
                PQ.insert((new_dist, new_bn, v))

    return NO_PATH
```

#### 1.2.2 Max-Flow for Key Distribution Capacity

The max-flow formulation treats the QKD network as a capacitated graph where each edge capacity equals the link key rate. The Ford-Fulkerson / Edmonds-Karp algorithm can compute the maximum key distribution capacity between any two endpoints.

**Network capacity theorem for trusted-node relay:**

For a trusted-node network, the max-flow equals the minimum cut (max-flow min-cut theorem):

```
max_flow(s, t) = min_cut(s, t) = min_{S: s in S, t not in S} sum_{(u,v): u in S, v not in S} R_{uv}
```

**Multi-commodity flow for simultaneous QKD sessions:**

When K endpoint pairs {(s_1,t_1), ..., (s_K,t_K)} simultaneously request key distribution:

```
maximize   sum_{k=1}^{K} f_k    (total key throughput)
subject to:
  sum_{k} f_k(e) <= c(e)        for all edges e  (capacity constraint)
  flow conservation at each node for each commodity
  f_k >= 0                       for all k
```

This is a linear program solvable by standard LP solvers (scipy.optimize.linprog or NetworkX's min-cost max-flow).

**Ref:** Mehic, M. et al., "Quantum Key Distribution: A Networking Perspective," ACM Computing Surveys 53(5), 2020.

#### 1.2.3 Widest-Path (Bottleneck Shortest Path) Algorithm

The existing `max_key_rate_path()` in `photonstrust/network/routing.py` implements the widest-path algorithm using a modified Dijkstra that maximizes the minimum key rate along the path. This is the correct approach for trusted-node networks where end-to-end rate equals the bottleneck link rate.

**Key insight for Phase C extension:**

The current implementation only considers the bottleneck rate. For networks with parallel paths, the effective end-to-end rate can exceed any single path's bottleneck by using multiple paths simultaneously:

```
R_effective(s,t) = sum_{p in parallel_paths} R_bottleneck(p)
```

This is precisely the max-flow formulation described above.

#### 1.2.4 Reliability-Aware Routing

Each link has an availability probability a_{ij} (probability of being operational at any given time). The end-to-end path reliability is:

```
A_path = product_{(i,j) in path} a_{ij}
```

**Reliability-constrained routing:**

```
maximize  R_bottleneck(path)
subject to  product_{(i,j) in path} a_{ij} >= A_min
```

Converting to additive form with -log(a_{ij}):

```
minimize  -R_bottleneck(path)
subject to  sum_{(i,j)} (-log(a_{ij})) <= -log(A_min)
```

**Backup path computation** (Suurballe's algorithm adapted for QKD):

Find K edge-disjoint paths between endpoints to ensure continued key distribution even when K-1 paths fail.

### 1.3 Objective Functions and Network Metrics

#### 1.3.1 Network-Wide Key Rate Optimization

**Total network key capacity:**

```
C_net = sum_{(s,t) in demand_pairs} R_e2e(s,t)
```

**Key rate fairness index** (Jain's fairness):

```
J = (sum R_i)^2 / (K * sum R_i^2)
```

where R_i is the key rate allocated to the i-th demand pair and K is the number of demand pairs. J = 1 implies perfect fairness.

#### 1.3.2 Minimize Trusted Nodes

Trusted nodes are security-sensitive. The optimization problem:

```
minimize  |{v in path(s,t) : v is trusted}|
subject to  R_e2e(s,t) >= R_min
```

This is implemented in `_path_to_network_path()` which already counts `trusted_node_count`.

#### 1.3.3 Rate-Fidelity Tradeoff

For repeater-assisted networks, there is a fundamental tradeoff between rate and fidelity. Adding purification rounds increases fidelity but decreases rate exponentially (each round consumes 2 pairs and succeeds with probability p < 1):

```
R_purified = R_raw * (p_purification / 2)^{n_rounds}
F_purified = BBPSSW^{n_rounds}(F_raw)
```

The Pareto-optimal frontier can be computed by sweeping purification rounds (0, 1, 2, ...) for each link.

### 1.4 Key Relay Protocols

#### 1.4.1 XOR-Based Trusted Node Relay

At each trusted node T_i on a path from Alice to Bob:

1. T_i shares key K_{i,left} with the left neighbor via QKD
2. T_i shares key K_{i,right} with the right neighbor via QKD
3. T_i computes C_i = K_{i,left} XOR K_{i,right} and sends C_i to Bob over authenticated classical channel
4. Bob reconstructs Alice's key from the chain of XOR ciphertexts

**Security implication:** Every intermediate node sees the plaintext key. If any single trusted node is compromised, the end-to-end key is compromised.

**Authentication overhead:** Each link requires information-theoretically secure authentication, consuming ~ 2*log2(1/epsilon_auth) bits per authentication round (Wegman-Carter universal hashing). For epsilon_auth = 10^{-10}, this is ~ 66 bits per round.

#### 1.4.2 Rate Bottleneck Analysis

End-to-end key rate through a chain of n trusted nodes:

```
R_e2e = min_{i=1,...,n+1} R_link_i - R_auth
```

where R_auth is the key consumption rate for authentication (typically negligible).

**Key buffering requirement:**

Each link must maintain a key buffer of size:

```
B_i >= R_link_i * T_buffer
```

where T_buffer accounts for key rate fluctuations. The buffer at the bottleneck link determines the sustainable end-to-end rate.

### 1.5 Published Network Benchmark Parameters

**Beijing-Shanghai backbone (Chen et al., PRL 2021):**
- 32 trusted nodes over 2,000 km
- Segment lengths: 50-96 km
- Protocol: BB84 with decoy states
- Per-link rates: 1-50 kbps (shorter segments faster)
- End-to-end rate (bottleneck): ~4.6 kbps across 2,000 km
- Fiber loss: 0.2 dB/km at 1550 nm

**SECOQC Vienna (Peev et al., New J. Phys. 2009):**
- 6 nodes, 8 links (mesh topology)
- Link technologies: BB84, entanglement, CV-QKD
- Maximum link: 85 km
- Demonstrated real-time key management across heterogeneous links

**Tokyo QKD (Sasaki et al., Opt. Express 2011):**
- 6 nodes in JGN2plus research network
- Multiple vendor devices integrated
- Key management layer: ETSI QKD 004 compliant
- Demonstrated 45 km link with 2.2 kbps key rate

**References:**
- Mehic, M. et al., ACM Computing Surveys 53(5), 2020
- Cao, Y. et al., Phys. Rev. Applied 17, 054035, 2022
- Chakraborty, K. et al., IEEE JSAC 37(10), 2019
- Chen, Y.-A. et al., PRL 2021 (Beijing-Shanghai integrated)
- Peev, M. et al., New J. Phys. 11, 075001, 2009 (SECOQC)
- Sasaki, M. et al., Opt. Express 19(11), 2011 (Tokyo)

---

## 2. Satellite Constellation Scheduling

### 2.1 LEO Satellite Pass Geometry

#### 2.1.1 Orbital Mechanics Foundations

A satellite in a circular orbit at altitude h above the Earth (radius R_E = 6371 km) has orbital period:

```
T_orb = 2 * pi * sqrt((R_E + h)^3 / mu)

where mu = 3.986 x 10^5 km^3/s^2 (standard gravitational parameter)
```

The angular velocity is:

```
omega = 2*pi / T_orb = sqrt(mu / (R_E + h)^3)
```

**Typical values:**

| Altitude (km) | T_orb (min) | v_ground (km/s) | Passes/day |
|--------------|-------------|-----------------|------------|
| 400 (ISS) | 92.6 | 7.67 | ~15.6 |
| 500 (Micius) | 94.6 | 7.61 | ~15.3 |
| 600 | 96.7 | 7.56 | ~14.9 |
| 800 | 100.9 | 7.45 | ~14.3 |

#### 2.1.2 Slant Range and Elevation

The slant range from ground station to satellite at elevation angle theta_el is:

```
D(theta) = -R_E * sin(theta) + sqrt((R_E * sin(theta))^2 + h^2 + 2*R_E*h)
```

This is implemented in `photonstrust/orbit/geometry.py` as `slant_range_km()`.

At zenith (theta = 90 deg): D = h (minimum distance)
At horizon (theta = 0 deg): D = sqrt(h^2 + 2*R_E*h) ~ sqrt(2*R_E*h) for h << R_E

**Atmospheric path length** (equivalent airmass approximation):

```
L_atm(theta) = H_atm / sin(theta)    for theta > 10 deg (flat-Earth)

L_atm(theta) = H_atm / sqrt(sin^2(theta) + 2*H_atm/R_E)  (curved-Earth correction)
```

where H_atm ~ 8-20 km is the effective atmospheric scale height.

#### 2.1.3 Visible Pass Duration

The half-angle of visibility above minimum elevation theta_min is computed via binary search (as in `_solve_visible_half_angle_rad()` in `geometry.py`). The visible pass duration is:

```
T_pass = 2 * gamma_max / omega
```

**Typical pass durations for Micius (h = 500 km):**

| Min Elevation | Pass Duration (s) | Max Slant Range (km) |
|--------------|-------------------|---------------------|
| 10 deg | ~360 | ~1660 |
| 20 deg | ~270 | ~1200 |
| 30 deg | ~200 | ~880 |
| 45 deg | ~130 | ~620 |

#### 2.1.4 TLE Propagation

For operational pass prediction, Two-Line Element sets (TLEs) are propagated using the SGP4/SDP4 model (Vallado et al., 2006):

```
Inputs:  TLE epoch, inclination, RAAN, eccentricity, arg_perigee, mean_anomaly, mean_motion
Output:  ECI position/velocity at any future time

Ground trace:  ECI -> ECEF -> geodetic (lat, lon, alt)
Topocentric:   ECEF -> local horizontal -> azimuth, elevation, range
```

The existing `photonstrust/orbit/providers/skyfield_provider.py` wraps Skyfield for high-fidelity TLE propagation.

### 2.2 Constellation Architectures for QKD

#### 2.2.1 Walker Delta Constellations

A Walker delta constellation is defined by T/P/F where:
- T = total number of satellites
- P = number of orbital planes
- F = phasing parameter (0 <= F < P)

Each plane has S = T/P satellites. The satellites in adjacent planes are offset by F * 360/(T) degrees in mean anomaly.

**Access analysis for QKD:**

For a ground station at latitude phi, the average number of accessible satellites at any instant from a Walker constellation with inclination i is approximately:

```
N_accessible ~ (T / (4*pi)) * 2*gamma_max * min(2, sec(phi-i))
```

where gamma_max is the visibility half-angle.

**Recommended QKD constellation parameters (from Sidhu et al., 2021):**

| Parameter | Small | Medium | Large |
|-----------|-------|--------|-------|
| Satellites | 12 | 40 | 168 |
| Planes | 3 | 8 | 12 |
| Inclination | 55-60 deg | 55-60 deg | 55-87 deg |
| Altitude | 500-600 km | 500-600 km | 500-800 km |
| Global coverage gap | Large | Small | None (>20 deg el) |

#### 2.2.2 Sun-Synchronous Orbits (SSO)

Sun-synchronous orbits maintain a constant angle between the orbital plane and the Sun. The inclination for SSO is:

```
cos(i) = -T_orb * J_2_rate / omega_sun

For h=500 km: i ~ 97.4 deg
For h=600 km: i ~ 97.8 deg
```

**QKD advantage of SSO:** Consistent local solar time at each latitude, which allows systematic scheduling of nighttime passes (critical for satellite QKD in the optical band).

**LTAN (Local Time of Ascending Node) selection:**
- Dawn-dusk orbit (LTAN ~ 06:00/18:00): Maximum nighttime ground coverage at mid-latitudes
- Pre-dawn orbit (LTAN ~ 04:00): Extended dark-sky windows for QKD

#### 2.2.3 Altitude vs Coverage Tradeoff

Higher altitude provides larger footprint but increases free-space loss:

```
Free-space loss (dB) = 20*log10(4*pi*D/lambda)

At lambda = 850 nm:
  D = 500 km: loss = 252.4 dB (geometric only)
  D = 1000 km: loss = 258.4 dB
  D = 2000 km: loss = 264.4 dB
```

**Key rate scaling with altitude:**

```
SKR(h) ~ R_source * eta_atm(theta) * eta_geo(h, theta) * eta_turb(theta) * eta_det * r_key
```

where:
- eta_geo = (D_rx / (D_tx + lambda*D/D_tx))^2 ~ (D_rx * D_tx / (lambda * D))^2 (far-field)
- eta_atm = exp(-tau / sin(theta)) with tau ~ 0.1-0.3 (extinction optical depth)
- eta_turb: turbulence-induced beam wander and scintillation loss

**Optimal altitude window:** 400-800 km (Bourgoin et al., 2013). Below 400 km, atmospheric drag limits lifetime. Above 800 km, geometric loss dominates.

### 2.3 Pass Scheduling Optimization

#### 2.3.1 Contact Window Computation

For each satellite-ground station pair, compute contact windows:

```
function COMPUTE_CONTACTS(sat, gs, t_start, t_end, el_min):
    contacts = []
    t = t_start
    while t < t_end:
        theta = elevation(sat, gs, t)
        if theta >= el_min and not in_contact:
            contact_start = refine_aos(t, el_min)  // Acquisition of Signal
            in_contact = true
        elif theta < el_min and in_contact:
            contact_end = refine_los(t, el_min)  // Loss of Signal
            contacts.append(Contact(contact_start, contact_end, max_el))
            in_contact = false
        t += dt_step
    return contacts
```

#### 2.3.2 Key Volume Per Pass

The total key bits accumulated during a pass is the integral of the instantaneous secure key rate over the pass duration:

```
K_total = integral_{t_AOS}^{t_LOS} SKR(theta(t)) * dt

Discretized: K_total = sum_{i=0}^{N} SKR(theta(t_i)) * dt
```

where SKR(theta) depends on the elevation-dependent channel loss:

```
SKR(theta) = R_source * sifting * [1 - H(QBER(theta)) - f_EC * H(QBER(theta))]
            * eta_total(theta)

eta_total(theta) = eta_source * eta_channel(theta) * eta_detector
eta_channel(theta) = eta_geo(D(theta)) * eta_atm(theta) * eta_turb(theta) * eta_pointing
```

This integral is already implemented in `photonstrust/satellite/pass_budget.py` as `compute_pass_key_budget()`.

**Typical key volumes (Micius, BB84-decoy, nighttime):**

| Max Elevation | Pass Duration (s) | Key Volume (kbit) |
|--------------|-------------------|-------------------|
| 30 deg | ~180 | ~50 |
| 50 deg | ~220 | ~300 |
| 70 deg | ~250 | ~800 |
| 85 deg (overhead) | ~260 | ~1200 |

*Ref: Liao et al., Nature 549, 43 (2017), PRL 120, 030501 (2018)*

#### 2.3.3 Multi-Ground-Station Scheduling

Given:
- S satellites, G ground stations, time horizon [0, T]
- Contact windows C_{sg} for each satellite-ground station pair
- Key volume K(C_{sg}) for each contact window
- Weather probability p_clear(g, t) for each ground station

The scheduling optimization is an assignment problem:

```
maximize   sum_{s,g,c} x_{sgc} * K(c) * p_clear(g, t_c)
subject to:
  sum_{g,c} x_{sgc} <= 1              for each satellite s at each time t
                                       (satellite can only point at one GS)
  sum_{s,c} x_{sgc} <= N_receivers(g)  for each GS g at each time t
                                       (GS has limited receivers)
  x_{sgc} in {0, 1}                    binary assignment
```

This is a variant of the generalized assignment problem (GAP), which is NP-hard but efficiently solvable for practical sizes via integer linear programming (ILP) or greedy heuristics.

**Algorithm: Priority-Based Greedy Scheduling (pseudocode)**

```
function GREEDY_SCHEDULE(contacts, priorities):
    schedule = {}
    sorted_contacts = sort(contacts, key=lambda c: -priority(c))

    for contact in sorted_contacts:
        if satellite_available(contact.sat, contact.time):
            if gs_available(contact.gs, contact.time):
                if weather_ok(contact.gs, contact.time):
                    schedule[contact] = True
                    mark_satellite_busy(contact.sat, contact.time)
                    mark_gs_busy(contact.gs, contact.time)

    return schedule
```

Priority function incorporating key volume and weather:

```
priority(c) = K(c) * p_clear(c.gs, c.time) * (1 + beta * ln(t_since_last_key(c.gs)))
```

The last term provides a fairness boost to ground stations that have not received keys recently.

#### 2.3.4 Weather-Adaptive Scheduling

Cloud cover is the primary weather constraint for optical satellite QKD. Key statistics:

```
p_clear(location) = historical clear-sky probability

Expected key volume = K_pass * p_clear
Annual expected keys = N_passes/year * K_avg * p_clear
```

**Global clear-sky probability (selected sites):**

| Location | Clear Night Fraction | Passes/day | Expected Keys/day (kbit) |
|----------|---------------------|------------|-------------------------|
| Mauna Kea, HI | 0.65 | 4.5 | ~500 |
| Xinglong, China | 0.45 | 4.0 | ~250 |
| Vienna, Austria | 0.30 | 3.5 | ~130 |
| Singapore | 0.20 | 5.0 | ~120 |

### 2.4 Key Volume Estimation Models

#### 2.4.1 SKR(elevation) Integration

For a satellite pass with elevation profile theta(t), the instantaneous secure key rate for BB84 decoy-state downlink:

```
SKR(theta) = f_rep * mu_1 * eta(theta) * exp(-mu_1) * [1 - H(e_1^U(theta))]
           - f_rep * Q_mu(theta) * f_EC * H(E_mu(theta))
```

where:
- f_rep: laser repetition rate (typically 100 MHz - 1 GHz)
- mu_1: signal-state mean photon number
- eta(theta): elevation-dependent total transmittance
- e_1^U(theta): upper bound on single-photon phase error rate
- Q_mu(theta): signal-state gain
- E_mu(theta): signal-state QBER

**Elevation dependence of transmittance:**

```
eta(theta) = eta_geo(D(theta)) * eta_atm(theta) * eta_turb(theta) * eta_pointing * eta_det

eta_geo(D) = (A_rx / (lambda * D / (pi * w_0)))^2  (Gaussian beam, far-field)
           ~ (pi * D_rx^2 / 4) / (pi * (lambda * D / (pi * w_0))^2)

eta_atm(theta) = exp(-tau_zenith / sin(theta))   (Beer-Lambert with airmass)

eta_turb(theta): Gamma-Gamma or lognormal fading (see Section 2.4.2)
```

#### 2.4.2 Turbulence Models for Key Rate

The Hufnagel-Valley Cn2 profile (implemented in `photonstrust/satellite/turbulence.py`):

```
Cn2(h) = 0.00594 * (v_wind/27)^2 * (10^{-5} * h)^{10} * exp(-h/1000)
        + 2.7e-16 * exp(-h/1500) + A_0 * exp(-h/100)

where:
  v_wind: rms wind speed (m/s), typically 21 m/s
  A_0: ground-level turbulence strength, typically 1.7e-14 m^{-2/3}
  h: altitude above ground (meters)
```

**Rytov variance** (scintillation strength for downlink):

```
sigma_R^2 = 2.25 * k^{7/6} * sec^{11/6}(zeta) * integral_0^H Cn2(h) * (h - h_0)^{5/6} dh

where:
  k = 2*pi/lambda (optical wavenumber)
  zeta = 90 - theta_el (zenith angle)
  H: satellite altitude
  h_0: ground station altitude
```

**Gamma-Gamma parameters from Rytov variance** (implemented in `pass_budget.py`):

```
alpha = [exp(0.49*sigma_R^2 / (1 + 1.11*sigma_R^{12/5})^{7/6}) - 1]^{-1}
beta  = [exp(0.51*sigma_R^2 / (1 + 0.69*sigma_R^{12/5})^{5/6}) - 1]^{-1}
```

#### 2.4.3 Daylight vs Nighttime Operation

Background photon rate from sky radiance:

```
R_bg = L_sky * A_rx * Omega_FOV * Delta_lambda * eta_filter * eta_det

where:
  L_sky: sky spectral radiance (W / (m^2 * sr * nm))
    Night: ~ 10^{-7} W/(m^2*sr*nm) at 850 nm
    Day:   ~ 10^{-2} W/(m^2*sr*nm) at 850 nm (5 orders of magnitude higher)
  A_rx: receiver aperture area
  Omega_FOV: receiver field of view (sr)
  Delta_lambda: spectral filter bandwidth (nm)
  eta_filter: spectral filter transmission
```

**Daytime mitigation strategies:**
- Narrowband spectral filters (< 0.1 nm)
- Spatial filtering (adaptive optics, single-mode fiber coupling)
- Temporal gating (synchronized to laser pulses)
- Wavelength shift to 1550 nm (lower solar radiance)

*Ref: Liao et al., Nature Physics 13, 648 (2017) -- daytime satellite QKD*

### 2.5 Published Satellite QKD Results

**Micius satellite (Liao et al., Nature 549, 43, 2017; PRL 120, 030501, 2018):**
- Altitude: 500 km, inclination: 97.4 deg (SSO)
- BB84 decoy-state downlink
- 1200 km satellite-to-ground QKD demonstrated
- Key rate: ~1 kbps at 1200 km (nighttime, high elevation)
- Wavelength: 850 nm
- Source: 100 MHz pulsed WCP
- Detectors: Si-APD (45% efficiency, 25 DCR)
- Telescope: 1.0 m Rx at Xinglong, 0.3 m Tx on satellite

**SpeQtral (Singapore):**
- CubeSat-class platform (6U-12U)
- Target: entanglement distribution from LEO
- Altitude: 500-550 km
- Planned key rate: ~1 kbps at 500 km

**QEYSSat (Canada, Bourgoin et al., 2013):**
- Microsatellite (~100 kg)
- BB84 uplink (ground-to-satellite)
- Altitude: 600 km
- Target: key distribution to Canadian ground network
- Uplink advantage: complex/expensive Tx on ground, simple Rx in space

**References:**
- Bourgoin, J.-P. et al., New J. Phys. 15, 023006, 2013
- Liao, S.-K. et al., Nature 549, 43, 2017
- Liao, S.-K. et al., PRL 120, 030501, 2018
- Sidhu, J. S. et al., IOP SciNotes 2(3), 035202, 2021
- Bedington, R. et al., npj Quantum Information 3, 30, 2017 (SpeQtral)

---

## 3. Noise Model Calibration Pipeline

### 3.1 Detector Calibration

#### 3.1.1 SNSPD Calibration

**Efficiency vs bias current:**

SNSPD detection efficiency follows a sigmoid curve as a function of bias current:

```
eta_SNSPD(I_b) = eta_max / (1 + exp(-k * (I_b - I_50)))

where:
  I_b: bias current
  I_50: current at 50% of maximum efficiency
  k: steepness parameter
  eta_max: saturated detection efficiency (system-level, includes coupling)
```

**Typical SNSPD parameters (WSi, 1550 nm):**

| Parameter | Value | Unit |
|-----------|-------|------|
| System detection efficiency | 85-93% | - |
| Dark count rate | 1-100 | cps |
| Timing jitter (FWHM) | 15-60 | ps |
| Dead time (recovery) | 20-80 | ns |
| Maximum count rate | 10-50 | MHz |
| Operating temperature | 0.8-2.5 | K |

**Timing jitter histogram fitting:**

The jitter histogram is typically fitted with a Gaussian convolved with an exponential decay:

```
h(t) = A * [Gaussian(t; t_0, sigma) * exp(-t/tau)] convolution
     = (A / (2*tau)) * exp(sigma^2/(2*tau^2) - (t-t_0)/tau)
       * erfc((sigma^2 - tau*(t-t_0)) / (sqrt(2)*sigma*tau))
```

Maximum likelihood fit with Poisson-distributed bin counts:

```
L = product_i Poisson(n_i | lambda_i = h(t_i) * dt)
log L = sum_i [n_i * log(h(t_i)*dt) - h(t_i)*dt - log(n_i!)]
```

#### 3.1.2 InGaAs APD Calibration

**Afterpulsing probability extraction:**

Afterpulsing is characterized by the time-dependent afterpulse probability:

```
P_ap(t) = sum_{j=1}^{M} A_j * exp(-t / tau_j)

where:
  A_j: amplitude of the j-th trap level
  tau_j: de-trapping time constant of the j-th trap
  M: number of trap levels (typically 2-4)
```

**Measurement protocol:**
1. Send a strong optical pulse to cause an avalanche at time t=0
2. Re-arm the detector at variable delay t_delay
3. Measure dark count rate in a window after re-arming
4. Afterpulse rate = measured rate - DCR_baseline
5. Fit multi-exponential model to P_ap(t_delay)

**DCR vs temperature:**

```
DCR(T) = DCR_0 * exp(E_a / (k_B * T_0) - E_a / (k_B * T))

where:
  E_a: activation energy (~0.3-0.7 eV for InGaAs)
  k_B: Boltzmann constant (8.617e-5 eV/K)
  T_0: reference temperature
  DCR_0: DCR at reference temperature
```

**Typical InGaAs APD parameters:**

| Parameter | Free-running | Gated (1 GHz) | Unit |
|-----------|-------------|---------------|------|
| Detection efficiency | 10-25% | 15-30% | - |
| Dark count rate | 1-10 k | 10^{-5}-10^{-4}/gate | cps or /gate |
| Afterpulsing prob. | 5-15% | 1-5% | per detection |
| Timing jitter | 100-500 | 50-200 | ps |
| Dead time | 1-10 us | 1 gate (1 ns) | - |

#### 3.1.3 ETSI QKD Calibration Standards

ETSI GS QKD 011 defines calibration procedures:

1. **Detector efficiency**: Use calibrated attenuator + power meter reference
2. **Dark count rate**: Block all input light, count over > 100 s integration
3. **Timing jitter**: Pulsed laser (< 10 ps) + time-correlated single photon counting (TCSPC)
4. **Afterpulsing**: Time-gated correlation measurement with known trigger pulse
5. **Wavelength calibration**: Reference to NIST-traceable wavelength standard

### 3.2 Channel Calibration

#### 3.2.1 Fiber Loss Measurement

**OTDR data fitting:**

Optical Time-Domain Reflectometry provides loss vs distance:

```
P(z) = P_0 * exp(-alpha * z)    (in linear)
P_dB(z) = P_0_dB - alpha_dB * z  (in dB)

alpha_dB (dB/km) = -slope of linear fit to P_dB(z)
```

**Connector/splice loss extraction:**

Event detection in OTDR trace:
- Reflective events (connectors): sharp spikes in backscatter
- Non-reflective events (splices): step changes in backscatter level
- Loss per event: difference in backscatter levels before and after

**Standard fiber loss values:**

| Fiber Type | Wavelength (nm) | Loss (dB/km) |
|-----------|----------------|--------------|
| SMF-28 | 1310 | 0.35 |
| SMF-28 | 1550 | 0.18-0.20 |
| SMF-28e+ | 1550 | 0.17 |
| Ultra-low-loss | 1550 | 0.14-0.16 |
| Multimode OM3 | 850 | 2.5-3.5 |

#### 3.2.2 Atmospheric Turbulence Cn2 Estimation

**From scintillation measurements:**

For a point source (star or satellite beacon) observed through the atmosphere, the scintillation index is:

```
sigma_I^2 = integral_0^L C_n^2(z) * W(z) dz

where W(z) is the weighting function depending on:
  - aperture diameter D_rx
  - propagation geometry (downlink/uplink)
  - wavelength lambda
```

**For weak turbulence (downlink, plane wave):**

```
sigma_I^2 = 2.25 * k^{7/6} * sec^{11/6}(zeta) * integral_0^H C_n^2(h) * h^{5/6} dh
```

**Cn2 profile estimation from multi-layer scintillation:**

Using SCIDAR (SCIntillation Detection And Ranging) or MASS (Multi-Aperture Scintillation Sensor):

```
C_n^2(h_j) is estimated by solving:

sigma_I^2(D_k) = sum_j C_n^2(h_j) * W(h_j, D_k)

for multiple aperture sizes D_k, yielding a discrete profile.
```

**Hufnagel-Valley 5/7 model parameters (standard reference):**
- A_0 = 1.7e-14 m^{-2/3}
- v_rms = 21 m/s
- Fried parameter r_0 ~ 5-7 cm at 500 nm, zenith

#### 3.2.3 Underwater Channel Characterization

For submarine QKD links (emerging application), the beam spread function (BSF) determines the channel:

```
PSF(r, z) = E_d(r, z) / E_0

where:
  E_d: diffuse irradiance at radial distance r and depth z
  E_0: source irradiance

Approximation (small-angle scattering):
  eta_water(z) = exp(-(c * z))   where c = a + b (total attenuation coefficient)
  a: absorption coefficient (m^{-1})
  b: scattering coefficient (m^{-1})
```

**Jerlov water types (attenuation at 532 nm):**

| Water Type | c (m^{-1}) | Max QKD Distance (m) |
|-----------|-----------|---------------------|
| Type I (clearest ocean) | 0.05 | ~80-100 |
| Type II (clear ocean) | 0.10 | ~40-60 |
| Type III (coastal) | 0.20 | ~20-30 |
| Type 1C (coastal, turbid) | 0.50 | ~8-12 |

### 3.3 Fitting Methods

#### 3.3.1 Maximum Likelihood Estimation for Poisson Detection

For photon-counting experiments, the detection counts follow Poisson statistics:

```
P(n | lambda) = lambda^n * exp(-lambda) / n!

Log-likelihood for N measurements:
  log L(params) = sum_{i=1}^{N} [n_i * log(lambda_i(params)) - lambda_i(params)]

where lambda_i(params) is the model-predicted count rate for measurement i.
```

**Fisher information matrix** (for parameter uncertainty estimation):

```
I_{jk} = -E[d^2 log L / (d theta_j * d theta_k)]

For Poisson: I_{jk} = sum_i (1/lambda_i) * (d lambda_i / d theta_j) * (d lambda_i / d theta_k)

Parameter covariance: Cov(theta) ~ I^{-1}
```

#### 3.3.2 Bayesian Parameter Estimation

The existing `photonstrust/calibrate/bayes.py` implements importance-sampling-based Bayesian calibration. The approach:

1. **Prior**: Uniform over physically plausible ranges (from `priors.py`)
2. **Likelihood**: Gaussian kernel centered on observed values
3. **Posterior**: Weighted samples (importance weights)
4. **Diagnostics**: ESS (Effective Sample Size), R-hat proxy, PPC score

**For improved calibration, the following extensions are recommended:**

**Markov Chain Monte Carlo (MCMC) with Metropolis-Hastings:**

```
function MCMC_CALIBRATE(model, observations, n_samples, priors):
    theta_current = sample_from_priors(priors)
    chain = [theta_current]

    for i in 1 to n_samples:
        theta_proposal = theta_current + N(0, step_size)

        log_alpha = log_posterior(theta_proposal) - log_posterior(theta_current)

        if log(uniform()) < log_alpha:
            theta_current = theta_proposal  // accept

        chain.append(theta_current)

    return chain[burn_in:]    // discard burn-in

where:
  log_posterior(theta) = log_prior(theta) + log_likelihood(observations | model(theta))
```

**Convergence diagnostics:**
- Gelman-Rubin R-hat < 1.01 (multiple chains)
- Effective sample size > 100 per parameter
- Trace plot stationarity
- Posterior predictive check (PPC) p-value > 0.05

#### 3.3.3 Chi-Squared Goodness of Fit

For binned data (e.g., histogram of detection times):

```
chi^2 = sum_{i=1}^{N_bins} (O_i - E_i)^2 / E_i

where:
  O_i: observed counts in bin i
  E_i: expected counts from model in bin i

Reduced chi^2 = chi^2 / (N_bins - N_params)

Good fit: reduced chi^2 ~ 1.0
Overfitting: reduced chi^2 << 1.0
Poor fit: reduced chi^2 >> 1.0
```

### 3.4 Validation Against Published Experiments

#### 3.4.1 BB84 Experiments

**Gobby, Yuan, Shields (APL 2004):**
- 122 km fiber, BB84 with decoy states
- Key rate: 1.02 kbps at 20 km, 24.6 bps at 122 km
- Fiber loss: 0.21 dB/km
- Detector: InGaAs APD, eta=10%, DCR=6.6e-6/gate, gate=1 GHz
- QBER: 3.2% at 20 km, 8.9% at 122 km

**Calibration targets for PhotonsTrust validation:**

```
At 20 km:
  eta_channel = 10^{-0.21*20/10} = 0.10 (-10 dB)
  Expected key_rate ~ 1 kbps (match within 50%)
  Expected QBER ~ 3-4%

At 122 km:
  eta_channel = 10^{-0.21*122/10} = 1.7e-3 (-27.6 dB)
  Expected key_rate ~ 10-50 bps (match within order of magnitude)
  Expected QBER ~ 8-10%
```

**Rosenberg et al. (PRL 2007):**
- BB84, InGaAs SPDs, 107 km fiber
- Key rate: 1.5 kbps (10 km), 5.7 bps (107 km)
- QBER: 2.7% (10 km), 7.2% (107 km)
- Source: 625 MHz WCP

#### 3.4.2 CV-QKD Experiments

**Jouguet et al. (Nature Photonics 2013):**
- Gaussian-modulated coherent states (GG02)
- 80.5 km fiber, 0.18 dB/km (ultra-low-loss)
- Key rate: 0.3 kbps at 80.5 km
- Shot-noise-limited homodyne detection
- Excess noise: 0.01 SNU (shot noise units)
- Reconciliation efficiency: beta = 95.9% at SNR < 1

**Calibration parameters:**

```
V_A = 3.6 SNU (modulation variance)
T = 10^{-0.18*80.5/10} = 0.0355 (-14.5 dB)
xi = 0.01 SNU (excess noise)
eta_det = 0.606 (detector efficiency)
v_el = 0.01 SNU (electronic noise)
beta = 0.959 (reconciliation efficiency)
```

#### 3.4.3 TF-QKD Experiments

**Chen et al. (Nature 2021) -- 511 km TF-QKD:**
- SNS-TF-QKD protocol
- 511 km ultra-low-loss fiber (0.157 dB/km)
- Key rate: 0.118 bps at 511 km
- Signal intensity mu_z = 0.08
- Source: 250 MHz laser
- Detectors: SNSPD, eta=55%, DCR=1 cps, jitter=68 ps
- Phase tracking: real-time reference-frame calibration

**Pittaluga et al. (Nature Photonics 2021) -- 605 km TF-QKD:**
- Sending-or-not-sending (SNS) variant
- 605 km fiber (0.167 dB/km)
- Key rate: 0.044 bps at 605 km (finite-key, composable)
- Detectors: SNSPD, eta=88%, DCR=0.02 cps
- Broke repeaterless bound (PLOB) at ~340 km

**Calibration benchmarks for TF-QKD validation:**

```
Target: match key rate within 1 order of magnitude at:
  - 200 km: ~100-1000 bps
  - 400 km: ~1-10 bps
  - 500 km: ~0.01-1 bps
  - 600 km: ~0.001-0.1 bps

PLOB bound: -log2(1-eta) ~ eta/ln(2) for small eta
  At 500 km (0.157 dB/km): eta = 10^{-78.5/10} = 1.41e-8
  PLOB: 2.04e-8 bps (per channel use)
  TF-QKD should exceed this at > 340 km
```

### 3.5 Calibration Pipeline Architecture

**Recommended calibration pipeline for Phase C:**

```
function CALIBRATE_SYSTEM(experimental_data, system_model):
    // Step 1: Detector calibration
    det_params = fit_detector_params(
        obs = {
            "pde": measured_efficiency,
            "dark_counts_cps": measured_dcr,
            "jitter_ps_fwhm": measured_jitter,
            "afterpulsing_prob": measured_afterpulse
        },
        method = "bayesian",  // or "mle"
        priors = DEFAULT_DETECTOR_PRIORS
    )

    // Step 2: Channel calibration
    channel_params = fit_channel_params(
        otdr_data = measured_loss_profile,
        cn2_data = scintillation_measurements,  // if free-space
        method = "least_squares"
    )

    // Step 3: Full system validation
    for each (distance, protocol) in benchmark_set:
        predicted = compute_point(calibrated_scenario, distance)
        measured = experimental_data[(distance, protocol)]
        residual = (predicted.key_rate - measured.key_rate) / measured.key_rate
        chi2 += residual^2 / measured.uncertainty^2

    // Step 4: Goodness of fit
    reduced_chi2 = chi2 / (N_points - N_params)
    assert reduced_chi2 < 2.0, "Calibration failed"

    return CalibrationResult(det_params, channel_params, reduced_chi2)
```

**References:**
- ETSI GS QKD 011 V1.1.1 (2016) -- Component characterization
- ETSI GS QKD 015 V2.1.1 (2022) -- Security proofs
- Gobby, C. et al., APL 84, 3762, 2004
- Rosenberg, D. et al., PRL 98, 010503, 2007
- Jouguet, P. et al., Nature Photonics 7, 378, 2013
- Chen, J.-P. et al., Nature 589, 238, 2021
- Pittaluga, M. et al., Nature Photonics 15, 530, 2021

---

## 4. Reliability Card and Protocol Comparison Framework

### 4.1 Technology Readiness Level (TRL) for QKD

Adapting NASA's TRL scale to QKD protocols:

| TRL | Stage | QKD Criteria | Examples |
|-----|-------|-------------|----------|
| 1 | Basic principles | Security proof published | New theoretical protocols |
| 2 | Technology concept | Key rate formula derived | PM-QKD (initial), DI-QKD (initial) |
| 3 | Proof of concept | Simulation validated | SNS-TF-QKD (early), DI-QKD |
| 4 | Lab validation | Table-top experiment | DI-QKD (Nadlinger 2022), PM-QKD |
| 5 | Lab demo (realistic) | Realistic noise conditions | TF-QKD fiber experiments |
| 6 | Prototype demo | Field fiber/free-space | CV-QKD field (80 km) |
| 7 | System demo | Full system integration | BB84 commercial (IDQ, Toshiba) |
| 8 | Operational | Deployed network | Beijing-Shanghai backbone |
| 9 | Mission-proven | Multi-year operation | BB84 trusted-node networks |

**Protocol TRL assignments (as of 2025):**

| Protocol | TRL | Justification |
|----------|-----|--------------|
| BB84 (WCP + decoy) | 9 | Multi-year commercial deployment |
| BBM92 | 7-8 | Deployed in Micius, field networks |
| CV-QKD (GG02) | 6-7 | 80 km field demo, commercial units |
| MDI-QKD | 5-6 | Lab demos to 404 km, field trials |
| TF-QKD | 5-6 | Record distances (600+ km), lab |
| SNS-TF-QKD | 5 | 511 km fiber, lab demonstration |
| PM-QKD | 4-5 | Lab demonstrations |
| DI-QKD | 3-4 | First loophole-free demos (2022) |

### 4.2 Protocol Comparison Metrics

#### 4.2.1 Key Rate at Standard Distances

**Asymptotic key rate comparison (simulated, typical parameters):**

| Protocol | 50 km (bps) | 100 km (bps) | 200 km (bps) | Max Distance (km) |
|----------|------------|-------------|-------------|-------------------|
| BB84 Decoy | 1.5e5 | 3.8e3 | 0.3 | ~240 |
| BBM92 | 5.0e4 | 1.2e3 | 0.08 | ~220 |
| CV-QKD | 2.0e5 | 1.0e3 | ~0 | ~150 (composable) |
| MDI-QKD | 8.0e3 | 1.5e2 | 0.01 | ~250 |
| TF-QKD | 2.0e4 | 5.0e3 | 50 | ~600 |
| SNS-TF-QKD | 1.8e4 | 4.5e3 | 45 | ~500 |
| PM-QKD | 1.5e4 | 4.0e3 | 40 | ~500 |
| DI-QKD | 5.0e1 | ~0 | ~0 | ~50 |

*Note: These are approximate values. Exact rates depend heavily on specific system parameters.*

#### 4.2.2 Key Rate Scaling Laws

Each protocol family exhibits characteristic rate-distance scaling:

```
BB84/BBM92 (prepare-and-measure / entanglement-based):
  R ~ eta * r_key  where eta = 10^{-alpha*L/10}
  Scaling: R ~ O(eta)

TF-QKD family (twin-field, SNS, PM):
  R ~ sqrt(eta) * r_key
  Scaling: R ~ O(sqrt(eta))

  This is because Alice and Bob each send to a central node,
  so each photon only traverses L/2, and the rate goes as sqrt(eta_total).

DI-QKD:
  R ~ eta^2 * r_key  (requires loophole-free Bell test)
  Scaling: R ~ O(eta^2)  (worst case for practical implementations)

CV-QKD:
  R ~ beta * I_AB - chi_BE
  Scaling: R ~ O(eta) for reverse reconciliation
  But max distance limited by reconciliation at low SNR.

PLOB bound (ultimate repeaterless limit):
  C = -log2(1 - eta) ~ eta/ln(2) for eta << 1
```

#### 4.2.3 Implementation Complexity Score

A composite score reflecting implementation difficulty (1 = simplest, 10 = most complex):

| Protocol | Source | Detection | Phase | Total Score |
|----------|--------|-----------|-------|-------------|
| BB84 Decoy | WCP laser (2) | SPD x2 (2) | None (1) | 5 |
| BBM92 | SPDC/QD (4) | SPD x4 (3) | None (1) | 8 |
| CV-QKD | Coherent (2) | Homodyne (3) | Local LO (3) | 8 |
| MDI-QKD | WCP x2 (3) | BSM node (4) | None (1) | 8 |
| TF-QKD | WCP x2 (3) | SPD x2 (2) | Global lock (5) | 10 |
| SNS-TF-QKD | WCP x2 (3) | SPD x2 (2) | Phase post-comp (3) | 8 |
| PM-QKD | WCP x2 (3) | SPD x2 (2) | Phase post-sel (3) | 8 |
| DI-QKD | Entangled (5) | Loophole-free (5) | Bell test (4) | 14 |

#### 4.2.4 Required Detector Technology

| Protocol | Minimum Detector | Recommended Detector |
|----------|-----------------|---------------------|
| BB84 (fiber, 1550 nm) | InGaAs APD (10%) | SNSPD (80%+) |
| BB84 (free-space, 850 nm) | Si-APD (50%) | Si-SPAD (70%+) |
| BBM92 | SNSPD (>50%) | SNSPD (>85%) |
| CV-QKD | Balanced homodyne | Balanced homodyne + DSP |
| MDI-QKD | SNSPD (>50%) | SNSPD (>85%) |
| TF-QKD | SNSPD (>40%) | SNSPD (>85%, <10 DCR) |
| DI-QKD | SNSPD (>90%) | SNSPD (>95%, near-unity) |

#### 4.2.5 Sensitivity to Device Imperfections

**QBER sensitivity matrix (partial derivatives):**

For BB84 decoy-state, the QBER has contributions:

```
QBER = e_detector + e_optical + e_background + e_multiphoton

where:
  e_detector = p_dark * (1 - eta) / (2 * (mu*eta + p_dark))
  e_optical ~ theta_misalign^2 / 4  (for small misalignment)
  e_background = R_bg * t_gate / (2 * (mu*eta + R_bg*t_gate))
  e_multiphoton ~ p_multi * (1-eta) / (2 * mu * eta)  (multiphoton contrib.)
```

**Key rate sensitivity (dR/d_param, at 100 km, BB84):**

| Parameter | Typical Value | dR/R per 10% change |
|-----------|--------------|---------------------|
| Detector efficiency | 0.85 | +0.15 (+15%) |
| Dark count rate | 10 cps | -0.02 (-2%) |
| Fiber loss (dB/km) | 0.20 | -0.40 (-40%) |
| Source rate (MHz) | 1000 | +0.10 (+10%) |
| EC efficiency f | 1.16 | -0.12 (-12%) |
| Misalignment | 1.5% | -0.05 (-5%) |
| Timing jitter (ps) | 50 | -0.03 (-3%) |

### 4.3 Figure of Merit Definitions

#### 4.3.1 Rate-Distance Product

```
FoM_RD = R(L_max/2) * L_max    [bps * km]

where L_max is the maximum distance for positive key rate and R(L_max/2) is the key rate at half the maximum distance.
```

**Published FoM_RD values:**

| Protocol | L_max (km) | R(L/2) (bps) | FoM_RD (bps*km) |
|----------|-----------|-------------|-----------------|
| BB84 Decoy | 240 | ~50 | ~12,000 |
| TF-QKD | 600 | ~5 | ~3,000 |
| CV-QKD | 150 | ~100 | ~15,000 |
| MDI-QKD | 250 | ~20 | ~5,000 |

#### 4.3.2 Rate x Security-Level Composite

```
FoM_RS = R * S_weight

where S_weight encodes the security guarantee level:
  Information-theoretic (composable, finite-key): S = 1.0
  Information-theoretic (asymptotic): S = 0.8
  Device-independent: S = 1.2 (premium for strongest security)
  Trusted-device: S = 0.6
```

#### 4.3.3 Cost Per Secure Bit

```
Cost_per_bit = (C_hardware + C_operations * T_lifetime) / (R_average * T_lifetime)

where:
  C_hardware: total hardware cost (source, detectors, electronics)
  C_operations: annual operational cost (maintenance, cooling)
  T_lifetime: system lifetime (years)
  R_average: average sustainable key rate (bps)
```

**Rough cost estimates (2025):**

| Component | BB84 | CV-QKD | TF-QKD |
|-----------|------|--------|--------|
| Source | $5-20K | $10-30K | $20-50K (x2) |
| Detectors | $50-200K (SNSPD) | $5-20K (homodyne) | $50-200K (SNSPD) |
| Electronics | $10-30K | $10-30K | $20-50K |
| Cooling | $20-50K/yr (SNSPD) | Minimal | $20-50K/yr (SNSPD) |
| Total 3-year | $200-500K | $80-200K | $300-700K |

### 4.4 Composable Security Verification

#### 4.4.1 Epsilon-Security Framework

A QKD protocol is epsilon-secure if the generated key is epsilon-close to ideal:

```
1/2 * ||rho_AE - U_A tensor rho_E||_1 <= epsilon_sec

where:
  rho_AE: joint state of Alice's key and Eve's system
  U_A: uniform distribution over key space
  ||.||_1: trace norm
  epsilon_sec: total security parameter
```

**Epsilon decomposition:**

```
epsilon_total = epsilon_correctness + epsilon_secrecy

where:
  epsilon_correctness: probability that Alice and Bob's keys differ
  epsilon_secrecy: distinguishability of key from uniform

Further decomposition:
  epsilon_secrecy = epsilon_PA + epsilon_PE + epsilon_smooth

  epsilon_PA: privacy amplification failure probability
  epsilon_PE: parameter estimation failure probability
  epsilon_smooth: smoothing parameter for min-entropy
```

This decomposition is already implemented in `photonstrust/orbit/pass_envelope.py` as `_build_orbit_finite_key_plan()` with:
- epsilon_correctness = 0.20 * epsilon_total
- epsilon_secrecy = 0.40 * epsilon_total
- epsilon_PE = 0.15 * epsilon_total
- epsilon_EC = 0.15 * epsilon_total
- epsilon_PA = 0.10 * epsilon_total

#### 4.4.2 Finite-Key vs Asymptotic Comparison

**Finite-key penalty:**

The key rate reduction due to finite block size N is (implemented in `finite_key.py`):

```
Delta_finite = sqrt(2 * log(2/epsilon) / n_eff)

where:
  n_eff = N * sifting * (1 - pe_fraction)  -- effective signal count
  epsilon: security parameter
  pe_fraction: fraction used for parameter estimation
```

**Key rate ratio (finite/asymptotic) vs block size:**

| Block Size N | epsilon = 10^{-10} | epsilon = 10^{-6} |
|-------------|-------------------|-------------------|
| 10^6 | 0.15 | 0.45 |
| 10^8 | 0.70 | 0.85 |
| 10^{10} | 0.95 | 0.98 |
| 10^{12} | 0.99 | 0.999 |

The crossover where finite-key rate exceeds 50% of asymptotic is approximately:

```
N_crossover ~ 8 * log(2/epsilon) / (sifting * r_asymptotic)^2
```

#### 4.4.3 Source Imperfection Bounds

For practical WCP sources with non-zero multi-photon probability:

```
p_multi = 1 - (1 + mu) * exp(-mu) ~ mu^2/2  (for mu << 1)

Eve's information from multi-photon pulses (PNS attack bound):
  Delta_PNS = p_multi / (mu * eta)  (fraction of detections from multi-photon)
```

For quantum dot single-photon sources with g^(2)(0) > 0:

```
p_multi = g^(2)(0) * mu / 2  (approximate, for mu ~ 1 photon/pulse)

Security impact:
  Effective key rate reduction proportional to g^(2)(0)
  For g^(2)(0) = 0.02: ~1% key rate penalty (typically negligible)
```

**Decoy-state method bounds (Lo, Ma, Chen, PRL 2005):**

```
Lower bound on single-photon gain:
  Q_1^L >= (mu * Q_nu * exp(nu) - nu^2/mu^2 * Q_mu * exp(mu) - (mu^2-nu^2)/mu^2 * Q_vacuum)
           / (mu - nu - nu^2/mu)

Upper bound on single-photon QBER:
  e_1^U <= (E_nu * Q_nu * exp(nu) - e_0 * Q_vacuum) / (Q_1^L * nu)
```

### 4.5 Reliability Card Structure for Protocol Comparison

**Proposed schema for the QKD Protocol Reliability Card:**

```json
{
  "schema_version": "2.0",
  "protocol_id": "BB84_DECOY",
  "trl": 9,
  "security": {
    "model": "composable_finite_key",
    "epsilon_total": 1e-10,
    "assumptions": ["trusted_source", "trusted_detectors", "basis_independent"],
    "proof_reference": "Tomamichel et al., Nature Comms 2012"
  },
  "performance": {
    "rate_at_50km_bps": 150000,
    "rate_at_100km_bps": 3800,
    "rate_at_200km_bps": 0.3,
    "max_distance_km": 240,
    "rate_distance_product": 12000
  },
  "implementation": {
    "complexity_score": 5,
    "source_type": "WCP_laser",
    "detector_type": "SNSPD",
    "phase_requirement": "none",
    "calibration_parameters": 8
  },
  "sensitivity": {
    "detector_efficiency": 0.15,
    "dark_counts": -0.02,
    "fiber_loss": -0.40,
    "misalignment": -0.05
  },
  "benchmarks": {
    "gobby_2004": {"distance_km": 122, "key_rate_bps": 24.6, "match": true},
    "rosenberg_2007": {"distance_km": 107, "key_rate_bps": 5.7, "match": true}
  }
}
```

**References:**
- Xu, F. et al., Rev. Mod. Phys. 92, 025002, 2020 (comprehensive review)
- Pirandola, S. et al., Advances in Optics and Photonics 12(4), 1012, 2020
- Tomamichel, M. et al., Nature Communications 3, 634, 2012 (finite-key)
- Lo, H.-K. et al., PRL 94, 230504, 2005 (decoy states)

---

## 5. Network-Layer QKD Architecture

### 5.1 ETSI QKD Network Architecture (GS QKD 004)

The ETSI QKD network architecture defines three layers:

```
+-------------------------------------------+
|         Application Layer (Apps)           |
|  Key Consumer (SAE - Secure Application    |
|  Entity): encryption, auth, QRNG seed     |
+-------------------------------------------+
           |  Key Supply Interface (KSI)
+-------------------------------------------+
|      Key Management Layer (KML)            |
|  - Key Store per link                      |
|  - Key ID management                       |
|  - Key relay / forwarding                  |
|  - Key lifecycle (generation -> expiry)    |
+-------------------------------------------+
           |  QKD Module Interface (QKDI)
+-------------------------------------------+
|         Quantum Layer (QL)                 |
|  - QKD transmitter/receiver modules        |
|  - Quantum channel (fiber/free-space)      |
|  - Classical auth. channel                 |
|  - Error correction + privacy amplification|
+-------------------------------------------+
```

#### 5.1.1 Key Supply Agent (KSA) Interface

The KSA interface (ETSI GS QKD 014) provides RESTful APIs:

```
GET  /api/v1/keys/{slave_SAE_ID}/status
  Response: { "source_KME_ID", "target_KME_ID",
              "master_SAE_ID", "slave_SAE_ID",
              "key_size", "stored_key_count",
              "max_key_count", "max_key_size",
              "max_key_per_request", "max_SAE_ID_count" }

POST /api/v1/keys/{slave_SAE_ID}/enc_keys
  Request: { "number": 1, "size": 256 }
  Response: { "keys": [{"key_ID": "uuid", "key": "base64"}] }

POST /api/v1/keys/{master_SAE_ID}/dec_keys
  Request: { "key_IDs": [{"key_ID": "uuid"}] }
  Response: { "keys": [{"key_ID": "uuid", "key": "base64"}] }
```

The existing `photonstrust/kms/store.py` implements a `KeyPoolStore` that manages per-link key pools and supports SAE-based lookup via `get_pool_by_sae()`.

#### 5.1.2 QKD Module Interface

The QKDI provides:

```
- start_qkd(link_id): initiate QKD session
- stop_qkd(link_id): terminate QKD session
- get_key(link_id, key_size): retrieve distilled key
- get_status(link_id): return {rate, qber, key_buffer_level}
- set_parameters(link_id, params): configure protocol parameters
```

### 5.2 Key Management in Networks

#### 5.2.1 Key Store Synchronization

Each link maintains synchronized key stores at both endpoints. Critical requirements:

1. **Key ID assignment**: UUIDv4 for global uniqueness
2. **Synchronization**: Classical authenticated channel confirms which key blocks passed verification
3. **Key buffer management**: FIFO consumption with minimum buffer threshold
4. **Expiry**: Keys have a configurable time-to-live (TTL), typically 1 hour to 1 day
5. **Accounting**: Total bits generated, consumed, expired, available

**Key buffer dynamics:**

```
B(t) = B(t-dt) + R_gen * dt - R_consume * dt - R_expire * dt

where:
  R_gen: key generation rate (from QKD link)
  R_consume: key consumption rate (from applications)
  R_expire: key expiry rate (keys exceeding TTL)
```

Sustainable operation requires: R_gen > R_consume + R_expire

#### 5.2.2 Key Request/Delivery API

```
function REQUEST_KEY(source_sae, target_sae, key_size_bits, qos):
    // Find path from source to target
    path = routing_table.lookup(source_sae.kme, target_sae.kme)

    // Check key availability on all links
    for link in path.links:
        if key_store[link].available < key_size_bits:
            return INSUFFICIENT_KEY_MATERIAL

    // For direct link (single hop)
    if path.length == 1:
        key_id = key_store[path.links[0]].consume(key_size_bits)
        return Key(key_id, key_material)

    // For multi-hop (trusted-node relay)
    relay_keys = []
    for link in path.links:
        relay_keys.append(key_store[link].consume(key_size_bits))

    // XOR relay through trusted nodes
    final_key = xor_relay(relay_keys, path.nodes)
    return Key(final_key_id, final_key)
```

### 5.3 Trusted-Node Relay Protocol Detail

#### 5.3.1 XOR Key Forwarding

For a path Alice -> T1 -> T2 -> ... -> Tn -> Bob:

```
Step 1: Each link generates independent keys via QKD
  K_{A,T1}: key shared between Alice and T1
  K_{T1,T2}: key shared between T1 and T2
  ...
  K_{Tn,B}: key shared between Tn and Bob

Step 2: Alice sends K_final = random key to be delivered to Bob

Step 3: Relay chain:
  Alice -> T1:  C1 = K_final XOR K_{A,T1}  (encrypted with link key)
  T1 decrypts: K_final = C1 XOR K_{A,T1}
  T1 -> T2:    C2 = K_final XOR K_{T1,T2}
  ...continues to Bob...

Security: Every intermediate node T_i sees K_final in plaintext.
```

#### 5.3.2 Authentication Requirements

Each link requires information-theoretically secure authentication:

```
Authentication tag length: l_auth = 2 * log2(1/epsilon_auth) bits
  For epsilon_auth = 10^{-10}: l_auth ~ 66 bits per message

Key consumption for authentication per protocol round:
  K_auth ~ l_auth * N_messages_per_round
  Typically: ~2 kbit per QKD protocol round (parameter estimation + sifting messages)
```

**Net key rate (accounting for authentication overhead):**

```
R_net = R_raw_key - R_auth_consumption

R_auth_consumption = l_auth * f_message * N_rounds_per_second
  << R_raw_key for practical systems (typically < 1% overhead)
```

#### 5.3.3 Key Consumption for Authentication in Networks

In a network with M active links, total authentication key consumption:

```
R_auth_total = sum_{i=1}^{M} R_auth_i ~ M * l_auth * f_message

For M=30 links (Beijing-Shanghai scale): R_auth_total ~ 60 kbps
```

### 5.4 Software-Defined QKD Networking

#### 5.4.1 SDN Controller for QKD

An SDN controller manages the QKD network as a logically centralized entity:

```
+---------------------+
| SDN Controller      |
| - Global topology   |
| - Key rate monitor   |
| - Routing decisions  |
| - Key relay control  |
+---------------------+
    |  Southbound API (OpenFlow-like)
+---+---+---+---+---+
| KME1 | KME2 | ... |  (Key Management Entities)
+---+---+---+---+---+
    |       |       |
   QKD    QKD    QKD     (Quantum links)
```

**Southbound interface messages:**

```
QKD_FLOW_MOD:
  - action: {add_relay, remove_relay, modify_rate}
  - path: [node_1, ..., node_n]
  - priority: int
  - key_rate_requested: float (bps)

QKD_STATUS:
  - link_id: string
  - key_rate_current: float (bps)
  - key_buffer_level: int (bits)
  - qber: float
  - link_status: {up, degraded, down}
```

#### 5.4.2 Network Orchestration Algorithm

```
function SDN_ORCHESTRATE(demands, topology, key_stores):
    // Monitor link health
    for link in topology.links:
        status = query_link_status(link)
        update_topology_weights(link, status)

    // Route each demand
    for demand in demands:
        path = multi_objective_route(
            topology,
            demand.source,
            demand.target,
            objectives = [maximize_rate, minimize_trusted_nodes, maximize_reliability]
        )

        if path.bottleneck_rate >= demand.min_rate:
            install_relay_path(path)
        else:
            // Try multi-path routing
            paths = k_shortest_paths(topology, demand.source, demand.target, k=3)
            aggregate_rate = sum(p.bottleneck_rate for p in paths)
            if aggregate_rate >= demand.min_rate:
                install_multi_path_relay(paths)
            else:
                reject_demand(demand, "insufficient capacity")

    // Periodic rebalancing
    every T_rebalance:
        reoptimize_all_routes()
```

**References:**
- ETSI GS QKD 004 V2.1.1 (2020) -- QKD network architecture
- ETSI GS QKD 014 V1.1.1 (2019) -- Protocol and data format for QKD key delivery
- Aguado, A. et al., IEEE Communications Magazine 57(7), 20, 2019 (SDN for QKD)
- Cao, Y. et al., Science Bulletin 68, 913, 2023
- Wang, S. et al., Optics Express 22(18), 21739, 2014

---

## Appendix A: Summary of Key Equations

### Network Routing

| Equation | Description |
|----------|-------------|
| R_e2e = min_{links} R_link | Trusted-node bottleneck rate |
| R_e2e = R_link / H_n * p_swap^m | 1G repeater end-to-end rate |
| F_chain = 0.5 + 0.5*(2F-1)^{2^m} | Nested swap fidelity |
| max_flow(s,t) = min_cut(s,t) | Max-flow min-cut for network capacity |

### Satellite QKD

| Equation | Description |
|----------|-------------|
| T_orb = 2*pi*sqrt((R_E+h)^3/mu) | Orbital period |
| D(theta) = -R_E*sin(theta) + sqrt(...) | Slant range |
| K_total = integral SKR(theta(t)) dt | Pass key volume |
| sigma_R^2 = 2.25*k^{7/6}*sec^{11/6}(zeta)*int Cn2 dh | Rytov variance |

### Calibration

| Equation | Description |
|----------|-------------|
| L = prod Poisson(n_i\|lambda_i) | Poisson MLE |
| chi^2 = sum (O_i - E_i)^2 / E_i | Goodness of fit |
| P_ap(t) = sum A_j*exp(-t/tau_j) | Afterpulse model |
| DCR(T) = DCR_0*exp(E_a/kT_0 - E_a/kT) | DCR temperature model |

### Security

| Equation | Description |
|----------|-------------|
| Delta_finite = sqrt(2*log(2/eps)/n_eff) | Finite-key penalty |
| epsilon_total = epsilon_cor + epsilon_sec | Epsilon decomposition |
| C_PLOB = -log2(1-eta) | PLOB capacity bound |

---

## Appendix B: Integration Points with Existing PhotonsTrust Codebase

### Current State (already implemented)

| Module | Status | Location |
|--------|--------|----------|
| Network topology graph | Implemented | `photonstrust/network/types.py` |
| Dijkstra shortest path | Implemented | `photonstrust/network/routing.py` |
| Max bottleneck-rate path | Implemented | `photonstrust/network/routing.py` |
| Routing table computation | Implemented | `photonstrust/network/routing.py` |
| Trusted-node relay rate | Implemented | `photonstrust/network/trusted_node.py` |
| Network simulation engine | Implemented | `photonstrust/network/simulator.py` |
| 1G/2G/3G repeater chains | Implemented | `photonstrust/network/repeater_chain.py` |
| BBPSSW/DEJMPS purification | Implemented | `photonstrust/network/purification.py` |
| Orbit geometry (slant range) | Implemented | `photonstrust/orbit/geometry.py` |
| Pass envelope simulation | Implemented | `photonstrust/orbit/pass_envelope.py` |
| Pass key budget | Implemented | `photonstrust/satellite/pass_budget.py` |
| Gamma-Gamma fading | Implemented | `photonstrust/satellite/turbulence.py` |
| Bayesian calibration | Implemented | `photonstrust/calibrate/bayes.py` |
| Detector/emitter/memory priors | Implemented | `photonstrust/calibrate/priors.py` |
| KMS key pool store | Implemented | `photonstrust/kms/store.py` |
| Finite-key composable | Implemented | `photonstrust/qkd_protocols/finite_key.py` |
| Reliability card (PIC) | Implemented | `photonstrust/reports/reliability_card.py` |

### Phase C Extensions (recommended)

| Feature | Priority | Builds On |
|---------|----------|-----------|
| Max-flow network routing | High | `network/routing.py` |
| Multi-commodity flow | High | `network/routing.py` + scipy/networkx |
| Reliability-aware routing | Medium | `network/routing.py` |
| Constellation scheduler | High | `orbit/geometry.py` + `orbit/pass_envelope.py` |
| Multi-GS scheduling optimizer | High | New module (`orbit/scheduler.py`) |
| Weather-adaptive scheduling | Medium | `orbit/pass_envelope.py` |
| MCMC calibration engine | High | `calibrate/bayes.py` |
| OTDR data ingestion | Medium | `calibrate/` + new module |
| Cn2 profile estimation | Medium | `satellite/turbulence.py` |
| Protocol comparison card | High | `reports/reliability_card.py` + `qkd_protocols/` |
| TRL assignment engine | Medium | New module (`reports/protocol_card.py`) |
| SDN controller interface | Low | `network/simulator.py` + `kms/` |
| ETSI QKD 014 API | Medium | `kms/store.py` |

---

## Appendix C: Key References (Complete)

1. Mehic, M. et al., "Quantum Key Distribution: A Networking Perspective," ACM Computing Surveys 53(5), 2020
2. Cao, Y. et al., "Multi-mode quantum key distribution network," Phys. Rev. Applied 17, 054035, 2022
3. Chakraborty, K. et al., "Distributed Routing in a Quantum Internet," IEEE JSAC 37(10), 2019
4. Bourgoin, J.-P. et al., "A comprehensive design and performance analysis of LEO satellite quantum communication," New J. Phys. 15, 023006, 2013
5. Liao, S.-K. et al., "Satellite-to-ground quantum key distribution," Nature 549, 43, 2017
6. Liao, S.-K. et al., "Satellite-Relayed Intercontinental Quantum Network," PRL 120, 030501, 2018
7. Sidhu, J. S. et al., "Advances in space quantum communications," IOP SciNotes 2(3), 035202, 2021
8. Chen, J.-P. et al., "Sending-or-Not-Sending with Independent Lasers over 511 km fiber," Nature 589, 238, 2021
9. Pittaluga, M. et al., "600 km repeater-like quantum communications with dual-band stabilisation," Nature Photonics 15, 530, 2021
10. Gobby, C. et al., "Quantum key distribution over 122 km of standard telecom fiber," APL 84, 3762, 2004
11. Rosenberg, D. et al., "Long-distance decoy-state quantum key distribution in optical fiber," PRL 98, 010503, 2007
12. Jouguet, P. et al., "Experimental demonstration of long-distance continuous-variable quantum key distribution," Nature Photonics 7, 378, 2013
13. Xu, F. et al., "Secure quantum key distribution with realistic devices," Rev. Mod. Phys. 92, 025002, 2020
14. Pirandola, S. et al., "Advances in quantum cryptography," Advances in Optics and Photonics 12(4), 1012, 2020
15. Pirandola, S. et al., "Fundamental limits of repeaterless quantum communications," Nature Communications 8, 15043, 2017 (PLOB bound)
16. Briegel, H.-J. et al., "Quantum Repeaters: The Role of Imperfect Local Operations," PRL 81, 5932, 1998
17. Muralidharan, S. et al., "Optimal architectures for long distance quantum communication," Scientific Reports 6, 20463, 2016
18. Azuma, K. et al., "All-photonic quantum repeaters," Nature Communications 6, 6787, 2015
19. ETSI GS QKD 004 V2.1.1 (2020), "Quantum Key Distribution (QKD); Application Interface"
20. ETSI GS QKD 014 V1.1.1 (2019), "Quantum Key Distribution (QKD); Protocol and data format"
21. ETSI GS QKD 011 V1.1.1 (2016), "Quantum Key Distribution (QKD); Component characterization"
22. Peev, M. et al., "The SECOQC quantum key distribution network in Vienna," New J. Phys. 11, 075001, 2009
23. Sasaki, M. et al., "Field test of quantum key distribution in the Tokyo QKD Network," Opt. Express 19(11), 2011
24. Aguado, A. et al., "The Engineering of Software-Defined Quantum Key Distribution Networks," IEEE Communications Magazine 57(7), 20, 2019
25. Tomamichel, M. et al., "A largely self-contained and complete security proof for quantum key distribution," Nature Communications 3, 634, 2012
26. Lo, H.-K. et al., "Decoy State Quantum Key Distribution," PRL 94, 230504, 2005
27. Bennett, C. H. et al., "Purification of Noisy Entanglement," PRL 76, 722, 1996 (BBPSSW)
28. Deutsch, D. et al., "Quantum Privacy Amplification," PRL 77, 2818, 1996 (DEJMPS)
29. Wang, X.-B., Yu, Z.-W., Hu, X.-L., "Twin-field quantum key distribution with large misalignment error," PRA 98, 062323, 2018 (SNS)
30. Andrews, L. C. and Phillips, R. L., "Laser Beam Propagation through Random Media," SPIE Press, 2005
