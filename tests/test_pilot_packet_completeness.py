from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_pilot_packet_checker_passes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    checker = repo_root / "scripts" / "check_pilot_packet.py"

    completed = subprocess.run(
        [sys.executable, str(checker)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Pilot readiness packet check: PASS" in completed.stdout
