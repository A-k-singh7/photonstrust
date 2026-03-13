export const PRODUCT_STAGE_ITEMS = [
  { id: "build", label: "Build" },
  { id: "run", label: "Run" },
  { id: "validate", label: "Validate" },
  { id: "compare", label: "Compare" },
  { id: "certify", label: "Certify" },
  { id: "export", label: "Export" },
];

export const PRODUCT_STAGE_ROUTES = {
  build: { mode: "graph", tab: "inspect", subtitle: "Design the graph and set trusted inputs." },
  run: { mode: "graph", tab: "run", subtitle: "Execute and inspect run outcomes." },
  validate: { mode: "graph", tab: "compile", subtitle: "Review assumptions and quality checks." },
  compare: { mode: "runs", tab: "diff", subtitle: "Compare candidates against baseline." },
  certify: { mode: "runs", tab: "manifest", subtitle: "Inspect trust posture and approvals." },
  export: { mode: "runs", tab: "manifest", subtitle: "Generate meeting-ready decision evidence." },
};

export const PRODUCT_COPY = {
  valueProposition:
    "PhotonTrust helps teams simulate, compare, certify, and export trusted quantum outcomes with reviewable evidence.",
  startHere:
    "Choose the job you want to complete first. Guided paths hide complexity; power mode exposes the full engineering surface when you need it.",
  quickActions: {
    guidedQkd: "Guided QKD quickstart",
    guidedPic: "Guided PIC quickstart",
    compareRuns: "Open compare lab",
    investorDemo: "Mark investor demo checkpoint",
  },
  capabilityCards: [
    {
      id: "qkd",
      title: "Simulate a QKD link",
      description: "Build a first trusted run, inspect key-rate outputs, and move directly into compare-ready evidence.",
      outcome: "Produces run manifests, cards, and compare-ready outputs.",
    },
    {
      id: "pic",
      title: "Generate PIC layout and GDS",
      description: "Use the PIC flow to build layout artifacts, emit a GDS file, and run KLayout-based extraction and DRC-lite checks.",
      outcome: "Produces layout.gds, ports, routes, and KLayout packs.",
    },
    {
      id: "compare",
      title: "Compare candidates and explain the delta",
      description: "Frame one run as the baseline, another as the candidate, and review the changes that matter for decision-making.",
      outcome: "Produces semantic diff summaries and review context.",
    },
    {
      id: "certify",
      title: "Certify and export the decision",
      description: "Review blockers, approvals, packets, and published evidence in one trust workflow.",
      outcome: "Produces decision packets, publishable bundles, and verification results.",
    },
  ],
};

export function stageLabel(stage) {
  const found = PRODUCT_STAGE_ITEMS.find((item) => item.id === String(stage || ""));
  return found ? found.label : "Build";
}

export function stageSubtitle(stage) {
  const key = String(stage || "build");
  return PRODUCT_STAGE_ROUTES[key]?.subtitle || PRODUCT_STAGE_ROUTES.build.subtitle;
}
