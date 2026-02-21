use pyo3::prelude::*;
use std::collections::BinaryHeap;
use std::cmp::Ordering;
use rand::Rng;
use rand::RngExt;
use rand::rngs::StdRng;
use rand::SeedableRng;
use rand_distr::{Normal, Distribution};

#[derive(PartialEq)]
enum Origin {
    Signal,
    Dark,
    Afterpulse,
}

#[derive(PartialEq)]
struct SimEvent {
    time_ps: f64,
    origin: Origin,
}

// BinaryHeap is a max-heap by default, so we reverse the ordering to get a min-heap (earliest time first).
impl Ord for SimEvent {
    fn cmp(&self, other: &Self) -> Ordering {
        // Rust's f64 doesn't implement Ord due to NaN. We assume valid times here.
        other.time_ps.partial_cmp(&self.time_ps).unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for SimEvent {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Eq for SimEvent {}

/// Rust implementation of the legacy heap event solver, avoiding Python object overhead.
#[pyfunction]
fn process_events_heap_rs(
    signal_events: Vec<f64>,
    dark_events: Vec<f64>,
    dead_time_ps: f64,
    afterpulse_prob: f64,
    afterpulse_delay_ps: f64,
    jitter_ps: f64,
    seed: u64,
) -> PyResult<(Vec<f64>, usize, usize)> {

    let mut events = BinaryHeap::new();
    
    // Seed RNG
    let mut rng = StdRng::seed_from_u64(seed);
    
    // Using simple Gaussian dist
    let ap_jitter = f64::max(1.0, jitter_ps * 0.25);
    let normal = if ap_jitter > 0.0 {
        Normal::new(0.0, ap_jitter).unwrap()
    } else {
        Normal::new(0.0, 1.0).unwrap()
    };

    for &t in &signal_events {
        events.push(SimEvent { time_ps: t, origin: Origin::Signal });
    }
    for &t in &dark_events {
        events.push(SimEvent { time_ps: t, origin: Origin::Dark });
    }

    let mut clicks: Vec<f64> = Vec::with_capacity(signal_events.len());
    let mut false_clicks = 0;
    let mut last_click = -1e18;
    let mut processed = 0;

    while let Some(event) = events.pop() {
        processed += 1;
        
        if dead_time_ps > 0.0 && (event.time_ps - last_click) < dead_time_ps {
            continue;
        }
        
        clicks.push(event.time_ps);
        last_click = event.time_ps;
        
        if event.origin != Origin::Signal {
            false_clicks += 1;
        }

        if afterpulse_prob > 0.0 && rng.random_range(0.0..1.0) <= afterpulse_prob {
            let offset = if ap_jitter > 0.0 { normal.sample(&mut rng) } else { 0.0 };
            events.push(SimEvent {
                time_ps: event.time_ps + afterpulse_delay_ps + offset,
                origin: Origin::Afterpulse,
            });
        }
    }

    Ok((clicks, false_clicks, processed))
}

#[pymodule]
fn photonstrust_rs(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_events_heap_rs, m)?)?;
    Ok(())
}
