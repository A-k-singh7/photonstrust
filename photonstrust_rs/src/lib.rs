use pyo3::prelude::*;
use std::collections::BinaryHeap;
use std::cmp::Ordering;
use rand::Rng;
use rand::RngExt;
use rand::rngs::StdRng;
use rand::SeedableRng;
use rand_distr::{Normal, Distribution};
use rayon::prelude::*;

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

#[pyfunction]
fn estimate_process_yield_rs(
    nominals: Vec<f64>,
    sigmas: Vec<f64>,
    mins: Vec<f64>,
    maxes: Vec<f64>,
    samples: usize,
    seed: u64,
    cov_cholesky: Option<Vec<Vec<f64>>>,
    active_idx: Option<Vec<usize>>,
) -> PyResult<f64> {
    let is_correlated = cov_cholesky.is_some() && active_idx.is_some();
    let num_metrics = nominals.len();

    let pass_count: usize = (0..samples)
        .into_par_iter()
        .map(|i| {
            // Seed uniquely per sample
            let mut rng = StdRng::seed_from_u64(seed.wrapping_add(i as u64));
            let mut sample_pass = true;

            if is_correlated {
                let cov = cov_cholesky.as_ref().unwrap();
                let active = active_idx.as_ref().unwrap();
                let normal = Normal::new(0.0, 1.0).unwrap();

                let mut z = Vec::with_capacity(active.len());
                for _ in 0..active.len() {
                    z.push(normal.sample(&mut rng));
                }

                let mut x = nominals.clone();
                for (i_sub, &idx) in active.iter().enumerate() {
                    let mut delta = 0.0;
                    for k in 0..=i_sub {
                        delta += cov[i_sub][k] * z[k];
                    }
                    x[idx] += delta;
                }

                for j in 0..num_metrics {
                    if x[j] < mins[j] || x[j] > maxes[j] {
                        sample_pass = false;
                        break;
                    }
                }
            } else {
                for j in 0..num_metrics {
                    let mut x_val = nominals[j];
                    if sigmas[j] > 0.0 {
                        let normal = Normal::new(nominals[j], sigmas[j]).unwrap();
                        x_val = normal.sample(&mut rng);
                    }
                    if x_val < mins[j] || x_val > maxes[j] {
                        sample_pass = false;
                        break;
                    }
                }
            }
            if sample_pass { 1 } else { 0 }
        })
        .sum();

    let yield_mc = (pass_count as f64) / f64::max(1.0, samples as f64);
    Ok(yield_mc)
}

#[pymodule]
fn photonstrust_rs(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_events_heap_rs, m)?)?;
    m.add_function(wrap_pyfunction!(estimate_process_yield_rs, m)?)?;
    Ok(())
}
