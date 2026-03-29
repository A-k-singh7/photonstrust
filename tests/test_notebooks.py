"""Tests for cookbook notebooks (execute with nbconvert)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

COOKBOOK_DIR = Path(__file__).parent.parent / "notebooks" / "cookbook"
NOTEBOOKS = sorted(COOKBOOK_DIR.glob("*.ipynb"))


def test_notebooks_are_valid_json():
    """All notebooks should be valid JSON."""
    for nb in NOTEBOOKS:
        data = json.loads(nb.read_text(encoding="utf-8"))
        assert data["nbformat"] == 4, f"{nb.name}: expected nbformat 4"
        assert len(data["cells"]) > 0, f"{nb.name}: no cells found"


def test_all_eight_notebooks_exist():
    """There should be exactly 8 cookbook notebooks."""
    assert len(NOTEBOOKS) == 8, f"Expected 8 notebooks, found {len(NOTEBOOKS)}"


def test_notebook_cell_counts():
    """Each notebook should have between 4 and 8 cells."""
    for nb in NOTEBOOKS:
        data = json.loads(nb.read_text(encoding="utf-8"))
        n_cells = len(data["cells"])
        assert 4 <= n_cells <= 8, (
            f"{nb.name}: expected 4-8 cells, found {n_cells}"
        )


def test_notebooks_have_no_outputs():
    """No notebook should contain pre-filled outputs."""
    for nb in NOTEBOOKS:
        data = json.loads(nb.read_text(encoding="utf-8"))
        for i, cell in enumerate(data["cells"]):
            if cell["cell_type"] == "code":
                assert cell.get("outputs", []) == [], (
                    f"{nb.name} cell {i}: expected empty outputs"
                )
                assert cell.get("execution_count") is None, (
                    f"{nb.name} cell {i}: expected null execution_count"
                )


@pytest.mark.slow
@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_executes(notebook, tmp_path):
    """Each notebook should execute without errors."""
    pytest.importorskip("nbconvert")
    result = subprocess.run(
        [
            sys.executable, "-m", "jupyter", "nbconvert",
            "--to", "notebook", "--execute",
            "--output-dir", str(tmp_path),
            str(notebook),
        ],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"Notebook {notebook.name} failed:\n{result.stderr}"
    )
