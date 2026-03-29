export const DEFAULT_API_BASE = import.meta.env.VITE_PHOTONTRUST_API_BASE_URL || "http://127.0.0.1:8000";
export const DEFAULT_LANDING_PROJECT_ID = "pilot_demo";
export const DEFAULT_LANDING_DEMO_CASE_ID = "bbm92_metro_50km";

export const DEFAULT_QKD_SCENARIO = {
  id: "ui_qkd_link",
  distance_km: 10,
  band: "c_1550",
  wavelength_nm: 1550,
  execution_mode: "preview",
};

export const DEFAULT_PIC_CIRCUIT = {
  id: "ui_pic_circuit",
  wavelength_nm: 1550,
};

export const DEFAULT_ORBIT_PASS_CONFIG = {
  orbit_pass: {
    id: "ui_orbit_pass_envelope",
    band: "c_1550",
    dt_s: 30,
    samples: [
      { t_s: 0, distance_km: 1200, elevation_deg: 20, background_counts_cps: 5000 },
      { t_s: 30, distance_km: 900, elevation_deg: 40, background_counts_cps: 2000 },
      { t_s: 60, distance_km: 600, elevation_deg: 70, background_counts_cps: 300 },
      { t_s: 90, distance_km: 900, elevation_deg: 40, background_counts_cps: 2000 },
      { t_s: 120, distance_km: 1200, elevation_deg: 20, background_counts_cps: 5000 },
    ],
    cases: [
      {
        id: "best",
        label: "Best case (night-like, low turbulence)",
        channel_overrides: {
          atmospheric_extinction_db_per_km: 0.01,
          pointing_jitter_urad: 1.0,
          turbulence_scintillation_index: 0.08,
          background_counts_cps_scale: 0.3,
        },
      },
      { id: "median", label: "Median", channel_overrides: {} },
      {
        id: "worst",
        label: "Worst case (day-like, high turbulence)",
        channel_overrides: {
          atmospheric_extinction_db_per_km: 0.05,
          pointing_jitter_urad: 3.0,
          turbulence_scintillation_index: 0.25,
          background_counts_cps_scale: 2.0,
        },
      },
    ],
  },
  source: {
    type: "emitter_cavity",
    physics_backend: "analytic",
    rep_rate_mhz: 150,
    collection_efficiency: 0.38,
    coupling_efficiency: 0.62,
    radiative_lifetime_ns: 1.0,
    purcell_factor: 5,
    dephasing_rate_per_ns: 0.5,
    g2_0: 0.02,
    pulse_window_ns: 5.0,
  },
  channel: {
    model: "free_space",
    connector_loss_db: 1.0,
    dispersion_ps_per_km: 0.0,
    tx_aperture_m: 0.12,
    rx_aperture_m: 0.3,
    beam_divergence_urad: 12.0,
    pointing_jitter_urad: 1.5,
    atmospheric_extinction_db_per_km: 0.02,
    turbulence_scintillation_index: 0.15,
    background_counts_cps: 0.0,
    elevation_deg: 45.0,
  },
  detector: {
    class: "snspd",
    pde: 0.3,
    dark_counts_cps: 100,
    jitter_ps_fwhm: 30,
    dead_time_ns: 100,
    afterpulsing_prob: 0.001,
  },
  timing: {
    sync_drift_ps_rms: 10,
    coincidence_window_ps: 250,
  },
  protocol: {
    name: "BBM92",
    sifting_factor: 0.5,
    ec_efficiency: 1.16,
  },
  uncertainty: {},
};

export const GUIDED_GLOSSARY_TERMS = [
  {
    term: "QBER",
    meaning: "Quantum bit error rate. Lower values generally indicate cleaner key generation conditions.",
  },
  {
    term: "Key rate",
    meaning: "Estimated secure key bits per second produced by a run.",
  },
  {
    term: "Baseline",
    meaning: "Reference run used for candidate comparison and promotion decisions.",
  },
  {
    term: "Reliability card",
    meaning: "Decision artifact summarizing assumptions, outputs, and trust posture.",
  },
  {
    term: "Evidence bundle",
    meaning: "Portable run package for integrity verification, audit, and review.",
  },
];

export const GUIDED_FLOW_VERSION = "2026-03-guided-power-v1";

export const GUIDED_STEP_ITEMS = [
  { id: "api_health", label: "Check API health" },
  { id: "first_run", label: "Run first simulation" },
  { id: "compare", label: "Compare baseline vs candidate" },
  { id: "decision", label: "Review decision and blockers" },
];

export const ROLE_PRESET_OPTIONS = [
  { id: "builder", label: "Builder" },
  { id: "reviewer", label: "Reviewer" },
  { id: "exec", label: "Exec" },
];

export const DEMO_SCENE_PLANS = {
  benchmark: {
    scene: "benchmark",
    stage: "compare",
    mode: "runs",
    tab: "diff",
    statusText: "Demo scene: Benchmark. Compare baseline and candidate outcomes.",
  },
  trust: {
    scene: "trust",
    stage: "certify",
    mode: "runs",
    tab: "manifest",
    statusText: "Demo scene: Trust. Review provenance and certification posture.",
  },
  decision: {
    scene: "decision",
    stage: "run",
    mode: "graph",
    tab: "run",
    statusText: "Demo scene: Decision. Present recommendation and confidence framing.",
  },
  packet: {
    scene: "packet",
    stage: "export",
    mode: "runs",
    tab: "manifest",
    statusText: "Demo scene: Packet. Export meeting-ready evidence.",
  },
};
