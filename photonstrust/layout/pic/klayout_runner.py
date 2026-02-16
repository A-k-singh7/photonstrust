"""KLayout batch runner seam (v0.1).

KLayout is treated as an external tool. The open-core must not depend on it.

This module provides:
- executable discovery
- a small wrapper to run a KLayout macro/script in batch mode
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ExternalToolNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class KLayoutRunResult:
    ok: bool
    returncode: int
    command: list[str]
    stdout: str
    stderr: str


def find_klayout_exe() -> str | None:
    # Allow explicit override (useful on Windows where `klayout_app.exe` may not be on PATH).
    env_override = str(os.environ.get("PHOTONTRUST_KLAYOUT_EXE", "") or os.environ.get("KLAYOUT_EXE", "")).strip()
    if env_override:
        p = Path(env_override).expanduser()
        if p.exists() and p.is_file():
            return str(p)

    # Cross-platform candidate names.
    candidates = [
        "klayout",
        "klayout_app",
        "klayout.exe",
        "klayout_app.exe",
    ]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return str(p)

    # Common install locations (best-effort, optional).
    if os.name == "nt":
        bases = [
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("PROGRAMFILES(X86)", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("APPDATA", ""),
        ]
        suffixes = [
            (Path("KLayout") / "klayout_app.exe"),
            (Path("KLayout") / "klayout.exe"),
            (Path("KLayout") / "bin" / "klayout_app.exe"),
            (Path("KLayout") / "bin" / "klayout.exe"),
        ]
        for base in bases:
            if not base:
                continue
            for suf in suffixes:
                cand = (Path(base) / suf).resolve()
                if cand.exists() and cand.is_file():
                    return str(cand)
    return None


def run_klayout_macro(
    macro_path: str | Path,
    *,
    klayout_exe: str | None = None,
    variables: dict[str, Any] | None = None,
    timeout_s: float | None = 300.0,
) -> KLayoutRunResult:
    exe = str(klayout_exe or "").strip() or find_klayout_exe()
    if not exe:
        raise ExternalToolNotFoundError("KLayout executable not found on PATH (expected `klayout` or `klayout_app`).")

    macro_path = Path(macro_path)
    if not macro_path.exists():
        raise FileNotFoundError(str(macro_path))

    cmd: list[str] = [exe, "-b", "-r", str(macro_path)]
    for k, v in sorted((variables or {}).items(), key=lambda kv: str(kv[0]).lower()):
        cmd.extend(["-rd", f"{k}={v}"])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=float(timeout_s) if timeout_s is not None else None,
    )
    return KLayoutRunResult(
        ok=proc.returncode == 0,
        returncode=int(proc.returncode),
        command=cmd,
        stdout=str(proc.stdout or ""),
        stderr=str(proc.stderr or ""),
    )
