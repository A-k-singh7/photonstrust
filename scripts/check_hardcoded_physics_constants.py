"""Detect module-level hardcoded numeric constants in runtime paths."""

from __future__ import annotations

import ast
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TARGETS = (
    _REPO_ROOT / "photonstrust" / "pipeline",
    _REPO_ROOT / "photonstrust" / "orbit",
    _REPO_ROOT / "photonstrust" / "physics",
    _REPO_ROOT / "photonstrust" / "channels",
    _REPO_ROOT / "photonstrust" / "qkd.py",
)
_ALLOWLIST_SUFFIXES = {
    "constants.py",
    "presets.py",
    "model_metadata.py",
}
_MARKER = "physics-constant-ok"


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for target in _TARGETS:
        if not target.exists():
            continue
        if target.is_file() and target.suffix == ".py":
            files.append(target)
            continue
        files.extend(path for path in target.rglob("*.py") if path.is_file())
    files.sort()
    return files


def _is_numeric_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _is_numeric_literal(node.operand)
    return False


def _has_allowlist_suffix(path: Path) -> bool:
    return any(str(path).endswith(suffix) for suffix in _ALLOWLIST_SUFFIXES)


def _line_has_marker(lines: list[str], line_number: int) -> bool:
    if line_number <= 0 or line_number > len(lines):
        return False
    return _MARKER in lines[line_number - 1]


def _module_level_numeric_assignments(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    violations: list[tuple[int, str]] = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = node.value
            if not _is_numeric_literal(value):
                continue
            if _line_has_marker(lines, node.lineno):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            name = str(node.targets[0].id)
            if name in {"__all__", "__version__"}:
                continue
            violations.append((node.lineno, name))
        elif isinstance(node, ast.AnnAssign):
            if node.value is None or not _is_numeric_literal(node.value):
                continue
            if _line_has_marker(lines, node.lineno):
                continue
            if not isinstance(node.target, ast.Name):
                continue
            name = str(node.target.id)
            if name in {"__all__", "__version__"}:
                continue
            violations.append((node.lineno, name))

    return violations


def main() -> int:
    failures: list[str] = []
    for path in _iter_python_files():
        if _has_allowlist_suffix(path):
            continue
        try:
            violations = _module_level_numeric_assignments(path)
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(_REPO_ROOT)}: syntax error: {exc}")
            continue
        for line, name in violations:
            rel = path.relative_to(_REPO_ROOT)
            failures.append(
                f"{rel}:{line} module-level numeric constant {name!r} is not allowed; "
                f"move to a constants/metadata registry or annotate with '{_MARKER}'"
            )

    if failures:
        print("hardcoded physics constants check: FAIL")
        for row in failures:
            print(f" - {row}")
        return 1

    print("hardcoded physics constants check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
