"""Scenario execution and artifact generation."""

from __future__ import annotations

import csv
import json
import os
import platform
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from photonstrust.physics.backends import resolve_backend
from photonstrust.plots import plot_key_rate
from photonstrust.qkd import compute_sweep
from photonstrust.report import (
    build_reliability_card,
    write_html_report,
    write_pdf_report,
    write_reliability_card,
)
from photonstrust.workflow.schema import multifidelity_report_schema_path


def _is_within_root(path_text: str, root_text: str) -> bool:
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _workspace_root() -> str:
    return os.path.realpath(os.getcwd())


def _allowed_roots() -> tuple[str, ...]:
    roots = (
        _workspace_root(),
        os.path.realpath(tempfile.gettempdir()),
        os.path.realpath(str(Path.home())),
    )
    return tuple(dict.fromkeys(roots))


def _is_within_allowed_roots(path_text: str) -> bool:
    return any(_is_within_root(path_text, root_text) for root_text in _allowed_roots())


def _resolve_output_root(output_root: Path) -> Path:
    candidate = os.path.realpath(os.path.join(_workspace_root(), os.fspath(output_root)))
    if not _is_within_allowed_roots(candidate):
        raise ValueError("output_root must stay within the workspace, home, or temp directories")
    return Path(candidate)


def _resolve_scenario_output_dir(output_root: Path, scenario: dict, *, scenario_id: str, band: str) -> Path:
    base_dir = os.path.realpath(os.fspath(output_root))
    raw_output_dir = scenario.get("output_dir")
    if raw_output_dir is None or str(raw_output_dir).strip() == "":
        candidate = os.path.realpath(os.path.join(base_dir, scenario_id, band))
    else:
        candidate = os.path.realpath(os.path.join(base_dir, os.path.expanduser(str(raw_output_dir).strip())))

    if not _is_within_root(candidate, base_dir):
        raise ValueError(f"scenario output_dir must stay within output_root: {base_dir}")
    return Path(candidate)


def run_scenarios(scenarios: list[dict], output_root: Path, *, run_id: str | None = None) -> dict:
    output_root = _resolve_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    grouped = {}
    cards = []

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        band = scenario["band"]
        output_dir = _resolve_scenario_output_dir(output_root, scenario, scenario_id=scenario_id, band=band)
        output_dir.mkdir(parents=True, exist_ok=True)

        sweep = compute_sweep(scenario)
        results = sweep["results"]
        uncertainty = sweep["uncertainty"]
        performance = sweep.get("performance")

        results_payload = _serialize_results(results)
        results_path = output_dir / "results.json"
        results_path.write_text(results_payload, encoding="utf-8")
        if uncertainty is not None:
            (output_dir / "uncertainty.json").write_text(
                json.dumps(uncertainty, indent=2),
                encoding="utf-8",
            )
        if performance:
            (output_dir / "performance.json").write_text(
                json.dumps(performance, indent=2),
                encoding="utf-8",
            )

        card = build_reliability_card(scenario, results, uncertainty, output_dir)
        report_path = output_dir / "report.html"
        pdf_path = output_dir / "report.pdf"
        card_path = output_dir / "reliability_card.json"
        card["artifacts"]["report_html_path"] = str(report_path)
        card["artifacts"]["report_pdf_path"] = str(pdf_path)
        card["artifacts"]["card_path"] = str(card_path)
        write_html_report(card, report_path)
        try:
            write_pdf_report(card, pdf_path)
        except RuntimeError:
            card["artifacts"]["report_pdf_path"] = None
        write_reliability_card(card, card_path)
        cards.append(card)

        grouped.setdefault(scenario_id, {})[band] = results

    for scenario_id, band_results in grouped.items():
        if len(band_results) > 1:
            plot_path = output_root / scenario_id / "key_rate_vs_distance.png"
            plot_key_rate(_label_curves(band_results), plot_path)
            for card in cards:
                if card["scenario_id"] == scenario_id:
                    card["artifacts"]["plots"]["key_rate_vs_distance_path"] = str(plot_path)
                    card_path = output_root / scenario_id / card["band"] / "reliability_card.json"
                    write_reliability_card(card, card_path)

    registry_path = output_root / "run_registry.json"
    _write_registry(cards, registry_path)

    multifidelity_report = _build_multifidelity_report(
        scenarios=scenarios,
        cards=cards,
        run_id=str(run_id or output_root.name or "run").strip() or "run",
    )
    multifidelity_path = output_root / "multifidelity_report.json"
    multifidelity_path.write_text(json.dumps(multifidelity_report, indent=2), encoding="utf-8")
    _validate_multifidelity_report_schema(multifidelity_report)

    return {
        "cards": cards,
        "registry_path": str(registry_path),
        "multifidelity_report_path": str(multifidelity_path),
    }


def write_summary_csv(cards: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "scenario_id",
                "band",
                "source",
                "detector",
                "key_rate_bps",
                "critical_distance_km",
                "qber",
                "safe_use_label",
            ]
        )
        for card in cards:
            writer.writerow(
                [
                    card["scenario_id"],
                    card["band"],
                    card["inputs"]["source"]["type"],
                    card["inputs"]["detector"]["class"],
                    f"{card['outputs']['key_rate_bps']:.6g}",
                    f"{card['outputs']['critical_distance_km']:.2f}",
                    f"{card['derived']['qber_total']:.4f}",
                    card["safe_use_label"]["label"],
                ]
            )


def _serialize_results(results):
    lines = ["{"]
    lines.append('  "results": [')
    for idx, res in enumerate(results):
        comma = "," if idx < len(results) - 1 else ""
        lines.append(
            "    {"
            f"\"distance_km\": {res.distance_km:.6g}, "
            f"\"entanglement_rate_hz\": {res.entanglement_rate_hz:.6g}, "
            f"\"key_rate_bps\": {res.key_rate_bps:.6g}, "
            f"\"qber_total\": {res.qber_total:.6g}, "
            f"\"fidelity\": {res.fidelity:.6g}, "
            f"\"p_pair\": {res.p_pair:.6g}, "
            f"\"p_false\": {res.p_false:.6g}, "
            f"\"loss_db\": {res.loss_db:.6g}"
            "}" + comma
        )
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines)


def _label_curves(band_results: dict) -> dict:
    return {band: results for band, results in band_results.items()}


def _write_registry(cards: list[dict], output_path: Path) -> None:
    rows = []
    for card in cards:
        rows.append(
            {
                "scenario_id": card["scenario_id"],
                "band": card["band"],
                "key_rate_bps": round(float(card["outputs"]["key_rate_bps"]), 6),
                "qber": round(float(card["derived"]["qber_total"]), 6),
                "safe_use": card["safe_use_label"]["label"],
                "card_path": card["artifacts"].get("card_path", ""),
            }
        )
    output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _build_multifidelity_report(*, scenarios: list[dict], cards: list[dict], run_id: str) -> dict:
    by_pair = {
        (str(card.get("scenario_id", "")), str(card.get("band", ""))): card
        for card in cards
        if isinstance(card, dict)
    }

    backend_results: dict[str, dict] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        band = str(scenario.get("band", "")).strip()
        card = by_pair.get((scenario_id, band), {})

        source_backend = str((scenario.get("source", {}) or {}).get("physics_backend", "analytic") or "analytic")
        detector_backend = str((scenario.get("detector", {}) or {}).get("physics_backend", "stochastic") or "stochastic")

        backend_results[f"{scenario_id}:{band}:source"] = _component_backend_entry(
            backend_name=source_backend,
            component="emitter",
            summary={
                "scenario_id": scenario_id,
                "band": band,
                "component": "emitter",
                "requested_backend": source_backend,
                "key_rate_bps": (card.get("outputs", {}) or {}).get("key_rate_bps") if isinstance(card, dict) else None,
            },
        )

        backend_results[f"{scenario_id}:{band}:detector"] = _component_backend_entry(
            backend_name=detector_backend,
            component="detector",
            summary={
                "scenario_id": scenario_id,
                "band": band,
                "component": "detector",
                "requested_backend": detector_backend,
                "qber_total": (card.get("derived", {}) or {}).get("qber_total") if isinstance(card, dict) else None,
            },
        )

    backend_results["qiskit:repeater_primitive"] = _qiskit_repeater_entry()

    report = {
        "schema_version": "0.1",
        "kind": "multifidelity.report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": str(run_id),
        "backend_results": backend_results,
        "provenance": {
            "photonstrust_version": _photonstrust_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    return report


def _component_backend_entry(*, backend_name: str, component: str, summary: dict) -> dict:
    backend = resolve_backend(backend_name)
    applicability = backend.applicability(component, {})
    status = applicability.status
    if status == "fail":
        if any("not installed" in str(reason).lower() for reason in applicability.reasons):
            status = "skipped"
    return {
        "status": status,
        "summary": dict(summary),
        "applicability": applicability.as_dict(),
        "provenance": backend.provenance().as_dict(),
    }


def _qiskit_repeater_entry() -> dict:
    backend = resolve_backend("qiskit")
    applicability = backend.applicability("repeater_primitive", {})
    status = applicability.status
    summary: dict = {
        "component": "repeater_primitive",
        "requested_backend": "qiskit",
    }
    tolerances: dict | None = None
    if applicability.status == "pass":
        simulated = backend.simulate("repeater_primitive", {"tolerance": 1.0e-9})
        if isinstance(simulated, dict):
            status = str(simulated.get("status", "pass"))
            summary = dict(simulated.get("summary", summary))
            raw_tolerances = simulated.get("tolerances")
            if isinstance(raw_tolerances, dict):
                tolerances = dict(raw_tolerances)
    elif any("not installed" in str(reason).lower() for reason in applicability.reasons):
        status = "skipped"

    payload = {
        "status": status,
        "summary": summary,
        "applicability": applicability.as_dict(),
        "provenance": backend.provenance().as_dict(),
    }
    if tolerances is not None:
        payload["tolerances"] = tolerances
    return payload


def _photonstrust_version() -> str:
    try:
        return str(version("photonstrust"))
    except PackageNotFoundError:
        return "0.0"


def _validate_multifidelity_report_schema(payload: dict) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema = json.loads(multifidelity_report_schema_path().read_text(encoding="utf-8"))
    validate(instance=payload, schema=schema)
