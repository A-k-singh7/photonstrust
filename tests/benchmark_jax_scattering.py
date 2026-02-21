import time
import jax
import jax.numpy as jnp
from photonstrust.pic.simulate import simulate_pic_netlist

jax.config.update("jax_enable_x64", True)

def run_benchmark():
    # Setup: a simple MZI
    base_netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "benchmark_mzi",
        "circuit": {
            "id": "benchmark_mzi",
            "wavelength_nm": 1550.0,
            "solver": "scattering",
            "inputs": [{"node": "cpl_in", "port": "in1", "amplitude": 1.0}],
            "outputs": [{"node": "cpl_out", "port": "out1"}, {"node": "cpl_out", "port": "out2"}],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2"},
        ],
    }

    n_runs = 500
    
    # Warmup
    simulate_pic_netlist(base_netlist)

    print(f"Running {n_runs} sequential evaluations of the JAX scattering solver...")
    start_t = time.time()
    for i in range(n_runs):
        base_netlist["nodes"][2]["params"]["phase_rad"] = float(i) / n_runs * jnp.pi
        simulate_pic_netlist(base_netlist)
    end_t = time.time()
    
    elapsed = end_t - start_t
    print(f"Total time for {n_runs} simulations: {elapsed:.4f} seconds")
    print(f"Time per eval: {(elapsed / n_runs) * 1000:.4f} ms")


if __name__ == "__main__":
    run_benchmark()
