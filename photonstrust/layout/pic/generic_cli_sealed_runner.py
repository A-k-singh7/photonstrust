"""Generic sealed CLI runner for external foundry tools.

This utility runs external commands in batch mode and returns only safe metadata.
It intentionally does not expose command arguments, environment values, or stdout/stderr
content in returned payloads.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_ESSENTIAL_ENV_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "TMP", "TEMP")
_BLOCKED_SHELL_BASENAMES = {
    "sh",
    "bash",
    "zsh",
    "ksh",
    "fish",
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
}

GENERIC_CLI_RUNNER_ERROR_CODES = (
    "invalid_command",
    "shell_not_allowed",
    "invalid_cwd",
    "invalid_path",
    "invalid_env",
    "timeout",
    "launch_error",
    "command_failed",
    "summary_json_missing",
    "invalid_summary_json",
    "empty_stdout_json",
    "invalid_stdout_json",
    "invalid_stdout_payload",
)

GENERIC_CLI_BACKEND_ERROR_CODE_MAP = {
    "invalid_command": "invalid_generic_cli_command",
    "shell_not_allowed": "generic_cli_shell_blocked",
    "invalid_cwd": "generic_cli_invalid_cwd",
    "invalid_path": "generic_cli_invalid_path",
    "invalid_env": "generic_cli_invalid_env",
    "timeout": "generic_cli_timeout",
    "launch_error": "generic_cli_exec_error",
    "command_failed": "generic_cli_nonzero_exit",
    "summary_json_missing": "generic_cli_invalid_summary_json",
    "invalid_summary_json": "generic_cli_invalid_summary_json",
    "empty_stdout_json": "generic_cli_empty_output",
    "invalid_stdout_json": "generic_cli_invalid_json",
    "invalid_stdout_payload": "generic_cli_invalid_payload",
}

GENERIC_CLI_BACKEND_FALLBACK_ERROR_CODE = "backend_execution_error"


def _render_template(value: str, context: dict[str, str]) -> str:
    rendered = str(value)
    for _ in range(4):
        previous = rendered
        for key, replacement in context.items():
            rendered = rendered.replace("{" + key + "}", replacement)
        if rendered == previous:
            break
    return rendered


def _normalize_string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        key = str(k).strip()
        if not key:
            continue
        out[key] = str(v)
    return out


def _build_template_context(
    *,
    input_paths: dict[str, str] | None,
    output_paths: dict[str, str] | None,
    summary_json_path: str | None,
) -> dict[str, str]:
    context: dict[str, str] = {}
    context.update(_normalize_string_map(input_paths))
    context.update(_normalize_string_map(output_paths))
    if summary_json_path:
        context["summary_json_path"] = str(summary_json_path)
    return context


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _parse_json_object(value: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None, "invalid_stdout_json"
    if not isinstance(payload, dict):
        return None, "invalid_stdout_payload"
    return payload, None


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GenericCLISealedResult:
    ok: bool
    returncode: int | None
    timed_out: bool
    duration_s: float
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str
    summary_json: dict[str, Any] | None
    error_code: str | None


@dataclass(frozen=True)
class GenericCLIBackendResult:
    status: str
    checks: list[dict[str, str]]
    error_code: str | None = None


def _error_result(error_code: str) -> GenericCLISealedResult:
    return GenericCLISealedResult(
        ok=False,
        returncode=None,
        timed_out=False,
        duration_s=0.0,
        stdout_bytes=0,
        stderr_bytes=0,
        stdout_sha256=_sha256_text(""),
        stderr_sha256=_sha256_text(""),
        summary_json=None,
        error_code=error_code,
    )


def _normalize_env_key(key: str) -> str:
    text = str(key).strip()
    if os.name == "nt":
        return text.upper()
    return text


def _normalize_env_allowlist(value: list[str] | None) -> set[str] | None:
    if value is None:
        return None
    out = {_normalize_env_key(k) for k in value if isinstance(k, str) and str(k).strip()}
    out.update(_normalize_env_key(k) for k in _ESSENTIAL_ENV_KEYS)
    return out


def _is_shell_launcher(command0: str) -> bool:
    basename = Path(str(command0)).name.strip().lower()
    return basename in _BLOCKED_SHELL_BASENAMES


def _has_relative_parent_reference(path_text: str) -> bool:
    path = Path(str(path_text))
    return (not path.is_absolute()) and any(part == ".." for part in path.parts)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_within_root(path_text: str, root_text: str) -> bool:
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _allowed_runner_roots() -> tuple[str, ...]:
    roots = (
        os.path.realpath(os.fspath(_repo_root())),
        os.path.realpath(os.getcwd()),
        os.path.realpath(tempfile.gettempdir()),
        os.path.realpath(str(Path.home())),
    )
    return tuple(dict.fromkeys(roots))


def _is_within_allowed_roots(path_text: str) -> bool:
    return any(_is_within_root(path_text, root_text) for root_text in _allowed_runner_roots())


def _validate_path_map(path_map: dict[str, str]) -> bool:
    for value in path_map.values():
        path_text = str(value).strip()
        if not path_text:
            return False
        if _has_relative_parent_reference(path_text):
            return False
    return True


def _resolve_cwd(cwd_value: str | None) -> tuple[str | None, str | None]:
    if cwd_value is None:
        return None, None
    cwd_text = str(cwd_value).strip()
    if not cwd_text:
        return None, None
    if _has_relative_parent_reference(cwd_text):
        return None, "invalid_cwd"

    try:
        cwd_path = Path(cwd_text)
        if not cwd_path.is_absolute():
            cwd_path = (Path.cwd() / cwd_path).resolve()
        else:
            cwd_path = cwd_path.resolve()
    except OSError:
        return None, "invalid_cwd"

    resolved_text = os.path.realpath(os.fspath(cwd_path))
    if not _is_within_allowed_roots(resolved_text):
        return None, "invalid_cwd"
    if not cwd_path.exists() or not cwd_path.is_dir():
        return None, "invalid_cwd"
    return resolved_text, None


def _resolve_path(path_text: str, *, cwd: str | None) -> tuple[Path | None, str | None]:
    raw = str(path_text).strip()
    if not raw:
        return None, "invalid_path"
    if _has_relative_parent_reference(raw):
        return None, "invalid_path"

    try:
        path = Path(raw)
        if not path.is_absolute():
            base = Path(cwd) if cwd else Path.cwd()
            path = (base / path).resolve()
        else:
            path = path.resolve()
    except OSError:
        return None, "invalid_path"

    resolved_text = os.path.realpath(os.fspath(path))
    if not _is_within_allowed_roots(resolved_text):
        return None, "invalid_path"
    return Path(resolved_text), None


def _build_run_env(
    *,
    env_allowlist: list[str] | None,
    env_overrides: dict[str, Any] | None,
) -> tuple[dict[str, str] | None, str | None]:
    allowed_env_keys = _normalize_env_allowlist(env_allowlist)
    env: dict[str, str] = {}

    for key in _ESSENTIAL_ENV_KEYS:
        if key in os.environ:
            env[key] = os.environ[key]

    if allowed_env_keys is not None:
        for key, value in os.environ.items():
            if _normalize_env_key(key) in allowed_env_keys:
                env[key] = value

    if isinstance(env_overrides, dict):
        for key_raw, value_raw in env_overrides.items():
            key = str(key_raw).strip()
            if not key:
                continue
            normalized_key = _normalize_env_key(key)
            if allowed_env_keys is not None and normalized_key not in allowed_env_keys:
                return None, "invalid_env"
            env[key] = str(value_raw)

    return env or None, None


def run_generic_cli_sealed(
    *,
    command: list[str],
    cwd: str | None = None,
    env_allowlist: list[str] | None = None,
    env_overrides: dict[str, Any] | None = None,
    timeout_s: float | None = 300.0,
    summary_json_path: str | None = None,
    input_paths: dict[str, str] | None = None,
    output_paths: dict[str, str] | None = None,
    parse_stdout_json_when_no_summary: bool = False,
) -> GenericCLISealedResult:
    if not isinstance(command, list) or not command or any(not isinstance(x, str) for x in command):
        return _error_result("invalid_command")

    normalized_input_paths = _normalize_string_map(input_paths)
    normalized_output_paths = _normalize_string_map(output_paths)
    if not _validate_path_map(normalized_input_paths):
        return _error_result("invalid_path")
    if not _validate_path_map(normalized_output_paths):
        return _error_result("invalid_path")

    context = _build_template_context(
        input_paths=normalized_input_paths,
        output_paths=normalized_output_paths,
        summary_json_path=summary_json_path,
    )
    resolved_command = [_render_template(arg, context).strip() for arg in command]
    if any(not arg for arg in resolved_command):
        return _error_result("invalid_command")
    if _is_shell_launcher(resolved_command[0]):
        return _error_result("shell_not_allowed")

    rendered_cwd = _render_template(str(cwd), context) if cwd is not None else None
    resolved_cwd, cwd_error = _resolve_cwd(rendered_cwd)
    if cwd_error is not None:
        return _error_result(cwd_error)

    resolved_summary_path: Path | None = None
    if summary_json_path:
        rendered_summary = _render_template(str(summary_json_path), context)
        summary_path, summary_path_error = _resolve_path(rendered_summary, cwd=resolved_cwd)
        if summary_path_error is not None:
            return _error_result(summary_path_error)
        assert summary_path is not None
        resolved_summary_path = summary_path

    run_env, env_error = _build_run_env(env_allowlist=env_allowlist, env_overrides=env_overrides)
    if env_error is not None:
        return _error_result(env_error)

    started = time.monotonic()
    stdout_text = ""
    stderr_text = ""
    returncode: int | None = None
    timed_out = False
    error_code: str | None = None

    try:
        proc = subprocess.run(
            resolved_command,
            capture_output=True,
            text=True,
            cwd=resolved_cwd,
            env=run_env,
            stdin=subprocess.DEVNULL,
            timeout=float(timeout_s) if timeout_s is not None else None,
            shell=False,
            check=False,
        )
        returncode = int(proc.returncode)
        stdout_text = str(proc.stdout or "")
        stderr_text = str(proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = str(exc.stdout or "")
        stderr_text = str(exc.stderr or "")
        error_code = "timeout"
    except OSError:
        error_code = "launch_error"

    duration_s = time.monotonic() - started

    logs_dir = Path(tempfile.mkdtemp(prefix="pt_generic_cli_"))
    _write_text(logs_dir / "stdout.txt", stdout_text)
    _write_text(logs_dir / "stderr.txt", stderr_text)

    summary_json: dict[str, Any] | None = None
    if resolved_summary_path is not None:
        if resolved_summary_path.exists() and resolved_summary_path.is_file():
            summary_json = _read_json_object(resolved_summary_path)
            if summary_json is None and error_code is None:
                error_code = "invalid_summary_json"
        elif error_code is None:
            error_code = "summary_json_missing"
    elif parse_stdout_json_when_no_summary and error_code is None and returncode == 0 and not timed_out:
        stdout_clean = stdout_text.strip()
        if not stdout_clean:
            error_code = "empty_stdout_json"
        else:
            summary_json, parse_error = _parse_json_object(stdout_clean)
            if parse_error is not None:
                error_code = parse_error

    ok = returncode == 0 and not timed_out and error_code is None
    if returncode is not None and returncode != 0 and error_code is None:
        error_code = "command_failed"

    return GenericCLISealedResult(
        ok=ok,
        returncode=returncode,
        timed_out=timed_out,
        duration_s=float(duration_s),
        stdout_bytes=len(stdout_text.encode("utf-8", errors="ignore")),
        stderr_bytes=len(stderr_text.encode("utf-8", errors="ignore")),
        stdout_sha256=_sha256_text(stdout_text),
        stderr_sha256=_sha256_text(stderr_text),
        summary_json=summary_json,
        error_code=error_code,
    )


def _normalize_timeout(value: Any, *, default: float = 60.0) -> float:
    if isinstance(value, (int, float)):
        timeout = float(value)
    else:
        timeout = default
    if timeout <= 0:
        timeout = default
    return timeout


def _normalize_status_with_map(
    raw_status: Any,
    status_map: dict[str, str],
    normalize_status: Any,
) -> str:
    status_raw = str(raw_status or "").strip().lower()
    if status_raw:
        for src, dst in status_map.items():
            if str(src).strip().lower() == status_raw:
                return normalize_status(dst, default="error")
    return normalize_status(raw_status, default="error")


def _normalize_checks_with_map(
    raw_checks: Any,
    status_map: dict[str, str],
    normalize_checks: Any,
    normalize_status: Any,
) -> list[dict[str, str]]:
    if not status_map:
        return normalize_checks(raw_checks)

    out: list[dict[str, str]] = []
    if not isinstance(raw_checks, list):
        return out

    for i, raw in enumerate(raw_checks):
        if not isinstance(raw, dict):
            continue
        check_id = str(raw.get("id") or raw.get("check_id") or f"check_{i}").strip() or f"check_{i}"
        check_name = str(raw.get("name") or raw.get("check_name") or check_id).strip() or check_id
        status = _normalize_status_with_map(raw.get("status"), status_map, normalize_status)
        out.append({"id": check_id, "name": check_name, "status": status})

    out.sort(key=lambda r: (r["id"].lower(), r["name"].lower()))
    return out


def _map_runner_error_code(error_code: str | None) -> str:
    if error_code in GENERIC_CLI_BACKEND_ERROR_CODE_MAP:
        return GENERIC_CLI_BACKEND_ERROR_CODE_MAP[error_code]
    return GENERIC_CLI_BACKEND_FALLBACK_ERROR_CODE


def run_generic_cli_backend(
    request: dict[str, Any],
    *,
    normalize_status: Any,
    normalize_checks: Any,
    derive_status: Any,
) -> GenericCLIBackendResult:
    raw_nested = request.get("generic_cli")
    nested: dict[str, Any] = dict(raw_nested) if isinstance(raw_nested, dict) else {}

    nested_command = nested.get("command")
    command_raw = nested_command if isinstance(nested_command, list) else request.get("generic_cli_command")
    if not isinstance(command_raw, list) or not command_raw or not all(isinstance(x, str) for x in command_raw):
        return GenericCLIBackendResult(status="error", checks=[], error_code="invalid_generic_cli_command")

    timeout_raw = nested.get("timeout_s", request.get("generic_cli_timeout_sec", 60))
    timeout_sec = _normalize_timeout(timeout_raw)

    nested_input_paths = nested.get("input_paths")
    nested_output_paths = nested.get("output_paths")

    context: dict[str, str] = {}
    context.update(_normalize_string_map(nested_input_paths))
    context.update(_normalize_string_map(nested_output_paths))

    summary_json_path_raw = nested.get("summary_json_path")
    if isinstance(summary_json_path_raw, str) and summary_json_path_raw.strip():
        context["summary_json_path"] = str(summary_json_path_raw).strip()

    command = [_render_template(str(x), context) for x in command_raw]

    nested_env_allowlist = nested.get("env_allowlist")
    env_allowlist = nested_env_allowlist if isinstance(nested_env_allowlist, list) else None

    nested_env = nested.get("env")
    extra_env = nested_env if isinstance(nested_env, dict) else request.get("generic_cli_env")
    env_overrides = extra_env if isinstance(extra_env, dict) else None

    cwd_raw = nested.get("cwd", request.get("generic_cli_cwd"))
    cwd = _render_template(str(cwd_raw), context) if isinstance(cwd_raw, str) and cwd_raw.strip() else None

    summary_json_path: str | None = None
    if isinstance(summary_json_path_raw, str) and summary_json_path_raw.strip():
        summary_json_path = _render_template(str(summary_json_path_raw), context)

    status_map = _normalize_string_map(nested.get("check_status_map"))

    runner_result = run_generic_cli_sealed(
        command=command,
        cwd=cwd,
        env_allowlist=env_allowlist,
        env_overrides=env_overrides,
        timeout_s=timeout_sec,
        summary_json_path=summary_json_path,
        input_paths=_normalize_string_map(nested_input_paths) or None,
        output_paths=_normalize_string_map(nested_output_paths) or None,
        parse_stdout_json_when_no_summary=True,
    )

    if not runner_result.ok:
        return GenericCLIBackendResult(
            status="error",
            checks=[],
            error_code=_map_runner_error_code(runner_result.error_code),
        )

    payload = runner_result.summary_json
    if not isinstance(payload, dict):
        return GenericCLIBackendResult(status="error", checks=[], error_code="generic_cli_invalid_payload")

    checks = _normalize_checks_with_map(payload.get("checks"), status_map, normalize_checks, normalize_status)
    status = _normalize_status_with_map(payload.get("status"), status_map, normalize_status)
    if status == "error" and not str(payload.get("status", "")).strip():
        status = derive_status(checks)
    return GenericCLIBackendResult(status=status, checks=checks, error_code=None)
