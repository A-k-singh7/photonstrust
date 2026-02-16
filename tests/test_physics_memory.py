from photonstrust.physics.memory import simulate_memory


def test_memory_decay_monotonic():
    cfg = {
        "t1_ms": 50,
        "t2_ms": 10,
        "retrieval_efficiency": 0.8,
        "physics_backend": "analytic",
    }
    short = simulate_memory(cfg, wait_time_ns=1e3)
    long = simulate_memory(cfg, wait_time_ns=1e9)
    assert long.fidelity <= short.fidelity
