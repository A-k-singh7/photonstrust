#!/usr/bin/env sh
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$HERE"
rm -rf replay_outputs
python -m photonstrust.cli run config.yml --output replay_outputs
python verify.py --bundle benchmark_bundle.json --output replay_outputs
