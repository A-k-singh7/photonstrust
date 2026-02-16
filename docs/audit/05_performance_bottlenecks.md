# 05 - Performance Bottlenecks & Optimizations

---

## Research Anchors (Implementation References)

- `concurrent.futures.ProcessPoolExecutor` (Python stdlib): https://docs.python.org/3/library/concurrent.futures.html
- `graphlib.TopologicalSorter` (Python stdlib, 3.9+): https://docs.python.org/3/library/graphlib.html
- `functools.lru_cache` (Python stdlib): https://docs.python.org/3/library/functools.html#functools.lru_cache
- joblib parallelization patterns: https://joblib.readthedocs.io/
- FastAPI background tasks (non-blocking API endpoints): https://fastapi.tiangolo.com/tutorial/background-tasks/

## Bottleneck 1: Uncertainty computation is serial

**Location:** `photonstrust/qkd.py:248-278`

```python
for _ in range(samples):        # 200-400 iterations
    varied = _apply_uncertainty(base, uncertainty, rng)
    for distance in distances:  # N distances per iteration
        compute_point(varied, distance, ...)
```

**Impact:** Certification mode runs 400 samples x N distances. Each
`compute_point()` call is independent. On a 4-core machine, this is ~4x slower
than necessary.

**Correction:**

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def _compute_uncertainty(scenario, samples=200, runtime_overrides=None):
    uncertainty = scenario.get("uncertainty", {})
    if not uncertainty:
        return None

    distances = scenario["distances_km"]
    seed_base = int(scenario.get("uncertainty", {}).get("seed", 42))

    def _run_sample(sample_idx):
        rng = np.random.default_rng(seed_base + sample_idx)
        varied = _apply_uncertainty(scenario, uncertainty, rng)
        return {
            d: compute_point(varied, d, runtime_overrides=runtime_overrides).key_rate_bps
            for d in distances
        }

    key_rate_samples = {d: [] for d in distances}

    # Use ProcessPoolExecutor for CPU-bound work.
    # Fall back to serial if pool creation fails (e.g., in tests).
    max_workers = min(4, samples)
    try:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_sample, i) for i in range(samples)]
            for f in as_completed(futures):
                result = f.result()
                for d, rate in result.items():
                    key_rate_samples[d].append(rate)
    except Exception:
        # Fallback to serial
        for i in range(samples):
            result = _run_sample(i)
            for d, rate in result.items():
                key_rate_samples[d].append(rate)

    # ... rest of CI computation unchanged
```

**Expected speedup:** 2-3x on typical 4-core machines. 4x on 8-core.

**Alternative (simpler):** Use `joblib` which handles serialization better:

```python
from joblib import Parallel, delayed

results = Parallel(n_jobs=-1)(
    delayed(_run_sample)(i) for i in range(samples)
)
```

This requires adding `joblib` to dev dependencies.

---

## Bottleneck 2: Detector simulation uses heap for small event lists

**Location:** `photonstrust/physics/detector.py:47-79`

```python
for t in gated_arrivals:
    if rng.random() <= pde_eff:
        heapq.heappush(events, (t + rng.normal(0.0, jitter_ps), "signal"))

# ... dark counts also pushed to heap
while events:
    t, origin = heapq.heappop(events)
```

**Impact:** For typical sample counts (500 arrivals), the heap adds O(n log n)
overhead. With < 100 events, a simple sorted list is faster.

**Correction:**

```python
# Replace heap with numpy vectorized approach for the common case.

def _simulate_fast_path(gated_arrivals, pde_eff, jitter_ps, dark_mean,
                        window_min, window_max, rng):
    """Vectorized detector simulation for the common (no-afterpulse) case."""
    # Signal detections
    mask = rng.random(len(gated_arrivals)) <= pde_eff
    signal_times = np.array(gated_arrivals)[mask] + rng.normal(0, jitter_ps, mask.sum())

    # Dark counts
    n_dark = rng.poisson(dark_mean)
    dark_times = rng.uniform(window_min, window_max, n_dark)

    # Merge and sort
    all_times = np.concatenate([signal_times, dark_times])
    origins = np.concatenate([
        np.ones(len(signal_times), dtype=bool),    # True = signal
        np.zeros(len(dark_times), dtype=bool),      # False = dark
    ])
    order = np.argsort(all_times)
    return all_times[order], origins[order]
```

Keep the heap-based path for cases with afterpulsing (where new events are
generated during processing).

**Expected speedup:** 3-5x for non-afterpulse scenarios.

---

## Bottleneck 3: Graph compiler topological sort

**Location:** `photonstrust/graph/compiler.py`

**Impact:** Uses naive recursive algorithm. O(N^2) worst case. Acceptable for
typical graphs (< 100 nodes) but could be a bottleneck for large PIC netlists.

**Correction:** Use `graphlib.TopologicalSorter` (stdlib, Python 3.9+):

```python
from graphlib import TopologicalSorter

def _topological_order(nodes, edges):
    ts = TopologicalSorter()
    for edge in edges:
        ts.add(edge["target"], edge["source"])
    return list(ts.static_order())
```

---

## Bottleneck 4: API server blocks on computation

**Location:** `photonstrust/api/server.py`

**Issue:** All endpoints are synchronous. A single long-running orbit
simulation blocks the entire server.

**Correction:** Use FastAPI's `BackgroundTasks` for compute endpoints:

```python
from fastapi import BackgroundTasks
from uuid import uuid4

_jobs: dict[str, dict] = {}

@app.post("/api/run")
async def run_simulation(config: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    _jobs[job_id] = {"status": "running", "result": None}
    background_tasks.add_task(_run_job, job_id, config)
    return {"job_id": job_id, "status": "running"}

@app.get("/api/run/{job_id}")
async def get_result(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

def _run_job(job_id: str, config: dict):
    try:
        scenarios = build_scenarios(config)
        results = [compute_sweep(s) for s in scenarios]
        _jobs[job_id] = {"status": "completed", "result": results}
    except Exception as e:
        _jobs[job_id] = {"status": "failed", "error": str(e)}
```

For production, replace the in-memory `_jobs` dict with Redis or a task queue
(Celery, ARQ).

---

## Bottleneck 5: No caching for deterministic computations

**Issue:** Graph compilation is deterministic (same JSON input = same output).
Repeated API calls recompile identical graphs.

**Correction:** Add hash-based memoization:

```python
from functools import lru_cache
from photonstrust.utils import hash_dict

@lru_cache(maxsize=128)
def _compile_cached(config_hash: str, config_json: str):
    import json
    config = json.loads(config_json)
    return _compile_graph_impl(config)

def compile_graph(config: dict):
    config_json = json.dumps(config, sort_keys=True)
    config_hash = hash_dict(config)
    return _compile_cached(config_hash, config_json)
```

---

## Summary

| Bottleneck | Location | Current | After fix | Effort |
|------------|----------|---------|-----------|--------|
| Uncertainty sampling | qkd.py:248 | Serial (400 iters) | Parallel (4x) | Medium |
| Detector heap | detector.py:47 | O(n log n) | O(n) vectorized | Medium |
| Topo sort | compiler.py | O(N^2) | O(N+E) stdlib | Low |
| Blocking API | api/server.py | Synchronous | Async + background | Medium |
| No caching | api/server.py | Recompute always | LRU cache | Low |
