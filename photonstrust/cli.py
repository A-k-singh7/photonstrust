"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from photonstrust.config import ConfigSchemaVersionError, build_scenarios, load_config
from photonstrust.calibrate import fit_detector_params, fit_emitter_params, fit_memory_params
from photonstrust.comparison import run_heralding_comparison
from photonstrust.graph import compile_graph_artifacts, format_graphspec_toml, load_graph_file, stable_graph_hash
from photonstrust.orbit import run_orbit_pass_from_config
from photonstrust.optimize import run_optimization
from photonstrust.components.pic.crosstalk import predict_parallel_waveguide_xt_db, recommended_min_gap_um
from photonstrust.pic import simulate_pic_netlist, simulate_pic_netlist_sweep
from photonstrust.repeater import run_repeater_optimization
from photonstrust.scenarios import run_source_benchmark, run_teleportation
from photonstrust.sweep import run_scenarios, write_summary_csv
from photonstrust.validation import ConfigValidationError, validate_scenarios_or_raise



def main() -> None:
    parser = argparse.ArgumentParser(description="PhotonTrust CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a scenario config")
    run_parser.add_argument("config", help="Path to config YAML")
    run_parser.add_argument("--output", default="results", help="Output directory")
    run_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate config without running simulation",
    )

    graph_parser = subparsers.add_parser("graph", help="Graph schema and compiler tools")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command")

    graph_compile = graph_subparsers.add_parser("compile", help="Compile a graph JSON/TOML into engine config/netlist")
    graph_compile.add_argument("graph", help="Path to graph JSON or GraphSpec TOML")
    graph_compile.add_argument("--output", default="results/graphs", help="Output directory")
    graph_compile.add_argument(
        "--require-schema",
        action="store_true",
        help="Fail if jsonschema validation is unavailable.",
    )

    fmt_parser = subparsers.add_parser("fmt", help="Deterministic formatting tools")
    fmt_subparsers = fmt_parser.add_subparsers(dest="fmt_command")

    fmt_graphspec = fmt_subparsers.add_parser("graphspec", help="Format GraphSpec (JSON/TOML) as canonical TOML")
    fmt_graphspec.add_argument("graph", help="Path to graph JSON or TOML")
    fmt_graphspec.add_argument("--write", action="store_true", help="Overwrite the input file")
    fmt_graphspec.add_argument("--output", default=None, help="Write formatted TOML to output path")
    fmt_graphspec.add_argument("--check", action="store_true", help="Exit 1 if formatted output differs from current file")
    fmt_graphspec.add_argument("--print-hash", action="store_true", help="Include stable graph hash in output")

    pic_parser = subparsers.add_parser("pic", help="PIC simulation tools (ChipVerify foundations)")
    pic_subparsers = pic_parser.add_subparsers(dest="pic_command")
    pic_sim = pic_subparsers.add_parser("simulate", help="Simulate a compiled PIC netlist JSON")
    pic_sim.add_argument("netlist", help="Path to compiled netlist JSON")
    pic_sim.add_argument("--output", default="results/pic", help="Output directory")
    pic_sim.add_argument("--wavelength-nm", type=float, default=None, help="Override circuit wavelength (nm)")
    pic_sim.add_argument(
        "--wavelength-sweep-nm",
        type=float,
        nargs="+",
        default=None,
        help="Simulate a list of wavelengths (nm). Overrides circuit wavelength.",
    )

    pic_xt = pic_subparsers.add_parser("crosstalk", help="Predict parallel waveguide crosstalk (performance DRC v0)")
    pic_xt.add_argument("--gap-um", type=float, required=True, help="Waveguide gap (um)")
    pic_xt.add_argument("--length-um", type=float, required=True, help="Parallel run length (um)")
    pic_xt.add_argument("--wavelength-nm", type=float, required=True, help="Wavelength (nm)")
    pic_xt.add_argument(
        "--target-xt-db",
        type=float,
        default=None,
        help="Optional target crosstalk spec (dB). If provided, compute recommended gap.",
    )

    bundle_parser = subparsers.add_parser("bundle", help="Evidence bundle tools (export/sign/verify)")
    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_command")

    bundle_keygen = bundle_subparsers.add_parser("keygen", help="Generate an Ed25519 signing keypair")
    bundle_keygen.add_argument("--private", required=True, help="Output path for private key PEM")
    bundle_keygen.add_argument("--public", required=True, help="Output path for public key PEM")

    bundle_sign = bundle_subparsers.add_parser("sign", help="Sign an evidence bundle zip (Ed25519)")
    bundle_sign.add_argument("zip", help="Path to evidence bundle zip")
    bundle_sign.add_argument("--key", required=True, help="Path to Ed25519 private key PEM")
    bundle_sign.add_argument("--output", default=None, help="Output signed zip path (default: <zip>.signed.zip)")

    bundle_verify = bundle_subparsers.add_parser("verify", help="Verify an evidence bundle zip")
    bundle_verify.add_argument("zip", help="Path to evidence bundle zip")
    bundle_verify.add_argument("--pubkey", default=None, help="Path to Ed25519 public key PEM")
    bundle_verify.add_argument(
        "--require-signature",
        action="store_true",
        help="Fail if signature is missing or invalid.",
    )

    card_parser = subparsers.add_parser("card", help="Reliability card tools (validate/diff)")
    card_subparsers = card_parser.add_subparsers(dest="card_command")

    card_validate = card_subparsers.add_parser("validate", help="Validate a reliability card JSON against schema")
    card_validate.add_argument("card", help="Path to reliability_card.json")
    card_validate.add_argument(
        "--schema",
        default=None,
        help="Schema version to use (v1 or v1.1). Default: infer from card.schema_version.",
    )

    card_diff = card_subparsers.add_parser("diff", help="Diff two reliability card JSON files")
    card_diff.add_argument("lhs", help="Left-hand card JSON")
    card_diff.add_argument("rhs", help="Right-hand card JSON")
    card_diff.add_argument("--limit", type=int, default=200, help="Max number of changes to emit")

    args = parser.parse_args()

    if args.command == "fmt":
        if args.fmt_command != "graphspec":
            fmt_parser.print_help()
            return

        input_path = Path(args.graph)
        graph = load_graph_file(input_path)
        formatted = format_graphspec_toml(graph)
        digest = stable_graph_hash(graph)

        raw_text = input_path.read_text(encoding="utf-8")
        changed = formatted != raw_text

        if args.check:
            print(
                json.dumps(
                    {
                        "ok": not changed,
                        "changed": changed,
                        "path": str(input_path),
                        "graph_hash": digest if bool(args.print_hash) else None,
                    },
                    indent=2,
                )
            )
            if changed:
                raise SystemExit(1)
            return

        out_path = None
        if args.output:
            out_path = Path(args.output)
        elif bool(args.write):
            out_path = input_path

        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(formatted, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "path": str(out_path),
                        "changed": changed,
                        "graph_hash": digest if bool(args.print_hash) else None,
                    },
                    indent=2,
                )
            )
            return

        print(formatted, end="")
        if bool(args.print_hash):
            print(json.dumps({"graph_hash": digest}, indent=2))
        return

    if args.command == "graph":
        if args.graph_command != "compile":
            graph_parser.print_help()
            return

        graph_path = Path(args.graph)
        graph = load_graph_file(graph_path)
        graph_id = str(graph.get("graph_id", "graph")).strip() or "graph"
        output_root = Path(args.output)
        output_dir = output_root / graph_id
        result = compile_graph_artifacts(graph, output_dir, require_schema=bool(args.require_schema))
        print(json.dumps(result, indent=2))
        return

    if args.command == "pic":
        if args.pic_command == "simulate":
            netlist_path = Path(args.netlist)
            netlist = json.loads(netlist_path.read_text(encoding="utf-8"))
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)

            if args.wavelength_sweep_nm:
                results = simulate_pic_netlist_sweep(netlist, wavelengths_nm=list(args.wavelength_sweep_nm))
            else:
                results = simulate_pic_netlist(netlist, wavelength_nm=args.wavelength_nm)
            out_path = output_dir / "pic_results.json"
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(json.dumps({"output_dir": str(output_dir), "results_path": str(out_path)}, indent=2))
            return

        if args.pic_command == "crosstalk":
            xt_db = predict_parallel_waveguide_xt_db(
                gap_um=float(args.gap_um),
                parallel_length_um=float(args.length_um),
                wavelength_nm=float(args.wavelength_nm),
            )
            out = {
                "gap_um": float(args.gap_um),
                "parallel_length_um": float(args.length_um),
                "wavelength_nm": float(args.wavelength_nm),
                "xt_db": float(xt_db),
            }
            if args.target_xt_db is not None:
                out["target_xt_db"] = float(args.target_xt_db)
                out["recommended_min_gap_um"] = float(
                    recommended_min_gap_um(
                        target_xt_db=float(args.target_xt_db),
                        parallel_length_um=float(args.length_um),
                        wavelength_nm=float(args.wavelength_nm),
                    )
                )
            print(json.dumps(out, indent=2))
            return

        if args.pic_command != "simulate":
            pic_parser.print_help()
            return

    if args.command == "bundle":
        if args.bundle_command == "keygen":
            from photonstrust.evidence.signing import write_keypair

            write_keypair(private_key_path=Path(args.private), public_key_path=Path(args.public))
            print(
                json.dumps(
                    {"ok": True, "private_key": str(Path(args.private)), "public_key": str(Path(args.public))},
                    indent=2,
                )
            )
            return

        if args.bundle_command == "sign":
            from photonstrust.evidence.bundle import sign_bundle_zip

            out = sign_bundle_zip(
                Path(args.zip),
                private_key_pem_path=Path(args.key),
                output_zip_path=Path(args.output) if args.output else None,
            )
            print(json.dumps(out, indent=2))
            return

        if args.bundle_command == "verify":
            from photonstrust.evidence.bundle import verify_bundle_zip

            res = verify_bundle_zip(
                Path(args.zip),
                public_key_pem_path=Path(args.pubkey) if args.pubkey else None,
                require_signature=bool(args.require_signature),
            )
            print(
                json.dumps(
                    {
                        "ok": bool(res.ok),
                        "bundle_root": res.bundle_root,
                        "manifest_sha256": res.manifest_sha256,
                        "verified_files": res.verified_files,
                        "missing_files": res.missing_files,
                        "mismatched_files": res.mismatched_files,
                        "signature_verified": res.signature_verified,
                        "errors": res.errors,
                    },
                    indent=2,
                )
            )
            if not res.ok:
                raise SystemExit(2)
            return

        bundle_parser.print_help()
        return

    if args.command == "card":
        if args.card_command == "validate":
            try:
                payload = json.loads(Path(args.card).read_text(encoding="utf-8"))
            except FileNotFoundError:
                print(f"Card file not found: {args.card}", file=sys.stderr)
                raise SystemExit(3)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON in {args.card}: {exc}", file=sys.stderr)
                raise SystemExit(2)

            ver = str(args.schema or payload.get("schema_version") or "").strip().lower()
            if ver in {"1", "1.0", "v1", "v1.0", ""}:
                schema_path = Path("schemas") / "photonstrust.reliability_card.v1.schema.json"
                used = "1.0"
            elif ver in {"1.1", "v1.1", "v1_1"}:
                schema_path = Path("schemas") / "photonstrust.reliability_card.v1_1.schema.json"
                used = "1.1"
            else:
                print(f"Unsupported schema version: {ver!r} (supported: v1, v1.1)", file=sys.stderr)
                raise SystemExit(2)

            try:
                from jsonschema import validate
            except Exception as exc:
                print(f"jsonschema is required for card validation: {exc}", file=sys.stderr)
                raise SystemExit(4)

            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"Failed to read schema: {schema_path}: {exc}", file=sys.stderr)
                raise SystemExit(4)

            try:
                validate(instance=payload, schema=schema)
            except Exception as exc:
                print(f"INVALID {args.card} (schema v{used}): {exc}")
                raise SystemExit(1)
            print(f"OK {args.card} (schema v{used})")
            return

        if args.card_command == "diff":
            from photonstrust.api.diff import diff_json

            try:
                lhs_obj = json.loads(Path(args.lhs).read_text(encoding="utf-8"))
                rhs_obj = json.loads(Path(args.rhs).read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                print(str(exc), file=sys.stderr)
                raise SystemExit(3)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}", file=sys.stderr)
                raise SystemExit(2)

            out = diff_json(lhs_obj, rhs_obj, limit=int(args.limit))
            changes = out.get("changes", []) or []
            truncated = bool(out.get("truncated", False))
            print(f"DIFF {args.lhs} -> {args.rhs}")
            print(f"changes_shown: {len(changes)} truncated: {str(truncated).lower()}")
            for ch in changes:
                p = ch.get("path", "")
                a = ch.get("lhs")
                b = ch.get("rhs")
                if a is None and b is not None:
                    kind = "+"
                    msg = f"{kind} {p}: {json.dumps(b, sort_keys=True)}"
                elif a is not None and b is None:
                    kind = "-"
                    msg = f"{kind} {p}: {json.dumps(a, sort_keys=True)}"
                else:
                    kind = "~"
                    msg = f"{kind} {p}: {json.dumps(a, sort_keys=True)} -> {json.dumps(b, sort_keys=True)}"
                if len(msg) > 500:
                    msg = msg[:500] + "..."
                print(msg)

            # Exit code semantics: 0 = identical, 1 = different
            raise SystemExit(0 if len(changes) == 0 and not truncated else 1)

        card_parser.print_help()
        return

    if args.command != "run":
        parser.print_help()
        return

    try:
        config = load_config(args.config)
    except ConfigSchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    output_root = Path(args.output)
    if "orbit_pass" in config:
        result = run_orbit_pass_from_config(config, output_root)
        _write_json(output_root / "orbit_pass_run.json", result)
        return
    if "repeater_optimization" in config:
        run_repeater_optimization(config, output_root)
        return
    if "heralding_comparison" in config:
        run_heralding_comparison(config, output_root)
        return
    if "teleportation" in config:
        run_teleportation(config, output_root)
        return
    if "source_benchmark" in config:
        run_source_benchmark(config, output_root)
        return
    if "calibration" in config:
        result = _run_calibration(config)
        _write_json(output_root / "calibration.json", result)
        return
    if "optimization" in config:
        run_optimization(config, output_root)
        return

    scenarios = build_scenarios(config)
    try:
        validate_scenarios_or_raise(scenarios)
    except ConfigValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    if bool(getattr(args, "validate_only", False)):
        print(json.dumps({"ok": True, "scenarios": int(len(scenarios))}, indent=2))
        return
    result = run_scenarios(scenarios, output_root)

    if "matrix_sweep" in config:
        outputs = config["matrix_sweep"].get("outputs", {})
        if outputs.get("write_summary_csv"):
            summary_path = output_root / "summary.csv"
            write_summary_csv(result["cards"], summary_path)


def _run_calibration(config: dict) -> dict:
    calibration = config["calibration"]
    obs = calibration.get("observations", {})
    calib_type = calibration.get("type", "emitter")
    gate_cfg = calibration.get("quality_gates", {})
    enforce_gates = bool(gate_cfg.get("enforce", False))
    thresholds = gate_cfg.get("thresholds")
    if calib_type == "emitter":
        return fit_emitter_params(obs, enforce_gates=enforce_gates, gate_thresholds=thresholds)
    if calib_type == "detector":
        return fit_detector_params(obs, enforce_gates=enforce_gates, gate_thresholds=thresholds)
    if calib_type == "memory":
        return fit_memory_params(obs, enforce_gates=enforce_gates, gate_thresholds=thresholds)
    raise ValueError(f"Unknown calibration type: {calib_type}")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
