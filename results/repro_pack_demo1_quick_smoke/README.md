# PhotonTrust Repro Pack: demo1_quick_smoke

This folder is a reproducibility package for PhotonTrust.

## Contents
- `config.yml`: scenario config used to generate the reference outputs
- `benchmark_bundle.json`: expected curves + config (schema-validated)
- `reference_outputs/`: outputs produced by the engine at generation time
- `env/`: environment capture
- `run.ps1` / `run.sh`: replay scripts
- `verify.py`: verification helper

## Replay
From this directory:

PowerShell:
```powershell
py .\run.ps1
```

Linux/macOS:
```sh
python ./run.sh
```

## Notes
- This pack assumes the `photonstrust` Python package is importable.
- Install dev dependencies if you want schema validation tooling.
