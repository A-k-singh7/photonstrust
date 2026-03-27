export const COMPONENT_INFO = {
  "pic.grating_coupler": {
    physics: "Diffractive coupling between waveguide mode and free-space/fiber mode. Period \u039b = \u03bb/(n_eff - n_clad\u00b7sin(\u03b8)).",
    keyParams: [
      { name: "insertion_loss_db", typical: "2\u20135 dB", notes: "Depends on design optimization" },
    ],
    applications: ["Fiber-to-chip coupling", "Wafer-level testing", "Vertical I/O"],
    foundryNotes: "Available in all silicon photonics PDKs. Bandwidth ~30-40nm.",
    references: ["Taillaert et al., Jpn J Appl Phys 2006"],
  },
  "pic.edge_coupler": {
    physics: "Evanescent mode expansion via inverse taper for mode-matching to fiber.",
    keyParams: [
      { name: "insertion_loss_db", typical: "1\u20133 dB", notes: "Lower than grating couplers" },
    ],
    applications: ["High-performance fiber coupling", "Broadband I/O", "Multi-chip assembly"],
    foundryNotes: "Requires edge facet preparation. Compatible with V-groove arrays.",
    references: ["Almeida et al., Opt Lett 2003"],
  },
  "pic.waveguide": {
    physics: "Total internal reflection in high-index-contrast strip/rib waveguide. Propagation loss dominated by sidewall scattering.",
    keyParams: [
      { name: "length_um", typical: "10\u201310000 \u03bcm", notes: "Layout dependent" },
      { name: "loss_db_per_cm", typical: "1\u20133 dB/cm", notes: "Si: ~2 dB/cm, SiN: ~0.1 dB/cm" },
    ],
    applications: ["Interconnect", "Delay lines", "Routing"],
    foundryNotes: "Standard in all platforms. Width 450-500nm for single-mode Si.",
    references: ["Bogaerts et al., Laser Photon Rev 2012"],
  },
  "pic.phase_shifter": {
    physics: "Thermo-optic or electro-optic index change. Si thermo-optic: dn/dT \u2248 1.86\u00d710\u207b\u2074 /K.",
    keyParams: [
      { name: "phase_rad", typical: "0\u20132\u03c0", notes: "Tunable" },
      { name: "insertion_loss_db", typical: "0.05\u20130.2 dB", notes: "Minimal for thermo-optic" },
    ],
    applications: ["MZI tuning", "Phase correction", "Programmable circuits"],
    foundryNotes: "TiN heaters standard in Si photonics. Power: ~25 mW/\u03c0.",
    references: ["Harris et al., Optica 2018"],
  },
  "pic.isolator_2port": {
    physics: "Non-reciprocal transmission via magneto-optic effect or spatio-temporal modulation.",
    keyParams: [
      { name: "isolation_db", typical: "20\u201340 dB", notes: "Critical for laser protection" },
      { name: "insertion_loss_db", typical: "0.5\u20133 dB", notes: "Higher than reciprocal components" },
    ],
    applications: ["Laser protection", "Feedback suppression", "Amplifier stages"],
    foundryNotes: "Not standard in most Si PDKs. Bonded Ce:YIG or active approaches.",
    references: ["Huang et al., Optica 2017"],
  },
  "pic.ring": {
    physics: "Whispering gallery mode resonance. FSR = \u03bb\u00b2/(n_g\u00b72\u03c0R). Q factor limited by coupling and loss.",
    keyParams: [
      { name: "insertion_loss_db", typical: "0.2\u20131 dB", notes: "Through-port at off-resonance" },
    ],
    applications: ["Wavelength filtering", "Modulation", "Sensing", "Delay"],
    foundryNotes: "Sensitive to fabrication variation. Thermal tuning typically needed.",
    references: ["Bogaerts et al., Laser Photon Rev 2012"],
  },
  "pic.coupler": {
    physics: "Evanescent coupling between adjacent waveguides. \u03ba = sin\u00b2(C\u00b7L) where C is coupling coefficient.",
    keyParams: [
      { name: "coupling_ratio", typical: "0.5 (3 dB)", notes: "Gap and length dependent" },
      { name: "insertion_loss_db", typical: "0.1\u20130.3 dB", notes: "Excess loss" },
    ],
    applications: ["Power splitting", "MZI building block", "Tap monitoring"],
    foundryNotes: "Standard. Gap ~200nm for Si, ~400nm for SiN.",
    references: ["Yariv, IEEE JQE 1973"],
  },
  "pic.mmi": {
    physics: "Self-imaging in a multimode waveguide. Beat length L_\u03c0 = 4\u00b7n_eff\u00b7W\u00b2/(3\u00b7\u03bb).",
    keyParams: [
      { name: "insertion_loss_db", typical: "0.2\u20130.5 dB", notes: "Lower for wider MMI" },
      { name: "imbalance_db", typical: "< 0.3 dB", notes: "Process-dependent" },
    ],
    applications: ["Power splitting", "MZI building block", "Coherent mixing"],
    foundryNotes: "Standard in all silicon photonics PDKs. SiN variants available.",
    references: ["Soldano & Pennings, JLT 1995"],
  },
  "pic.y_branch": {
    physics: "Adiabatic mode evolution splitting. Symmetric Y-junction divides power equally.",
    keyParams: [
      { name: "insertion_loss_db", typical: "0.1\u20130.3 dB", notes: "Excess loss" },
      { name: "splitting_ratio", typical: "0.5", notes: "Fixed by symmetry" },
    ],
    applications: ["Power splitting", "Interferometer arms", "Fan-out"],
    foundryNotes: "Simple geometry, wide process window. Standard in all PDKs.",
    references: ["Izutsu et al., IEEE JQE 1982"],
  },
  "pic.crossing": {
    physics: "Mode expansion at intersection suppresses coupling. Optimized with subwavelength taper or MMI.",
    keyParams: [
      { name: "insertion_loss_db", typical: "0.01\u20130.05 dB", notes: "Per crossing" },
      { name: "crosstalk_db", typical: "< -35 dB", notes: "Critical for dense layouts" },
    ],
    applications: ["Waveguide routing", "Mesh networks", "Switch fabrics"],
    foundryNotes: "Available in most Si PDKs. SiN crossings have lower loss.",
    references: ["Bogaerts et al., Opt Lett 2007"],
  },
  "pic.mzm": {
    physics: "Soref-Bennett electro-refractive effect in PN-junction phase shifters. \u0394n = -(8.8e-22\u00b7\u0394Ne + 8.5e-18\u00b7\u0394Nh^0.8).",
    keyParams: [
      { name: "V_pi_L_pi_Vcm", typical: "1.5\u20133.0 V\u00b7cm", notes: "Lower = more efficient" },
      { name: "insertion_loss_db", typical: "3\u20137 dB", notes: "Dominated by doping loss" },
    ],
    applications: ["Data modulation", "Variable attenuation", "Pulse carving"],
    foundryNotes: "Requires PN/PIN junction process. GF 45CLO: V_\u03c0L_\u03c0 \u2248 2.0 V\u00b7cm.",
    references: ["Soref & Bennett, IEEE JQE 1987"],
  },
  "pic.photodetector": {
    physics: "Ge-on-Si absorption. Responsivity R = (\u03b7\u00b7q\u00b7\u03bb)/(h\u00b7c). Bandwidth limited by RC and transit time.",
    keyParams: [
      { name: "length_um", typical: "10\u201340 \u03bcm", notes: "Longer = higher responsivity, lower BW" },
      { name: "eta_coupling", typical: "0.8\u20130.95", notes: "Waveguide-to-Ge coupling" },
    ],
    applications: ["Optical detection", "Monitoring", "Coherent reception"],
    foundryNotes: "Standard in Si photonics. Dark current ~1-10 nA at -1V.",
    references: ["Vivien et al., Opt Express 2012"],
  },
  "pic.awg": {
    physics: "Phased array of waveguides with path length differences. Rowland circle geometry for focusing.",
    keyParams: [
      { name: "n_channels", typical: "4\u201340", notes: "Common: 4, 8, 16, 32" },
      { name: "channel_spacing_nm", typical: "0.8\u20133.2 nm", notes: "ITU grid compatible" },
      { name: "insertion_loss_db", typical: "2\u20135 dB", notes: "Including slab losses" },
    ],
    applications: ["WDM demux/mux", "Spectral analysis", "Wavelength routing"],
    foundryNotes: "Large footprint (~mm\u00b2). SiN preferred for low loss. Temperature sensitive.",
    references: ["Smit & Van Dam, IEEE JSTQE 1996"],
  },
  "pic.heater": {
    physics: "Resistive heating changes refractive index. Si: dn/dT = 1.86\u00d710\u207b\u2074/K. P_\u03c0 \u221d \u03bb/(2\u00b7L\u00b7dn/dT).",
    keyParams: [
      { name: "power_mW", typical: "0\u201350 mW", notes: "Typical P_\u03c0 ~ 25 mW" },
      { name: "length_um", typical: "50\u2013500 \u03bcm", notes: "Longer = lower P_\u03c0" },
    ],
    applications: ["Phase tuning", "Resonance alignment", "Switch actuation"],
    foundryNotes: "TiN or doped-Si heaters. Thermal crosstalk ~5-10% to adjacent waveguides.",
    references: ["Jacques et al., Opt Express 2019"],
  },
  "pic.ssc": {
    physics: "Inverse taper expands mode from ~0.5 \u03bcm to ~10 \u03bcm for fiber mode matching. Coupling ~ overlap integral.",
    keyParams: [
      { name: "tip_width_nm", typical: "80\u2013200 nm", notes: "Narrower = better coupling, harder fab" },
      { name: "fiber_mfd_um", typical: "5\u201310 \u03bcm", notes: "SMF-28: 10.4 \u03bcm" },
    ],
    applications: ["Fiber-chip coupling", "Die-to-die coupling", "Packaging"],
    foundryNotes: "Requires deep etch and sometimes SiO2 upper cladding mode converter.",
    references: ["Almeida et al., Opt Lett 2003"],
  },
  "pic.touchstone_2port": {
    physics: "Frequency-domain S-parameter model loaded from industry-standard Touchstone file.",
    keyParams: [
      { name: "touchstone_path", typical: "*.s2p", notes: "Touchstone v1/v2 format" },
    ],
    applications: ["Measured data import", "PDK model integration", "Co-simulation"],
    foundryNotes: "Compatible with all foundry-provided S-parameter models.",
    references: ["IBIS Open Forum, Touchstone Spec v2.0"],
  },
  "pic.touchstone_nport": {
    physics: "N-port S-parameter network from Touchstone file. Supports arbitrary port count.",
    keyParams: [
      { name: "n_ports", typical: "2\u201316", notes: "Must match file" },
      { name: "touchstone_path", typical: "*.snp", notes: "Touchstone format" },
    ],
    applications: ["Complex device modeling", "Multi-port characterization"],
    foundryNotes: "Port ordering must match file convention.",
    references: ["IBIS Open Forum, Touchstone Spec v2.0"],
  },
};
