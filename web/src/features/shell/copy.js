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
    "PhotonTrust turns a QKD link run into reviewable reliability evidence: simulate it, compare it, certify it, and export the decision packet.",
  startHere:
    "Pick the shortest path to the artifact you need today. Guided mode keeps the QKD reliability path opinionated; power mode exposes the broader engineering surface only when you need it.",
  quickActions: {
    guidedQkd: "Start guided QKD run",
    guidedPic: "Open PIC layout path",
    compareRuns: "Review existing runs",
    investorDemo: "Open trust-story demo",
  },
  startingPaths: [
    {
      id: "qkd",
      title: "Run a trusted QKD scenario",
      description: "Start with the shortest guided QKD path and produce a fresh run manifest plus reliability evidence.",
      artifact: "Ends with a manifest and reliability card",
      duration: "About 5 min",
      action: "guidedQkd",
    },
    {
      id: "compare",
      title: "Review a candidate against baseline",
      description: "Jump directly to the run registry, load two runs, and explain the delta that matters for promotion.",
      artifact: "Ends with a decision delta",
      duration: "About 2 min",
      action: "compareRuns",
    },
    {
      id: "pic",
      title: "Open the advanced PIC path",
      description: "Use the PIC workflow when the goal is layout, optimization, or fabrication evidence beyond the front-door QKD wedge.",
      artifact: "Ends with layout and verification artifacts",
      duration: "Advanced path",
      action: "guidedPic",
    },
  ],
  capabilityCards: [
    {
      id: "qkd",
      title: "Simulate a QKD link",
      description: "Build a first trusted run, inspect key-rate outputs, and move directly into compare-ready evidence.",
      outcome: "Produces run manifests, cards, and compare-ready outputs.",
    },
    {
      id: "pic",
      title: "Use the advanced PIC flow",
      description: "Use the PIC surface to build layout artifacts, emit a GDS file, and run KLayout-based extraction and DRC-lite checks when you need the broader photonics workflow.",
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
