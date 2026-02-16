"""External reproducibility pack generator (v0).

This produces a self-contained folder that includes:
- the input config
- a benchmark bundle (expected results + config)
- reference outputs produced by the current engine
- environment capture (pip freeze)
- replay scripts (PowerShell + sh) and a small verification helper
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.benchmarks.schema import (
    benchmark_bundle_schema_path,
    repro_pack_manifest_schema_path,
    validate_instance,
)
from photonstrust.benchmarks.open_benchmarks import bundle_from_results
from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep
from photonstrust.sweep import run_scenarios
from photonstrust.utils import hash_dict


def generate_repro_pack(
    config_path: str | Path,
    output_dir: str | Path,
    *,
    pack_id: str | None = None,
) -> Path:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    pack_root = Path(output_dir)
    pack_root.mkdir(parents=True, exist_ok=True)

    cfg = load_config(config_path)
    pack_id = pack_id or _default_pack_id(cfg)
    generated_at = datetime.now(timezone.utc).isoformat()

    # Copy config into the pack.
    packed_config_path = pack_root / "config.yml"
    shutil.copy2(config_path, packed_config_path)

    # Reference outputs.
    reference_outputs_dir = pack_root / "reference_outputs"
    scenarios = build_scenarios(cfg)
    run_scenarios(scenarios, reference_outputs_dir)

    # Compute expected sweeps (no uncertainty by default).
    sweeps = [compute_sweep(s, include_uncertainty=False) for s in scenarios]
    bundle = bundle_from_results(
        benchmark_id=str(pack_id),
        title=f"PhotonTrust repro pack: {pack_id}",
        config=cfg,
        scenarios=scenarios,
        sweeps=sweeps,
        created_at=generated_at,
        photonstrust_version=_photonstrust_version(),
        requires=_engine_requirements_from_config(cfg),
    )
    validate_instance(bundle, benchmark_bundle_schema_path(), require_jsonschema=False)
    bundle_path = pack_root / "benchmark_bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    env_dir = pack_root / "env"
    env_dir.mkdir(parents=True, exist_ok=True)
    pip_freeze_path = env_dir / "pip_freeze.txt"
    _write_pip_freeze(pip_freeze_path)
    python_info_path = env_dir / "python_info.json"
    python_info_path.write_text(
        json.dumps(
            {
                "python": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    verify_py = pack_root / "verify.py"
    verify_py.write_text(_verify_script_source(), encoding="utf-8")
    run_ps1 = pack_root / "run.ps1"
    run_ps1.write_text(_run_ps1_source(), encoding="utf-8")
    run_sh = pack_root / "run.sh"
    run_sh.write_text(_run_sh_source(), encoding="utf-8")

    manifest = {
        "schema_version": "0",
        "generated_at": generated_at,
        "pack_id": str(pack_id),
        "benchmark_bundle_path": "benchmark_bundle.json",
        "reference_outputs_dir": "reference_outputs",
        "env": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pip_freeze_path": "env/pip_freeze.txt",
        },
        "scripts": {"run_ps1": "run.ps1", "run_sh": "run.sh", "verify_py": "verify.py"},
        "provenance": {
            "config_hash": hash_dict(cfg),
        },
    }
    # Manifest schema doesn't include provenance in v0; keep it separate for now.
    manifest_path = pack_root / "repro_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    validate_instance(manifest, repro_pack_manifest_schema_path(), require_jsonschema=False)

    readme_path = pack_root / "README.md"
    readme_path.write_text(_readme_source(pack_id=str(pack_id)), encoding="utf-8")

    return pack_root


def _default_pack_id(cfg: dict) -> str:
    if "scenario" in cfg and isinstance(cfg["scenario"], dict):
        return str(cfg["scenario"].get("id", "repro_pack")).strip() or "repro_pack"
    if "matrix_sweep" in cfg and isinstance(cfg["matrix_sweep"], dict):
        return str(cfg["matrix_sweep"].get("id", "repro_pack")).strip() or "repro_pack"
    for key in ("repeater_optimization", "teleportation", "source_benchmark", "optimization", "calibration"):
        if key in cfg and isinstance(cfg[key], dict):
            return str(cfg[key].get("id", key)).strip() or "repro_pack"
    return "repro_pack"


def _engine_requirements_from_config(cfg: dict) -> list[str]:
    req = []
    # If any source explicitly requests QuTiP, record it as an optional requirement.
    if "source" in cfg and isinstance(cfg["source"], dict):
        if str(cfg["source"].get("physics_backend", "analytic")).strip().lower() == "qutip":
            req.append("qutip>=4.7")
    return req


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        # Fallback to repo pyproject version if metadata isn't present.
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None


def _write_pip_freeze(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        path.write_text(output.strip() + "\n", encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        path.write_text(f"# pip freeze failed: {exc}\n", encoding="utf-8")


def _readme_source(pack_id: str) -> str:
    return (
        f"# PhotonTrust Repro Pack: {pack_id}\n\n"
        "This folder is a reproducibility package for PhotonTrust.\n\n"
        "## Contents\n"
        "- `config.yml`: scenario config used to generate the reference outputs\n"
        "- `benchmark_bundle.json`: expected curves + config (schema-validated)\n"
        "- `reference_outputs/`: outputs produced by the engine at generation time\n"
        "- `env/`: environment capture\n"
        "- `run.ps1` / `run.sh`: replay scripts\n"
        "- `verify.py`: verification helper\n\n"
        "## Replay\n"
        "From this directory:\n\n"
        "PowerShell:\n"
        "```powershell\n"
        "powershell -ExecutionPolicy Bypass -File .\\run.ps1\n"
        "```\n\n"
        "Linux/macOS:\n"
        "```sh\n"
        "sh ./run.sh\n"
        "```\n\n"
        "## Notes\n"
        "- This pack assumes the `photonstrust` Python package is importable.\n"
        "- Install dev dependencies if you want schema validation tooling.\n"
    )


def _run_ps1_source() -> str:
    return (
        "$ErrorActionPreference = 'Stop'\n"
        "$here = Split-Path -Parent $MyInvocation.MyCommand.Path\n"
        "Set-Location $here\n"
        "if (Test-Path 'replay_outputs') { Remove-Item -Recurse -Force 'replay_outputs' }\n"
        "py -m photonstrust.cli run 'config.yml' --output 'replay_outputs'\n"
        "py 'verify.py' --bundle 'benchmark_bundle.json' --output 'replay_outputs'\n"
    )


def _run_sh_source() -> str:
    return (
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "HERE=\"$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\"\n"
        "cd \"$HERE\"\n"
        "rm -rf replay_outputs\n"
        "python -m photonstrust.cli run config.yml --output replay_outputs\n"
        "python verify.py --bundle benchmark_bundle.json --output replay_outputs\n"
    )


def _verify_script_source() -> str:
    return (
        "from __future__ import annotations\n"
        "\n"
        "import argparse\n"
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "from photonstrust.benchmarks.open_benchmarks import check_bundle_file\n"
        "\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser(description='Verify PhotonTrust repro pack outputs.')\n"
        "    parser.add_argument('--bundle', type=Path, default=Path('benchmark_bundle.json'))\n"
        "    parser.add_argument('--output', type=Path, default=Path('replay_outputs'))\n"
        "    args = parser.parse_args()\n"
        "\n"
        "    ok, failures = check_bundle_file(args.bundle, require_jsonschema=False)\n"
        "    if not ok:\n"
        "        print('Benchmark bundle check failed:')\n"
        "        for line in failures:\n"
        "            print(f' - {line}')\n"
        "        return 1\n"
        "\n"
        "    # Minimal artifact existence checks for the replay output.\n"
        "    bundle = json.loads(args.bundle.read_text(encoding='utf-8'))\n"
        "    expected = bundle['expected']['qkd_sweeps']\n"
        "    missing = []\n"
        "    for entry in expected:\n"
        "        scenario_id = entry['scenario_id']\n"
        "        band = entry['band']\n"
        "        results_path = args.output / scenario_id / band / 'results.json'\n"
        "        card_path = args.output / scenario_id / band / 'reliability_card.json'\n"
        "        if not results_path.exists():\n"
        "            missing.append(str(results_path))\n"
        "        if not card_path.exists():\n"
        "            missing.append(str(card_path))\n"
        "    if missing:\n"
        "        print('Missing expected replay artifacts:')\n"
        "        for path in missing:\n"
        "            print(f' - {path}')\n"
        "        return 2\n"
        "\n"
        "    print('Repro pack verification: PASS')\n"
        "    return 0\n"
        "\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
