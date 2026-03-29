import streamlit as st
import json
import traceback
import numpy as np
from pathlib import Path

st.set_page_config(
    page_title="PhotonTrust Designer",
    page_icon="photon",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
body { font-family: 'Inter', sans-serif; }
.metric-label { font-size: 0.8rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.title("PhotonTrust v3 Designer")
st.caption("Visual AI-accelerated layout analysis and Performance DRC integration.")

# ── Session state ─────────────────────────────────────────────
if "netlist" not in st.session_state:
    st.session_state.netlist = None

# ── Sidebar – Workspace ───────────────────────────────────────
with st.sidebar:
    st.header("Workspace")
    uploaded = st.file_uploader("Upload Circuit Netlist (.json)", type=["json"])
    if uploaded:
        try:
            st.session_state.netlist = json.loads(uploaded.read())
            st.success("Netlist loaded!")
        except Exception as exc:
            st.error(f"Parse error: {exc}")

    if st.session_state.netlist:
        st.divider()
        if st.checkbox("Show raw JSON"):
            st.json(st.session_state.netlist)

# ── Topology Viewer ───────────────────────────────────────────
if st.session_state.netlist:
    with st.expander("Circuit Topology", expanded=True):
        try:
            from streamlit_agraph import agraph, Node, Edge, Config
            circuit = st.session_state.netlist.get("circuit", {})
            KIND_COLOR = {
                "source": "#e74c3c",
                "coupler": "#3498db",
                "splitter": "#2ecc71",
                "detector": "#9b59b6",
                "phase_shift": "#f39c12",
                "waveguide": "#95a5a6",
            }
            ag_nodes = [
                Node(
                    id=n["id"], label=n["id"], size=20,
                    color=KIND_COLOR.get(n.get("kind", ""), "#3498db"),
                )
                for n in circuit.get("nodes", [])
            ]
            ag_edges = [
                Edge(source=e["from"], target=e["to"],
                     label=f"{e['from_port']}\u2192{e['to_port']}")
                for e in circuit.get("edges", [])
            ]
            if ag_nodes:
                agraph(nodes=ag_nodes, edges=ag_edges,
                       config=Config(width=900, height=350, directed=True,
                                     nodeHighlightBehavior=True, highlightColor="#f1c40f"))
            else:
                st.info("No nodes found in the loaded netlist.")
        except ImportError:
            st.warning("Install `streamlit-agraph` for the topology visualiser: `pip install streamlit-agraph`")

st.divider()

# ── Main Tabs ─────────────────────────────────────────────────
drc_tab, sweep_tab, invdes_tab, yield_tab = st.tabs([
    "Performance DRC",
    "Wavelength Sweep",
    "Inverse Design",
    "Process Yield",
])

# ── Tab 1: Performance DRC ────────────────────────────────────
with drc_tab:
    st.subheader("Crosstalk Margin Check")
    c1, c2, c3, c4 = st.columns(4)
    gap        = c1.number_input("Gap (um)", value=1.0, step=0.1, format="%.2f")
    length     = c2.number_input("Length (um)", value=100.0, step=10.0)
    wavelength = c3.number_input("Wavelength (nm)", value=1550.0, step=5.0)
    target_xt  = c4.slider("Target XT (dB)", min_value=-60, max_value=-10, value=-30)

    if st.button("Run DRC", type="primary"):
        try:
            from photonstrust import sdk as pt
            with st.spinner("Checking physics constraints..."):
                xt   = pt.predict_crosstalk(gap_um=gap, length_um=length, wavelength_nm=wavelength)
                mgap = pt.min_gap_for_crosstalk(target_xt_db=target_xt, length_um=length, wavelength_nm=wavelength)
            passed = xt <= target_xt
            m1, m2, m3 = st.columns(3)
            m1.metric("Predicted Crosstalk", f"{xt:.2f} dB",
                      delta=f"{xt - target_xt:+.2f} dB vs target", delta_color="inverse")
            m2.metric("Recommended Min Gap", f"{mgap:.3f} µm")
            m3.metric("DRC Status", "PASS ✅" if passed else "FAIL ❌",
                      delta=None)
            if passed:
                st.success("All routing margins are within spec.")
            else:
                st.error("Crosstalk exceeds the spec. Increase gap or reduce coupling length.")
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.code(traceback.format_exc())

# ── Tab 2: Wavelength Sweep ───────────────────────────────────
with sweep_tab:
    st.subheader("Transmission vs Wavelength")

    if not st.session_state.netlist:
        st.info("Upload a netlist in the sidebar first.")
    else:
        wl_min = st.number_input("Start wavelength (nm)", value=1480.0, step=5.0)
        wl_max = st.number_input("End wavelength (nm)", value=1580.0, step=5.0)
        wl_pts = st.slider("Number of points", min_value=10, max_value=200, value=50)

        if st.button("Run Sweep", type="primary"):
            wls = list(np.linspace(wl_min, wl_max, int(wl_pts)))
            try:
                from photonstrust import sdk as pt
                import pandas as pd
                with st.spinner(f"Simulating {len(wls)} wavelengths..."):
                    sweep_results = pt.simulate_netlist_sweep(
                        st.session_state.netlist,
                        wavelengths_nm=wls,
                    )

                # Build power table from outputs
                all_rows = []
                for res in sweep_results:
                    wl_res = res.get("wavelength_nm", None)
                    for out in res.get("outputs", []):
                        all_rows.append({
                            "wavelength_nm": wl_res,
                            "port": f"{out.get('node')}.{out.get('port')}",
                            "power_dB": out.get("power_dB", None),
                        })

                if all_rows:
                    df = pd.DataFrame(all_rows)
                    st.line_chart(df.pivot(index="wavelength_nm", columns="port", values="power_dB"))
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("Simulation returned no output ports. Check the netlist outputs field.")
            except Exception as exc:
                st.error(f"Sweep failed: {exc}")
                st.code(traceback.format_exc())

# ── Tab 3: Inverse Design ─────────────────────────────────────
with invdes_tab:
    st.subheader("JAX Gradient-Based Inverse Design")
    st.markdown("""
    Adjust a **target transmission** and let JAX trace gradients back through the
    scattering matrix solver to find the optimum parameter values automatically.
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        target_power_db = st.slider("Target output power (dB)", min_value=-30.0, max_value=0.0,
                                    value=-3.0, step=0.5,
                                    help="The desired transmission at the output port.")
        n_steps = st.number_input("Optimisation steps", value=30, min_value=5, max_value=200)
        lr = st.number_input("Learning rate", value=0.05, format="%.4f")

    with col_b:
        st.markdown("#### What the optimiser changes")
        st.info(
            "Currently sweeps the **waveguide coupling coefficient** (κ) of the first coupler "
            "node in the loaded netlist using JAX autodiff + gradient descent.",
            icon="ℹ️"
        )
        opt_param = st.selectbox("Parameter to optimise", ["coupling_ratio", "phase_bias_rad"])

    if not st.session_state.netlist:
        st.warning("Upload a netlist in the sidebar to enable this feature.")
    elif st.button("Optimise", type="primary"):
        try:
            import jax
            import jax.numpy as jnp
            from photonstrust.pic.simulate import simulate_pic_netlist_jax

            netlist = st.session_state.netlist
            target = 10 ** (target_power_db / 10.0)   # linear

            log_area = st.empty()
            prog = st.progress(0)

            # Find coupler node
            nodes = netlist.get("circuit", {}).get("nodes", [])
            coupler_ids = [n["id"] for n in nodes if "coupler" in n.get("kind", "")]
            if not coupler_ids:
                st.error("No coupler node found in netlist to optimise.")
            else:
                cid = coupler_ids[0]

                @jax.jit
                def loss_fn(param):
                    nt = dict(netlist)
                    # Inject parameter into circuit
                    modified_nodes = []
                    for n in netlist["circuit"]["nodes"]:
                        nd = dict(n)
                        if nd["id"] == cid:
                            nd = dict(nd)
                            nd["params"] = dict(nd.get("params", {}))
                            nd["params"][opt_param] = float(param)
                        modified_nodes.append(nd)
                    nt = {**netlist, "circuit": {**netlist["circuit"], "nodes": modified_nodes}}
                    result = simulate_pic_netlist_jax(nt)
                    outputs = result.get("outputs", [])
                    if not outputs:
                        return jnp.array(1.0)
                    power_lin = jnp.array(10 ** (outputs[0].get("power_dB", -100) / 10.0))
                    return (power_lin - target) ** 2

                grad_fn = jax.grad(loss_fn)

                # Initial guess
                init_nodes = [n for n in nodes if n["id"] == cid]
                param = jnp.array(
                    float(init_nodes[0].get("params", {}).get(opt_param, 0.5))
                )

                history_loss = []
                history_param = []
                for step in range(int(n_steps)):
                    g = grad_fn(param)
                    param = param - lr * g
                    param = jnp.clip(param, 0.0, 1.0)
                    lv = float(loss_fn(param))
                    history_loss.append(lv)
                    history_param.append(float(param))
                    prog.progress((step + 1) / int(n_steps))
                    log_area.code(
                        f"Step {step+1:3d}/{int(n_steps)} | {opt_param}={float(param):.4f} | loss={lv:.6f}"
                    )

                import pandas as pd
                st.success(f"Optimised {opt_param} = **{float(param):.4f}** (loss={history_loss[-1]:.6f})")
                df_hist = pd.DataFrame({"step": range(len(history_loss)), "loss": history_loss, opt_param: history_param})
                st.line_chart(df_hist.set_index("step")[["loss"]])

        except ImportError as exc:
            st.error(f"JAX not available: {exc}. Install with `pip install jax`.")
        except Exception as exc:
            st.error(f"Optimisation failed: {exc}")
            st.code(traceback.format_exc())

# ── Tab 4: Process Yield ─────────────────────────────────────
with yield_tab:
    st.subheader("Monte Carlo Process Yield Estimation")
    st.markdown("Define process variation metrics and run Rust-accelerated Monte Carlo.")

    default_metrics = json.dumps([
        {"name": "width_nm", "nominal": 500, "sigma": 5.0, "sensitivity": 1.0,
         "min_allowed": 488, "max_allowed": 512},
        {"name": "etch_depth_nm", "nominal": 220, "sigma": 3.0, "sensitivity": 0.8,
         "min_allowed": 213, "max_allowed": 227},
    ], indent=2)

    metrics_str = st.text_area("Process metrics (JSON)", value=default_metrics, height=200)
    mc_col1, mc_col2 = st.columns(2)
    mc_samples = mc_col1.number_input("MC samples", value=10_000, step=1000)
    min_yield  = mc_col2.slider("Min required yield", 0.5, 0.999, 0.9, step=0.01)

    if st.button("Estimate Yield", type="primary"):
        try:
            metrics = json.loads(metrics_str)
            from photonstrust import sdk as pt
            with st.spinner(f"Running {mc_samples:,} Monte Carlo trials (Rust-accelerated)..."):
                res = pt.estimate_yield(metrics, mc_samples=int(mc_samples), min_required_yield=float(min_yield))

            y_val = res.get("estimated_yield", 0)
            y_pass = res.get("pass", False)
            ya, yb = st.columns(2)
            ya.metric("Estimated Yield", f"{y_val:.2%}", delta="PASS ✅" if y_pass else "FAIL ❌",
                      delta_color="normal" if y_pass else "inverse")
            yb.metric("Required Yield", f"{float(min_yield):.2%}")

            st.json({k: v for k, v in res.items() if k not in ("points",)})
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON in metrics: {exc}")
        except Exception as exc:
            st.error(f"Yield estimation failed: {exc}")
            st.code(traceback.format_exc())
