"""Fail-closed metadata contract check for physics models."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_model_metadata_module() -> ModuleType:
    module_path = _REPO_ROOT / "photonstrust" / "physics" / "model_metadata.py"
    spec = importlib.util.spec_from_file_location("photonstrust_day30_model_metadata", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load metadata module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    metadata_module = _load_model_metadata_module()
    validate_model_metadata_registry = getattr(metadata_module, "validate_model_metadata_registry", None)
    if not callable(validate_model_metadata_registry):
        raise RuntimeError("validate_model_metadata_registry is missing from model_metadata module")

    registry = validate_model_metadata_registry()
    failures: list[str] = []

    for key, model in sorted(registry.items()):
        if not model.known_failure_regimes:
            failures.append(f"{key}: known_failure_regimes must not be empty")
        if "-" not in model.validity_domain and "<" not in model.validity_domain and ">" not in model.validity_domain:
            failures.append(f"{key}: validity_domain should include explicit bounds or envelope")

    if failures:
        print("model metadata contract: FAIL")
        for row in failures:
            print(f" - {row}")
        return 1

    print(f"model metadata contract: PASS ({len(registry)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
