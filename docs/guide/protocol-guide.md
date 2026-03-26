# Protocol Guide

PhotonsTrust supports 9 QKD protocols spanning discrete-variable,
continuous-variable, measurement-device-independent, twin-field, and
device-independent families. This guide helps you choose the right protocol
for your use case.

---

## Protocol Comparison Table

| Protocol    | Type       | Max Distance | Key Rate  | Security   | Channel    | Best For                        |
|-------------|------------|-------------|-----------|------------|------------|---------------------------------|
| `bb84`      | DV, P&M    | ~200 km     | High      | Proven     | All        | Metro and intercity fiber links |
| `bbm92`     | DV, EB     | ~150 km     | Medium    | Proven     | All        | Entanglement-based applications |
| `cv_qkd`    | CV, P&M    | ~50 km      | Very High | Good       | All        | Short urban links, telecom HW   |
| `mdi_qkd`   | DV, relay  | ~100 km     | Medium    | Very High  | Fiber only | Untrusted relay nodes           |
| `amdi_qkd`  | DV, relay  | ~100 km     | Medium-High| Very High | Fiber only | Async mode-pairing relay        |
| `tf_qkd`    | DV, TF     | ~500 km     | Medium    | High       | Fiber only | Long-haul fiber                 |
| `pm_qkd`    | DV, TF     | ~500 km     | Medium    | High       | Fiber only | Phase-matching TF variant       |
| `sns_tf_qkd`| DV, TF     | ~500 km     | Medium    | High       | Fiber only | Sending-or-not-sending TF       |
| `di_qkd`    | DV, EB     | ~10 km      | Low       | Ultimate   | All        | Maximum security guarantee      |

**Type abbreviations:** DV = discrete-variable, CV = continuous-variable,
P&M = prepare-and-measure, EB = entanglement-based, TF = twin-field.

---

## Decision Flowchart

Use this flowchart to narrow down your protocol choice:

```
1. What is your link distance?
   ├── < 50 km ─────────────────> CV-QKD (highest rate) or BB84 (proven)
   ├── 50-200 km ───────────────> BB84 or BBM92
   └── > 200 km ────────────────> TF-QKD, PM-QKD, or SNS-TF-QKD

2. Do you need protection against detector side-channel attacks?
   └── Yes ─────────────────────> MDI-QKD or AMDI-QKD

3. Do you need device-independent security (no trust in devices)?
   └── Yes ─────────────────────> DI-QKD (short range only, ~10 km)

4. Is your channel free-space or satellite?
   └── Yes ─────────────────────> BB84, BBM92, CV-QKD, or DI-QKD
       (MDI/TF/PM/SNS are fiber-only)

5. Do you need the highest possible key rate at short range?
   └── Yes ─────────────────────> CV-QKD (uses standard telecom hardware)
```

---

## Protocol Details

### BB84 (bb84_decoy)

The workhorse of QKD. Alice prepares single photons in one of four polarization
or phase states drawn from two conjugate bases and sends them to Bob. The decoy-
state variant uses multiple intensity levels to detect photon-number-splitting
attacks, making it practical with weak coherent pulse sources. BB84 is the most
widely deployed QKD protocol with well-understood security proofs.

```python
result = simulate_qkd_link(protocol="bb84", distance_km=100)
```

### BBM92 (E91)

An entanglement-based protocol where a source distributes entangled photon pairs
to Alice and Bob. Both parties independently choose measurement bases and later
compare results. Security can be verified through Bell-inequality violation.
BBM92 removes the need for a trusted source, as eavesdropping disturbs the
entanglement in a detectable way.

```python
result = simulate_qkd_link(protocol="bbm92", distance_km=80)
```

### CV-QKD (GG02)

Encodes key information in the continuous amplitude and phase quadratures of
coherent states. Bob uses homodyne or heterodyne detection -- standard telecom
components that do not require single-photon detectors. CV-QKD achieves very
high key rates at short distances but drops off quickly beyond ~50 km.

```python
result = simulate_qkd_link(protocol="cv_qkd", distance_km=30)
```

### MDI-QKD

Both Alice and Bob send quantum states to an untrusted central node (Charlie)
that performs a Bell-state measurement. Since Charlie's detectors do not need to
be trusted, MDI-QKD is immune to all detector side-channel attacks. The cost is
a lower key rate compared to direct protocols at the same total distance.

```python
result = simulate_qkd_link(protocol="mdi_qkd", distance_km=50)
```

### AMDI-QKD (Asynchronous MDI)

An asynchronous variant of MDI-QKD that uses mode-pairing: successful detection
events are paired after measurement rather than requiring precise timing
synchronization. This relaxes hardware requirements and can achieve higher key
rates than standard MDI-QKD in practice.

```python
result = simulate_qkd_link(protocol="amdi_qkd", distance_km=50)
```

### TF-QKD (Twin-Field)

Two remote users send weak coherent pulses to a central node where single-photon
interference is measured. TF-QKD is the first protocol family to surpass the
PLOB bound, enabling key generation at distances beyond 300 km without quantum
repeaters. Requires phase stabilization of the two long fiber arms.

```python
result = simulate_qkd_link(
    protocol="tf_qkd",
    distance_km={"start": 0, "stop": 400, "step": 20},
)
```

### PM-QKD (Phase-Matching)

A twin-field variant where Alice and Bob each apply random phases to their
pulses from a discrete set of phase slices. Post-measurement, they sift events
where their phase choices were compatible. Achieves similar distances to TF-QKD
with a different phase-matching strategy.

```python
result = simulate_qkd_link(protocol="pm_qkd", distance_km=300)
```

### SNS-TF-QKD (Sending-or-Not-Sending)

A twin-field variant where each user randomly decides to send a coherent pulse
or vacuum in each time window. The protocol determines which events contribute
to the key after Charlie announces detection results. Simplifies phase tracking
compared to standard TF-QKD.

```python
result = simulate_qkd_link(protocol="sns_tf_qkd", distance_km=300)
```

### DI-QKD (Device-Independent)

The strongest form of QKD security: the security proof makes no assumptions
about the internal workings of the quantum devices. Security is certified through
observed CHSH inequality violation. Currently limited to very short distances
(~10 km) due to the stringent requirement for high detection efficiency and low
loss.

```python
result = simulate_qkd_link(protocol="di_qkd", distance_km=5)
```

---

## Comparing Protocols

Use `compare_protocols` to evaluate multiple protocols side by side:

```python
from photonstrust.easy import compare_protocols

# Compare the three main protocol families
comp = compare_protocols(
    protocols=["bb84", "cv_qkd", "tf_qkd"],
    distances={"start": 0, "stop": 300, "step": 10},
)
print(comp.summary())
comp.plot(save_path="protocol_comparison.png")
```

To compare all 9 protocols:

```python
comp = compare_protocols()  # protocols=None uses all registered protocols
```

---

## Channel Compatibility

Not all protocols work with all channel models. The table below shows which
combinations are supported:

| Protocol    | Fiber | Free-space | Satellite |
|-------------|-------|------------|-----------|
| `bb84`      | Yes   | Yes        | Yes       |
| `bbm92`     | Yes   | Yes        | Yes       |
| `cv_qkd`    | Yes   | Yes        | Yes       |
| `mdi_qkd`   | Yes   | No         | No        |
| `amdi_qkd`  | Yes   | No         | No        |
| `tf_qkd`    | Yes   | No         | No        |
| `pm_qkd`    | Yes   | No         | No        |
| `sns_tf_qkd`| Yes   | No         | No        |
| `di_qkd`    | Yes   | Yes        | Yes       |

If you attempt an unsupported combination, you will receive a "Protocol
applicability failed" error. See [troubleshooting.md](troubleshooting.md).
