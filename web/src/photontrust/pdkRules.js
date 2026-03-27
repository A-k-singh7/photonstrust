export const PDK_LIST = [
  { id: "generic_si", name: "Generic Silicon (220nm SOI)" },
  { id: "generic_sin", name: "Generic SiN (400nm)" },
  { id: "imec_isipp50g", name: "IMEC iSiPP50G" },
];

export const PDK_RULES = {
  generic_si: {
    "pic.waveguide": {
      length_um: { min: 1, max: 50000, unit: "\u03BCm" },
      loss_db_per_cm: { min: 0.5, max: 5.0, unit: "dB/cm" },
    },
    "pic.coupler": {
      coupling_ratio: { min: 0.01, max: 0.99 },
      insertion_loss_db: { min: 0.05, max: 1.0, unit: "dB" },
    },
    "pic.mzm": {
      phase_shifter_length_mm: { min: 0.5, max: 10.0, unit: "mm" },
      V_pi_L_pi_Vcm: { min: 1.0, max: 4.0, unit: "V\u00B7cm" },
      insertion_loss_db: { min: 2.0, max: 10.0, unit: "dB" },
    },
    "pic.photodetector": {
      length_um: { min: 5, max: 50, unit: "\u03BCm" },
      wavelength_nm: { min: 1260, max: 1620, unit: "nm" },
    },
    "pic.ring": {
      insertion_loss_db: { min: 0.1, max: 3.0, unit: "dB" },
    },
    "pic.phase_shifter": {
      insertion_loss_db: { min: 0.02, max: 0.5, unit: "dB" },
    },
    "pic.heater": {
      length_um: { min: 20, max: 1000, unit: "\u03BCm" },
      power_mW: { min: 0, max: 100, unit: "mW" },
    },
    "pic.mmi": {
      insertion_loss_db: { min: 0.1, max: 1.0, unit: "dB" },
    },
    "pic.crossing": {
      insertion_loss_db: { min: 0.005, max: 0.2, unit: "dB" },
      crosstalk_db: { min: -60, max: -20, unit: "dB" },
    },
    "pic.ssc": {
      tip_width_nm: { min: 80, max: 300, unit: "nm" },
    },
    "pic.awg": {
      n_channels: { min: 2, max: 40 },
      channel_spacing_nm: { min: 0.4, max: 6.4, unit: "nm" },
      insertion_loss_db: { min: 1.0, max: 8.0, unit: "dB" },
    },
    "pic.grating_coupler": {
      insertion_loss_db: { min: 1.5, max: 6.0, unit: "dB" },
    },
    "pic.edge_coupler": {
      insertion_loss_db: { min: 0.5, max: 4.0, unit: "dB" },
    },
    "pic.y_branch": {
      insertion_loss_db: { min: 0.05, max: 0.5, unit: "dB" },
    },
  },
  generic_sin: {
    "pic.waveguide": {
      length_um: { min: 1, max: 100000, unit: "\u03BCm" },
      loss_db_per_cm: { min: 0.05, max: 1.0, unit: "dB/cm" },
    },
    "pic.coupler": {
      coupling_ratio: { min: 0.01, max: 0.99 },
      insertion_loss_db: { min: 0.02, max: 0.5, unit: "dB" },
    },
    "pic.mmi": {
      insertion_loss_db: { min: 0.05, max: 0.5, unit: "dB" },
    },
    "pic.ring": {
      insertion_loss_db: { min: 0.05, max: 1.0, unit: "dB" },
    },
    "pic.awg": {
      n_channels: { min: 2, max: 64 },
      channel_spacing_nm: { min: 0.2, max: 6.4, unit: "nm" },
      insertion_loss_db: { min: 0.5, max: 4.0, unit: "dB" },
    },
    "pic.grating_coupler": {
      insertion_loss_db: { min: 2.0, max: 8.0, unit: "dB" },
    },
    "pic.edge_coupler": {
      insertion_loss_db: { min: 0.3, max: 2.0, unit: "dB" },
    },
  },
  imec_isipp50g: {
    "pic.waveguide": {
      length_um: { min: 1, max: 30000, unit: "\u03BCm" },
      loss_db_per_cm: { min: 1.0, max: 3.0, unit: "dB/cm" },
    },
    "pic.mzm": {
      phase_shifter_length_mm: { min: 1.0, max: 5.0, unit: "mm" },
      V_pi_L_pi_Vcm: { min: 1.5, max: 2.5, unit: "V\u00B7cm" },
      insertion_loss_db: { min: 3.0, max: 7.0, unit: "dB" },
    },
    "pic.photodetector": {
      length_um: { min: 10, max: 40, unit: "\u03BCm" },
      wavelength_nm: { min: 1270, max: 1590, unit: "nm" },
    },
    "pic.coupler": {
      coupling_ratio: { min: 0.01, max: 0.99 },
      insertion_loss_db: { min: 0.1, max: 0.5, unit: "dB" },
    },
    "pic.grating_coupler": {
      insertion_loss_db: { min: 2.0, max: 5.0, unit: "dB" },
    },
    "pic.heater": {
      length_um: { min: 50, max: 500, unit: "\u03BCm" },
      power_mW: { min: 0, max: 60, unit: "mW" },
    },
  },
};
