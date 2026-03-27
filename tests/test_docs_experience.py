from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CURATED_DOCS = [
    "README.md",
    "docs/README.md",
    "docs/guide/getting-started.md",
    "docs/guide/use-cases.md",
    "docs/guide/reliability-card.md",
    "docs/guide/limitations.md",
    "docs/user/README.md",
    "docs/user/quickstart.md",
    "docs/user/product-ui.md",
    "docs/reference/README.md",
    "docs/reference/cli.md",
    "docs/reference/config.md",
]
KNOWN_TRUST_LEAKS = [
    "PhotonsTrust",
    "10_minute_quickstart_2026-02-18.md",
    "JAX is a required dependency",
]


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "photonstrust.cli", *args],
        cwd=str(cwd or REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def test_curated_docs_exist_and_known_trust_leaks_are_absent() -> None:
    for relative_path in CURATED_DOCS:
        path = REPO_ROOT / relative_path
        assert path.exists(), f"Expected curated doc to exist: {relative_path}"

        text = path.read_text(encoding="utf-8")
        for trust_leak in KNOWN_TRUST_LEAKS:
            assert trust_leak not in text, f"Unexpected stale string in {relative_path}: {trust_leak}"


def test_readme_and_assets_manifest_reference_existing_images() -> None:
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    image_paths = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme_text)
    assert image_paths, "README should reference at least one curated image"

    local_image_paths = [image_path for image_path in image_paths if not image_path.startswith("http")]
    assert local_image_paths, "README should reference at least one local curated image"

    for image_path in local_image_paths:
        assert (REPO_ROOT / image_path).exists(), f"Missing README image asset: {image_path}"

    asset_manifest = REPO_ROOT / "docs" / "assets" / "README.md"
    asset_text = asset_manifest.read_text(encoding="utf-8")
    for asset_name in (
        "ui-landing.png",
        "ui-decision-review.png",
        "ui-certification.png",
        "ui-pic-gds-layout.png",
    ):
        assert asset_name in asset_text
        assert (REPO_ROOT / "docs" / "assets" / asset_name).exists()


def test_documented_qkd_smoke_path_generates_expected_artifacts(tmp_path: Path) -> None:
    listed = _run_cli("list", "protocols")
    assert "bb84" in listed.stdout.lower()

    output_dir = tmp_path / "smoke_quick"
    _run_cli(
        "run",
        "configs/quickstart/qkd_quick_smoke.yml",
        "--output",
        str(output_dir),
    )

    registry_path = output_dir / "run_registry.json"
    assert registry_path.exists()

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry, "run_registry.json should contain at least one run entry"

    card_rel = str(registry[0]["card_path"]).replace("\\", "/")
    card_candidate = Path(card_rel)
    if card_candidate.is_absolute():
        card_path = card_candidate
    else:
        repo_card = REPO_ROOT / card_candidate
        output_card = output_dir / "demo1_quick_smoke" / "nir_850" / "reliability_card.json"
        card_path = output_card if output_card.exists() else repo_card

    report_html = card_path.parent / "report.html"
    report_pdf = card_path.parent / "report.pdf"
    results_json = card_path.parent / "results.json"

    assert card_path.exists()
    assert report_html.exists()
    assert report_pdf.exists()
    assert results_json.exists()

    validated = _run_cli("card", "validate", str(card_path))
    assert "OK" in validated.stdout


def test_documented_graph_compile_path_generates_expected_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "graphs_demo"
    _run_cli(
        "graph",
        "compile",
        "graphs/demo8_qkd_link_graph.json",
        "--output",
        str(output_dir),
    )

    compiled_dir = output_dir / "demo8_qkd_link"
    assert (compiled_dir / "compiled_config.yml").exists()
    assert (compiled_dir / "assumptions.md").exists()
    assert (compiled_dir / "compile_provenance.json").exists()
    assert (compiled_dir / "graph.json").exists()
