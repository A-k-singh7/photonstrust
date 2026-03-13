import { chromium, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildRun, buildRunManifest, installMockApi } from "./mockProjectApi.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const assetDir = path.join(repoRoot, "docs", "assets");
const baseUrl = "http://127.0.0.1:5175";

function picGraph(title = "PIC GDS Workspace") {
  return {
    schema_version: "0.1",
    graph_id: "ui_pic_layout",
    profile: "pic_circuit",
    metadata: {
      title,
      description: "PIC design workspace for layout and GDS export.",
      created_at: "2026-03-13",
    },
    circuit: {
      id: "ui_pic_layout",
      wavelength_nm: 1550,
      sweep_nm: [1540, 1550, 1560],
      layout: "mzi",
    },
    nodes: [
      { id: "src_1", kind: "pic.source", label: "Laser", params: {}, ui: { position: { x: 60, y: 120 } } },
      { id: "split_1", kind: "pic.coupler", label: "Splitter", params: {}, ui: { position: { x: 260, y: 120 } } },
      { id: "phase_1", kind: "pic.phase_shifter", label: "Phase", params: { phase_rad: 1.57 }, ui: { position: { x: 470, y: 70 } } },
      { id: "delay_1", kind: "pic.waveguide", label: "Delay", params: {}, ui: { position: { x: 470, y: 180 } } },
      { id: "comb_1", kind: "pic.coupler", label: "Combiner", params: {}, ui: { position: { x: 700, y: 120 } } },
      { id: "det_1", kind: "pic.detector", label: "Output", params: {}, ui: { position: { x: 920, y: 120 } } },
    ],
    edges: [
      { id: "e1", from: "src_1", to: "split_1", kind: "optical" },
      { id: "e2", from: "split_1", to: "phase_1", kind: "optical" },
      { id: "e3", from: "split_1", to: "delay_1", kind: "optical" },
      { id: "e4", from: "phase_1", to: "comb_1", kind: "optical" },
      { id: "e5", from: "delay_1", to: "comb_1", kind: "optical" },
      { id: "e6", from: "comb_1", to: "det_1", kind: "optical" },
    ],
  };
}

async function screenshotWithMock(name, options, action) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1180 } });
  const page = await context.newPage();

  await page.addInitScript((storage) => {
    localStorage.clear();
    sessionStorage.clear();
    Object.entries(storage || {}).forEach(([key, value]) => {
      localStorage.setItem(key, value);
    });
  }, options.localStorage || {});

  await installMockApi(page, options.mock || {});
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  if (action) await action(page);
  await page.screenshot({ path: path.join(assetDir, name), fullPage: true });

  await context.close();
  await browser.close();
}

async function main() {
  await screenshotWithMock("ui-landing.png", {}, null);

  await screenshotWithMock(
    "ui-decision-review.png",
    {
      localStorage: {
        pt_show_landing: "0",
        pt_project_id: "pilot_demo",
      },
      mock: {
        runs: [
          buildRun("pilot_demo", "baseline12345678", "2026-03-13T10:00:00Z"),
          buildRun("pilot_demo", "candidate87654321", "2026-03-13T11:00:00Z"),
        ],
        runManifests: {
          baseline12345678: { ...buildRunManifest("pilot_demo", "baseline12345678"), input: { project_id: "pilot_demo", protocol_selected: "BB84" } },
          candidate87654321: { ...buildRunManifest("pilot_demo", "candidate87654321"), input: { project_id: "pilot_demo", protocol_selected: "BBM92" } },
        },
        workspace: {
          stage: "compare",
          mode: "runs",
          active_right_tab: "diff",
          user_mode: "reviewer",
          selected_run_id: "candidate87654321",
        },
      },
    },
    async (page) => {
      const panel = page.locator('section[aria-label="Week 6 compare lab panel"]');
      await panel.getByRole("combobox", { name: "Baseline run", exact: true }).selectOption("baseline12345678");
      await panel.getByRole("combobox", { name: "Candidate run", exact: true }).selectOption("candidate87654321");
      await panel.getByRole("button", { name: "Compare baseline vs candidate", exact: true }).click();
      await page.waitForTimeout(700);
    },
  );

  await screenshotWithMock(
    "ui-certification.png",
    {
      localStorage: {
        pt_show_landing: "0",
        pt_project_id: "pilot_demo",
      },
      mock: {
        workspace: {
          stage: "certify",
          mode: "runs",
          active_right_tab: "manifest",
          user_mode: "reviewer",
          selected_run_id: "abcdef12345678",
        },
      },
    },
    async (page) => {
      const cert = page.locator('section[aria-label="Certification workspace"]');
      await cert.getByRole("button", { name: "Publish shareable packet", exact: true }).click();
      await page.waitForTimeout(600);
      await cert.getByRole("button", { name: "Verify published packet", exact: true }).click();
      await page.waitForTimeout(600);
    },
  );

  await screenshotWithMock(
    "ui-pic-gds-layout.png",
    {
      localStorage: {
        pt_show_landing: "0",
        pt_project_id: "pic_demo",
        pt_experience_mode: "power",
      },
      mock: {
        projectId: "pic_demo",
        title: "PIC GDS Workspace",
        workspace: {
          stage: "build",
          mode: "graph",
          active_right_tab: "layout",
          user_mode: "builder",
          graph: picGraph(),
        },
      },
    },
    async (page) => {
      await page.locator("header.ptTopbar label").filter({ hasText: "Profile" }).first().locator("select").selectOption("pic_circuit");
      await page.getByRole("tab", { name: "GDS/Layout", exact: true }).click();
      await page.waitForTimeout(800);
    },
  );

  console.log("Captured documentation assets in docs/assets");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
