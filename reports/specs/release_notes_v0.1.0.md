# Release Notes v0.1.0

## Highlights
- Physics-calibrated QKD and repeater analysis with QuTiP fallback
- Teleportation and source benchmarking scenarios
- Reliability Card v1.0 standard with HTML/PDF reports
- Benchmark dataset generator and Streamlit run registry
- CI + regression baselines

## Installation
```bash
pip install -e .
pip install -e .[qutip,qiskit]
```

## Key Commands
```bash
photonstrust run configs/quickstart/qkd_default.yml
photonstrust run configs/demo2_repeater_spacing.yml
photonstrust run configs/demo3_teleportation.yml
photonstrust run configs/demo4_source_benchmark.yml
```

## Notes
- QuTiP/Qiskit are optional; analytic fallback is supported.
- PDF reports require `.[pdf]` extras.
