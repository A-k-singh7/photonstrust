#!/usr/bin/env python3
"""Initialize synthetic measurement bundle templates for PIC Gate B."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize PIC Gate B measurement templates")
    parser.add_argument("--root", type=Path, default=Path("datasets/measurements/private"), help="Base directory")
    parser.add_argument("--rc-id", default="rc_template", help="Release candidate identifier")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    return parser.parse_args()


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, text: str, *, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_bundle(
    *,
    dataset_id: str,
    kind: str,
    title: str,
    file_rel_path: str,
    file_sha256: str,
    file_description: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0",
        "dataset_id": dataset_id,
        "kind": kind,
        "title": title,
        "created_at": _utc_now_z(),
        "license": "Internal-Use-Only",
        "share_level": "private",
        "restrictions": {
            "contains_personal_data": False,
            "contains_export_controlled": False,
            "contains_proprietary": True,
            "notes": "Synthetic template starter rows; replace with measured silicon values before release evidence use.",
        },
        "provenance": {
            "description": "Template measurement bundle for PIC Gate B correlation workflow.",
        },
        "links": {
            "calibration_bundle_id": None,
            "graph_id": None,
            "config_hash": None,
        },
        "files": [
            {
                "path": file_rel_path,
                "sha256": file_sha256,
                "content_type": "text/csv",
                "description": file_description,
            }
        ],
    }


def main() -> int:
    args = parse_args()
    root = (Path.cwd() / args.root).resolve() if not args.root.is_absolute() else args.root.resolve()
    rc_root = (root / str(args.rc_id)).resolve()
    rc_root.mkdir(parents=True, exist_ok=True)

    b1_dir = rc_root / "b1_insertion_loss"
    b2_dir = rc_root / "b2_resonance"
    b4_dir = rc_root / "b4_delay_rc"

    b1_csv = (
        "lot_id,wafer_id,die_id,component_id,wavelength_nm,measured_loss_db,model_loss_db\n"
        "L001,W01,D01,wg_chain_1,1550.0,2.34,2.31\n"
        "L001,W01,D02,wg_chain_1,1550.0,2.29,2.27\n"
        "L001,W02,D03,wg_chain_1,1550.0,2.37,2.35\n"
    )
    b2_csv = (
        "lot_id,wafer_id,die_id,device_id,temperature_c,measured_resonance_nm,model_resonance_nm\n"
        "L001,W01,D01,ring_1,25.0,1550.120,1550.116\n"
        "L001,W01,D02,ring_1,25.0,1550.118,1550.115\n"
        "L001,W02,D03,ring_1,25.0,1550.125,1550.121\n"
    )
    b4_csv = (
        "lot_id,wafer_id,die_id,net_id,corner,temperature_c,measured_delay_ps,model_delay_ps,measured_resistance_ohm,model_resistance_ohm,measured_capacitance_ff,model_capacitance_ff\n"
        "L001,W01,D01,net_a,tt,25.0,48.2,47.9,182.0,180.0,41.5,41.0\n"
        "L001,W01,D02,net_a,ss,85.0,61.3,60.7,223.0,220.0,47.2,46.8\n"
        "L001,W02,D03,net_a,ff,0.0,39.6,39.1,152.0,150.0,36.8,36.4\n"
    )

    b1_csv_path = b1_dir / "data" / "insertion_loss_measurements.csv"
    b2_csv_path = b2_dir / "data" / "resonance_measurements.csv"
    b4_csv_path = b4_dir / "data" / "delay_rc_measurements.csv"
    _write_text(b1_csv_path, b1_csv, force=bool(args.force))
    _write_text(b2_csv_path, b2_csv, force=bool(args.force))
    _write_text(b4_csv_path, b4_csv, force=bool(args.force))

    b1_bundle = _build_bundle(
        dataset_id=f"{args.rc_id}_b1_insertion_loss",
        kind="pic_component_measurements",
        title=f"{args.rc_id} insertion-loss measurements template",
        file_rel_path="data/insertion_loss_measurements.csv",
        file_sha256=_sha256_file(b1_csv_path),
        file_description="Insertion-loss measured vs model values for Gate B1.",
    )
    b2_bundle = _build_bundle(
        dataset_id=f"{args.rc_id}_b2_resonance",
        kind="pic_resonance_measurements",
        title=f"{args.rc_id} resonance measurements template",
        file_rel_path="data/resonance_measurements.csv",
        file_sha256=_sha256_file(b2_csv_path),
        file_description="Resonance center measured vs model values for Gate B2.",
    )
    b4_bundle = _build_bundle(
        dataset_id=f"{args.rc_id}_b4_delay_rc",
        kind="pic_delay_rc_measurements",
        title=f"{args.rc_id} delay/RC measurements template",
        file_rel_path="data/delay_rc_measurements.csv",
        file_sha256=_sha256_file(b4_csv_path),
        file_description="Delay/RC measured vs model values for Gate B4.",
    )

    b1_bundle_path = b1_dir / "measurement_bundle.json"
    b2_bundle_path = b2_dir / "measurement_bundle.json"
    b4_bundle_path = b4_dir / "measurement_bundle.json"

    _write_text(b1_bundle_path, json.dumps(b1_bundle, indent=2) + "\n", force=bool(args.force))
    _write_text(b2_bundle_path, json.dumps(b2_bundle, indent=2) + "\n", force=bool(args.force))
    _write_text(b4_bundle_path, json.dumps(b4_bundle, indent=2) + "\n", force=bool(args.force))

    manifest = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_gate_b_measurement_template_manifest",
        "generated_at": _utc_now_z(),
        "root": str(rc_root),
        "bundles": {
            "b1_insertion_loss": str(b1_bundle_path),
            "b2_resonance_alignment": str(b2_bundle_path),
            "b4_delay_rc": str(b4_bundle_path),
        },
        "notes": [
            "These bundles contain synthetic starter rows. Replace with measured silicon data before production correlation claims.",
            "Use scripts/build_pic_gate_b_packet.py with these bundle paths to run Gate B automation.",
        ],
    }
    manifest_path = rc_root / "gate_b_template_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2) + "\n", force=True)

    print(json.dumps({"manifest": str(manifest_path), "bundles": manifest["bundles"]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
