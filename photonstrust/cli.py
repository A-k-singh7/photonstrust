"""Command-line interface."""

from __future__ import annotations

import argparse
import inspect
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

    certify_parser = subparsers.add_parser("certify", help="Run PIC->QKD certification orchestrator")
    certify_parser.add_argument("graph", help="Path to graph JSON or GraphSpec TOML")
    certify_parser.add_argument("--pdk", default="generic_silicon_photonics", help="PDK name")
    certify_parser.add_argument("--protocol", default="BB84_DECOY", help="QKD protocol name")
    certify_parser.add_argument("--wavelength", type=float, default=1550.0, help="Wavelength in nm")
    certify_parser.add_argument("--target-distance", type=float, default=50.0, help="Target distance in km")
    certify_parser.add_argument(
        "--distances",
        nargs="+",
        default=None,
        help="Distance grid in km (space and/or comma separated values)",
    )
    certify_parser.add_argument("--output", default="results/certify", help="Output directory")
    certify_parser.add_argument("--dry-run", action="store_true", help="Skip simulation and QKD sweep")
    certify_parser.add_argument("--require-go", action="store_true", help="Exit non-zero if decision is HOLD")
    certify_parser.add_argument("--signing-key", default=None, help="Optional Ed25519 private key PEM")

    compliance_parser = subparsers.add_parser("compliance", help="ETSI QKD compliance tools")
    compliance_subparsers = compliance_parser.add_subparsers(dest="compliance_command")

    compliance_check = compliance_subparsers.add_parser(
        "check",
        help="Build an ETSI compliance report from scenario YAML or PIC certificate JSON",
    )
    compliance_check.add_argument("input", help="Path to scenario YAML or PIC certificate JSON")
    compliance_check.add_argument(
        "--standards",
        nargs="+",
        default=None,
        help="Standards to assess (space/comma separated)",
    )
    compliance_check.add_argument(
        "--use-case",
        default=None,
        help="Optional ETSI GS QKD 002 use case ID (for example UC-1)",
    )
    compliance_check.add_argument(
        "--k-min",
        type=float,
        default=1000.0,
        help="Minimum key rate threshold in bps",
    )
    compliance_check.add_argument(
        "--d-spec",
        type=float,
        default=None,
        help="Specified operational distance override (km)",
    )
    compliance_check.add_argument(
        "--output",
        default=None,
        help="Output path for compliance report JSON",
    )
    compliance_check.add_argument(
        "--format",
        choices=("json", "pdf", "text"),
        default="json",
        help="Primary output format",
    )
    compliance_check.add_argument("--signing-key", default=None, help="Optional Ed25519 private key PEM")
    compliance_check.add_argument("--strict", action="store_true", help="Exit with code 1 if any FAIL is present")

    m3_parser = subparsers.add_parser("m3", help="M3 checkpoint orchestration tools")
    m3_subparsers = m3_parser.add_subparsers(dest="m3_command")

    m3_checkpoint = m3_subparsers.add_parser("checkpoint", help="Run M3 QKD + repeater checkpoint lane")
    m3_checkpoint.add_argument(
        "--qkd-config",
        default="configs/quickstart/qkd_default.yml",
        help="Path to QKD config YAML",
    )
    m3_checkpoint.add_argument(
        "--repeater-config",
        default="configs/demo2_repeater_spacing.yml",
        help="Path to repeater config YAML",
    )
    m3_checkpoint.add_argument(
        "--output-dir",
        default="results/m3_checkpoint",
        help="Output directory for checkpoint artifacts",
    )
    force_group = m3_checkpoint.add_mutually_exclusive_group()
    force_group.add_argument(
        "--force-analytic",
        dest="force_analytic",
        action="store_true",
        help="Force analytic backend execution (default)",
    )
    force_group.add_argument(
        "--no-force-analytic",
        dest="force_analytic",
        action="store_false",
        help="Allow non-analytic backend execution",
    )
    m3_checkpoint.set_defaults(force_analytic=True)
    m3_checkpoint.add_argument(
        "--perturbation-fraction",
        type=float,
        default=0.05,
        help="Relative perturbation fraction used by checkpoint stability checks",
    )
    m3_checkpoint.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when overall_status is not PASS",
    )

    satellite_chain_parser = subparsers.add_parser(
        "satellite-chain",
        help="Run satellite-to-ground PIC digital twin chain",
    )
    satellite_chain_parser.add_argument("config", help="Path to satellite chain YAML config")
    satellite_chain_parser.add_argument(
        "--output",
        default="results/satellite_chain",
        help="Output directory for chain artifacts",
    )
    satellite_chain_parser.add_argument(
        "--signing-key",
        default=None,
        help="Optional Ed25519 private key PEM used to sign the certificate",
    )
    satellite_chain_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if the satellite chain decision is HOLD",
    )

    sweep_parser = subparsers.add_parser("sweep", help="Run PIC process-corner sweep")
    sweep_parser.add_argument("graph_path", help="Path to PIC graph JSON")
    sweep_parser.add_argument("--pdk", default="generic_sip_corners", help="PDK name")
    sweep_parser.add_argument(
        "--pdk-manifest",
        default=None,
        help="Optional path to a PDK manifest JSON",
    )
    sweep_parser.add_argument("--protocol", default="BB84_DECOY", help="QKD protocol name")
    sweep_parser.add_argument(
        "--target-distance",
        type=float,
        default=50.0,
        help="Target link distance in km",
    )
    sweep_parser.add_argument(
        "--wavelength",
        type=float,
        default=1550.0,
        help="Wavelength in nm",
    )
    sweep_parser.add_argument(
        "--corners",
        default="all",
        help="Corner selection: all or comma-separated subset of SS,TT,FF,FS,SF",
    )
    sweep_parser.add_argument(
        "--monte-carlo",
        type=int,
        default=0,
        help="Number of Monte Carlo samples (0 disables MC)",
    )
    sweep_parser.add_argument("--mc-seed", type=int, default=42, help="Monte Carlo seed")
    sweep_parser.add_argument(
        "--threshold",
        type=float,
        default=1000.0,
        help="Key-rate threshold in bps",
    )
    sweep_parser.add_argument("--output", default="results/corner_sweep", help="Output directory")

    # -- Phase D ease-of-use subcommands --------------------------------------

    list_parser = subparsers.add_parser("list", help="List available resources")
    list_parser.add_argument(
        "resource",
        choices=["protocols", "detectors", "bands", "pdks", "scenarios", "channels"],
        help="Resource type to list",
    )

    info_parser = subparsers.add_parser("info", help="Show details about a protocol, detector, or band")
    info_parser.add_argument("entity", help="Name of protocol, detector, or band")

    demo_parser = subparsers.add_parser("demo", help="Run a pre-built scenario")
    demo_parser.add_argument("scenario", nargs="?", default=None, help="Scenario name (omit to list all)")

    quickstart_parser = subparsers.add_parser("quickstart", help="Interactive QKD simulation wizard")
    quickstart_parser.add_argument(
        "--non-interactive", action="store_true", help="Use defaults without prompting",
    )
    quickstart_parser.add_argument("--save", default=None, help="Save config to YAML file")

    # -- end Phase D subcommands ------------------------------------------------

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

    if args.command == "certify":
        from photonstrust.pipeline.certify import run_certify

        distances_km = _parse_float_values(args.distances, default=[0.0, 25.0, 50.0, 75.0, 100.0])
        result = run_certify(
            Path(args.graph),
            pdk_name=str(args.pdk),
            protocol=str(args.protocol),
            wavelength_nm=float(args.wavelength),
            target_distance_km=float(args.target_distance),
            distances_km=distances_km,
            output_dir=Path(args.output),
            dry_run=bool(args.dry_run),
            signing_key=Path(args.signing_key) if args.signing_key else None,
        )
        summary = {
            "decision": str(result.get("decision") or "HOLD"),
            "output_path": result.get("output_path"),
        }
        print(json.dumps(summary, indent=2))
        if bool(args.require_go) and summary["decision"] != "GO":
            raise SystemExit(1)
        return

    if args.command == "compliance":
        if args.compliance_command != "check":
            compliance_parser.print_help()
            return

        from photonstrust.compliance.cli_compliance import run_compliance_check

        standards = _parse_text_values(args.standards)
        result = run_compliance_check(
            Path(args.input),
            standards=standards,
            use_case_id=str(args.use_case).strip() if args.use_case else None,
            k_min_bps=float(args.k_min),
            d_spec_km=float(args.d_spec) if args.d_spec is not None else None,
            output_path=Path(args.output) if args.output else None,
            output_format=str(args.format),
            signing_key=Path(args.signing_key) if args.signing_key else None,
            strict=bool(args.strict),
        )

        report = result.get("report") if isinstance(result.get("report"), dict) else {}
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        output = {
            "ok": not bool(result.get("has_failures")),
            "strict_violation": bool(result.get("strict_violation")),
            "failure_count": int(result.get("failure_count", 0)),
            "overall_status": str(report.get("overall_status") or report.get("status") or ""),
            "input_kind": result.get("input_kind"),
            "output_format": result.get("output_format"),
            "output_path": result.get("output_path"),
            "pdf_path": result.get("pdf_path"),
            "summary": summary,
        }
        print(json.dumps(output, separators=(",", ":"), sort_keys=True))
        if bool(result.get("strict_violation")):
            raise SystemExit(1)
        return

    if args.command == "satellite-chain":
        try:
            from photonstrust.pipeline.satellite_chain import run_satellite_chain
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"satellite_chain_api_unavailable: {exc}",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            raise SystemExit(2)

        try:
            chain_config = load_config(args.config)
        except ConfigSchemaVersionError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc

        output_dir = Path(args.output) if args.output else None
        result = run_satellite_chain(
            chain_config,
            output_dir=output_dir,
            signing_key=Path(args.signing_key) if args.signing_key else None,
        )
        summary = _summarize_satellite_chain_result(result, output_dir=output_dir)
        print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
        if bool(args.strict) and str(summary.get("decision") or "").strip().upper() != "GO":
            raise SystemExit(1)
        return

    if args.command == "sweep":
        try:
            from photonstrust.pic.corner_sweep import run_corner_sweep
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"corner_sweep_api_unavailable: {exc}",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            raise SystemExit(2)

        output_dir = Path(args.output)
        try:
            corner_set = _normalize_corner_selection(args.corners)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc

        result = _invoke_corner_sweep(
            run_corner_sweep,
            graph_path=Path(args.graph_path),
            pdk_name=str(args.pdk),
            pdk_manifest_path=Path(args.pdk_manifest) if args.pdk_manifest else None,
            protocol=str(args.protocol),
            target_distance_km=float(args.target_distance),
            wavelength_nm=float(args.wavelength),
            corner_set=corner_set,
            n_monte_carlo=int(args.monte_carlo),
            mc_seed=int(args.mc_seed),
            key_rate_threshold_bps=float(args.threshold),
            output_dir=output_dir,
        )

        summary = _summarize_corner_sweep_result(result, output_dir=output_dir)
        print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
        return

    if args.command == "m3":
        if args.m3_command != "checkpoint":
            m3_parser.print_help()
            return

        try:
            from photonstrust.pipeline.m3_checkpoint import run_m3_checkpoint
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"m3_checkpoint_api_unavailable: {exc}",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            raise SystemExit(2)

        output_dir = Path(args.output_dir)
        result = run_m3_checkpoint(
            qkd_config_path=Path(args.qkd_config),
            repeater_config_path=Path(args.repeater_config),
            output_dir=output_dir,
            force_analytic_backend=bool(args.force_analytic),
            perturbation_fraction=float(args.perturbation_fraction),
        )

        summary = _summarize_m3_checkpoint_result(result, output_dir=output_dir)
        print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
        if bool(args.strict) and str(summary.get("overall_status") or "").strip().upper() != "PASS":
            raise SystemExit(1)
        return

    # -- Phase D ease-of-use handlers -----------------------------------------

    if args.command == "list":
        from photonstrust.cli_helpers import print_table

        resource = args.resource

        if resource == "protocols":
            from photonstrust.qkd_protocols.registry import _PROTOCOLS

            headers = ["Name", "Aliases", "Type", "Gate Policy"]
            rows = []
            for pid, mod in sorted(_PROTOCOLS.items()):
                aliases = ", ".join(mod.aliases) if mod.aliases else ""
                gp = mod.gate_policy or {}
                gate = str(gp.get("plob_repeaterless_bound", ""))
                rows.append([pid, aliases, "QKD", gate])
            print_table(headers, rows, title="Available Protocols")
            return

        if resource == "detectors":
            from photonstrust.presets import DETECTOR_PRESETS

            headers = ["Name", "PDE", "Dark Counts (cps)", "Jitter (ps)", "Dead Time (ns)"]
            rows = []
            for name, det in sorted(DETECTOR_PRESETS.items()):
                rows.append([
                    name,
                    str(det["pde"]),
                    str(det["dark_counts_cps"]),
                    str(det["jitter_ps_fwhm"]),
                    str(det["dead_time_ns"]),
                ])
            print_table(headers, rows, title="Detector Presets")
            return

        if resource == "bands":
            from photonstrust.presets import BAND_PRESETS

            headers = ["Name", "Wavelength (nm)", "Fiber Loss (dB/km)", "Dispersion (ps/km)"]
            rows = []
            for name, band in sorted(BAND_PRESETS.items()):
                rows.append([
                    name,
                    str(band["wavelength_nm"]),
                    str(band["fiber_loss_db_per_km"]),
                    str(band["dispersion_ps_per_km"]),
                ])
            print_table(headers, rows, title="Band Presets")
            return

        if resource == "pdks":
            pdk_dir = Path(__file__).resolve().parent.parent / "configs" / "pdks"
            headers = ["Name", "File"]
            rows = []
            if pdk_dir.is_dir():
                for f in sorted(pdk_dir.glob("*.pdk.json")):
                    pdk_name = f.name.replace(".pdk.json", "")
                    rows.append([pdk_name, f.name])
            print_table(headers, rows, title="Available PDKs")
            return

        if resource == "scenarios":
            from photonstrust.gallery import list_scenarios

            scenarios = list_scenarios()
            headers = ["Name", "Category", "Difficulty", "Title"]
            rows = []
            for s in scenarios:
                rows.append([s.name, s.category, s.difficulty, s.title])
            print_table(headers, rows, title="Available Scenarios")
            return

        if resource == "channels":
            headers = ["Channel"]
            rows = [["fiber"], ["free_space"], ["satellite"], ["underwater"]]
            print_table(headers, rows, title="Available Channels")
            return

    if args.command == "info":
        entity = str(args.entity).strip()

        # Try protocols first
        from photonstrust.qkd_protocols.common import normalize_protocol_name
        from photonstrust.qkd_protocols.registry import _PROTOCOLS

        normalized = normalize_protocol_name(entity)
        if normalized in _PROTOCOLS:
            mod = _PROTOCOLS[normalized]
            gp = mod.gate_policy or {}
            lines = [
                f"Protocol: {mod.protocol_id}",
                f"Aliases:  {', '.join(mod.aliases) if mod.aliases else '(none)'}",
                f"Gate Policy:",
                f"  PLOB bound: {gp.get('plob_repeaterless_bound', 'N/A')}",
                f"  Rationale:  {gp.get('rationale', 'N/A')}",
            ]
            print("\n".join(lines))
            return

        # Try detectors
        from photonstrust.presets import DETECTOR_PRESETS

        if entity.lower() in DETECTOR_PRESETS:
            det = DETECTOR_PRESETS[entity.lower()]
            lines = [
                f"Detector: {entity.lower()}",
                f"  PDE:              {det['pde']}",
                f"  Dark counts (cps): {det['dark_counts_cps']}",
                f"  Jitter (ps FWHM): {det['jitter_ps_fwhm']}",
                f"  Dead time (ns):   {det['dead_time_ns']}",
                f"  Afterpulsing:     {det.get('afterpulsing_prob', 'N/A')}",
            ]
            print("\n".join(lines))
            return

        # Try bands
        from photonstrust.presets import BAND_PRESETS

        if entity.lower() in BAND_PRESETS:
            band = BAND_PRESETS[entity.lower()]
            lines = [
                f"Band: {entity.lower()}",
                f"  Wavelength (nm):      {band['wavelength_nm']}",
                f"  Fiber loss (dB/km):   {band['fiber_loss_db_per_km']}",
                f"  Dispersion (ps/km):   {band['dispersion_ps_per_km']}",
            ]
            print("\n".join(lines))
            return

        print(f"Unknown entity: {entity!r}", file=sys.stderr)
        print("Try: photonstrust list protocols | photonstrust list detectors | photonstrust list bands",
              file=sys.stderr)
        raise SystemExit(1)

    if args.command == "demo":
        if args.scenario is None:
            # List available scenarios (same as list scenarios)
            from photonstrust.gallery import list_scenarios
            from photonstrust.cli_helpers import print_table

            scenarios = list_scenarios()
            headers = ["Name", "Category", "Difficulty", "Title"]
            rows = [[s.name, s.category, s.difficulty, s.title] for s in scenarios]
            print_table(headers, rows, title="Available Scenarios")
            return

        from photonstrust.gallery import run_scenario
        from photonstrust.cli_helpers import print_result_summary

        result = run_scenario(args.scenario)
        print_result_summary(result)
        return

    if args.command == "quickstart":
        interactive = not bool(args.non_interactive) and sys.stdin.isatty()

        if interactive:
            from photonstrust.cli_helpers import prompt_choice, prompt_float
            from photonstrust.qkd_protocols.registry import available_protocols
            from photonstrust.presets import BAND_PRESETS, DETECTOR_PRESETS

            protocol = prompt_choice(
                "Select a QKD protocol:",
                list(available_protocols()),
                default="bb84_decoy",
            )
            distance = prompt_float("Distance (km)", default=50.0)
            band = prompt_choice(
                "Select a wavelength band:",
                sorted(BAND_PRESETS.keys()),
                default="c_1550",
            )
            detector = prompt_choice(
                "Select a detector:",
                sorted(DETECTOR_PRESETS.keys()),
                default="snspd",
            )
        else:
            protocol = "bb84_decoy"
            distance = 50.0
            band = "c_1550"
            detector = "snspd"

        from photonstrust.easy import simulate_qkd_link
        from photonstrust.cli_helpers import print_result_summary

        result = simulate_qkd_link(
            protocol=protocol,
            distance_km=distance,
            band=band,
            detector=detector,
            include_uncertainty=False,
        )
        print_result_summary(result)

        if args.save:
            import yaml

            config = {
                "protocol": protocol,
                "distance_km": distance,
                "band": band,
                "detector": detector,
            }
            save_path = Path(args.save)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(yaml.dump(config, default_flow_style=False), encoding="utf-8")
            print(f"\nConfig saved to {save_path}")

        return

    # -- end Phase D handlers --------------------------------------------------

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


def _parse_float_values(raw_values: list[str] | None, *, default: list[float]) -> list[float]:
    if not raw_values:
        return list(default)

    out: list[float] = []
    for raw in raw_values:
        chunks = [part.strip() for part in str(raw).split(",")]
        for chunk in chunks:
            if not chunk:
                continue
            out.append(float(chunk))
    return out if out else list(default)


def _parse_text_values(raw_values: list[str] | None) -> list[str] | None:
    if not raw_values:
        return None

    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        chunks = [part.strip() for part in str(raw).split(",")]
        for chunk in chunks:
            if not chunk or chunk in seen:
                continue
            seen.add(chunk)
            out.append(chunk)
    return out or None


def _summarize_m3_checkpoint_result(result: object, *, output_dir: Path) -> dict:
    payload = result if isinstance(result, dict) else {}
    overall_status = str(payload.get("overall_status") or payload.get("status") or "UNKNOWN").strip().upper()
    qkd_status = None
    repeater_status = None

    qkd_pass_flags = payload.get("qkd_pass_flags")
    if not isinstance(qkd_pass_flags, dict):
        qkd_pass_flags = {}
        qkd_section = payload.get("qkd")
        if isinstance(qkd_section, dict):
            status_raw = qkd_section.get("status")
            if status_raw is not None:
                qkd_status = str(status_raw).strip().upper()
                qkd_pass_flags["status_pass"] = qkd_status == "PASS"

            bands = qkd_section.get("bands")
            if isinstance(bands, list):
                for row in bands:
                    if not isinstance(row, dict):
                        continue
                    scenario_id = str(row.get("scenario_id") or "").strip()
                    band = str(row.get("band") or "").strip()
                    if not scenario_id and not band:
                        continue
                    key = f"{scenario_id}:{band}".strip(":")
                    qkd_pass_flags[key] = str(row.get("status") or "").strip().upper() == "PASS"

    summary = payload.get("summary")
    if isinstance(summary, dict):
        all_qkd = summary.get("all_qkd_checks_pass")
        if isinstance(all_qkd, bool):
            qkd_pass_flags.setdefault("all_qkd_checks_pass", all_qkd)

    repeater_stability = payload.get("repeater_stability")
    if repeater_stability is None:
        repeater_section = payload.get("repeater")
        if isinstance(repeater_section, dict):
            status_raw = repeater_section.get("status")
            if status_raw is not None:
                repeater_status = str(status_raw).strip().upper()

            if "stability" in repeater_section:
                repeater_stability = repeater_section.get("stability")
            elif "stable" in repeater_section:
                repeater_stability = repeater_section.get("stable")
            elif "is_stable" in repeater_section:
                repeater_stability = repeater_section.get("is_stable")
            elif "distances" in repeater_section and isinstance(repeater_section.get("distances"), list):
                distances = repeater_section.get("distances") or []
                stable_flags = [bool(row.get("stable")) for row in distances if isinstance(row, dict)]
                if stable_flags:
                    repeater_stability = all(stable_flags)

    if repeater_stability is None and isinstance(summary, dict):
        stable_pass = summary.get("repeater_stability_pass")
        if isinstance(stable_pass, bool):
            repeater_stability = stable_pass

    output_path_raw = payload.get("output_path")
    if output_path_raw is None:
        output_path_raw = payload.get("output_dir")
    if output_path_raw is None and isinstance(payload.get("artifacts"), dict):
        output_path_raw = payload["artifacts"].get("output_dir")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "overall_status": overall_status,
        "output_path": output_path,
        "qkd_status": qkd_status,
        "repeater_status": repeater_status,
        "qkd_pass_flags": qkd_pass_flags,
        "repeater_stability": repeater_stability,
    }


def _normalize_corner_selection(raw_value: object) -> str | None:
    value = str(raw_value if raw_value is not None else "all").strip()
    if not value or value.lower() == "all":
        return None

    allowed = {"SS", "TT", "FF", "FS", "SF"}
    tokens: list[str] = []
    for part in value.split(","):
        token = part.strip().upper()
        if not token:
            continue
        if token == "ALL" and len(value.split(",")) == 1:
            return None
        if token not in allowed:
            allowed_text = ",".join(sorted(allowed))
            raise ValueError(f"Invalid --corners value {part!r}. Expected 'all' or subset of: {allowed_text}")
        if token not in tokens:
            tokens.append(token)

    return ",".join(tokens) if tokens else None


def _invoke_corner_sweep(
    run_fn: object,
    *,
    graph_path: Path,
    pdk_name: str,
    pdk_manifest_path: Path | None,
    protocol: str,
    target_distance_km: float,
    wavelength_nm: float,
    corner_set: str | None,
    n_monte_carlo: int,
    mc_seed: int,
    key_rate_threshold_bps: float,
    output_dir: Path,
) -> dict:
    if not callable(run_fn):
        raise TypeError("run_corner_sweep is not callable")

    try:
        sig = inspect.signature(run_fn)
        params = sig.parameters
    except (TypeError, ValueError):
        params = {}

    kwargs: dict[str, object] = {}

    def _set(names: tuple[str, ...], value: object) -> None:
        for name in names:
            if name in params:
                kwargs[name] = value
                return

    _set(("pdk_name", "pdk"), pdk_name)
    if pdk_manifest_path is not None:
        _set(("pdk_manifest_path", "pdk_manifest"), pdk_manifest_path)
    _set(("protocol",), protocol)
    _set(("target_distance_km", "target_distance"), float(target_distance_km))
    _set(("wavelength_nm", "wavelength"), float(wavelength_nm))
    if corner_set is not None:
        _set(("corner_set", "corners"), corner_set)
    _set(("n_monte_carlo", "monte_carlo"), int(n_monte_carlo))
    _set(("mc_seed",), int(mc_seed))
    _set(("key_rate_threshold_bps", "threshold_bps", "threshold"), float(key_rate_threshold_bps))
    _set(("output_dir", "output_path"), output_dir)

    try:
        result = run_fn(graph_path, **kwargs)
    except TypeError:
        if pdk_manifest_path is None:
            result = run_fn(
                graph_path,
                pdk_name=pdk_name,
                protocol=protocol,
                target_distance_km=float(target_distance_km),
                wavelength_nm=float(wavelength_nm),
                corner_set=corner_set,
                n_monte_carlo=int(n_monte_carlo),
                mc_seed=int(mc_seed),
                key_rate_threshold_bps=float(key_rate_threshold_bps),
                output_dir=output_dir,
            )
        else:
            result = run_fn(
                graph_path,
                pdk_name=pdk_name,
                pdk_manifest_path=pdk_manifest_path,
                protocol=protocol,
                target_distance_km=float(target_distance_km),
                wavelength_nm=float(wavelength_nm),
                corner_set=corner_set,
                n_monte_carlo=int(n_monte_carlo),
                mc_seed=int(mc_seed),
                key_rate_threshold_bps=float(key_rate_threshold_bps),
                output_dir=output_dir,
            )

    if not isinstance(result, dict):
        raise ValueError("run_corner_sweep returned a non-dict payload")
    return result


def _summarize_corner_sweep_result(result: object, *, output_dir: Path) -> dict:
    payload = result if isinstance(result, dict) else {}
    risk = payload.get("risk_assessment") if isinstance(payload.get("risk_assessment"), dict) else {}
    monte_carlo = payload.get("monte_carlo") if isinstance(payload.get("monte_carlo"), dict) else {}

    worst_corner = risk.get("worst_corner")
    if worst_corner is None:
        worst_corner = payload.get("worst_corner")

    worst_case_key_rate_bps = risk.get("worst_case_key_rate_bps")
    if worst_case_key_rate_bps is None:
        worst_case_key_rate_bps = payload.get("worst_case_key_rate_bps")

    risk_level = risk.get("risk_level")
    if risk_level is None:
        risk_level = payload.get("risk_level")

    yield_above_threshold = risk.get("yield_above_threshold")
    if yield_above_threshold is None:
        yield_above_threshold = monte_carlo.get("yield_above_threshold")
    if yield_above_threshold is None:
        yield_above_threshold = monte_carlo.get("yield_fraction")
    if yield_above_threshold is None:
        yield_above_threshold = payload.get("yield_above_threshold")

    output_path_raw = payload.get("output_path")
    if output_path_raw is None:
        output_path_raw = payload.get("output_dir")
    artifacts = payload.get("artifacts")
    if output_path_raw is None and isinstance(artifacts, dict):
        output_path_raw = artifacts.get("output_dir")
        if output_path_raw is None:
            output_path_raw = artifacts.get("report_path")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "output_path": output_path,
        "risk_level": risk_level,
        "worst_case_key_rate_bps": worst_case_key_rate_bps,
        "worst_corner": worst_corner,
        "yield_above_threshold": yield_above_threshold,
    }


def _summarize_satellite_chain_result(result: object, *, output_dir: Path) -> dict:
    payload = result if isinstance(result, dict) else {}
    cert = payload.get("certificate") if isinstance(payload.get("certificate"), dict) else {}
    signoff = cert.get("signoff") if isinstance(cert.get("signoff"), dict) else {}
    pass_section = cert.get("pass") if isinstance(cert.get("pass"), dict) else {}

    decision = signoff.get("decision")
    if decision is None:
        decision = payload.get("decision")
    if decision is None:
        decision = "HOLD"

    key_bits = pass_section.get("key_bits_accumulated")
    mean_rate = pass_section.get("mean_key_rate_bps")

    output_path_raw = payload.get("output_path")
    if output_path_raw is None:
        output_path_raw = cert.get("output_path")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "decision": str(decision).strip().upper(),
        "key_bits_accumulated": key_bits,
        "mean_key_rate_bps": mean_rate,
        "output_path": output_path,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        if hasattr(exc, "suggestion"):
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1)
        raise

