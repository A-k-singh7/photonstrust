import time
import numpy as np

try:
    import photonstrust_rs
    has_rust = True
except ImportError:
    has_rust = False

from photonstrust.physics.detector import _process_events_heap_legacy

def run_benchmark():
    n_signal = 100_000
    n_dark = 50_000
    window_ps = 1_000_000.0
    dead_time_ps = 10_000.0
    afterpulse_prob = 0.05
    afterpulse_delay_ps = 50_000.0
    jitter_ps = 100.0

    print(f"Generating {n_signal} signal and {n_dark} dark events...")
    rng = np.random.default_rng(42)
    signal_events = rng.uniform(0, window_ps, size=n_signal).tolist()
    dark_events = rng.uniform(0, window_ps, size=n_dark).tolist()
    rng = np.random.default_rng(17)

    print("Running pure Python fallback (_process_events_heap_legacy without rust interception)...")
    import sys
    if "photonstrust_rs" in sys.modules:
        rs_mod = sys.modules.pop("photonstrust_rs")
    
    start_t = time.time()
    for _ in range(10):
        clicks, false, processed = _process_events_heap_legacy(
            signal_events.copy(),
            dark_events.copy(),
            dead_time_ps,
            afterpulse_prob,
            afterpulse_delay_ps,
            jitter_ps,
            rng
        )
    end_t = time.time()
    py_time = (end_t - start_t) / 10.0
    print(f"Python time per eval: {py_time * 1000:.2f} ms")


    if has_rust:
        sys.modules["photonstrust_rs"] = rs_mod
        print("Running Rust PyO3 implementation...")
        start_t = time.time()
        for _ in range(10):
            clicks_rs, false_rs, processed_rs = _process_events_heap_legacy(
                signal_events.copy(),
                dark_events.copy(),
                dead_time_ps,
                afterpulse_prob,
                afterpulse_delay_ps,
                jitter_ps,
                rng
            )
        end_t = time.time()
        rs_time = (end_t - start_t) / 10.0
        print(f"Rust time per eval:   {rs_time * 1000:.2f} ms")
        
        speedup = py_time / rs_time
        print(f"Speedup: {speedup:.2f}x")

if __name__ == '__main__':
    run_benchmark()
