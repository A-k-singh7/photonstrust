from __future__ import annotations

import pytest

from photonstrust.layout.pic.klayout_runner import ExternalToolNotFoundError, find_klayout_exe, run_klayout_macro


def test_klayout_runner_missing_tool_raises_clear_error(tmp_path):
    if find_klayout_exe():
        pytest.skip("KLayout is available in this environment")

    with pytest.raises(ExternalToolNotFoundError, match="KLayout executable not found"):
        run_klayout_macro(tmp_path / "dummy.py")
