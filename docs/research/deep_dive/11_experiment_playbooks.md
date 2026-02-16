# Experiment Playbooks

This document defines reproducible experiment playbooks for flagship scenarios.

## Playbook A: Metro QKD
1. Run scenario config for 20-80 km sweep.
2. Capture key rate and QBER curves.
3. Generate reliability card and compare to baseline.

## Playbook B: Repeater chain
1. Sweep spacing for 200-600 km.
2. Record throughput and fidelity with memory decay.
3. Publish recommended spacing and confidence bounds.

## Playbook C: Teleportation SLA
1. Run teleportation with latency profile.
2. Capture success probability and fidelity distributions.
3. Evaluate outage probability against SLA threshold.

## Playbook D: Source benchmarking
1. Calibrate source parameters from observables.
2. Project to network-level key rate impact.
3. Publish source-focused reliability card.

## Figure generation guidance
- Use consistent axis units and scales.
- Include uncertainty bands where available.
- Include benchmark identifiers in figure captions.

## Definition of done
- Each playbook reproducible from a clean environment with documented commands.


## Inline citations (web, verified 2026-02-12)
Applied to: flagship playbook scenarios, benchmarking baselines, and expected performance sanity checks.
- NetSquid simulator reference paper: https://www.nature.com/articles/s42005-021-00647-8
- SeQUeNCe simulator project page: https://www.anl.gov/sequence-simulator-of-quantum-network-communication
- SeQUeNCe paper record (Argonne): https://www.anl.gov/argonne-scientific-publications/pub/170140
- PLOB repeaterless bound (Nature Communications, 2017): https://www.nature.com/articles/ncomms15043
- MDI-QKD reference protocol: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.130503
- Twin-field QKD at 1000 km (PRL 130, 210801): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.130.210801
- Link layer protocol for quantum networks: https://arxiv.org/abs/1903.09778

