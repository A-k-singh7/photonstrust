from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.benchmarks.open_benchmarks import check_bundle_file


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify PhotonTrust repro pack outputs.')
    parser.add_argument('--bundle', type=Path, default=Path('benchmark_bundle.json'))
    parser.add_argument('--output', type=Path, default=Path('replay_outputs'))
    args = parser.parse_args()

    ok, failures = check_bundle_file(args.bundle)
    if not ok:
        print('Benchmark bundle check failed:')
        for line in failures:
            print(f' - {line}')
        return 1

    # Minimal artifact existence checks for the replay output.
    bundle = json.loads(args.bundle.read_text(encoding='utf-8'))
    expected = bundle['expected']['qkd_sweeps']
    missing = []
    for entry in expected:
        scenario_id = entry['scenario_id']
        band = entry['band']
        results_path = args.output / scenario_id / band / 'results.json'
        card_path = args.output / scenario_id / band / 'reliability_card.json'
        if not results_path.exists():
            missing.append(str(results_path))
        if not card_path.exists():
            missing.append(str(card_path))
    if missing:
        print('Missing expected replay artifacts:')
        for path in missing:
            print(f' - {path}')
        return 2

    print('Repro pack verification: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
