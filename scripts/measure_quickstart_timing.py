#!/usr/bin/env python3
"""Run a command, measure elapsed time, and emit JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure execution time for a command")
    parser.add_argument(
        "--command",
        required=True,
        help="Command string to execute",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Timeout in seconds (default: 60)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.perf_counter()

    timed_out = False
    return_code = None
    stdout = ""
    stderr = ""

    try:
        completed = subprocess.run(
            args.command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = -1
        if exc.stdout:
            stdout = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(errors="replace")
        if exc.stderr:
            stderr = exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode(errors="replace")

    elapsed_seconds = time.perf_counter() - start
    result = {
        "command": args.command,
        "timeout_seconds": args.timeout,
        "elapsed_seconds": elapsed_seconds,
        "returncode": return_code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }
    print(json.dumps(result, sort_keys=True))

    if timed_out:
        return 124
    return int(return_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
