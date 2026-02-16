from __future__ import annotations

from pathlib import Path

import pytest

from photonstrust.spice.ngspice_runner import ExternalToolNotFoundError, find_ngspice_exe, run_ngspice


def test_ngspice_runner_missing_or_executes(tmp_path: Path):
    netlist = tmp_path / "rc.cir"
    netlist.write_text(
        "\n".join(
            [
                "* rc test",
                "V1 in 0 DC 1",
                "R1 in out 1k",
                "C1 out 0 1u",
                ".op",
                ".end",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exe = find_ngspice_exe()
    if not exe:
        with pytest.raises(ExternalToolNotFoundError, match="ngspice executable not found"):
            run_ngspice(netlist, output_dir=tmp_path / "out")
        return

    res = run_ngspice(netlist, output_dir=tmp_path / "out", ngspice_exe=exe, timeout_s=30.0)
    assert res.ok is True
    assert res.log_path.exists()

