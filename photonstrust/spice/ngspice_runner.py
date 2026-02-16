"""ngspice runner seam (v0.1).

ngspice is treated as an external tool (not a Python dependency).

This is a generic runner for batch execution. Parsing analog results (.raw)
is intentionally deferred until we standardize an ingestion contract.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ExternalToolNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class NgspiceRunResult:
    ok: bool
    returncode: int
    command: list[str]
    stdout: str
    stderr: str
    log_path: Path
    raw_path: Path


def find_ngspice_exe() -> str | None:
    candidates = ["ngspice", "ngspice.exe"]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return str(p)
    return None


def run_ngspice(
    netlist_path: str | Path,
    *,
    output_dir: str | Path,
    ngspice_exe: str | None = None,
    timeout_s: float | None = 300.0,
) -> NgspiceRunResult:
    exe = str(ngspice_exe or "").strip() or find_ngspice_exe()
    if not exe:
        raise ExternalToolNotFoundError("ngspice executable not found on PATH (expected `ngspice`).")

    netlist_path = Path(netlist_path)
    if not netlist_path.exists():
        raise FileNotFoundError(str(netlist_path))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "ngspice.log"
    raw_path = output_dir / "ngspice.raw"

    # Batch mode: write console output to log (-o) and rawfile to (-r).
    cmd = [exe, "-b", "-r", str(raw_path), "-o", str(log_path), str(netlist_path)]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=float(timeout_s) if timeout_s is not None else None,
    )
    return NgspiceRunResult(
        ok=proc.returncode == 0,
        returncode=int(proc.returncode),
        command=cmd,
        stdout=str(proc.stdout or ""),
        stderr=str(proc.stderr or ""),
        log_path=log_path,
        raw_path=raw_path,
    )

