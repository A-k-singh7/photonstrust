from pathlib import Path

from photonstrust.config import build_scenarios, load_config
from photonstrust.sweep import run_scenarios


def main() -> None:
    config_path = Path("configs/demo1_default.yml")
    config = load_config(config_path)
    scenarios = build_scenarios(config)
    run_scenarios(scenarios, Path("results"))


if __name__ == "__main__":
    main()
