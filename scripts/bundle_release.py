"""Create a consolidated release bundle of demo artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    results_root = root / "results"
    bundle_root = results_root / "release_bundle"
    bundle_root.mkdir(parents=True, exist_ok=True)

    cards = []
    for card_path in results_root.glob("**/reliability_card.json"):
        if "release_bundle" in card_path.parts or "golden" in card_path.parts:
            continue
        card = json.loads(card_path.read_text(encoding="utf-8"))
        scenario_id = card["scenario_id"]
        band = card["band"]
        target_dir = bundle_root / scenario_id / band
        target_dir.mkdir(parents=True, exist_ok=True)

        artifacts = card.get("artifacts", {})
        copied = _copy_artifact(card_path, target_dir, "reliability_card.json")
        if copied:
            artifacts["card_path"] = str(copied)

        report_html = _copy_by_path(artifacts.get("report_html_path"), target_dir)
        report_pdf = _copy_by_path(artifacts.get("report_pdf_path"), target_dir)
        if report_html:
            artifacts["report_html_path"] = str(report_html)
        if report_pdf:
            artifacts["report_pdf_path"] = str(report_pdf)

        results_json = _copy_sibling(card_path, target_dir, "results.json")
        if results_json:
            artifacts["results_path"] = str(results_json)

        plot_path = artifacts.get("plots", {}).get("key_rate_vs_distance_path")
        plot_copy = _copy_by_path(plot_path, target_dir)
        if plot_copy:
            artifacts.setdefault("plots", {})["key_rate_vs_distance_path"] = str(plot_copy)

        card["artifacts"] = artifacts
        bundled_card_path = target_dir / "reliability_card.json"
        bundled_card_path.write_text(json.dumps(card, indent=2), encoding="utf-8")
        cards.append(card)

    _bundle_singleton(results_root / "repeater", bundle_root, "repeater")
    _bundle_singleton(results_root / "teleportation", bundle_root, "teleportation")
    _bundle_singleton(results_root / "source_benchmark", bundle_root, "source_benchmark")

    registry_path = bundle_root / "run_registry.json"
    registry_path.write_text(json.dumps(_build_registry(cards), indent=2), encoding="utf-8")

    _write_bundle_readme(bundle_root)


def _copy_by_path(path_str: str | None, target_dir: Path) -> Path | None:
    if not path_str:
        return None
    source = Path(path_str)
    if not source.exists():
        return None
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target


def _copy_artifact(card_path: Path, target_dir: Path, filename: str) -> Path | None:
    source = card_path
    if not source.exists():
        return None
    target = target_dir / filename
    shutil.copy2(source, target)
    return target


def _copy_sibling(card_path: Path, target_dir: Path, filename: str) -> Path | None:
    source = card_path.parent / filename
    if not source.exists():
        return None
    target = target_dir / filename
    shutil.copy2(source, target)
    return target


def _build_registry(cards: list[dict]) -> list[dict]:
    registry = []
    seen = set()
    for card in cards:
        row = {
            "scenario_id": card["scenario_id"],
            "band": card["band"],
            "key_rate_bps": card["outputs"]["key_rate_bps"],
            "qber": card["derived"]["qber_total"],
            "safe_use": card["safe_use_label"]["label"],
            "card_path": card["artifacts"].get("card_path"),
        }
        key = (
            str(row["scenario_id"]).strip().lower(),
            str(row["band"]).strip().lower(),
            _normalize_card_path(row["card_path"]),
        )
        if key in seen:
            continue
        seen.add(key)
        registry.append(row)
    return registry


def _normalize_card_path(path: str | None) -> str:
    if not path:
        return ""
    return str(Path(path).resolve()).replace("\\", "/").lower()


def _bundle_singleton(source_dir: Path, bundle_root: Path, scenario_id: str) -> None:
    if not source_dir.exists():
        return
    target_dir = bundle_root / scenario_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in source_dir.glob("*"):
        if path.is_file():
            shutil.copy2(path, target_dir / path.name)


def _write_bundle_readme(bundle_root: Path) -> None:
    readme = bundle_root / "README.md"
    readme.write_text(
        "# PhotonTrust Release Bundle\n\n"
        "This folder contains consolidated demo artifacts and a run registry.\n\n"
        "## Contents\n"
        "- demo1_*: per-band QKD reliability cards\n"
        "- repeater/: repeater spacing outputs\n"
        "- teleportation/: teleportation SLA outputs\n"
        "- source_benchmark/: source benchmarking outputs\n"
        "- run_registry.json: index for Streamlit UI\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
