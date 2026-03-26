# Glossary

Definitions of key terms used in PhotonsTrust and the broader field of quantum
key distribution and photonic engineering.

---

- **APD** -- Avalanche Photodiode. A semiconductor photodetector that exploits
  avalanche multiplication of photo-generated carriers to detect single photons.
  Common materials include silicon (Si-APD) for visible/NIR and InGaAs for telecom wavelengths.

- **AWG** -- Arrayed Waveguide Grating. A planar lightwave circuit that
  separates or combines multiple wavelengths using an array of waveguides with
  carefully designed path-length differences. Used in WDM-compatible QKD systems.

- **BB84** -- The first QKD protocol, proposed by Bennett and Brassard in 1984.
  Uses four quantum states in two conjugate bases (rectilinear and diagonal) to
  establish a shared secret key. PhotonsTrust implements the decoy-state variant.

- **BBM92** -- An entanglement-based QKD protocol proposed by Bennett, Brassard,
  and Mermin in 1992. Both parties measure halves of entangled photon pairs. Also
  referred to as E91 (Ekert 1991) in contexts emphasizing Bell-inequality testing.

- **Bell State** -- One of four maximally entangled two-qubit quantum states.
  Bell states form the basis for entanglement-based QKD protocols like BBM92 and
  for quantum teleportation.

- **CHSH Inequality** -- Clauser-Horne-Shimony-Holt inequality. A Bell-type
  inequality whose violation certifies the presence of quantum entanglement. Used
  in device-independent QKD to verify security without trusting the devices.

- **Cn2** -- Refractive-index structure constant. A measure of atmospheric
  optical turbulence strength, typically expressed in units of m^(-2/3). Higher
  values indicate stronger turbulence and more beam degradation.

- **CV-QKD** -- Continuous-Variable QKD. Encodes information in the amplitude
  and phase quadratures of coherent or squeezed states. Detected using homodyne
  or heterodyne receivers built from standard telecom components.

- **Dark Count** -- A false detection event caused by thermal excitation,
  tunneling, or electronic noise in a single-photon detector. Dark counts set a
  noise floor that limits the maximum QKD link distance.

- **Decoy State** -- A technique where the sender randomly varies the intensity
  of transmitted pulses to detect photon-number-splitting attacks. Essential for
  practical BB84 implementations using weak coherent pulses.

- **DI-QKD** -- Device-Independent QKD. A protocol whose security proof does not
  rely on any assumptions about the internal workings of the quantum devices. Provides the
  strongest security guarantee but currently works only at short distances.

- **DRC** -- Design Rule Check. Automated verification that a photonic
  integrated circuit layout meets the manufacturing constraints of a specific
  foundry process.

- **Entanglement** -- A quantum correlation between two or more particles where
  the quantum state of each particle cannot be described independently. Entangled
  photon pairs are the resource for BBM92, MDI-QKD, and DI-QKD protocols.

- **Error Correction** -- Also called information reconciliation. The classical
  post-processing step where Alice and Bob correct discrepancies in their raw key
  strings using public communication without revealing the key.

- **Fidelity** -- A measure of how close a quantum state is to an ideal target
  state. F=1 means a perfect match; F=0.5 for a qubit indicates a completely
  mixed state.

- **Fried Parameter** -- A measure of atmospheric coherence length (r0),
  characterizing the spatial scale over which wavefront distortions from
  turbulence are correlated. Larger values mean better seeing conditions for
  free-space QKD.

- **FSO** -- Free-Space Optical. Communication using optical beams transmitted
  through the atmosphere (or vacuum) rather than through optical fibers.

- **GDS** -- Graphic Data System (GDSII). The standard binary file format for
  integrated circuit and photonic circuit layout data. Used for mask fabrication.

- **GEO** -- Geostationary Earth Orbit. A circular orbit at approximately
  35 786 km altitude where the satellite appears stationary relative to the
  ground. QKD from GEO is extremely challenging due to high free-space loss.

- **Heterodyne Detection** -- A coherent detection scheme that simultaneously
  measures both quadratures of an optical field by mixing it with a local
  oscillator at a slightly different frequency. Used in some CV-QKD
  implementations.

- **Homodyne Detection** -- A coherent detection scheme that measures one
  quadrature of an optical field by mixing it with a local oscillator at the same
  frequency. The primary detection method for CV-QKD.

- **InGaAs** -- Indium Gallium Arsenide. A III-V semiconductor material used in
  single-photon avalanche detectors (SPADs) sensitive at telecom wavelengths
  (1310 nm and 1550 nm). Typically gated to manage high dark-count rates.

- **Information Reconciliation** -- See Error Correction. The step where Alice
  and Bob use classical communication to agree on an identical key string from
  their correlated but imperfect raw data.

- **LEO** -- Low Earth Orbit. Orbits at altitudes between approximately 200 km
  and 2000 km. LEO satellites offer lower free-space loss for QKD but have
  limited pass durations (typically 5-10 minutes).

- **MDI-QKD** -- Measurement-Device-Independent QKD. A protocol where both users
  send quantum states to an untrusted central relay that performs a Bell-state
  measurement. Immune to all detector side-channel attacks.

- **MMI** -- Multi-Mode Interference coupler. A photonic component that splits or
  combines light using interference in a wide multimode waveguide section. A key
  building block in photonic integrated circuits.

- **Mode-Pairing** -- A technique used in asynchronous MDI-QKD (AMDI-QKD) where
  successful detection events are paired after measurement to form key bits,
  relaxing the requirement for precise timing synchronization.

- **MZI** -- Mach-Zehnder Interferometer. A two-arm interferometer that splits
  light, sends it through paths of different lengths or phase shifts, and
  recombines it. Used for optical switching, modulation, and phase encoding in QKD.

- **MZM** -- Mach-Zehnder Modulator. An electro-optic modulator based on the MZI
  structure. Applies an electric field to one or both arms to control the output
  intensity or phase.

- **OTDR** -- Optical Time-Domain Reflectometer. An instrument that characterizes
  optical fiber by injecting pulses and analyzing backscattered light. Useful for
  detecting fiber taps or splices that could indicate eavesdropping.

- **PDK** -- Process Design Kit. A collection of design rules, component models,
  and layout cells provided by a photonics foundry for a specific fabrication
  process. PhotonsTrust supports generic and foundry-specific PDKs.

- **PDE** -- Photon Detection Efficiency. The probability that a photon arriving
  at a detector produces a registered detection event. A critical parameter for
  QKD performance.

- **Phase Matching** -- In the context of TF-QKD and PM-QKD, a technique where
  Alice and Bob pre-compensate the random phase of their transmitted pulses so
  that single-photon interference at the central node is constructive.

- **PIC** -- Photonic Integrated Circuit. An optical circuit fabricated on a
  chip, typically on silicon, InP, or silicon-nitride platforms. PICs can integrate
  sources, modulators, filters, and detectors for compact QKD systems.

- **PLOB Bound** -- Pirandola-Laurenza-Ottaviani-Banchi bound. The fundamental
  capacity limit for point-to-point quantum communication over a lossy channel
  without quantum repeaters: R <= -log2(1-eta), where eta is the channel
  transmittance. TF-QKD family protocols can surpass this bound.

- **Privacy Amplification** -- A classical post-processing step that compresses
  the error-corrected key using universal hash functions to eliminate any partial
  information an eavesdropper may have gained.

- **QBER** -- Quantum Bit Error Rate. The fraction of detected bits that are
  incorrect after basis reconciliation. The QBER must remain below a protocol-
  dependent threshold (e.g., ~11% for BB84) for positive key generation.

- **QKD** -- Quantum Key Distribution. A family of protocols that use quantum
  mechanics to establish shared secret keys between two parties with
  information-theoretic security guarantees.

- **Scintillation** -- Rapid fluctuations in the intensity of an optical beam
  propagating through a turbulent atmosphere. Quantified by the scintillation
  index (variance of intensity normalized by mean intensity squared).

- **Sifting** -- The classical post-processing step where Alice and Bob publicly
  compare their measurement basis choices and discard events where they used
  different bases (in prepare-and-measure protocols like BB84).

- **SKR** -- Secure Key Rate. The rate at which secret key bits can be generated
  after all post-processing steps (sifting, error correction, privacy
  amplification). Usually expressed in bits per second (bps).

- **SNS** -- Sending-or-Not-Sending. A variant of TF-QKD where each user
  randomly decides whether to send a coherent pulse or vacuum in each time window.
  The protocol determines which events contribute to key generation after
  measurement.

- **SNSPD** -- Superconducting Nanowire Single-Photon Detector. A high-
  performance detector that operates at cryogenic temperatures (~1-3 K) and
  achieves >90% detection efficiency, <100 ps jitter, and very low dark counts.

- **SPDC** -- Spontaneous Parametric Down-Conversion. A nonlinear optical
  process where a pump photon splits into two lower-energy photons (signal and
  idler) in a nonlinear crystal. A primary source of entangled photon pairs for
  QKD.

- **Squeezed State** -- A quantum state of light where the noise in one
  quadrature is reduced below the vacuum level at the expense of increased noise
  in the conjugate quadrature. Used in advanced CV-QKD protocols.

- **SSC** -- Spot-Size Converter. A photonic component that gradually transitions
  the optical mode between the small mode of an on-chip waveguide and the larger
  mode of an optical fiber, minimizing coupling loss.

- **TF-QKD** -- Twin-Field QKD. A protocol that overcomes the PLOB bound by
  having two remote users send weak coherent pulses to a central node where
  single-photon interference is measured. Enables key generation at distances
  beyond 500 km.

- **TGW Bound** -- Takeuchi-Guha-Wilde bound. A capacity bound for quantum
  communication networks that generalizes the PLOB bound to channels with
  intermediate repeater nodes.

- **TRL** -- Technology Readiness Level. A scale from 1 (basic concept) to 9
  (operational system) indicating the maturity of a technology. Used in
  PhotonsTrust to characterize the readiness of QKD components and systems.

- **Walker Constellation** -- A satellite constellation design pattern that
  distributes satellites evenly across multiple orbital planes with specified
  phase offsets. Used by PhotonsTrust to model satellite QKD networks.

- **WDM** -- Wavelength Division Multiplexing. A technique that combines
  multiple optical signals at different wavelengths onto a single fiber.
  QKD signals can coexist with classical data channels using WDM.
